"""
Pydantic Schemas for Request, Response, Traces, and Agent States.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ==========================================
# API Request & Response Schemas
# ==========================================

class RunInput(BaseModel):
    query: str = Field(..., description="Architecture decision question from the Tech Lead")
    repo: str = Field("django_app", description="Target repository name or identifier")
    module_path: Optional[str] = Field(None, description="Specific module directory path to analyze")


class RunOptions(BaseModel):
    sample_mode: Optional[bool] = Field(None, description="Force sample mode (SQLite local) without external credentials")


class RunRequest(BaseModel):
    input: RunInput
    options: Optional[RunOptions] = Field(default_factory=RunOptions)


class EvidenceItem(BaseModel):
    claim: str = Field(..., description="Specific claim made in analysis")
    metric: str = Field(..., description="Name of the metric (e.g. cyclomatic_complexity_max, god_class_count)")
    source_table: str = Field(..., description="Table queried (e.g. modules, antipatterns, tests)")
    sql_query: str = Field(..., description="SQL query executed to gather or verify this evidence")
    value: Any = Field(..., description="Actual value retrieved")
    threshold: Optional[Any] = Field(None, description="Standard threshold applied from rules table")
    verified: bool = Field(False, description="True if verified independently by the EvidenceEvaluator")


class OptionComparison(BaseModel):
    option: Literal["maintain", "refactor", "migrate"]
    score: float = Field(..., description="Calculated suitability score (0-100)")
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    rationale: str = Field(..., description="Justification based strictly on verified evidence")


class AgentInfo(BaseModel):
    name: str
    role: str


class RunOutput(BaseModel):
    decision: Literal["maintain", "refactor", "migrate", "insufficient_evidence"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level between 0 and 1")
    options_compared: List[OptionComparison] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    action_plan: List[str] = Field(default_factory=list)
    summary: str


class StructuredErrorDetail(BaseModel):
    type: str
    message: str
    recoverable: bool = False


class RunResponse(BaseModel):
    run_id: str
    status: Literal["success", "insufficient_evidence", "error"]
    output: Optional[RunOutput] = None
    error: Optional[StructuredErrorDetail] = None
    agents: List[AgentInfo] = Field(default_factory=list)
    trace_id: str
    log_file: str
    execution_time_seconds: float


# ==========================================
# Orchestration & Shared State Schemas
# ==========================================

class SharedState(BaseModel):
    run_id: str
    trace_id: str
    query: str
    repo: str
    module_path: Optional[str] = None
    sample_mode: bool = False

    # Agent step tracking
    current_step: str = "init"
    revision_count: int = 0
    max_revisions: int = 2

    # Shared artifacts
    plan_criteria: List[str] = Field(default_factory=list)
    planned_queries: List[Dict[str, str]] = Field(default_factory=list)
    retrieved_data: Dict[str, Any] = Field(default_factory=dict)
    sql_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    proposed_decision: Optional[str] = None
    claims_to_verify: List[Dict[str, Any]] = Field(default_factory=list)
    verified_evidence: List[EvidenceItem] = Field(default_factory=list)
    evaluator_feedback: Optional[str] = None
    evaluator_status: Literal["approved", "needs_revision", "abstain"] = "needs_revision"
    
    missing_evidence: List[str] = Field(default_factory=list)
    final_output: Optional[RunOutput] = None
    error: Optional[StructuredErrorDetail] = None
