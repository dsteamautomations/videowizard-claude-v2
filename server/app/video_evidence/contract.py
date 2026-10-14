"""Compact first-pass validation for the isolated v2 test, not a production gate.

``validate_response(body, expected)`` returns ``identity_errors`` (blocking) and
``gaps`` (retain the first response and expose limitations; never auto-correct).
``expected`` uses the v1 local metadata shape: request_id, script_id, passage_ids,
sources[{source_id, window_id, media_kind, requested_interval, duration_s,
audio_track_count}]. Optional source_audio_allowed and planned_visual_slots carry
the actual brief. This bounded adapter supports one source and no external context.
Neither successful validation nor a model's complete flag proves accuracy. The
caller preserves the raw response and checks provider completion separately.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "source-evidence-v2.schema.json"
COLLECTIONS = ("entities", "speech", "visual_events", "visible_text", "interpretations")
ITEM_COLLECTIONS = COLLECTIONS + ("editorial_ideas", "unresolved")


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _number(value):
    return type(value) in (float, int) and math.isfinite(value)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _interval(value):
    return (isinstance(value, dict) and _number(value.get("start_s"))
            and _number(value.get("end_s")) and 0 <= value["start_s"] < value["end_s"])


def _schema_gaps(value, rule, schema, path="response"):
    if "$ref" in rule:
        return _schema_gaps(value, schema["$defs"][rule["$ref"].split("/")[-1]], schema, path)
    if "anyOf" in rule:
        return [] if any(not _schema_gaps(value, r, schema, path) for r in rule["anyOf"]) else [f"{path}: invalid type/value"]
    kind = rule.get("type")
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "number": _number(value),
               "boolean": type(value) is bool, "null": value is None}
    if kind and not matches.get(kind, False):
        return [f"{path}: expected {kind}"]
    gaps = []
    if "enum" in rule and value not in rule["enum"]:
        gaps.append(f"{path}: unsupported value")
    if kind == "object":
        props = rule["properties"]
        gaps.extend(f"{path}.{key}: missing" for key in rule.get("required", []) if key not in value)
        gaps.extend(f"{path}.{key}: unexpected field" for key in value if key not in props)
        for key in props.keys() & value.keys():
            gaps.extend(_schema_gaps(value[key], props[key], schema, f"{path}.{key}"))
    elif kind == "array":
        if len(value) < rule.get('minItems', 0) or len(value) > rule.get('maxItems', math.inf):
            gaps.append(f"{path}: invalid item count")
        for index, child in enumerate(value):
            gaps.extend(_schema_gaps(child, rule["items"], schema, f"{path}[{index}]"))
    return gaps


def _rows(source, name):
    value = source.get(name, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _refs(row, field):
    return _rows(row, field)


def _ref_key(row):
    key = tuple(row.get(name) for name in ("source_id", "window_id", "collection", "item_id"))
    return key if all(value is None or isinstance(value, str) for value in key) else None


def _covers(rows, target, tolerance):
    cursor = target["start_s"]
    spans = [row["interval"] for row in rows if _interval(row.get("interval"))]
    for span in sorted(spans, key=lambda value: value["start_s"]):
        if span["start_s"] > cursor + tolerance:
            return False
        cursor = max(cursor, span["end_s"])
    return cursor >= target["end_s"] - tolerance


def validate_response(body, expected) -> dict:
    """Never mutate evidence; report identity failures separately from content gaps."""
    result = {"identity_errors": [], "gaps": []}
    errors, gaps = result["identity_errors"], result["gaps"]
    try:
        if not isinstance(expected, dict) or not isinstance(body, dict):
            errors.append("response/expected: object required")
            return result
        for name in ("request_id", "script_id"):
            if not _text(expected.get(name)) or body.get(name) != expected[name]:
                errors.append(f"{name}: missing or does not match local request identity")
        if body.get("contract_version") != "source-evidence-v2":
            errors.append("contract_version: source-evidence-v2 required")
        metas, sources = expected.get("sources"), body.get("sources")
        if not isinstance(metas, list) or len(metas) != 1 or not isinstance(metas[0], dict):
            errors.append("expected.sources: this isolated validator requires one source")
            return result
        if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
            errors.append("sources: exactly the requested source/window must be returned")
            return result
        if expected.get("context_registry"):
            errors.append("expected.context_registry: external context is unsupported in this isolated test")
        tolerance = expected.get("tolerance_s", 0.001)
        if not _number(tolerance) or not 0 <= tolerance <= 0.01:
            errors.append("expected.tolerance_s: must be finite and between 0 and 0.01")
            return result
        source, meta = sources[0], metas[0]
        if not _text(meta.get("source_id")):
            errors.append("expected.source_id: nonempty local identity required")
        for name in ("source_id", "window_id", "media_kind"):
            if name not in meta or name not in source or source[name] != meta[name]:
                errors.append(f"source.{name}: missing or contradicts local source identity")
        video = meta.get("media_kind") == "video"
        target = meta.get("requested_interval")
        count = meta.get("audio_track_count")
        if type(count) is not int or count < 0 or meta.get("media_kind") not in ("video", "image"):
            errors.append("expected.source: invalid media/audio metadata")
        if video:
            if (not _text(meta.get("window_id")) or not _interval(target)
                    or not _number(meta.get("duration_s")) or meta["duration_s"] < target["end_s"]):
                errors.append("expected.source: invalid original window/duration")
            returned = source.get("requested_interval")
            if (not _interval(returned) or not _interval(target)
                    or any(abs(returned[k] - target[k]) > tolerance for k in ("start_s", "end_s"))):
                errors.append("source.requested_interval: does not match original-source window")
        elif any(meta.get(k) is not None for k in ("window_id", "requested_interval", "duration_s")) or count != 0:
            errors.append("expected.source: image must be untimed with no audio")
        if not video and source.get("requested_interval") is not None:
            errors.append("source.requested_interval: image must be untimed")
        if source.get("clock") != ("original_source_seconds" if video else "not_applicable"):
            errors.append("source.clock: incompatible source clock")
        if errors:
            return result
        schema = load_schema()
        gaps.extend(_schema_gaps(body, schema, schema))
        _content_checks(source, meta, expected, tolerance, errors, gaps)
    except (OSError, json.JSONDecodeError):
        errors.append("schema: unavailable or invalid; validation cannot complete")
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        gaps.append("response: malformed content; affected evidence remains unusable")
    result["identity_errors"] = list(dict.fromkeys(errors))
    result["gaps"] = list(dict.fromkeys(gaps))
    return result


def _content_checks(source, meta, expected, tolerance, errors, gaps):
    video, target = meta["media_kind"] == "video", meta["requested_interval"]

    def check_time(value, path, optional=False):
        if value is None:
            if video and not optional:
                gaps.append(f"{path}: source interval missing")
        elif not video:
            errors.append(f"{path}: still image has invented source timing")
        elif not _interval(value):
            errors.append(f"{path}: invalid original-source interval")
        elif value["start_s"] < target["start_s"] - tolerance or value["end_s"] > target["end_s"] + tolerance:
            errors.append(f"{path}: outside original-source request window")

    coverage = source.get("coverage") if isinstance(source.get("coverage"), dict) else {}
    visual, audio = _rows(coverage, "visual"), _rows(coverage, "audio")
    for name, rows in (("visual", visual), ("audio", audio)):
        for index, row in enumerate(rows):
            check_time(row.get("interval"), f"coverage.{name}[{index}]")
        if video and not _covers(rows, target, tolerance):
            gaps.append(f"coverage.{name}: grouped spans do not account for the whole requested window")
    for row in visual:
        if row.get("status") != "reviewed":
            gaps.append("coverage.visual: unreviewed/inaccessible content remains")
    for row in audio:
        state = row.get("state")
        if ((not video and state != "not_applicable")
                or (video and meta["audio_track_count"] == 0 and state != "no_track")
                or (video and meta["audio_track_count"] > 0 and state in ("no_track", "not_applicable"))):
            errors.append("coverage.audio: state contradicts locally verified audio metadata")
        if state in ("unintelligible", "inaccessible"):
            gaps.append(f"coverage.audio: {state} evidence remains unknown")
    omissions = _rows(source, "scope_omissions")
    if any(row.get("state") == "omitted_background_speech" for row in audio) and not any(row.get("field") == "speech" for row in omissions):
        gaps.append("scope_omissions: omitted background speech lacks explicit scope note")
    for index, row in enumerate(omissions):
        check_time(row.get("interval"), f"scope_omissions[{index}]", optional=True)
        if not _text(row.get("reason")):
            gaps.append(f"scope_omissions[{index}]: reason missing")

    known, ids = set(), set()
    for collection in ITEM_COLLECTIONS:
        for index, row in enumerate(_rows(source, collection)):
            path = f"{collection}[{index}]"
            item_id = row.get("id")
            if not _text(item_id) or item_id in ids:
                gaps.append(f"{path}.id: missing or duplicate item identity")
            elif collection in COLLECTIONS:
                known.add((source["source_id"], source["window_id"], collection, item_id))
            if _text(item_id):
                ids.add(item_id)
            if collection not in ("entities", "interpretations"):
                check_time(row.get("interval"), path, optional=collection in ("unresolved", "editorial_ideas"))
    entities = {r["id"] for r in _rows(source, "entities") if _text(r.get("id"))}
    for row in _rows(source, "speech"):
        if not video or meta["audio_track_count"] == 0:
            errors.append("speech: contradicts source media/audio metadata")
        if row.get("speaker_id") is not None and (not _text(row.get("speaker_id")) or row["speaker_id"] not in entities):
            gaps.append("speech: unresolved speaker reference")
        if not _text(row.get("original_text")) or not _text(row.get("english_translation")):
            gaps.append("speech: missing retained original text or complete English translation")
        if row.get("transcription_status") != "clear":
            gaps.append("speech: uncertain/partial transcription remains")
    if any(r.get("state") == "speech" for r in audio) and not _rows(source, "speech"):
        gaps.append("speech: relevant speech coverage has no returned utterances")
    for row in _rows(source, "visual_events"):
        for field in ("actor_ids", "object_ids"):
            values = row.get(field, [])
            if isinstance(values, list) and any(not isinstance(v, str) or v not in entities for v in values):
                gaps.append(f"visual_events.{field}: unresolved entity reference")
    passages = expected.get("passage_ids", [])
    for collection in ("interpretations", "editorial_ideas", "visual_slot_guidance"):
        for row in _rows(source, collection):
            for ref in _refs(row, "evidence_refs"):
                if _ref_key(ref) not in known:
                    gaps.append(f"{collection}: unsupported evidence reference")
            if collection == "interpretations" and not _refs(row, "evidence_refs"):
                gaps.append("interpretations: claim lacks evidence")
            if collection != "interpretations" and isinstance(row.get("passage_ids"), list):
                if any(p not in passages for p in row["passage_ids"]):
                    gaps.append(f"{collection}: unknown script passage")
            if collection == "editorial_ideas":
                kind = row.get("kind")
                if kind != "future_visual" and not _refs(row, "evidence_refs"):
                    gaps.append("editorial_ideas: supported recommendation lacks evidence")
                details = row.get("details") if isinstance(row.get("details"), dict) else {}
                for ref in _refs(details, "alternative_refs"):
                    if _ref_key(ref) not in known:
                        gaps.append("editorial_ideas: unsupported alternative reference")
                check_time(details.get("alternative_interval"), "editorial_ideas.alternative_interval", optional=True)
                if kind == "source_audio" and expected.get("source_audio_allowed") is not True:
                    gaps.append("editorial_ideas: actionable source audio not allowed by output policy")
                if kind == "future_visual" and details.get("asset_status") != "planned_not_created":
                    gaps.append("editorial_ideas: future visual must be marked planned_not_created")
            if collection == "visual_slot_guidance":
                reservations = [r for r in expected.get("planned_visual_slots", []) if isinstance(r, dict) and r.get("origin") == "user_supplied"]
                matched = next((r for r in reservations if r.get("slot_id") == row.get("slot_id")), None)
                if row.get("origin") == "user_supplied" and matched is None:
                    gaps.append("visual_slot_guidance: invented user reservation")
                if matched and (row.get("intended_kind") != matched.get("intended_kind") or row.get("preserve_reservation") is not True):
                    gaps.append("visual_slot_guidance: supplied reservation not preserved")
                if row.get("origin") == "agent_proposal" and row.get("preserve_reservation") is True:
                    gaps.append("visual_slot_guidance: agent proposal is not a user reservation")
                if row.get("origin") == "agent_proposal" and row.get("intended_kind") == "generated_video" and row.get("asset_status") != "planned_not_created":
                    gaps.append("visual_slot_guidance: proposed generated video must be planned_not_created")
    if source.get("review_status") != "complete":
        gaps.append("review_status: compact inspection reported incomplete")
    if _rows(source, "unresolved"):
        gaps.append("unresolved: provider reports remaining evidence limitations")
