/**
 * API Client for AI Job Agent Backend
 *
 * Provides type-safe functions for interacting with the FastAPI backend.
 * All endpoints use the /api proxy configured in next.config.ts.
 */

const API_BASE = "/api/admin";

export interface TableSchema {
  table_name: string;
  columns: Array<{
    name: string;
    type: string;
    nullable: boolean;
    default: string | null;
    primary_key: boolean;
  }>;
  primary_keys: string[];
  foreign_keys: Array<{
    constrained_columns: string[];
    referred_table: string;
    referred_columns: string[];
  }>;
}

export interface TableDataResponse {
  table_name: string;
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
  data: Array<Record<string, any>>;
}

export interface Profile {
  profile_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface BulkJobsRequest {
  urls: string[];
  profile_id: number;
}

export interface JobCreated {
  id: number;
  url: string;
  status: string;
}

export interface BulkJobsResponse {
  created: JobCreated[];
  failed: Array<{ url: string; reason: string }>;
  summary: {
    total_submitted: number;
    created: number;
    failed: number;
  };
}

/**
 * Fetch the list of all available database tables
 */
export async function fetchTables(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/db/tables`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tables: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch the schema (columns, types, constraints) for a specific table
 */
export async function fetchTableSchema(
  tableName: string
): Promise<TableSchema> {
  const response = await fetch(`${API_BASE}/db/tables/${tableName}/schema`);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch schema for ${tableName}: ${response.statusText}`
    );
  }
  return response.json();
}

/**
 * Fetch paginated data from a specific table
 */
export async function fetchTableData(
  tableName: string,
  limit: number = 50,
  offset: number = 0
): Promise<TableDataResponse> {
  const response = await fetch(
    `${API_BASE}/db/tables/${tableName}/data?limit=${limit}&offset=${offset}`
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch data for ${tableName}: ${response.statusText}`
    );
  }
  return response.json();
}

/**
 * Fetch all profiles for dropdown selection
 */
export async function fetchProfiles(): Promise<Profile[]> {
  const response = await fetch(`${API_BASE}/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to fetch profiles: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create multiple jobs from URLs
 */
export async function bulkCreateJobs(
  request: BulkJobsRequest
): Promise<BulkJobsResponse> {
  const response = await fetch(`${API_BASE}/db/jobs/bulk-create-urls`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to create jobs: ${response.statusText}`
    );
  }

  return response.json();
}

// ============================================================================
// LLM Provider & Model Management
// ============================================================================

export interface LLMProvider {
  llm_provider_id: number;
  llm_provider_name: string;
}

export interface LLMModel {
  llm_model_id: number;
  llm_model_name: string;
  llm_provider_id: number;
  llm_provider_name: string;
}

/**
 * Fetch all LLM providers
 */
export async function fetchLLMProviders(): Promise<LLMProvider[]> {
  const response = await fetch(`${API_BASE}/llm-providers`);
  if (!response.ok) {
    throw new Error(`Failed to fetch LLM providers: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create a new LLM provider
 */
export async function createLLMProvider(
  name: string
): Promise<LLMProvider> {
  const response = await fetch(`${API_BASE}/llm-providers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ llm_provider_name: name }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to create provider: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Update an existing LLM provider
 */
export async function updateLLMProvider(
  id: number,
  name: string
): Promise<LLMProvider> {
  const response = await fetch(`${API_BASE}/llm-providers/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ llm_provider_name: name }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to update provider: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Delete an LLM provider
 */
export async function deleteLLMProvider(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/llm-providers/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to delete provider: ${response.statusText}`
    );
  }
}

/**
 * Create a new LLM model
 */
export async function createLLMModel(
  modelName: string,
  providerId: number
): Promise<LLMModel> {
  const response = await fetch(`${API_BASE}/llm-models`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      llm_model_name: modelName,
      llm_provider_id: providerId,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to create model: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Update an existing LLM model
 */
export async function updateLLMModel(
  id: number,
  modelName?: string,
  providerId?: number
): Promise<LLMModel> {
  const updates: any = {};
  if (modelName !== undefined) updates.llm_model_name = modelName;
  if (providerId !== undefined) updates.llm_provider_id = providerId;

  const response = await fetch(`${API_BASE}/llm-models/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to update model: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Delete an LLM model
 */
export async function deleteLLMModel(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/llm-models/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to delete model: ${response.statusText}`
    );
  }
}

// ============================================================================
// Settings Management
// ============================================================================

export interface Setting {
  setting_id: number;
  setting_name: string;
  setting_value: Record<string, any>;
  created_at: string;
  updated_at: string;
}

/**
 * Fetch all settings
 */
export async function fetchSettings(): Promise<Setting[]> {
  const response = await fetch(`${API_BASE}/settings`);
  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get a specific setting by name
 */
export async function getSetting(name: string): Promise<Setting | null> {
  const response = await fetch(`${API_BASE}/settings/${name}`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch setting: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create or update a setting (upsert)
 */
export async function upsertSetting(
  name: string,
  value: Record<string, any>
): Promise<Setting> {
  const response = await fetch(`${API_BASE}/settings/${name}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ setting_value: value }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to save setting: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Delete a setting
 */
export async function deleteSetting(name: string): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/${name}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to delete setting: ${response.statusText}`
    );
  }
}
