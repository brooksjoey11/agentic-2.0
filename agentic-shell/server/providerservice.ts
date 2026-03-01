import { db } from './db.js';
import { apiProviders, providerApiKeys, providerModels } from '../drizzle/schema.js';
import { eq, and } from 'drizzle-orm';
import { encrypt, decrypt } from './encryption.js';
import { logger } from './logger.js';
import axios, { AxiosInstance } from 'axios';
import { config } from './configService.js';

export class ProviderService {
  private clients: Map<string, AxiosInstance> = new Map();
  
  async getProvider(providerId: string) {
    const provider = await db.query.apiProviders.findFirst({
      where: and(
        eq(apiProviders.id, providerId),
        eq(apiProviders.isEnabled, true)
      ),
      with: {
        apiKeys: true,
      },
    });
    
    if (!provider) {
      throw new Error(`Provider not found: ${providerId}`);
    }
    
    return provider;
  }
  
  async getClient(providerId: string): Promise<AxiosInstance> {
    if (this.clients.has(providerId)) {
      return this.clients.get(providerId)!;
    }
    
    const provider = await this.getProvider(providerId);
    const apiKey = provider.apiKeys[0]; // Use first active key
    
    if (!apiKey) {
      throw new Error(`No API key for provider: ${provider.name}`);
    }
    
    // Decrypt API key
    const decryptedKey = decrypt(apiKey.encryptedKey, apiKey.keyIv, apiKey.keyAuth);
    
    // Create axios client with auth headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    switch (provider.authType) {
      case 'bearer':
        headers['Authorization'] = `Bearer ${decryptedKey}`;
        break;
      case 'api-key':
        headers['X-API-Key'] = decryptedKey;
        break;
      case 'basic':
        headers['Authorization'] = `Basic ${Buffer.from(decryptedKey).toString('base64')}`;
        break;
      default:
        if (provider.authHeaders) {
          Object.entries(provider.authHeaders).forEach(([key, value]) => {
            headers[key] = value.replace('{{apiKey}}', decryptedKey);
          });
        }
    }
    
    const client = axios.create({
      baseURL: provider.baseUrl,
      timeout: provider.timeout,
      headers,
    });
    
    // Add response interceptor for logging
    client.interceptors.response.use(
      (response) => {
        // Update last used timestamp
        db.update(providerApiKeys)
          .set({ lastUsed: new Date() })
          .where(eq(providerApiKeys.id, apiKey.id))
          .catch(err => logger.error('Failed to update key last used', err));
        
        return response;
      },
      (error) => {
        logger.error({ error, provider: provider.name }, 'Provider request failed');
        return Promise.reject(error);
      }
    );
    
    this.clients.set(providerId, client);
    return client;
  }
  
  async callLLM({ providerId, modelId, prompt, temperature = 0.7, maxTokens = 2000 }: {
    providerId: string;
    modelId: string;
    prompt: string;
    temperature?: number;
    maxTokens?: number;
  }) {
    const client = await this.getClient(providerId);
    const provider = await this.getProvider(providerId);
    
    // Different providers have different API formats
    let requestBody;
    
    if (provider.name.toLowerCase().includes('openai')) {
      requestBody = {
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
        temperature,
        max_tokens: maxTokens,
      };
    } else if (provider.name.toLowerCase().includes('anthropic')) {
      requestBody = {
        model: modelId,
        prompt: `\n\nHuman: ${prompt}\n\nAssistant:`,
        max_tokens_to_sample: maxTokens,
        temperature,
      };
    } else if (provider.name.toLowerCase().includes('mistral')) {
      requestBody = {
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
        temperature,
        max_tokens: maxTokens,
      };
    } else {
      // Default OpenAI-compatible format
      requestBody = {
        model: modelId,
        messages: [{ role: 'user', content: prompt }],
        temperature,
        max_tokens: maxTokens,
      };
    }
    
    try {
      const response = await client.post('/chat/completions', requestBody);
      
      return {
        content: response.data.choices[0].message.content,
        usage: {
          promptTokens: response.data.usage?.prompt_tokens,
          completionTokens: response.data.usage?.completion_tokens,
          totalTokens: response.data.usage?.total_tokens,
        },
        model: response.data.model,
      };
    } catch (error) {
      logger.error({ error, providerId, modelId }, 'LLM call failed');
      throw new Error(`LLM call failed: ${error.response?.data?.error?.message || error.message}`);
    }
  }
  
  async syncModels(providerId: string) {
    const client = await this.getClient(providerId);
    const provider = await this.getProvider(providerId);
    
    let models = [];
    
    if (provider.name.toLowerCase().includes('openai')) {
      const response = await client.get('/models');
      models = response.data.data;
    } else if (provider.name.toLowerCase().includes('anthropic')) {
      // Anthropic doesn't have a models endpoint, use static list
      models = [
        { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' },
        { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet' },
        { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku' },
        { id: 'claude-2.1', name: 'Claude 2.1' },
        { id: 'claude-2.0', name: 'Claude 2.0' },
        { id: 'claude-instant-1.2', name: 'Claude Instant 1.2' },
      ];
    } else if (provider.name.toLowerCase().includes('mistral')) {
      const response = await client.get('/models');
      models = response.data.data;
    }
    
    // Upsert models
    for (const model of models) {
      await db.insert(providerModels)
        .values({
          providerId,
          modelId: model.id,
          displayName: model.name || model.id,
          contextWindow: model.context_window || 4096,
          maxTokens: model.max_tokens || 2048,
          supportsStreaming: true,
        })
        .onDuplicateKeyUpdate({
          set: {
            displayName: model.name || model.id,
            lastSynced: new Date(),
          },
        });
    }
    
    logger.info(`Synced ${models.length} models for provider ${provider.name}`);
  }
  
  async healthCheck(providerId: string): Promise<boolean> {
    try {
      const client = await this.getClient(providerId);
      await client.get('/health', { timeout: 5000 });
      
      await db.update(apiProviders)
        .set({
          healthStatus: 'healthy',
          lastHealthCheck: new Date(),
        })
        .where(eq(apiProviders.id, providerId));
      
      return true;
    } catch (error) {
      await db.update(apiProviders)
        .set({
          healthStatus: 'unhealthy',
          lastHealthCheck: new Date(),
          errorRate: (error.code === 'ECONNABORTED' ? 100 : 50),
        })
        .where(eq(apiProviders.id, providerId));
      
      return false;
    }
  }
}

export const providerService = new ProviderService();