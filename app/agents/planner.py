from __future__ import annotations

from app.agents.base import Agent
from app.models import Assignment, Resource


class Planner(Agent):
    name = "Planner"

    def assign(self, *, round: int, resources: list[Resource],
               recheck_requests: list[dict]) -> Assignment:
        if recheck_requests:
            target_ids = [r["resource_id"] for r in recheck_requests]
            lookback = max(r.get("lookback_hours", self.ctx.config.lookback_hours)
                           for r in recheck_requests)
            focus = "recheck"
        else:
            target_ids = [r.resource_id for r in resources][: self.ctx.config.max_resources]
            lookback = self.ctx.config.lookback_hours
            focus = "initial"

        assignment = Assignment(assignment_id=f"A-{round}", round=round, resource_ids=target_ids,
                                lookback_hours=lookback, focus=focus)
        self.ctx.state.append("assignment", {"round": round, "focus": focus,
                                             "resource_ids": target_ids,
                                             "lookback_hours": lookback})
        self._emit("delegate_task", round=round, target_agent="Scout",
                   input_summary=f"round {round}, {len(target_ids)} target(s), "
                                 f"lookback {lookback}h",
                   output_summary=f"assignment {assignment.assignment_id} ({focus})",
                   confidence=0.8)
        return assignment

    def wants_another_round(self, *, round: int, recheck_requests: list[dict]) -> bool:
        return bool(recheck_requests) and round < self.ctx.config.max_rounds
