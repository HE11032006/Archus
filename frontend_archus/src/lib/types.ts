// API types matching the Archus FastAPI backend schemas

export interface RunInput {
  query: string;
  repo: string;
  module_path?: string;
}

export interface RunOptions {
  sample_mode?: boolean;
}

export interface RunRequest {
  input: RunInput;
  options?: RunOptions;
}

export interface EvidenceItem {
  claim: string;
  metric: string;
  source_table: string;
  sql_query: string;
  value: unknown;
  threshold?: unknown;
  verified: boolean;
}

export interface OptionComparison {
  option: "maintain" | "refactor" | "migrate";
  score: number;
  pros: string[];
  cons: string[];
  rationale: string;
}

export interface AgentInfo {
  name: string;
  role: string;
}

export interface RunOutput {
  decision: "maintain" | "refactor" | "migrate" | "insufficient_evidence";
  confidence: number;
  options_compared: OptionComparison[];
  evidence: EvidenceItem[];
  missing_data: string[];
  action_plan: string[];
  summary: string;
}

export interface RunResponse {
  run_id: string;
  status: "success" | "insufficient_evidence" | "error";
  output?: RunOutput;
  error?: {
    type: string;
    message: string;
    recoverable: boolean;
  };
  agents: AgentInfo[];
  trace_id: string;
  log_file: string;
  execution_time_seconds: number;
}

export interface HealthResponse {
  status: string;
  zetaris_configured: boolean;
  meterless_configured: boolean;
  sample_mode_enabled: boolean;
}
