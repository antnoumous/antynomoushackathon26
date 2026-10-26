"""Reproductions from the independent whole-branch review; no real credentials."""
import json
from pathlib import Path
import pytest


@pytest.mark.parametrize("bad",["meterless/catalog-secret-sentinel","meterless/"+"x"*260,
                                "meterless/bad\nroute","meterless/\ud800"])
def test_discovery_rejects_secret_echo_or_unsafe_unbounded_ids(bad):
    from app.providers.meterless_settings import MeterlessSettings,discover
    settings=MeterlessSettings(token="catalog-secret-sentinel")
    result=discover(settings,transport=lambda *a,**k:{"data":[{"id":"meterless/local"},{"id":bad}]},timeout_s=1)
    assert result.state == "offline"
    assert result.model_ids == ()
    assert "catalog-secret-sentinel" not in repr(result)


@pytest.mark.parametrize("encoded",[False,True])
def test_publication_rejects_catalog_credentials_before_any_copy(tmp_path,encoded):
    from tests.test_meterless_acceptance import run,ENV
    from scripts.verify_meterless_sponsors import export_proof
    from app.providers.meterless_settings import MeterlessError
    run(tmp_path)
    raw=tmp_path / "proof";target=tmp_path / "public"
    path=raw / "base-outcomes.json"
    data=json.loads(path.read_text())
    token=ENV["METERLESS_TOKEN"]
    data["readiness"]={"state":"online","model_ids":["meterless/local","meterless/"+token]}
    rendered=json.dumps(data)
    if encoded:
        rendered=rendered.replace(token,"".join(chr(92)+"u"+format(ord(c),"04x") for c in token))
    path.write_text(rendered)
    original=path.read_bytes()
    with pytest.raises(MeterlessError) as caught:
        export_proof(raw,target,runtime_env=ENV)
    assert caught.value.category == "schema" and token not in str(caught.value)
    assert not target.exists() and path.read_bytes() == original


@pytest.mark.parametrize("name,context,field",[
    ("finding_claim",{"rule_id":"R-2","resource_name":"ip-x","stats":{}},"claim"),
    ("verdict_reason",{"reason_key":"frequency_mismatch"},"reason"),
    ("run_summary",{"resources":6,"sources":4,"accepted":3,"rejected":0,"undetermined":4},"summary")])
@pytest.mark.parametrize("codepoint",[0xD800,0xDFFF])
def test_non_scalar_model_text_is_schema_fallback_not_success(name,context,field,codepoint):
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    invalid={field:"bad "+chr(codepoint),"confidence":0.8}
    gen=MeterlessGenerator(MeterlessSettings(token="unicode-test-sentinel"),transport=lambda *a,**k:{
        "choices":[{"message":{"content":json.dumps(invalid)}}]})
    out=gen.complete(prompt="",schema={"name":name},context=context)
    out[field].encode("utf-8")
    assert gen.diagnostics()["successes"] == 0 and gen.diagnostics()["fallbacks"] == 1
    assert gen.recorder.outcomes()[0].category == "schema"


