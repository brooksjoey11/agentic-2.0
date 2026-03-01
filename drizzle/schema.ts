import { mysqlTable, varchar, text, timestamp, int, json, boolean, index, uniqueIndex, foreignKey, primaryKey } from 'drizzle-orm/mysql-core';
import { relations } from 'drizzle-orm';

// ============================================================================
// USERS TABLE
// ============================================================================
export const users = mysqlTable('users', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  email: varchar('email', { length: 255 }).notNull().unique(),
  name: varchar('name', { length: 255 }),
  avatar: varchar('avatar', { length: 512 }),
  role: varchar('role', { length: 20 }).notNull().default('user'),
  googleId: varchar('google_id', { length: 255 }).unique(),
  lastLogin: timestamp('last_login'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
  deletedAt: timestamp('deleted_at'), // Soft delete for GDPR
}, (table) => ({
  emailIdx: uniqueIndex('idx_users_email').on(table.email),
  googleIdIdx: uniqueIndex('idx_users_google_id').on(table.googleId),
  roleIdx: index('idx_users_role').on(table.role),
  createdAtIdx: index('idx_users_created_at').on(table.createdAt),
}));

// ============================================================================
// API PROVIDERS TABLE
// ============================================================================
export const apiProviders = mysqlTable('api_providers', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  name: varchar('name', { length: 100 }).notNull().unique(),
  baseUrl: varchar('base_url', { length: 512 }).notNull(),
  authType: varchar('auth_type', { length: 20 }).notNull().default('bearer'), // bearer, api-key, basic, custom
  authHeaders: json('auth_headers'), // Custom headers JSON
  isEnabled: boolean('is_enabled').notNull().default(true),
  priority: int('priority').notNull().default(0), // Higher priority = used first
  timeout: int('timeout').notNull().default(30000), // ms
  maxRetries: int('max_retries').notNull().default(3),
  rateLimit: int('rate_limit'), // Requests per minute
  metadata: json('metadata'), // Provider-specific metadata
  lastHealthCheck: timestamp('last_health_check'),
  healthStatus: varchar('health_status', { length: 20 }).default('unknown'),
  errorRate: int('error_rate').default(0),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  nameIdx: uniqueIndex('idx_providers_name').on(table.name),
  enabledIdx: index('idx_providers_enabled').on(table.isEnabled),
  priorityIdx: index('idx_providers_priority').on(table.priority),
}));

// ============================================================================
// PROVIDER API KEYS (ENCRYPTED)
// ============================================================================
export const providerApiKeys = mysqlTable('provider_api_keys', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  providerId: varchar('provider_id', { length: 36 }).notNull().references(() => apiProviders.id, { onDelete: 'cascade' }),
  keyName: varchar('key_name', { length: 100 }).notNull().default('default'),
  encryptedKey: text('encrypted_key').notNull(), // AES-256-GCM encrypted
  keyIv: varchar('key_iv', { length: 64 }).notNull(), // Initialization vector
  keyAuth: varchar('key_auth', { length: 64 }).notNull(), // Authentication tag
  lastUsed: timestamp('last_used'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  expiresAt: timestamp('expires_at'),
}, (table) => ({
  providerIdx: index('idx_api_keys_provider').on(table.providerId),
  nameIdx: index('idx_api_keys_name').on(table.keyName),
}));

// ============================================================================
// PROVIDER MODELS (SYNCED FROM PROVIDER)
// ============================================================================
export const providerModels = mysqlTable('provider_models', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  providerId: varchar('provider_id', { length: 36 }).notNull().references(() => apiProviders.id, { onDelete: 'cascade' }),
  modelId: varchar('model_id', { length: 255 }).notNull(), // Provider's model ID (e.g., "gpt-4")
  displayName: varchar('display_name', { length: 255 }),
  contextWindow: int('context_window'),
  maxTokens: int('max_tokens'),
  supportsStreaming: boolean('supports_streaming').default(true),
  supportsFunctions: boolean('supports_functions').default(false),
  inputPrice: int('input_price'), // Per 1M tokens in cents
  outputPrice: int('output_price'), // Per 1M tokens in cents
  isEnabled: boolean('is_enabled').notNull().default(true),
  metadata: json('metadata'),
  lastSynced: timestamp('last_synced').notNull().defaultNow(),
}, (table) => ({
  providerModelIdx: uniqueIndex('idx_provider_model').on(table.providerId, table.modelId),
  enabledIdx: index('idx_models_enabled').on(table.isEnabled),
}));

