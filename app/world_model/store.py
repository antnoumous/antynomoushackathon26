from __future__ import annotations

from dataclasses import asdict
import hashlib
from functools import wraps
import json
from pathlib import Path
import sqlite3
from typing import Sequence

from app.world_model.contracts import Observation, SnapshotRef, WorldError
from app.world_model.identity import canonical_json, entity_id, observation_id


def _storage_errors(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (sqlite3.Error, OSError) as exc:
            category = "limit" if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_FULL else "storage"
            raise WorldError(category) from None
    return guarded


class WorldStoreService:
    """A single-writer, append-only canonical store with run-scoped snapshots."""

    def __init__(self, path: Path, *, max_observations: int = 10_000,
                 max_payload_bytes: int = 2*1024*1024,
                 max_database_bytes: int = 128*1024*1024) -> None:
        if any(type(x) is not int or x <= 0 for x in
               (max_observations, max_payload_bytes, max_database_bytes)):
            raise WorldError("configuration")
        self.max_observations = max_observations
        self.max_payload_bytes = max_payload_bytes
        self.path = Path(path)
        self._closed = True
        self._db = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.path.is_symlink():
                raise WorldError("configuration")
            self.path.touch(mode=0o600, exist_ok=True)
            self.path.chmod(0o600)
            self._db = sqlite3.connect(self.path, timeout=0.25)
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA busy_timeout=250")
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            expected = {"entities", "observations", "snapshots", "members", "run_snapshots", "relationships"}
            if version not in (0, 1) or (version == 0 and tables) or (version == 1 and tables != expected):
                raise WorldError("schema")
            page_size = self._db.execute("PRAGMA page_size").fetchone()[0]
            if self._db.execute("PRAGMA page_count").fetchone()[0] * page_size > max_database_bytes:
                raise WorldError("limit")
            self._db.execute(f"PRAGMA max_page_count={max(1, max_database_bytes // page_size)}")
            self._db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL,
                    entity_type TEXT NOT NULL, external_key TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id),
                    namespace TEXT NOT NULL, record_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL, source TEXT NOT NULL,
                    complete INTEGER NOT NULL, degraded INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS members (
                    snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    observation_id TEXT NOT NULL REFERENCES observations(id),
                    PRIMARY KEY(snapshot_id, observation_id));
                CREATE TABLE IF NOT EXISTS run_snapshots (
                    run_id TEXT NOT NULL, namespace TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    PRIMARY KEY(run_id, namespace, snapshot_id));
                CREATE TABLE IF NOT EXISTS relationships (
                    entity_id TEXT NOT NULL REFERENCES entities(id),
                    snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    kind TEXT NOT NULL, PRIMARY KEY(entity_id, snapshot_id, kind));
                PRAGMA user_version=1;
                COMMIT;
            """)
            self._closed = False
        except (sqlite3.Error, OSError, WorldError) as exc:
            if self._db is not None:
                self._db.close()
            if isinstance(exc, WorldError):
                raise
            code = getattr(exc, "sqlite_errorcode", None)
            category = ("schema" if code in (sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_CORRUPT)
                        else "limit" if code == sqlite3.SQLITE_FULL else "storage")
            raise WorldError(category) from None

    @_storage_errors
    def put_batch(self, *, run_id: str, namespace: str, source: str,
                  observations: Sequence[Observation], complete: bool,
                  degraded: bool = False) -> SnapshotRef:
        if not run_id or not namespace or source not in {"inventory", "iac", "policy", "telemetry"}:
            raise WorldError("provenance")
        if any(item.source != source for item in observations):
            raise WorldError("provenance")
        pairs = sorted({observation_id(namespace, item): item for item in observations}.items())
        ids = tuple(key for key, _ in pairs)
        snapshot_id = hashlib.sha256(canonical_json({"schema": 1, "namespace": namespace,
            "source": source, "complete": complete, "degraded": degraded,
            "observations": ids}).encode()).hexdigest()
        if any(len(item.payload_json.encode("utf-8")) > self.max_payload_bytes for _, item in pairs):
            raise WorldError("limit")
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            existing = {row[0] for row in self._db.execute("""SELECT DISTINCT m.observation_id
                FROM members m JOIN run_snapshots r ON r.snapshot_id=m.snapshot_id
                WHERE r.run_id=?""", (run_id,))}
            if len(existing | set(ids)) > self.max_observations:
                raise WorldError("limit")
            for oid, item in pairs:
                eid = entity_id(namespace, item)
                self._db.execute("INSERT OR IGNORE INTO entities VALUES (?,?,?,?)",
                    (eid, namespace, item.entity_type, item.external_key))
                self._db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?)",
                    (oid, eid, namespace, canonical_json(asdict(item))))
            self._db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?)",
                (snapshot_id, namespace, source, int(complete), int(degraded)))
            self._db.executemany("INSERT OR IGNORE INTO members VALUES (?,?)",
                [(snapshot_id, oid) for oid in ids])
            self._db.execute("INSERT OR IGNORE INTO run_snapshots VALUES (?,?,?)",
                (run_id, namespace, snapshot_id))
            self._db.executemany("INSERT OR IGNORE INTO relationships VALUES (?,?,?)",
                [(entity_id(namespace, item), snapshot_id, "observed_in") for _, item in pairs])
        return SnapshotRef(snapshot_id, source, ids, bool(complete), bool(degraded))

    @_storage_errors
    def snapshot(self, *, run_id: str, namespace: str, snapshot_id: str) -> SnapshotRef:
        row = self._db.execute("""SELECT s.source,s.complete,s.degraded FROM snapshots s
            JOIN run_snapshots r ON r.snapshot_id=s.id
            WHERE r.run_id=? AND r.namespace=? AND s.namespace=? AND s.id=?""",
            (run_id, namespace, namespace, snapshot_id)).fetchone()
        if row is None:
            raise WorldError("context")
        ids = tuple(x[0] for x in self._db.execute(
            "SELECT observation_id FROM members WHERE snapshot_id=? ORDER BY observation_id",
            (snapshot_id,)))
        return SnapshotRef(snapshot_id, row[0], ids, bool(row[1]), bool(row[2]))

    @_storage_errors
    def read(self, *, run_id: str, namespace: str, snapshot_id: str) -> tuple[Observation, ...]:
        self.snapshot(run_id=run_id, namespace=namespace, snapshot_id=snapshot_id)
        rows = self._db.execute("""SELECT o.record_json FROM observations o
            JOIN members m ON m.observation_id=o.id
            WHERE m.snapshot_id=? AND o.namespace=? ORDER BY o.id""", (snapshot_id, namespace))
        return tuple(Observation(**json.loads(row[0])) for row in rows)

    @_storage_errors
    def counts(self, *, run_id: str, namespace: str) -> dict[str, int]:
        refs = self._db.execute("""SELECT COUNT(DISTINCT o.id),COUNT(DISTINCT o.entity_id)
            FROM observations o JOIN members m ON m.observation_id=o.id
            JOIN run_snapshots r ON r.snapshot_id=m.snapshot_id
            WHERE r.run_id=? AND r.namespace=? AND o.namespace=?""",
            (run_id, namespace, namespace)).fetchone()
        snapshots = self._db.execute("SELECT COUNT(*) FROM run_snapshots WHERE run_id=? AND namespace=?",
            (run_id, namespace)).fetchone()[0]
        relationships = self._db.execute("""SELECT COUNT(*) FROM relationships t
            JOIN run_snapshots r ON r.snapshot_id=t.snapshot_id
            WHERE r.run_id=? AND r.namespace=?""", (run_id, namespace)).fetchone()[0]
        return {"entities": refs[1], "observations": refs[0],
                "snapshots": snapshots, "relationships": relationships}

    @_storage_errors
    def rebuild_projections(self) -> None:
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("DELETE FROM relationships")
            self._db.execute("""INSERT INTO relationships
                SELECT DISTINCT o.entity_id,m.snapshot_id,'observed_in'
                FROM observations o JOIN members m ON m.observation_id=o.id""")

    def close(self) -> None:
        if not self._closed:
            self._db.close()
            self._closed = True
