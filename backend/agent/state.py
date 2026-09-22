from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class EvidenceItem:
    """A verified piece of evidence collected during agent execution."""
    source_type: str  # "contract", "statute", "case", "benchmark"
    source_identifier: str  # e.g., "Clause 4", "Indian Contract Act § 27"
    title: str
    content: str
    contract_name: Optional[str] = None
    page: Optional[int] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "title": self.title,
            "content": self.content[:300] + ("..." if len(self.content) > 300 else ""),
            "contract_name": self.contract_name,
            "page": self.page,
            "confidence_score": round(self.confidence_score, 4),
            "metadata": self.metadata
        }

@dataclass
class ToolCallRecord:
    """Record of an individual tool invocation during an agent step."""
    step: int
    tool_name: str
    tool_args: Dict[str, Any]
    output_summary: str
    latency_seconds: float
    success: bool
    num_evidence_items: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "output_summary": self.output_summary,
            "latency_seconds": round(self.latency_seconds, 4),
            "success": self.success,
            "num_evidence_items": self.num_evidence_items
        }

@dataclass
class AgentState:
    """
    Explicit state tracker for the controlled agent workflow.
    Ensures bounded multi-step reasoning with auditable evidence accumulation.
    """
    user_query: str
    contract_name: Optional[str] = None
    step_count: int = 0
    max_steps: int = 5
    evidence: List[EvidenceItem] = field(default_factory=list)
    tool_call_history: List[ToolCallRecord] = field(default_factory=list)
    final_answer: Optional[str] = None
    verification_result: Optional[Dict[str, Any]] = None
    abstained: bool = False
    abstention_reason: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def add_evidence(self, item: EvidenceItem):
        # Avoid duplicate evidence
        for existing in self.evidence:
            if existing.source_type == item.source_type and existing.source_identifier == item.source_identifier:
                return
        self.evidence.append(item)

    def get_contract_evidence(self) -> List[EvidenceItem]:
        return [e for e in self.evidence if e.source_type == "contract"]

    def get_external_evidence(self) -> List[EvidenceItem]:
        return [e for e in self.evidence if e.source_type in {"statute", "case", "benchmark"}]

    def to_trace_summary(self) -> Dict[str, Any]:
        return {
            "query": self.user_query,
            "contract_name": self.contract_name,
            "total_steps": self.step_count,
            "max_steps": self.max_steps,
            "tools_used": [t.tool_name for t in self.tool_call_history],
            "tool_calls": [t.to_dict() for t in self.tool_call_history],
            "total_evidence_collected": len(self.evidence),
            "evidence_items": [e.to_dict() for e in self.evidence],
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "verification": self.verification_result,
            "errors": self.errors
        }