// ============================================================================
// PIPELINE STEPS CONFIGURATION
// ============================================================================
export const pipelineSteps = mysqlTable('pipeline_steps', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  stepName: varchar('step_name', { length: 50 }).notNull().unique(), // 'forensic', 'rebuilder', 'quality'
  systemPrompt: text('system_prompt').notNull(),
  providerId: varchar('provider_id', { length: 36 }).references(() => apiProviders.id),
  modelId: varchar('model_id', { length: 255 }),
  temperature: int('temperature').default(70), // 0-100
  maxTokens: int('max_tokens'),
  isActive: boolean('is_active').notNull().default(true),
  version: int('version').notNull().default(1),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  stepNameIdx: uniqueIndex('idx_pipeline_step_name').on(table.stepName),
  providerModelIdx: index('idx_pipeline_provider_model').on(table.providerId, table.modelId),
}));

// ============================================================================
// CODE SUBMISSIONS
// ============================================================================
export const codeSubmissions = mysqlTable('code_submissions', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  userId: varchar('user_id', { length: 36 }).notNull().references(() => users.id, { onDelete: 'cascade' }),
  code: text('code').notNull(),
  language: varchar('language', { length: 50 }).notNull(),
  comment: text('comment'),
  status: varchar('status', { length: 20 }).notNull().default('pending'), // pending, processing, completed, failed
  forensicResult: json('forensic_result'),
  rebuiltCode: text('rebuilt_code'),
  qualityResult: json('quality_result'),
  errorMessage: text('error_message'),
  metadata: json('metadata'),
  startedAt: timestamp('started_at'),
  completedAt: timestamp('completed_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  userIdx: index('idx_submissions_user').on(table.userId),
  statusIdx: index('idx_submissions_status').on(table.status),
  createdAtIdx: index('idx_submissions_created').on(table.createdAt),
  userIdStatusIdx: index('idx_submissions_user_status').on(table.userId, table.status),
}));

// ============================================================================
// PIPELINE RESULTS (PER STEP)
// ============================================================================
export const pipelineResults = mysqlTable('pipeline_results', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  submissionId: varchar('submission_id', { length: 36 }).notNull().references(() => codeSubmissions.id, { onDelete: 'cascade' }),
  stepName: varchar('step_name', { length: 50 }).notNull(),
  providerId: varchar('provider_id', { length: 36 }),
  modelId: varchar('model_id', { length: 255 }),
  prompt: text('prompt'),
  response: json('response'),
  tokensUsed: int('tokens_used'),
  durationMs: int('duration_ms'),
  status: varchar('status', { length: 20 }).notNull().default('success'),
  errorMessage: text('error_message'),
  retryCount: int('retry_count').default(0),
  createdAt: timestamp('created_at').notNull().defaultNow(),
}, (table) => ({
  submissionIdx: index('idx_results_submission').on(table.submissionId),
  stepIdx: index('idx_results_step').on(table.stepName),
  providerIdx: index('idx_results_provider').on(table.providerId),
  createdAtIdx: index('idx_results_created').on(table.createdAt),
}));

// ============================================================================
// AUDIT LOGS
// ============================================================================
export const auditLogs = mysqlTable('audit_logs', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  userId: varchar('user_id', { length: 36 }).references(() => users.id),
  action: varchar('action', { length: 100 }).notNull(),
  entityType: varchar('entity_type', { length: 50 }).notNull(), // 'prompt', 'model', 'provider', 'user', 'config'
  entityId: varchar('entity_id', { length: 36 }),
  before: json('before'),
  after: json('after'),
  ipAddress: varchar('ip_address', { length: 45 }),
  userAgent: text('user_agent'),
  metadata: json('metadata'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
}, (table) => ({
  userIdx: index('idx_audit_user').on(table.userId),
  actionIdx: index('idx_audit_action').on(table.action),
  entityIdx: index('idx_audit_entity').on(table.entityType, table.entityId),
  createdAtIdx: index('idx_audit_created').on(table.createdAt),
}));

