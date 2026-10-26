"""Per-run generation outcomes; no prompts, headers or raw errors enter diagnostics."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class GenerationOutcome:
    schema_name: str
    configured_provider: str
    actual_backend: str
    model: str | None
    attempted: bool
    fallback: bool
    category: str | None
    latency_s: float


class GenerationRecorder:
    def __init__(self, configured_provider: str) -> None:
        self.configured_provider = configured_provider
        self._outcomes: list[GenerationOutcome] = []

    def record(self, outcome: GenerationOutcome) -> None:
        valid = (isinstance(outcome, GenerationOutcome)
            and outcome.configured_provider == self.configured_provider
            and outcome.configured_provider in {"rules", "openai-compatible", "meterless"}
            and outcome.actual_backend in {"rules", "openai-compatible", "meterless"}
            and outcome.schema_name in {"finding_claim", "verdict_reason", "run_summary"}
            and type(outcome.attempted) is bool and type(outcome.fallback) is bool
            and type(outcome.latency_s) in {int, float}
            and math.isfinite(outcome.latency_s) and outcome.latency_s >= 0
            and outcome.category in {None,"configuration","unauthorized","offline","unsupported_mode","timeout","schema","transport"}
            and (not outcome.fallback or (outcome.actual_backend == "rules" and outcome.category is not None))
            and (outcome.fallback or outcome.category is None)
            and (outcome.actual_backend == "rules" or outcome.attempted)
            and (not outcome.attempted or outcome.actual_backend != "rules" or outcome.fallback))
        if not valid:
            raise ValueError("invalid generation outcome")
        self._outcomes.append(outcome)

    def outcomes(self) -> tuple[GenerationOutcome, ...]:
        return tuple(self._outcomes)

    def summary(self) -> dict:
        def counts(rows):
            return {"attempts": sum(row.attempted for row in rows),
                    "successes": sum(row.attempted and not row.fallback and row.actual_backend != "rules" for row in rows),
                    "fallbacks": sum(row.fallback for row in rows)}
        result = counts(self._outcomes)
        return {"configured_provider": self.configured_provider, **result,
                "status": "partial" if result["fallbacks"] else "success" if result["successes"] else "not_used",
                "models": sorted({row.model for row in self._outcomes if row.model is not None}),
                "schemas": {name: counts([r for r in self._outcomes if r.schema_name == name])
                            for name in sorted({r.schema_name for r in self._outcomes})}}
