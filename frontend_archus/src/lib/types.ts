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

export interface AntiPatternItem {
  pattern: string;
  file: string;
  severity: "high" | "medium" | "low" | string;
  value: number;
  description?: string;
}

export interface ComplexityHotspot {
  file: string;
  max_complexity: number;
  num_functions: number;
  num_lines: number;
}

export interface RefactoringRecipe {
  title: string;
  pattern: string;
  impact: string;
  before_snippet: string;
  after_snippet: string;
}

export interface RepoMetadata {
  repo_name?: string;
  language?: string;
  architecture_pattern?: string;
  files_analyzed?: number;
  total_loc?: number;
  total_functions?: number;
  total_classes?: number;
}

export interface MetricsOverview {
  complexity_avg?: number;
  complexity_max?: number;
  coupling_score?: number;
  cohesion_score?: number;
  coverage_estimate?: number;
  god_class_count?: number;
  hotspot_fixes?: number;
  outdated_deps?: number;
}

export interface RunOutput {
  decision: "maintain" | "refactor" | "migrate" | "insufficient_evidence";
  confidence: number;
  options_compared: OptionComparison[];
  evidence: EvidenceItem[];
  missing_data: string[];
  action_plan: string[];
  summary: string;
  detailed_explanation?: string;
  architecture_style?: string;
  repo_metadata?: RepoMetadata;
  metrics_overview?: MetricsOverview;
  antipatterns?: AntiPatternItem[];
  complexity_hotspots?: ComplexityHotspot[];
  refactoring_recipes?: RefactoringRecipe[];
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
