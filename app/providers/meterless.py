"""Optional Nightshift structured generator. Rules remain the factual fallback."""
from __future__ import annotations
import json
import math
import time
from app.generation_status import GenerationOutcome, GenerationRecorder
from app.generator import ModelGenerator, RulesGenerator
from app.providers.meterless_settings import MeterlessSettings, MeterlessError
from app.providers.meterless_transport import request_json


class MeterlessGenerator:
    def __init__(self, settings: MeterlessSettings | None, *, transport=request_json,
                 recorder: GenerationRecorder | None = None, configuration_error: str | None = None):
        self.settings = settings
        self.configuration_error = configuration_error
        self.transport = transport
        self.recorder = recorder if recorder is not None else GenerationRecorder("meterless")
        self._deadline = None
        self._fallback = RulesGenerator()

    def set_deadline(self, deadline: float | None) -> None:
        self._deadline = deadline

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        name = schema["name"]
        full_schema = ModelGenerator.SCHEMAS[name]  # Unknown schema is a caller error, not a fallback.
        started = time.monotonic()
        attempted = False
        model = self.settings.model if self.settings is not None else None
        try:
            if self.settings is None:
                raise MeterlessError(self.configuration_error or "configuration")
            timeout_s = min(60.0, self.settings.timeout_s)
            if self._deadline is not None:
                timeout_s = min(timeout_s, self._deadline - time.monotonic())
            if not math.isfinite(timeout_s) or timeout_s <= 0:
                raise MeterlessError("timeout")
            payload = {"model": model, "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": "Respond with a single JSON object matching this JSON schema, no prose around it.\n" + json.dumps(full_schema)},
                                    {"role": "user", "content": prompt + "\nContext: " + json.dumps(context, default=str)}]}
            self.recorder.attempt(name, model, timeout_s)
            attempted = True
            response = self.transport("POST", self.settings.base_url + "/chat/completions", headers={
                "Authorization": "Bearer " + self.settings.token.get_secret_value(),
                "meterless-app": self.settings.app_id, "meterless-scope": "user"},
                payload=payload, timeout_s=timeout_s)
            try:
                content = response["choices"][0]["message"]["content"]
                out = json.loads(content, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
                if not isinstance(out, dict) or any(key not in out for key in full_schema["required"]):
                    raise ValueError()
                confidence = out["confidence"]
                if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                    raise ValueError()
                for key, definition in full_schema["properties"].items():
                    if definition["type"] == "string" and not isinstance(out[key], str):
                        raise ValueError()
            except (ValueError, TypeError, KeyError, IndexError, RecursionError):
                raise MeterlessError("schema") from None
        except Exception as exc:
            category = exc.category if isinstance(exc, MeterlessError) else "transport"
            self.recorder.record(GenerationOutcome(name, "meterless", "rules", model,
                attempted, True, category, max(0, time.monotonic()-started)))
            return self._fallback.complete(prompt=prompt, schema=schema, context=context)
        self.recorder.record(GenerationOutcome(name, "meterless", "meterless", model,
                                               True, False, None, max(0, time.monotonic()-started)))
        return out

    def diagnostics(self) -> dict:
        return self.recorder.summary()
