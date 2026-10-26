from pathlib import Path
import json


def test_real_loop_consumes_world_context_and_preserves_revision(tmp_path, monkeypatch):
    from app.pipeline import run_pipeline
    from app.world_model.context import ContextBuilderService
    calls = []
    original = ContextBuilderService.build
    def tracking(self, **kwargs):
        context = original(self, **kwargs)
        calls.append(list(context.selection.observation_ids))
        return context
    monkeypatch.setattr(ContextBuilderService,"build",tracking)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    report,_ = run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios/example_1"))
    world = report.summary["integrations"]["meterless_world_model"]
    assert world["status"] == "used"
    assert world["store"].endswith("world.sqlite3")
    assert world["sources"]["telemetry"]["backends"] == ["fixture"]
    assert {"Scout","Skeptic"} <= set(world["consumers"])
    assert [f.status for f in report.findings if f.resource_id.endswith("bbb2")] == ["rejected","revised"]
    events = [json.loads(line) for line in Path(report.trace_path).read_text().splitlines()]
    selected = [json.loads(e["output_summary"]) for e in events if e["action"] == "world_context"]
    assert selected and all(e["selection"]["observation_ids"] for e in selected)
    assert [e["selection"]["observation_ids"] for e in selected] == calls
    assert any(e["action"] == "world_ingest" and e["input_summary"] == "telemetry" for e in events)
    assert events[-1]["action"] == "synthesise"


def test_world_constructor_failure_returns_partial_not_direct_read_success(tmp_path,monkeypatch):
    from app.pipeline import run_pipeline
    from app.world_model.contracts import WorldError
    import app.world_model.runtime as runtime
    def fail(*args,**kwargs):
        raise WorldError("storage")
    monkeypatch.setattr(runtime,"WorldStoreService",fail)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    report,_ = run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios/example_1"))
    assert report.status == "partial"
    assert report.findings == []
    world = report.summary["integrations"]["meterless_world_model"]
    assert world["status"] == "failed" and "storage" in world["failures"]
    assert report.summary["resources_examined"] == 0
    states=[json.loads(line) for line in (tmp_path / ("state-"+report.run_id+".jsonl")).read_text().splitlines()]
    assert states[-1]["kind"] == "report" and states[-1]["status"] == report.status


def test_context_failure_abstains_only_affected_resource_and_closes_store(tmp_path,monkeypatch):
    import pytest, sqlite3
    from app.pipeline import run_pipeline
    from app.world_model.context import ContextBuilderService
    from app.world_model.contracts import WorldError
    import app.world_model.runtime as runtime
    original = ContextBuilderService.build
    def broken(self,**kwargs):
        if kwargs["resource_id"].endswith("bbb2"):
            raise WorldError("context")
        return original(self,**kwargs)
    stores = []
    real_store = runtime.WorldStoreService
    def tracked(*args,**kwargs):
        store = real_store(*args,**kwargs)
        stores.append(store)
        return store
    monkeypatch.setattr(runtime,"WorldStoreService",tracked)
    monkeypatch.setattr(ContextBuilderService,"build",broken)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    report,_ = run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios/example_1"))
    assert report.status == "partial"
    assert not any(f.resource_id.endswith("bbb2") for f in report.findings)
    assert any(u.resource_id.endswith("bbb2") for u in report.undetermined)
    assert any(f.resource_class == "block_volume" for f in report.findings)
    with pytest.raises(sqlite3.ProgrammingError):
        stores[0]._db.execute("SELECT 1")


def test_world_hashes_never_expand_writer_numeric_allowlist(tmp_path):
    import io
    from app.agents.base import AgentContext
    from app.agents.writer import Writer
    from app.config import RunConfig
    from app.generator import RulesGenerator
    from app.state import RunState
    from app.trace import Tracer
    from app.evidence import EvidenceLedger
    config=RunConfig(sample_mode=True)
    state=RunState(config.run_id,tmp_path)
    trace=Tracer(config.run_id,tmp_path,stream=io.StringIO())
    ledger=EvidenceLedger()
    ledger.add(source="inventory",kind="resource",resource_id="r",summary="proof",
               payload={"ocpus":1,"_world":{"observation_ids":["999987654321"]}})
    ctx=AgentContext(config,{},RulesGenerator(),state,trace,ledger)
    allowed,computed=Writer(ctx).allowed_figures([])
    assert "999987654321" not in allowed and "999987654321" not in computed
    state.close();trace.close()


