from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol

import requests

from app.config import RunConfig
from app.generation_status import GenerationOutcome, GenerationRecorder

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
    def set_deadline(self, deadline: float | None) -> None: ...


class RulesGenerator:
    """Deterministic, offline. The same structured outputs a model would produce, from rules."""

    def diagnostics(self) -> dict:
        return GenerationRecorder("rules").summary()

    def set_deadline(self, deadline: float | None) -> None:
        """Nothing to bound: this generator does no I/O. Present so every backend honours the
        same interface, and so the loop never has to ask which kind it is holding."""

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

    # The call sites pass a schema by name only ({"name": "finding_claim"}), which the rule
    # engine can switch on but a model cannot: it needs the shape spelled out. These mirror
    # RulesGenerator's contract exactly — same keys, same requiredness.
    SCHEMAS: dict[str, dict] = {
        "finding_claim": {"type": "object",
                          "properties": {"claim": {"type": "string"},
                                         "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
                          "required": ["claim", "confidence"]},
        "verdict_reason": {"type": "object",
                           "properties": {"reason": {"type": "string"},
                                          "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
                           "required": ["reason", "confidence"]},
        "run_summary": {"type": "object",
                        "properties": {"summary": {"type": "string"},
                                       "confidence": {"type": "number"}},
                        "required": ["summary", "confidence"]},
    }

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: int = 60) -> None:
        self.base_url, self.api_key, self.model, self.timeout_s = base_url, api_key, model, timeout_s
        self._deadline: float | None = None
        # Partner-call rule: every outbound call has a timeout and a fallback. If the model
        # errors, times out, or answers off-schema, this generator degrades to the deterministic
        # rule engine per call — the run finishes on prose the loop already proves, instead of
        # crashing mid-audit because a hosted endpoint had a bad minute.
        self._fallback = RulesGenerator()
        self.recorder = GenerationRecorder("openai-compatible")

    def set_deadline(self, deadline: float | None) -> None:
        """The run's wall-clock deadline, so no single call can outlive the run's budget."""
        self._deadline = deadline

    def current_timeout(self) -> float:
        if self._deadline is None:
            return float(self.timeout_s)
        return max(1.0, min(float(self.timeout_s), self._deadline - time.monotonic()))

    @classmethod
    def from_env(cls) -> "ModelGenerator":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise GeneratorUnavailableError("LLM_API_KEY is not set")
        return cls(base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                   api_key=api_key, model=os.environ.get("LLM_MODEL", "gpt-4o-mini"))

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        name = schema["name"]
        if name not in self.SCHEMAS:
            raise KeyError(name)
        started = time.monotonic()
        try:
            result = self._complete_model(prompt=prompt, schema=schema, context=context)
        except Exception as exc:  # A fallback is visible rather than reported as model success.
            category = "schema" if isinstance(exc, (ValueError, KeyError, TypeError)) else "transport"
            self.recorder.record(GenerationOutcome(name, "openai-compatible", "rules", self.model,
                True, True, category, max(0, time.monotonic()-started)))
            return self._fallback.complete(prompt=prompt, schema=schema, context=context)
        self.recorder.record(GenerationOutcome(name, "openai-compatible", "openai-compatible", self.model,
            True, False, None, max(0, time.monotonic()-started)))
        return result

    def diagnostics(self) -> dict:
        return self.recorder.summary()

    def _complete_model(self, *, prompt: str, schema: dict, context: dict) -> dict:
        # Call sites pass {"name": ...} and sometimes an empty prompt (the rule engine needs
        # neither; a model needs both). Expand to the real schema and render the context into
        # the prompt so every backend produces the same shape from the same inputs.
        name = schema.get("name")
        full_schema = self.SCHEMAS.get(name) if isinstance(name, str) else None
        if full_schema is None:
            raise KeyError(name)
        brief = (f"{prompt}\nContext: {json.dumps(context, default=str)}"
                 if prompt else f"Produce the {name} for this context: {json.dumps(context, default=str)}")
        # response_format=json_object requires the word "json" to appear in the messages on
        # OpenAI-compatible endpoints (Token Plan rejects the request otherwise with a 400).
        # The schema is JSON, so saying so is also the honest instruction.
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system",
                                "content": "Respond with a single JSON object matching this "
                                           f"JSON schema, no prose around it.\n{json.dumps(full_schema)}"},
                               {"role": "user", "content": brief}]},
            timeout=self.current_timeout(),
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        out = json.loads(content)
        missing = [k for k in full_schema["required"] if k not in out]
        if missing:
            raise ValueError(f"model response for {name} missing {missing}")
        return out


def generator_diagnostics(generator: object) -> dict:
    method = getattr(generator, "diagnostics", None)
    if callable(method):
        return method()
    return {"configured_provider": "unknown", "attempts": 0, "successes": 0, "fallbacks": 0,
            "status": "unverified", "models": [], "schemas": {}}


def get_generator(config: RunConfig) -> Generator:
    if config.sample_mode:
        return RulesGenerator()
    selected = config.llm_provider or os.environ.get("LLM_PROVIDER", "openai-compatible")
    if selected not in {"rules", "openai-compatible", "meterless"}:
        raise ValueError("LLM_PROVIDER must be rules, openai-compatible or meterless")
    if selected == "meterless":
        from app.providers.meterless import MeterlessGenerator
        from app.providers.meterless_settings import MeterlessSettings, MeterlessError
        try:
            return MeterlessGenerator(MeterlessSettings.from_env(os.environ))
        except MeterlessError as exc:
            return MeterlessGenerator(None, configuration_error=exc.category)
    if selected == "rules" or not os.environ.get("LLM_API_KEY"):
        return RulesGenerator()
    return ModelGenerator.from_env()
