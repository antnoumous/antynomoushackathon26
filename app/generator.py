from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from app.config import RunConfig

TEMPLATES: dict[str, str] = {
    "R-1": "{resource_name} is a detached {size_gb} GB block volume. It is billed continuously "
           "and is attached to nothing.",
    "R-2": "{resource_name} is a reserved public IP with no assigned entity. It is billed "
           "whether or not it is attached.",
    "R-3": "{resource_name} averages {mean}% CPU with a peak of {peak}% across the "
           "requested window, and is declared in Terraform. Nothing in the evidence attributes "
           "a purpose to it.",
    "R-4": "{resource_name} averages {mean}% CPU but peaks at {peak}%. The cost is the "
           "idle shape it holds around the clock, not the work it does.",
    "R-5": "{resource_name} is running and appears in no Terraform declaration. No owner tag "
           "attributes it to a team.",
}

REASONS: dict[str, str] = {
    "schedule_signal": "the declaration or tag names a repeating cadence, so the requested "
                       "window may exclude the most recent run",
    "recheck_cap": "this finding has already been re-investigated {n} times",
    "frequency_mismatch": "a low mean with a peak this high is a duty-cycle problem, not an "
                          "idle resource",
    "declared_purpose": "the declaration states a deliberate purpose ({signal}), which is exactly "
                        "the falsifier this finding published",
}


class GeneratorUnavailableError(Exception):
    pass


class Generator(Protocol):
    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict: ...


class RulesGenerator:
    """Deterministic, offline. The same structured outputs a model would produce, from rules."""

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        name = schema.get("name")
        if name == "finding_claim":
            rule_id = context["rule_id"]
            template = TEMPLATES[rule_id]                 # KeyError on an unmapped rule: fail loudly
            text = template.format(resource_name=context["resource_name"],
                                   mean=context["stats"].get("mean", 0.0),
                                   peak=context["stats"].get("peak", 0.0),
                                   size_gb=context.get("size_gb"))
            confidence = 0.75 if context.get("iac_match_rule") == "tag" else 0.55
            return {"claim": text, "confidence": confidence}
        if name == "verdict_reason":
            return {"reason": REASONS[context["reason_key"]].format(n=context.get("n", 0),
                                                                    signal=context.get("signal", "")),
                    "confidence": 0.8}
        if name == "run_summary":
            return {"summary": ("Audited {resources} resources across {sources} sources; "
                                "{accepted} findings accepted, {rejected} rejected, "
                                "{undetermined} left undetermined.").format(**context),
                    "confidence": 1.0}
        raise KeyError(name)


class ModelGenerator:
    """OpenAI-compatible chat completions. Never instantiated in sample mode."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: int = 60) -> None:
        self.base_url, self.api_key, self.model, self.timeout_s = base_url, api_key, model, timeout_s

    @classmethod
    def from_env(cls) -> "ModelGenerator":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise GeneratorUnavailableError("LLM_API_KEY is not set")
        return cls(base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                   api_key=api_key, model=os.environ.get("LLM_MODEL", "gpt-4o-mini"))

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": json.dumps(schema)},
                               {"role": "user", "content": prompt}]},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def get_generator(config: RunConfig) -> Generator:
    if config.sample_mode or not os.environ.get("LLM_API_KEY"):
        return RulesGenerator()
    return ModelGenerator.from_env()
