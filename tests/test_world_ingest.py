def test_ingest_inventory_retry_keeps_validated_copies(tmp_path):
    from app.world_model.store import WorldStoreService
    from app.world_model.ingest import IngestPipelineService
    from tests.world_helpers import fetch_fixture
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="a", namespace="fixture:test")
    result = fetch_fixture("inventory")
    first = ingest.ingest("inventory", result)
    before = store.counts(run_id="a", namespace="fixture:test")
    again = ingest.ingest("inventory", result)
    assert first == again
    assert store.counts(run_id="a", namespace="fixture:test") == before
    result.records[0]["display_name"] = "not the captured name"
    captured = store.read(run_id="a", namespace="fixture:test", snapshot_id=first.snapshot_id)
    assert all(o.payload["display_name"] != "not the captured name" for o in captured)
    assert {o.backend for o in captured} == {"fixture"}
    store.close()


def test_invalid_batch_is_classified_without_partial_ingestion(tmp_path):
    import pytest
    from app.sources.base import SourceResult
    from app.world_model.contracts import WorldError
    from app.world_model.ingest import IngestPipelineService
    from app.world_model.store import WorldStoreService
    from tests.world_helpers import fetch_fixture
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="a", namespace="n")
    good = fetch_fixture("inventory")
    for name, result in [("unknown",good), ("policy",good),
        ("inventory",good.model_copy(update={"records": [good.records[0], {"broken": "private"}]}))]:
        with pytest.raises(WorldError) as caught:
            ingest.ingest(name, result)
        assert caught.value.category in {"schema", "provenance"}
        assert "private" not in str(caught.value)
    assert store.counts(run_id="a", namespace="n")["observations"] == 0
    store.close()


def test_policy_lineage_preserves_measurement_and_fetch_but_not_fetch_identity(tmp_path):
    from app.source_metadata import SourceProvenance
    from app.world_model.ingest import IngestPipelineService
    from app.world_model.store import WorldStoreService
    from tests.world_helpers import fetch_fixture
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="a", namespace="n")
    result = fetch_fixture("policy").model_copy(update={"backend":"live"})
    result.provenance = SourceProvenance(provider="zetaris", object_name="policy_rules",
        manifest_object="policy_manifest", snapshot_id="snapshot-a", schema_version=1,
        requested_scope_hash="scope", content_sha256="content", row_count=len(result.records),
        expected_count=len(result.records), complete=True, observed_at_utc="2026-10-25T00:00:00Z",
        fetched_at_utc="2026-10-26T01:00:00Z", query_sha256="query")
    first = ingest.ingest("policy", result)
    result.provenance = result.provenance.model_copy(update={"fetched_at_utc":"2026-10-26T02:00:00Z"})
    second = ingest.ingest("policy", result)
    assert first == second
    obs = store.read(run_id="a", namespace="n", snapshot_id=first.snapshot_id)[0]
    assert obs.payload["_provenance"]["snapshot_id"] == "snapshot-a"
    assert obs.payload["_provenance"]["content_sha256"] == "content"
    assert obs.measured_at == "2026-10-25T00:00:00Z"
    assert obs.fetched_at == "2026-10-26T01:00:00Z"
    store.close()
