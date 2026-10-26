import pytest
from app.models import MetricSeries
from app.world_model.store import WorldStoreService
from app.world_model.ingest import IngestPipelineService
from app.world_model.context import ContextBuilderService
from tests.world_helpers import fetch_fixture


@pytest.fixture
def seeded_world(tmp_path):
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="run-test", namespace="fixture:test")
    inventory = fetch_fixture("inventory")
    refs = {name+"_snapshot": ingest.ingest(name, result).snapshot_id for name,result in
        (("inventory", inventory), ("iac",fetch_fixture("iac")), ("policy",fetch_fixture("policy")))}
    rid = next(r["resource_id"] for r in inventory.records if r.get("tags",{}).get("schedule") == "month-end")
    short, long = [MetricSeries(**next(r for r in fetch_fixture("telemetry",lookback_hours=h).records
                                      if r["resource_id"] == rid)) for h in (168,744)]
    builder = ContextBuilderService(store,run_id="run-test",namespace="fixture:test")
    try:
        yield store, ingest, builder, refs, rid, short, long
    finally:
        store.close()


def test_context_uses_source_models_and_current_snapshot(tmp_path):
    from app.models import Resource, IaCDeclaration
    from app.analysis import match_iac
    from app.world_model.store import WorldStoreService
    from app.world_model.ingest import IngestPipelineService
    from app.world_model.context import ContextBuilderService
    from tests.world_helpers import fetch_fixture
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="a", namespace="fixture:test")
    results = {name: fetch_fixture(name) for name in ("inventory", "iac", "policy")}
    refs = {name+"_snapshot": ingest.ingest(name, result).snapshot_id for name,result in results.items()}
    raw = next(r for r in results["inventory"].records if r.get("tags",{}).get("schedule") == "month-end")
    resource = Resource(**raw)
    context = ContextBuilderService(store, run_id="a", namespace="fixture:test").build(
        resource_id=resource.resource_id, **refs, telemetry_snapshot=None,
        lookback_hours=168, resolution_minutes=5)
    assert context.complete
    assert context.resource == resource
    rule, declaration = match_iac(resource, [IaCDeclaration(**r) for r in results["iac"].records])
    assert (context.iac_match_rule, context.declaration) == (rule, declaration)
    assert {r.rule_id for r in context.rules} == {r["rule_id"] for r in results["policy"].records}
    assert context.selection.observation_ids
    store.close()


def test_builder_keeps_short_and_long_windows_and_pinned_replay(seeded_world):
    store, ingest, builder, refs, rid, short, long = seeded_world
    a = ingest.ingest_series(rid, short, backend="fixture", degraded=False)
    b = ingest.ingest_series(rid, long, backend="fixture", degraded=False)
    before = builder.build(resource_id=rid,**refs,telemetry_snapshot=a.snapshot_id,
                           lookback_hours=168,resolution_minutes=short.resolution_minutes)
    after = builder.build(resource_id=rid,**refs,telemetry_snapshot=b.snapshot_id,
                          lookback_hours=744,resolution_minutes=long.resolution_minutes)
    assert before.series.lookback_hours == 168
    assert after.series.lookback_hours == 744
    assert before.selection.observation_ids != after.selection.observation_ids
    before.resource.tags["schedule"] = "not original"
    before.series.points.clear()
    replay = builder.replay(before.selection)
    assert replay.resource.tags["schedule"] == "month-end"
    assert replay.series.model_dump() == short.model_dump()
    store.rebuild_projections()
    assert builder.replay(before.selection).selection == replay.selection


@pytest.mark.parametrize("missing", ["iac", "policy", "inventory", "budget", "window"])
def test_incomplete_essential_context_or_budget_cannot_claim_success(seeded_world, missing):
    store, ingest, builder, refs, rid, short, long = seeded_world
    refs = dict(refs)
    a = ingest.ingest_series(rid, short, backend="fixture", degraded=False)
    if missing in {"inventory", "iac", "policy"}:
        refs[missing+"_snapshot"] = ingest.ingest(missing, fetch_fixture(missing), complete=False).snapshot_id
    if missing == "budget":
        builder = ContextBuilderService(store,run_id="run-test",namespace="fixture:test",max_records=1)
    ctx = builder.build(resource_id=rid,**refs,telemetry_snapshot=a.snapshot_id,
        lookback_hours=744 if missing == "window" else 168,resolution_minutes=short.resolution_minutes)
    assert not ctx.complete
    assert ctx.reasons
    if missing in {"policy", "budget"}:
        assert ctx.rules == ()
    if missing == "budget":
        assert len(ctx.selection.observation_ids) <= 1


def test_later_empty_policy_cannot_rewrite_a_pinned_context(seeded_world):
    store, ingest, builder, refs, rid, short, long = seeded_world
    old = builder.build(resource_id=rid,**refs,telemetry_snapshot=None,lookback_hours=168,resolution_minutes=5)
    result = fetch_fixture("policy").model_copy(update={"records": []})
    changed = ingest.ingest("policy",result)
    fresh = builder.build(resource_id=rid,**(refs|{"policy_snapshot":changed.snapshot_id}),
                           telemetry_snapshot=None,lookback_hours=168,resolution_minutes=5)
    assert fresh.complete and fresh.rules == ()
    assert builder.replay(old.selection).rules == old.rules


def test_foreign_resource_telemetry_is_not_relabelled(seeded_world):
    from app.world_model.contracts import WorldError
    store, ingest, builder, refs, rid, short, long = seeded_world
    with pytest.raises(WorldError) as caught:
        ingest.ingest_series("other-resource",short,backend="fixture",degraded=False)
    assert caught.value.category == "provenance"