def test_locked_store_abstains_and_closes_actual_connection(tmp_path,monkeypatch):
    import sqlite3,pytest
    import app.world_model.runtime as runtime
    from app.pipeline import run_pipeline
    actual=runtime.WorldStoreService
    stores=[];locks=[]
    def locked(*args,**kwargs):
        store=actual(*args,**kwargs);stores.append(store)
        lock=sqlite3.connect(store.path);lock.execute("BEGIN EXCLUSIVE");locks.append(lock)
        return store
    monkeypatch.setattr(runtime,"WorldStoreService",locked)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    try:
        report,_=run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios/example_1"))
        assert report.status == "partial" and report.findings == []
        assert "storage" in report.summary["integrations"]["meterless_world_model"]["failures"]
        with pytest.raises(sqlite3.ProgrammingError):
            stores[0]._db.execute("SELECT 1")
    finally:
        for lock in locks:lock.rollback();lock.close()


def test_ambiguous_masked_telemetry_join_abstains_instead_of_first_match(tmp_path):
    from copy import deepcopy
    from tests.test_loop import build
    from tests.world_helpers import fetch_fixture
    from app.loop import Orchestrator
    cfg,ctx=build(tmp_path)
    class Ambiguous:
        def fetch(self,scope):
            result=fetch_fixture("telemetry",lookback_hours=scope.lookback_hours)
            copies=deepcopy(result.records)
            for row in copies:row["points"][0]["value"]+=10
            return result.model_copy(update={"records":result.records+copies})
    ctx.sources["telemetry"]=Ambiguous()
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "partial"
        assert not any(f.resource_class == "compute_instance" for f in report.findings)
        assert report.summary["integrations"]["meterless_world_model"]["status"] == "failed"
    finally:
        ctx.state.close();ctx.trace.close()


def test_published_evidence_resolves_into_consumed_world_observations(tmp_path):
    import sqlite3
    from tests.test_loop import build
    from app.loop import Orchestrator
    cfg,ctx=build(tmp_path)
    try:
        report=Orchestrator(ctx).run()
        with sqlite3.connect(ctx.world.store.path) as db:
            for finding in report.findings:
                for evidence in ctx.ledger.resolve(finding.evidence_refs):
                    ids=evidence.payload["_world"]["observation_ids"]
                    assert ids
                    for oid in ids:
                        assert db.execute("SELECT COUNT(*) FROM observations WHERE id=? AND namespace=?",
                                          (oid,ctx.world.namespace)).fetchone()[0] == 1
    finally:
        ctx.state.close();ctx.trace.close()


def test_missing_skeptic_pin_is_partial_not_an_accepted_finding(tmp_path,monkeypatch):
    from app.pipeline import run_pipeline
    from app.world_model.runtime import WorldRuntime
    from app.world_model.contracts import WorldError
    real=WorldRuntime.for_candidate
    def missing(self,candidate_id):
        if self.pins[candidate_id].resource_id.endswith("bbb2"):
            raise WorldError("context")
        return real(self,candidate_id)
    monkeypatch.setattr(WorldRuntime,"for_candidate",missing)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    report,_=run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios/example_1"))
    assert report.status == "partial"
    assert not any(f.resource_id.endswith("bbb2") for f in report.findings)
    assert any(u.resource_id.endswith("bbb2") for u in report.undetermined)


def test_real_resource_cap_outranks_world_failure_but_preserves_both(tmp_path,monkeypatch):
    from app.pipeline import run_pipeline
    from app.world_model.context import ContextBuilderService
    from app.world_model.contracts import WorldError
    def failed(*args,**kwargs):raise WorldError("storage")
    monkeypatch.setattr(ContextBuilderService,"build",failed)
    monkeypatch.setenv("LOGS_DIR",str(tmp_path))
    report,_=run_pipeline({"sample_mode":True,"caps":{"max_resources":1}},
                           scenario_dir=Path("data/scenarios/example_1"))
    assert report.status == "capped" and "max_resources" in report.caps_hit
    assert report.summary["integrations"]["meterless_world_model"]["status"] == "failed"
    assert report.findings == []


def test_candidate_pins_cannot_be_rewritten_by_later_snapshots(tmp_path):
    import pytest
    from dataclasses import replace
    from tests.test_loop import build
    from app.loop import Orchestrator
    from app.world_model.contracts import WorldError
    cfg,ctx=build(tmp_path)
    try:
        Orchestrator(ctx).run()
        candidate_id=next(iter(ctx.world.pins))
        original=ctx.world.pins[candidate_id]
        from app.world_model.contracts import ResourceContext
        # Pin checks are identity-only and must reject a differing selection before any DB read.
        bad=ResourceContext(replace(original,observation_ids=("not-the-original",)),
            next(iter(ctx.state.facts["resources"].values())),None,None,(),None,True,())
        with pytest.raises(WorldError) as caught:
            ctx.world.pin(candidate_id,bad)
        assert caught.value.category == "context"
        assert ctx.world.pins[candidate_id] == original
    finally:
        ctx.state.close();ctx.trace.close()
