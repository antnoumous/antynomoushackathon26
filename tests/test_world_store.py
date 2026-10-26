from pathlib import Path
import stat


def test_retry_reopen_and_read_preserve_one_observation(tmp_path):
    from app.world_model.contracts import Observation
    from app.world_model.store import WorldStoreService
    path = tmp_path / "world.sqlite3"
    obs = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"name": "one"})
    store = WorldStoreService(path)
    first = store.put_batch(run_id="run-a", namespace="n", source="inventory",
                           observations=[obs], complete=True)
    assert store.counts(run_id="run-a", namespace="n") == {
        "entities": 1, "observations": 1, "snapshots": 1, "relationships": 1}
    store.close()
    store = WorldStoreService(path)
    again = store.put_batch(run_id="run-a", namespace="n", source="inventory",
                           observations=[obs], complete=True)
    assert first == again
    assert store.counts(run_id="run-a", namespace="n")["observations"] == 1
    assert store.read(run_id="run-a", namespace="n", snapshot_id=first.snapshot_id)[0].payload == {"name": "one"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    store.close()
    store.close()


def test_mid_batch_sql_failure_rolls_back_every_row_then_retry_succeeds(tmp_path):
    import sqlite3
    import pytest
    from app.world_model.contracts import Observation, WorldError
    from app.world_model.store import WorldStoreService
    path = tmp_path / "world.sqlite3"
    store = WorldStoreService(path)
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TRIGGER fail_second BEFORE INSERT ON observations
            WHEN (SELECT COUNT(*) FROM observations) = 1
            BEGIN SELECT RAISE(ABORT, 'private-transaction-detail'); END""")
    items = [Observation.from_payload(entity_type="resource", external_key=key,
        source="inventory", backend="fixture", payload={"name": key}) for key in ("r1", "r2")]
    with pytest.raises(WorldError) as caught:
        store.put_batch(run_id="run-a", namespace="n", source="inventory",
                        observations=items, complete=True)
    assert caught.value.category == "storage"
    assert "private-transaction-detail" not in str(caught.value)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0
        db.execute("DROP TRIGGER fail_second")
    store.close()
    store = WorldStoreService(path)
    ref = store.put_batch(run_id="run-a", namespace="n", source="inventory",
                          observations=items, complete=True)
    assert len(store.read(run_id="run-a", namespace="n", snapshot_id=ref.snapshot_id)) == 2
    store.close()


def test_namespace_run_and_empty_snapshot_cannot_reuse_old_facts(tmp_path):
    import pytest
    from app.world_model.contracts import Observation, WorldError
    from app.world_model.store import WorldStoreService
    store = WorldStoreService(tmp_path / "world.sqlite3")
    item = Observation.from_payload(entity_type="policy", external_key="R-1", source="policy",
                                    backend="fixture", payload={"rule": "R-1"})
    old = store.put_batch(run_id="a", namespace="n", source="policy", observations=[item], complete=True)
    for run, namespace in [("b", "n"), ("a", "other")]:
        with pytest.raises(WorldError) as caught:
            store.read(run_id=run, namespace=namespace, snapshot_id=old.snapshot_id)
        assert caught.value.category == "context"
    empty = store.put_batch(run_id="b", namespace="n", source="policy", observations=[], complete=True)
    missing = store.put_batch(run_id="b", namespace="n", source="policy", observations=[], complete=False)
    assert store.read(run_id="b", namespace="n", snapshot_id=empty.snapshot_id) == ()
    assert store.snapshot(run_id="b", namespace="n", snapshot_id=empty.snapshot_id).complete
    assert not store.snapshot(run_id="b", namespace="n", snapshot_id=missing.snapshot_id).complete
    store.close()


def test_unknown_schema_and_corrupt_file_are_rejected_without_overwriting(tmp_path):
    import sqlite3
    import pytest
    from app.world_model.contracts import WorldError
    from app.world_model.store import WorldStoreService
    for corrupt in [False, True]:
        path = tmp_path / ("corrupt.sqlite3" if corrupt else "future.sqlite3")
        if corrupt:
            path.write_bytes(b"not a sqlite database; preserve this")
        else:
            with sqlite3.connect(path) as db:
                db.execute("PRAGMA user_version=42")
                db.execute("CREATE TABLE private_data(value TEXT)")
                db.execute("INSERT INTO private_data VALUES ('preserve')")
        before = path.read_bytes()
        with pytest.raises(WorldError) as caught:
            WorldStoreService(path)
        assert caught.value.category == "schema"
        assert path.read_bytes() == before


def test_row_payload_and_page_limits_fail_atomically(tmp_path):
    import pytest
    from app.world_model.contracts import Observation, WorldError
    from app.world_model.store import WorldStoreService
    items = [Observation.from_payload(entity_type="resource", external_key=key,
        source="inventory", backend="fixture", payload={"name": key}) for key in ("r1", "r2")]
    store = WorldStoreService(tmp_path / "row.sqlite3", max_observations=1)
    with pytest.raises(WorldError) as caught:
        store.put_batch(run_id="a", namespace="n", source="inventory", observations=items, complete=True)
    assert caught.value.category == "limit"
    assert store.counts(run_id="a", namespace="n")["observations"] == 0
    for _ in range(2):
        store.put_batch(run_id="a", namespace="n", source="inventory", observations=items[:1], complete=True)
    assert store.counts(run_id="a", namespace="n")["observations"] == 1
    store.close()
    big = Observation.from_payload(entity_type="resource", external_key="large", source="inventory",
                                    backend="fixture", payload={"data": "x"*256_000})
    for name, budgets in [("payload", {"max_payload_bytes": 30}),
                          ("page", {"max_database_bytes": 128*1024})]:
        store = WorldStoreService(tmp_path / (name + ".sqlite3"), **budgets)
        with pytest.raises(WorldError) as caught:
            store.put_batch(run_id="a", namespace="n", source="inventory", observations=[big], complete=True)
        assert caught.value.category == "limit"
        assert store.counts(run_id="a", namespace="n")["observations"] == 0
        store.close()


def test_lock_wait_is_bounded_and_failed_write_can_recover(tmp_path):
    import sqlite3, time
    import pytest
    from app.world_model.contracts import WorldError
    from app.world_model.store import WorldStoreService
    path = tmp_path / "lock.sqlite3"
    store = WorldStoreService(path)
    other = sqlite3.connect(path)
    other.execute("BEGIN EXCLUSIVE")
    started = time.monotonic()
    try:
        with pytest.raises(WorldError) as caught:
            store.put_batch(run_id="a", namespace="n", source="policy", observations=[], complete=True)
        assert caught.value.category == "storage"
        assert time.monotonic() - started < 1.5
    finally:
        other.rollback()
        other.close()
    ref = store.put_batch(run_id="a", namespace="n", source="policy", observations=[], complete=True)
    assert ref.complete
    store.close()


def test_rebuilt_relationships_and_returned_copies_preserve_world(tmp_path):
    import sqlite3
    from app.world_model.contracts import Observation
    from app.world_model.store import WorldStoreService
    path = tmp_path / "world.sqlite3"
    store = WorldStoreService(path)
    obs = Observation.from_payload(entity_type="resource", external_key="r1", source="inventory",
        backend="fixture", payload={"tags": {"schedule": "month-end"}})
    ref = store.put_batch(run_id="a", namespace="n", source="inventory", observations=[obs], complete=True)
    original = store.read(run_id="a", namespace="n", snapshot_id=ref.snapshot_id)
    original[0].payload["tags"]["schedule"] = "changed"
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM relationships")
    store.rebuild_projections()
    assert store.counts(run_id="a", namespace="n")["relationships"] == 1
    assert store.read(run_id="a", namespace="n", snapshot_id=ref.snapshot_id)[0].payload == {
        "tags": {"schedule": "month-end"}}
    store.close()


def test_closed_store_errors_are_classified(tmp_path):
    import pytest
    from app.world_model.contracts import WorldError
    from app.world_model.store import WorldStoreService
    store = WorldStoreService(tmp_path / "world.sqlite3")
    store.close()
    with pytest.raises(WorldError) as caught:
        store.counts(run_id="a", namespace="n")
    assert caught.value.category == "storage"