// ============================================================================
// RUNTIME CONFIGURATION
// ============================================================================
export const runtimeConfig = mysqlTable('runtime_config', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  key: varchar('key', { length: 100 }).notNull().unique(),
  value: json('value').notNull(),
  description: text('description'),
  version: int('version').notNull().default(1),
  createdBy: varchar('created_by', { length: 36 }).references(() => users.id),
  updatedBy: varchar('updated_by', { length: 36 }).references(() => users.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  keyIdx: uniqueIndex('idx_config_key').on(table.key),
}));

// ============================================================================
// RATE LIMITS
// ============================================================================
export const rateLimits = mysqlTable('rate_limits', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  userId: varchar('user_id', { length: 36 }).references(() => users.id),
  tier: varchar('tier', { length: 20 }).notNull().default('free'), // free, pro, enterprise
  dailyLimit: int('daily_limit').notNull().default(5),
  monthlyLimit: int('monthly_limit'),
  concurrentLimit: int('concurrent_limit').default(1),
  overrides: json('overrides'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  userIdx: uniqueIndex('idx_rate_limits_user').on(table.userId),
  tierIdx: index('idx_rate_limits_tier').on(table.tier),
}));

// ============================================================================
// DAILY USAGE
// ============================================================================
export const dailyUsage = mysqlTable('daily_usage', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  userId: varchar('user_id', { length: 36 }).notNull().references(() => users.id),
  date: varchar('date', { length: 10 }).notNull(), // YYYY-MM-DD
  submissionCount: int('submission_count').notNull().default(0),
  tokensUsed: int('tokens_used').notNull().default(0),
  costCents: int('cost_cents').notNull().default(0),
  metadata: json('metadata'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  userDateIdx: uniqueIndex('idx_usage_user_date').on(table.userId, table.date),
  dateIdx: index('idx_usage_date').on(table.date),
}));

// ============================================================================
// DEAD LETTER QUEUE
// ============================================================================
export const deadLetterQueue = mysqlTable('dead_letter_queue', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  jobId: varchar('job_id', { length: 36 }),
  jobType: varchar('job_type', { length: 50 }).notNull(),
  payload: json('payload').notNull(),
  error: json('error'),
  retryCount: int('retry_count').default(0),
  status: varchar('status', { length: 20 }).default('failed'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow().onUpdateNow(),
}, (table) => ({
  statusIdx: index('idx_dlq_status').on(table.status),
  createdAtIdx: index('idx_dlq_created').on(table.createdAt),
}));

// ============================================================================
// IDEMPOTENCY KEYS
// ============================================================================
export const idempotencyKeys = mysqlTable('idempotency_keys', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  key: varchar('key', { length: 255 }).notNull().unique(),
  response: json('response'),
  expiresAt: timestamp('expires_at').notNull(),
  createdAt: timestamp('created_at').notNull().defaultNow(),
}, (table) => ({
  keyIdx: uniqueIndex('idx_idempotency_key').on(table.key),
  expiresIdx: index('idx_idempotency_expires').on(table.expiresAt),
}));

// ============================================================================
// BACKUPS
// ============================================================================
export const backups = mysqlTable('backups', {
  id: varchar('id', { length: 36 }).primaryKey().$defaultFn(() => crypto.randomUUID()),
  filename: varchar('filename', { length: 255 }).notNull(),
  size: int('size'),
  status: varchar('status', { length: 20 }).default('pending'),
  type: varchar('type', { length: 20 }).default('manual'), // manual, scheduled
  metadata: json('metadata'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  completedAt: timestamp('completed_at'),
}, (table) => ({
  statusIdx: index('idx_backups_status').on(table.status),
  createdAtIdx: index('idx_backups_created').on(table.createdAt),
}));

// ============================================================================
// RELATIONS
// ============================================================================
export const usersRelations = relations(users, ({ many }) => ({
  submissions: many(codeSubmissions),
  auditLogs: many(auditLogs),
  rateLimit: one(rateLimits),
  usage: many(dailyUsage),
}));

export const apiProvidersRelations = relations(apiProviders, ({ many }) => ({
  apiKeys: many(providerApiKeys),
  models: many(providerModels),
  pipelineSteps: many(pipelineSteps),
}));

export const codeSubmissionsRelations = relations(codeSubmissions, ({ one, many }) => ({
  user: one(users, { fields: [codeSubmissions.userId], references: [users.id] }),
  results: many(pipelineResults),
}));

export const pipelineResultsRelations = relations(pipelineResults, ({ one }) => ({
  submission: one(codeSubmissions, { fields: [pipelineResults.submissionId], references: [codeSubmissions.id] }),
}));