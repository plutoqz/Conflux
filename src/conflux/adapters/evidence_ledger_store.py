"""Cross-run, append-only Evidence Ledger persistence and impact analysis."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from conflux.research_protocol import ClaimRecord, EvidenceRecord, LedgerSnapshot

from .sqlite_store import SQLiteDatabase


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default


def _digest(*parts: Any) -> str:
    payload = "\x1f".join(_json(part) if not isinstance(part, str) else part for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _row(row: Any, json_fields: Mapping[str, Any] | None = None) -> dict[str, Any]:
    item = {key: row[key] for key in row.keys()}
    for field, default in (json_fields or {}).items():
        item[field.removesuffix("_json")] = _loads(item.pop(field, None), default)
    return item


class EvidenceLedgerRepository:
    """Persist immutable ledger versions and create explicit review work."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self.db = db

    def persist_run(
        self,
        snapshot: LedgerSnapshot | Mapping[str, Any],
        claims: Iterable[ClaimRecord | Mapping[str, Any]],
        *,
        artifacts: Iterable[Mapping[str, Any]] = (),
        transformations: Iterable[Mapping[str, Any]] = (),
        project_id: str = "",
    ) -> dict[str, Any]:
        ledger = snapshot if isinstance(snapshot, LedgerSnapshot) else LedgerSnapshot.from_dict(dict(snapshot))
        claim_records = [
            item if isinstance(item, ClaimRecord) else ClaimRecord.from_dict(dict(item))
            for item in claims
        ]
        connection = self.db.connection
        now = time.time()
        source_ids: dict[str, str] = {}
        review_ids: list[str] = []
        connection.execute("BEGIN")
        try:
            for evidence in ledger.records:
                source_snapshot, review_id = self._record_source_snapshot(evidence, now=now)
                source_ids[evidence.evidence_id] = source_snapshot["snapshot_id"]
                if review_id and review_id not in review_ids:
                    review_ids.append(review_id)
                connection.execute(
                    """
                    INSERT OR IGNORE INTO ledger_evidence_items (
                        evidence_id, run_id, source_snapshot_id, subquestion_id, query_id,
                        evidence_type, relationship, visibility, claim_text, quote,
                        locator_json, limitations_json, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.evidence_id,
                        ledger.run_id,
                        source_snapshot["snapshot_id"],
                        evidence.subquestion_id,
                        evidence.query_id,
                        evidence.evidence_class or evidence.evidence_role,
                        evidence.relationship,
                        evidence.visibility,
                        evidence.claim,
                        evidence.verbatim_quote,
                        _json({"url": evidence.url, "title": evidence.document_title}),
                        _json([]),
                        _json({
                            "source_authority": evidence.source_authority,
                            "claim_fitness": evidence.claim_fitness,
                            "evidence_refs": evidence.evidence_refs,
                            "subquestion_ids": evidence.subquestion_ids,
                            "supersedes": evidence.supersedes,
                            "promoted_from": evidence.promoted_from,
                        }),
                        now,
                    ),
                )
            for claim in claim_records:
                verification = dict(claim.verification_result or {})
                connection.execute(
                    """
                    INSERT OR IGNORE INTO ledger_claims (
                        claim_id, run_id, subquestion_id, text, claim_type, importance,
                        status, confidence, verification_json, generation_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claim.claim_id,
                        ledger.run_id,
                        claim.subquestion_id,
                        claim.text,
                        claim.claim_type,
                        claim.importance,
                        str(verification.get("verdict") or "uncertain"),
                        float(verification.get("confidence") or 0.0),
                        _json(verification),
                        _json({
                            "derivation_type": claim.derivation_type,
                            "derivation_inputs": claim.derivation_inputs,
                            "generation_attribution": claim.generation_attribution,
                        }),
                        now,
                    ),
                )
                for evidence_id in claim.evidence_ids:
                    if evidence_id in source_ids:
                        evidence_record = next(
                            item for item in ledger.records if item.evidence_id == evidence_id
                        )
                        self._add_relation(
                            run_id=ledger.run_id,
                            source_kind="evidence",
                            source_id=evidence_id,
                            target_kind="claim",
                            target_id=claim.claim_id,
                            relation_type=evidence_record.relationship or "supports",
                            metadata={"verification_status": str(verification.get("verdict") or "uncertain")},
                            now=now,
                        )
                for input_id in claim.derivation_inputs:
                    kind = "claim" if input_id.startswith(f"{ledger.run_id}:claim:") else "evidence"
                    self._add_relation(
                        run_id=ledger.run_id,
                        source_kind=kind,
                        source_id=input_id,
                        target_kind="claim",
                        target_id=claim.claim_id,
                        relation_type="derived_from",
                        metadata={},
                        now=now,
                    )
            artifact_rows = list(artifacts)
            for artifact in artifact_rows:
                self._bind_artifact_rows(claim_records, artifact, project_id=project_id, now=now)
            transformation_rows = list(transformations)
            if not transformation_rows:
                transformation_rows = [{
                    "step_type": "ledger_persist",
                    "input_refs": [item.evidence_id for item in ledger.records],
                    "output_refs": [item.claim_id for item in claim_records],
                    "metadata": {
                        "snapshot_id": ledger.snapshot_id,
                        "round": ledger.round,
                        "source_statuses": {key: value for key, value in ledger.source_statuses},
                    },
                }]
            for index, transformation in enumerate(transformation_rows, start=1):
                self._record_transformation(ledger.run_id, transformation, index=index, now=now)
            for review_id in review_ids:
                self._populate_review_impacts(review_id)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {
            "run_id": ledger.run_id,
            "snapshot_id": ledger.snapshot_id,
            "source_snapshot_count": len(set(source_ids.values())),
            "evidence_count": len(ledger.records),
            "claim_count": len(claim_records),
            "artifact_count": len(artifact_rows),
            "review_ids": review_ids,
        }

    def bind_claim_artifact(
        self,
        claim_id: str,
        *,
        artifact_id: str,
        artifact_type: str,
        project_id: str = "",
        location: str = "",
    ) -> None:
        self.db.connection.execute(
            """
            INSERT OR IGNORE INTO ledger_artifact_claims (
                artifact_id, claim_id, artifact_type, project_id, location, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, claim_id, artifact_type, project_id, location, time.time()),
        )
        self.db.connection.commit()

    def source_history(self, source_identity: str) -> list[dict[str, Any]]:
        rows = self.db.connection.execute(
            "SELECT * FROM source_snapshots WHERE source_identity = ? ORDER BY created_at",
            (source_identity,),
        ).fetchall()
        return [_row(item, {"metadata_json": {}}) for item in rows]

    def run_ledger(self, run_id: str) -> dict[str, Any]:
        evidence = self.db.connection.execute(
            """
            SELECT e.*, s.source_identity, s.content_hash, s.source_type, s.url,
                   s.title, s.publisher, s.published_at, s.retrieved_at, s.status AS source_status
            FROM ledger_evidence_items e
            JOIN source_snapshots s ON s.snapshot_id = e.source_snapshot_id
            WHERE e.run_id = ? ORDER BY e.created_at, e.evidence_id
            """,
            (run_id,),
        ).fetchall()
        claims = self.db.connection.execute(
            "SELECT * FROM ledger_claims WHERE run_id = ? ORDER BY created_at, claim_id",
            (run_id,),
        ).fetchall()
        relations = self.db.connection.execute(
            "SELECT * FROM evidence_relations WHERE run_id = ? ORDER BY created_at, relation_id",
            (run_id,),
        ).fetchall()
        transformations = self.db.connection.execute(
            "SELECT * FROM ledger_transformations WHERE run_id = ? ORDER BY created_at, transformation_id",
            (run_id,),
        ).fetchall()
        return {
            "run_id": run_id,
            "evidence": [_row(item, {"locator_json": {}, "limitations_json": [], "metadata_json": {}}) for item in evidence],
            "claims": [_row(item, {"verification_json": {}, "generation_json": {}}) for item in claims],
            "relations": [_row(item, {"metadata_json": {}}) for item in relations],
            "transformations": [_row(item, {"input_refs_json": [], "output_refs_json": [], "metadata_json": {}}) for item in transformations],
        }

    def list_reviews(self, *, status: str | None = "pending", limit: int = 100) -> list[dict[str, Any]]:
        if status is None:
            rows = self.db.connection.execute(
                "SELECT * FROM evidence_review_runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self.db.connection.execute(
                "SELECT * FROM evidence_review_runs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        reviews = []
        for value in rows:
            item = _row(value, {"metadata_json": {}})
            impacts = self.db.connection.execute(
                "SELECT * FROM evidence_review_impacts WHERE review_id = ? ORDER BY target_kind, target_id",
                (item["review_id"],),
            ).fetchall()
            item["impacts"] = [_row(impact, {"metadata_json": {}}) for impact in impacts]
            reviews.append(item)
        return reviews

    def resolve_review(self, review_id: str, *, status: str = "confirmed") -> bool:
        if status not in {"confirmed", "dismissed"}:
            raise ValueError("review status must be confirmed or dismissed")
        cursor = self.db.connection.execute(
            "UPDATE evidence_review_runs SET status = ?, updated_at = ? WHERE review_id = ? AND status = 'pending'",
            (status, time.time(), review_id),
        )
        self.db.connection.commit()
        return cursor.rowcount > 0

    def _record_source_snapshot(self, evidence: EvidenceRecord, *, now: float) -> tuple[dict[str, Any], str]:
        identity = evidence.source_identity or evidence.url or evidence.document_title or evidence.source_type
        content_hash = evidence.content_hash or _digest(evidence.verbatim_quote or evidence.claim)
        snapshot_id = f"src-{_digest(identity, content_hash)[:24]}"
        previous = self.db.connection.execute(
            "SELECT * FROM source_snapshots WHERE source_identity = ? ORDER BY created_at DESC LIMIT 1",
            (identity,),
        ).fetchone()
        self.db.connection.execute(
            """
            INSERT OR IGNORE INTO source_snapshots (
                snapshot_id, source_identity, content_hash, source_type, url, title,
                publisher, published_at, retrieved_at, status, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id, identity, content_hash, evidence.source_type, evidence.url,
                evidence.document_title, evidence.publisher, evidence.published_at,
                evidence.retrieved_at,
                "available",
                _json({
                    "evidence_role": evidence.evidence_role,
                    "untrusted_content": True,
                    "prompt_injection_detected": bool(re.search(
                        r"ignore (all |any )?(previous|prior) instructions|system prompt|developer message",
                        f"{evidence.claim}\n{evidence.verbatim_quote}",
                        re.IGNORECASE,
                    )),
                }),
                now,
            ),
        )
        review_id = ""
        if previous is not None and str(previous["content_hash"]) != content_hash:
            review_id = f"review-{uuid.uuid4().hex[:16]}"
            self.db.connection.execute(
                """
                INSERT INTO evidence_review_runs (
                    review_id, source_identity, prior_snapshot_id, current_snapshot_id,
                    status, reason, requested_by_run_id, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', 'source_content_changed', ?, '{}', ?, ?)
                """,
                (review_id, identity, str(previous["snapshot_id"]), snapshot_id, evidence.evidence_id.split(":ev-", 1)[0], now, now),
            )
        row = self.db.connection.execute(
            "SELECT * FROM source_snapshots WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()
        assert row is not None
        return _row(row, {"metadata_json": {}}), review_id

    def _add_relation(self, *, run_id: str, source_kind: str, source_id: str, target_kind: str, target_id: str, relation_type: str, metadata: Mapping[str, Any], now: float) -> None:
        relation_id = f"rel-{_digest(source_kind, source_id, target_kind, target_id, relation_type)[:24]}"
        self.db.connection.execute(
            """
            INSERT OR IGNORE INTO evidence_relations (
                relation_id, run_id, source_kind, source_id, target_kind, target_id,
                relation_type, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (relation_id, run_id, source_kind, source_id, target_kind, target_id, relation_type, _json(dict(metadata)), now),
        )

    def _bind_artifact_rows(self, claims: list[ClaimRecord], artifact: Mapping[str, Any], *, project_id: str, now: float) -> None:
        artifact_id = str(artifact.get("artifact_id") or artifact.get("id") or _digest(artifact)[:16])
        artifact_type = str(artifact.get("artifact_type") or artifact.get("type") or "report")
        location = str(artifact.get("location") or artifact.get("path") or "")
        for claim in claims:
            self.db.connection.execute(
                """
                INSERT OR IGNORE INTO ledger_artifact_claims (
                    artifact_id, claim_id, artifact_type, project_id, location, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, claim.claim_id, artifact_type, str(artifact.get("project_id") or project_id), location, now),
            )

    def _record_transformation(self, run_id: str, transformation: Mapping[str, Any], *, index: int, now: float) -> None:
        input_refs = list(transformation.get("input_refs") or [])
        output_refs = list(transformation.get("output_refs") or [])
        step_type = str(transformation.get("step_type") or "unknown")
        input_hash = str(transformation.get("input_hash") or _digest(input_refs))
        output_hash = str(transformation.get("output_hash") or _digest(output_refs))
        transformation_id = str(
            transformation.get("transformation_id")
            or f"{run_id}:transform:{index:02d}:{_digest(step_type, input_hash, output_hash)[:12]}"
        )
        self.db.connection.execute(
            """
            INSERT OR IGNORE INTO ledger_transformations (
                transformation_id, run_id, step_type, input_hash, output_hash,
                input_refs_json, output_refs_json, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (transformation_id, run_id, step_type, input_hash, output_hash, _json(input_refs), _json(output_refs), _json(dict(transformation.get("metadata") or {})), now),
        )

    def _populate_review_impacts(self, review_id: str) -> None:
        review = self.db.connection.execute(
            "SELECT * FROM evidence_review_runs WHERE review_id = ?", (review_id,)
        ).fetchone()
        if review is None:
            return
        prior_snapshot_id = str(review["prior_snapshot_id"])
        claims = self.db.connection.execute(
            """
            SELECT DISTINCT c.claim_id
            FROM ledger_evidence_items e
            JOIN evidence_relations r ON r.source_kind = 'evidence' AND r.source_id = e.evidence_id
            JOIN ledger_claims c ON r.target_kind = 'claim' AND r.target_id = c.claim_id
            WHERE e.source_snapshot_id = ?
            """,
            (prior_snapshot_id,),
        ).fetchall()
        for claim_row in claims:
            claim_id = str(claim_row["claim_id"])
            self._insert_impact(review_id, "claim", claim_id, "", "source_changed", {})
            artifacts = self.db.connection.execute(
                "SELECT * FROM ledger_artifact_claims WHERE claim_id = ?", (claim_id,)
            ).fetchall()
            for artifact in artifacts:
                self._insert_impact(
                    review_id,
                    str(artifact["artifact_type"] or "artifact"),
                    str(artifact["artifact_id"]),
                    str(artifact["project_id"] or ""),
                    "source_changed",
                    {"location": str(artifact["location"] or ""), "claim_id": claim_id},
                )

    def _insert_impact(self, review_id: str, target_kind: str, target_id: str, project_id: str, impact_type: str, metadata: Mapping[str, Any]) -> None:
        self.db.connection.execute(
            """
            INSERT OR IGNORE INTO evidence_review_impacts (
                review_id, target_kind, target_id, project_id, impact_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (review_id, target_kind, target_id, project_id, impact_type, _json(dict(metadata))),
        )


def persist_final_state(
    state: Mapping[str, Any],
    *,
    db_path: str | Path,
    artifacts: Iterable[Mapping[str, Any]] = (),
    project_id: str = "",
) -> dict[str, Any]:
    """Persist the final V3 ledger without making persistence a graph concern."""

    snapshot_payload = state.get("_ledger_snapshot") or {}
    if not isinstance(snapshot_payload, Mapping) or not snapshot_payload.get("run_id"):
        return {"persisted": False, "reason": "ledger_snapshot_missing"}
    claim_payloads = [item for item in state.get("_claim_records") or [] if isinstance(item, Mapping)]
    db = SQLiteDatabase(db_path).connect()
    try:
        db.bootstrap_schema()
        result = EvidenceLedgerRepository(db).persist_run(
            dict(snapshot_payload),
            claim_payloads,
            artifacts=artifacts,
            project_id=project_id,
        )
        return {"persisted": True, **result}
    finally:
        db.close()