def test_http_escaped_surrogate_summary_finishes_with_partial_report(tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from tests.test_loop import build
    from app.generator import RulesGenerator
    from app.loop import Orchestrator
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            system=payload["messages"][0]["content"]
            name="run_summary" if '"summary"' in system else "finding_claim" if '"claim"' in system else "verdict_reason"
            user=payload["messages"][1]["content"]
            context=json.loads(user[user.index("{"):])
            result=RulesGenerator().complete(prompt="",schema={"name":name},context=context)
            if name == "run_summary":result["summary"]="invalid "+chr(0xD800)
            body=json.dumps({"choices":[{"message":{"content":json.dumps(result)}}]}).encode()
            self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers()
            try:self.wfile.write(body)
            except OSError:pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    _,ctx=build(tmp_path)
    ctx.generator=MeterlessGenerator(MeterlessSettings(base_url="http://127.0.0.1:"+str(server.server_port),token="unicode-http-sentinel"))
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "partial"
        assert report.summary["integrations"]["meterless_nightshift"]["fallbacks"] == 1
        assert ctx.state.records()[-1]["kind"] == "report"
        assert json.loads(ctx.trace.path.read_text().splitlines()[-1])["action"] == "synthesise"
    finally:
        ctx.trace.close();ctx.state.close()
        server.shutdown();server.server_close();thread.join(timeout=2)


def _stalled_ipc_frame(connection,method,url,*args):
    import struct,time
    body=json.dumps(["ok",{"value":"done"}]).encode()
    header=struct.pack("!i",len(body))
    connection._send(header[:2] if url.endswith("/header") else header+body[:1])
    time.sleep(30)
    connection._send(body)
    connection.close()


def _ipc_deadline_probe(phase):
    import time,multiprocessing
    import app.providers.meterless_transport as transport
    from app.providers.meterless_settings import MeterlessError
    transport._worker=_stalled_ipc_frame
    started=time.monotonic()
    try:
        transport.request_json("GET","http://127.0.0.1/"+phase,headers={},payload=None,timeout_s=0.5)
        category="unexpected_success"
    except MeterlessError as error:category=error.category
    print(json.dumps({"category":category,"elapsed":time.monotonic()-started,
                      "children":[child.pid for child in multiprocessing.active_children()]}),flush=True)


@pytest.mark.parametrize("phase",["header","body"])
def test_stalled_ipc_frame_cannot_block_deadline_or_leak_child(phase):
    import os,signal,subprocess,sys
    if os.name != "posix":pytest.skip("Approved Nightshift hosts are macOS/POSIX Linux")
    process=subprocess.Popen([sys.executable,"-m","tests.test_meterless_review_regressions","--ipc-probe",phase],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        try:out,err=process.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:pytest.fail("supervising thread blocked in partial IPC beyond outer deadline")
        assert process.returncode == 0,err
        result=json.loads(out)
        assert result["category"] == "timeout"
        assert result["elapsed"] < 1.5
        assert result["children"] == []
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL)
            process.communicate(timeout=2)


def test_name_only_schedule_signal_uses_pinned_resource_and_forces_wider_recheck(tmp_path,monkeypatch):
    import shutil
    from tests.test_loop import build
    from app.loop import Orchestrator
    from app.agents.skeptic import Skeptic
    scenario=tmp_path / "nightly-scenario"
    shutil.copytree("data/scenarios/example_1",scenario)
    inventory=json.loads((scenario / "inventory.json").read_text())
    row=next(r for r in inventory["resources"] if r["resource_id"].endswith("bbb2"))
    row.update(display_name="nightly-worker",tags={})
    inventory["resources"]=[row]
    (scenario / "inventory.json").write_text(json.dumps(inventory))
    (scenario / "iac.json").write_text(json.dumps({"declarations":[]}))
    _,ctx=build(tmp_path / "run",scenario=scenario)
    judge=Skeptic.judge
    def mutable_projection_changed(self,candidate,round):
        self.ctx.state.facts["resources"][candidate.resource_id].display_name="plain-worker"
        return judge(self,candidate,round)
    monkeypatch.setattr(Skeptic,"judge",mutable_projection_changed)
    try:
        report=Orchestrator(ctx,scenario_dir=scenario).run()
        events=[json.loads(line) for line in ctx.trace.path.read_text().splitlines()]
        assert any(event["action"] == "request_recheck" and "744h" in event["output_summary"] for event in events)
        cost=[f for f in report.findings if f.finding_class == "cost_waste"]
        assert [f.status for f in cost] == ["rejected","revised"]
        assert "58.0%" in cost[-1].claim and "peaks at" in cost[-1].claim
        assert report.status == "success"
    finally:ctx.trace.close();ctx.state.close()


def test_model_paraphrases_do_not_create_revisions_or_change_accounting(tmp_path):
    import shutil
    from tests.test_loop import build
    from app.generator import RulesGenerator
    from app.loop import Orchestrator
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    scenario=tmp_path / "undeclared"
    shutil.copytree("data/scenarios/example_1",scenario)
    (scenario / "iac.json").write_text(json.dumps({"declarations":[]}))
    reports=[]
    for changing in (False,True):
        calls={}
        def transport(method,url,*,headers,payload,timeout_s):
            system=payload["messages"][0]["content"]
            name="run_summary" if '"summary"' in system else "finding_claim" if '"claim"' in system else "verdict_reason"
            user=payload["messages"][1]["content"];context=json.loads(user[user.index("{"):])
            out=RulesGenerator().complete(prompt="",schema={"name":name},context=context)
            if changing and name == "finding_claim":
                key=(context["resource_name"],context["rule_id"])
                calls[key]=calls.get(key,0)+1
                out["claim"] += " Observed." if calls[key] % 2 else " Recorded."
            return {"choices":[{"message":{"content":json.dumps(out)}}]}
        _,ctx=build(tmp_path / str(changing),scenario=scenario)
        ctx.generator=MeterlessGenerator(MeterlessSettings(token="paraphrase-test-only"),transport=transport)
        try:
            report=Orchestrator(ctx,scenario_dir=scenario).run()
            reports.append(report)
            batch=[f for f in report.findings if f.resource_id.endswith("bbb2") and f.finding_class == "unattributed"]
            assert len(batch) == 1 and batch[0].status == "accepted"
        finally:ctx.trace.close();ctx.state.close()
    def conclusions(report):
        return sorted((f.resource_id,f.finding_class,f.status,json.dumps(f.impact,sort_keys=True)) for f in report.findings)
    assert conclusions(reports[0]) == conclusions(reports[1])
    for field in ("spend_audited_usd_per_month","waste_found_usd_per_month","findings_accepted","findings_rejected"):
        assert reports[0].summary[field] == reports[1].summary[field]
    assert all(report.status == "success" for report in reports)


@pytest.mark.parametrize("field,bad",[("resource_id",None),("resource_id",17),
    ("resource_id",{"private":"malformed-source-sentinel"}),("compartment_id",None),
    ("compartment_id",17),("compartment_id",["malformed-source-sentinel"])])
def test_malformed_live_namespace_input_finishes_classified_partial(tmp_path,monkeypatch,field,bad):
    from tests.test_loop import build
    from tests.world_helpers import fetch_fixture
    from app.loop import Orchestrator
    _,ctx=build(tmp_path)
    ctx.config.sample_mode=False
    monkeypatch.setenv("OCI_REGION","ap-batam-1")
    class Malformed:
        def fetch(self,scope):
            result=fetch_fixture("inventory")
            row=dict(result.records[0]);row[field]=bad
            return result.model_copy(update={"backend":"live","records":[row]})
    ctx.sources["inventory"]=Malformed()
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "partial" and not report.findings
        assert "schema" in report.summary["integrations"]["meterless_world_model"]["failures"]
        assert ctx.state.records()[-1]["kind"] == "report"
        assert ctx.state.records()[-1]["status"] == "partial"
        assert "malformed-source-sentinel" not in ctx.trace.path.read_text()+report.model_dump_json()
    finally:ctx.trace.close();ctx.state.close()


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--ipc-probe"]:_ipc_deadline_probe(sys.argv[2])
