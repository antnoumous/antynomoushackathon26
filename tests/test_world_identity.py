"""Identity must survive retries but isolate different observation scopes."""

def test_identity_ignores_dictionary_order_but_isolates_namespace():
    from app.world_model.contracts import Observation
    from app.world_model.identity import observation_id
    a = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"b": 2, "a": 1})
    b = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"a": 1, "b": 2})
    assert observation_id("scenario:a", a) == observation_id("scenario:a", b)
    assert observation_id("scenario:b", a) != observation_id("scenario:a", a)


def test_payload_mutation_cannot_rewrite_a_captured_observation():
    from app.world_model.contracts import Observation
    payload = {"tags": {"schedule": "monthly"}}
    observation = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload=payload)
    payload["tags"]["schedule"] = "nightly"
    exposed = observation.payload
    exposed["tags"]["schedule"] = "weekly"
    assert observation.payload == {"tags": {"schedule": "monthly"}}


def test_entities_stay_stable_when_observations_change():
    from dataclasses import replace
    from app.world_model.contracts import Observation
    from app.world_model.identity import entity_id, observation_id
    first = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"name": "old"})
    changed = replace(first, payload_json='{"name":"new"}')
    assert entity_id("n", first) == entity_id("n", changed)
    assert observation_id("n", first) != observation_id("n", changed)
    assert entity_id("other", first) != entity_id("n", first)


def test_missing_or_unknown_source_provenance_is_rejected():
    import pytest
    from app.world_model.contracts import Observation, WorldError
    for field, value in [("source", ""), ("source", "mystery"), ("backend", "unknown"),
                         ("external_key", ""), ("entity_type", "")]:
        args = dict(entity_type="resource", external_key="r1", source="inventory",
                    backend="fixture", payload={"name": "x"})
        args[field] = value
        with pytest.raises(WorldError) as caught:
            Observation.from_payload(**args)
        assert caught.value.category == "provenance"
        assert value not in str(caught.value) if value else True


def test_equivalent_aware_datetimes_produce_the_same_canonical_payload():
    from datetime import datetime, timezone, timedelta
    from app.world_model.identity import canonical_json
    utc = datetime(2026, 10, 1, 2, tzinfo=timezone.utc)
    local = datetime(2026, 10, 1, 10, tzinfo=timezone(timedelta(hours=8)))
    assert canonical_json({"at": utc}) == '{"at":"2026-10-01T02:00:00Z"}'
    assert canonical_json({"at": local}) == canonical_json({"at": utc})


def test_invalid_json_values_fail_with_classified_schema_errors():
    import pytest
    from datetime import datetime
    from app.world_model.contracts import WorldError
    from app.world_model.identity import canonical_json
    for value in [{"x": float("nan")}, {"x": float("inf")}, {"x": datetime(2026, 1, 1)},
                  {1: "ambiguous-key"}, {"x": object()}]:
        with pytest.raises(WorldError) as caught:
            canonical_json(value)
        assert caught.value.category == "schema"


def test_window_backend_and_source_revision_are_part_of_observation_identity():
    from dataclasses import replace
    from app.world_model.contracts import Observation
    from app.world_model.identity import observation_id
    first = Observation.from_payload(entity_type="telemetry", external_key="r1",
        source="telemetry", backend="fixture", payload={"points": []},
        lookback_hours=168, resolution_minutes=5)
    variants = [replace(first, lookback_hours=744), replace(first, backend="live"),
                replace(first, source_version="next"), replace(first, resolution_minutes=60)]
    assert len({observation_id("n", item) for item in [first, *variants]}) == 5


def test_observation_rejects_non_object_payload_or_invalid_window():
    import pytest
    from app.world_model.contracts import Observation, WorldError
    for override in [{"payload": []}, {"lookback_hours": -1}, {"lookback_hours": True},
                     {"resolution_minutes": 0}, {"source_version": {"not": "a version"}}]:
        args = dict(entity_type="telemetry", external_key="r1", source="telemetry",
                    backend="fixture", payload={"points": []})
        with pytest.raises(WorldError) as caught:
            Observation.from_payload(**(args | override))
        assert caught.value.category == "schema"
