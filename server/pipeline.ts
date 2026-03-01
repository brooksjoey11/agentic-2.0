import { z } from 'zod';
import { db } from './db.js';
import { pipelineSteps, pipelineResults, codeSubmissions } from '../drizzle/schema.js';
import { eq, and } from 'drizzle-orm';
import { providerService } from './providerService.js';
import { logger } from './logger.js';
import { metrics } from './metrics.js';
import { tracer } from './tracing.js';
import { redis } from './redis.js';
import { config } from './configService.js';

// Pipeline step schemas
export const ForensicResultSchema = z.object({
  bugs: z.array(z.object({
    type: z.string(),
    line: z.number().optional(),
    description: z.string(),
    severity: z.enum(['critical', 'high', 'medium', 'low']),
    suggestion: z.string(),
  })),
  security: z.array(z.object({
    vulnerability: z.string(),
    cwe: z.string().optional(),
    impact: z.string(),
    fix: z.string(),
  })),
  performance: z.array(z.object({
    issue: z.string(),
    impact: z.string(),
    optimization: z.string(),
  })),
  quality: z.array(z.object({
    violation: z.string(),
    recommendation: z.string(),
  })),
  summary: z.string(),
  confidence: z.number().min(0).max(100),
});

export const QualityResultSchema = z.object({
  improvements: z.array(z.string()),
  warnings: z.array(z.string()),
  productionReadiness: z.enum(['ready', 'needs-work', 'reject']),
  confidence: z.number().min(0).max(100),
  summary: z.string(),
});

// Pipeline runner
export class PipelineRunner {
  private submissionId: string;
  private code: string;
  private language: string;
  
  constructor(submissionId: string, code: string, language: string) {
    this.submissionId = submissionId;
    this.code = code;
    this.language = language;
  }
  
  async run(): Promise<void> {
    const span = tracer.startSpan('pipeline.run');
    
    try {
      // Update submission status
      await db.update(codeSubmissions)
        .set({ status: 'processing', startedAt: new Date() })
        .where(eq(codeSubmissions.id, this.submissionId));
      
      // Run pipeline steps sequentially
      const forensicResult = await this.runStep('forensic');
      const rebuiltCode = await this.runRebuilder(forensicResult);
      const qualityResult = await this.runStep('quality', rebuiltCode);
      
      // Update submission with results
      await db.update(codeSubmissions)
        .set({
          status: 'completed',
          forensicResult,
          rebuiltCode,
          qualityResult,
          completedAt: new Date()
        })
        .where(eq(codeSubmissions.id, this.submissionId));
      
      // Cache result in Redis
      await redis.setex(
        `result:${this.submissionId}`,
        config.CACHE_TTL_SECONDS,
        JSON.stringify({ forensicResult, rebuiltCode, qualityResult })
      );
      
      metrics.pipelineSuccess.inc();
      
    } catch (error) {
      logger.error({ error, submissionId: this.submissionId }, 'Pipeline failed');
      
      await db.update(codeSubmissions)
        .set({
          status: 'failed',
          errorMessage: error.message,
          completedAt: new Date()
        })
        .where(eq(codeSubmissions.id, this.submissionId));
      
      metrics.pipelineFailure.inc();
      
      throw error;
      
    } finally {
      span.end();
    }
  }
  
  private async runStep(stepName: string, additionalContext?: string): Promise<any> {
    const span = tracer.startSpan(`pipeline.step.${stepName}`);
    
    try {
      // Get step configuration
      const step = await db.query.pipelineSteps.findFirst({
        where: and(
          eq(pipelineSteps.stepName, stepName),
          eq(pipelineSteps.isActive, true)
        ),
        with: {
          provider: true,
        },
      });
      
      if (!step) {
        throw new Error(`No active configuration for step: ${stepName}`);
      }
      
      // Get provider and model
      const provider = step.provider;
      if (!provider || !provider.isEnabled) {
        throw new Error(`Provider not available for step: ${stepName}`);
      }
      
      // Build prompt
      let prompt = step.systemPrompt
        .replace('{{code}}', this.code)
        .replace('{{language}}', this.language);
      
      if (additionalContext) {
        prompt += `\n\nAdditional context:\n${additionalContext}`;
      }
      
      // Call LLM with retry logic
      const startTime = Date.now();
      let retries = 0;
      let response;
      
      while (retries <= provider.maxRetries) {
        try {
          response = await providerService.callLLM({
            providerId: provider.id,
            modelId: step.modelId,
            prompt,
            temperature: step.temperature / 100,
            maxTokens: step.maxTokens,
          });
          break;
        } catch (error) {
          retries++;
          if (retries > provider.maxRetries) throw error;
          await new Promise(resolve => setTimeout(resolve, 1000 * retries));
        }
      }
      
      const duration = Date.now() - startTime;
      
      // Store result
      await db.insert(pipelineResults).values({
        submissionId: this.submissionId,
        stepName,
        providerId: provider.id,
        modelId: step.modelId,
        prompt,
        response,
        tokensUsed: response.usage?.totalTokens,
        durationMs: duration,
        status: 'success',
      });
      
      // Update metrics
      metrics.llmCalls.labels({ provider: provider.name, step: stepName }).inc();
      metrics.llmTokens.labels({ provider: provider.name }).inc(response.usage?.totalTokens || 0);
      metrics.llmLatency.labels({ provider: provider.name }).observe(duration / 1000);
      
      // Parse response based on step
      if (stepName === 'forensic') {
        return ForensicResultSchema.parse(JSON.parse(response.content));
      } else if (stepName === 'quality') {
        return QualityResultSchema.parse(JSON.parse(response.content));
      } else {
        return response.content;
      }
      
    } finally {
      span.end();
    }
  }
  
  private async runRebuilder(forensicResult: any): Promise<string> {
    const step = await db.query.pipelineSteps.findFirst({
      where: and(
        eq(pipelineSteps.stepName, 'rebuilder'),
        eq(pipelineSteps.isActive, true)
      ),
    });
    
    if (!step) {
      throw new Error('No active rebuilder configuration');
    }
    
    const prompt = step.systemPrompt
      .replace('{{code}}', this.code)
      .replace('{{language}}', this.language)
      .replace('{{forensicResult}}', JSON.stringify(forensicResult, null, 2));
    
    const response = await providerService.callLLM({
      providerId: step.providerId,
      modelId: step.modelId,
      prompt,
      temperature: step.temperature / 100,
      maxTokens: step.maxTokens,
    });
    
    // Extract code from response (assuming it's wrapped in markdown code blocks)
    const codeMatch = response.content.match(/```(?:\w+)?\n([\s\S]*?)```/);
    return codeMatch ? codeMatch[1].trim() : response.content.trim();
  }
}