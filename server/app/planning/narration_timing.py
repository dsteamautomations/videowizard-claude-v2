"""Derive narration timeline windows from checked source word times.

This is an offline calculation, not an aligner or a source-transcription route.
Callers must verify the recording identity against the configured audio and call
the intake gate before dependent editorial work. All original audio is retained
once, in order and at speed 1. Splits are checked natural boundaries; only pauses
may be added. Passage windows follow the supplied script passage order.
"""

from copy import deepcopy
from fractions import Fraction
import math
from pathlib import PurePosixPath
import re


class TimingError(ValueError):
    """Missing, inconsistent or unusable checked narration timing."""


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


def _fail(message):
    raise TimingError(message)


def _object(value, name, required):
    if not isinstance(value, dict):
        _fail(f"{name} must be an object")
    missing = set(required) - value.keys()
    if missing:
        _fail(f"{name} is missing {', '.join(sorted(missing))}")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        _fail(f"{name} must be nonempty text")
    return value


def _identifier(value, name):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail(f"{name} must be a nonempty identifier")
    return value


def _seconds(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{name} must be finite numeric seconds")
    try:
        number = Fraction(str(value))
        finite = math.isfinite(float(number))
    except (ValueError, OverflowError):
        _fail(f"{name} must be finite numeric seconds")
    if not finite or number < 0 or (positive and number == 0):
        _fail(f"{name} must be {'positive' if positive else 'nonnegative'} finite seconds")
    return number


def _fps(value):
    if isinstance(value, bool):
        _fail("fps must be a positive rational frame rate")
    if isinstance(value, dict):
        if set(value) != {"numerator", "denominator"}:
            _fail("fps object requires only numerator and denominator")
        numerator, denominator = value["numerator"], value["denominator"]
        if any(isinstance(part, bool) or not isinstance(part, int)
               for part in (numerator, denominator)) or denominator <= 0:
            _fail("fps numerator and denominator must be integers with positive denominator")
        value = f"{numerator}/{denominator}"
    if not isinstance(value, (Fraction, int, float, str)):
        _fail("fps must be a positive rational frame rate")
    try:
        number = value if isinstance(value, Fraction) else Fraction(str(value))
        finite = math.isfinite(float(number))
    except (ValueError, ZeroDivisionError, OverflowError):
        _fail("fps must be a positive rational frame rate")
    if not finite or number <= 0:
        _fail("fps must be a positive rational frame rate")
    return number


def _as_seconds(value):
    """Return JSON-safe seconds; calculations retain exact decimal fractions."""
    try:
        result = float(value)
    except OverflowError:
        _fail("derived timing exceeds finite numeric seconds")
    if not math.isfinite(result):
        _fail("derived timing exceeds finite numeric seconds")
    return result


def derive_timing(timing, passage_ids, fps):
    """Validate and derive the single canonical narration timing record.

    ``timing`` requires recording(path, sha256, duration_s), checked provenance
    (method, checked_by, boundaries_checked=True), a nonempty ``words`` list
    (id, text, start_s, end_s, passage_id), a nonempty ``segments`` list
    (id, source_start_s, source_end_s, timeline_start_s), and an ordered list of
    ``natural_boundaries_s``. Optional ``trailing_hold_s`` defaults to zero.

    Every passage ID must appear, in order, in nonoverlapping source words.
    Segments must exactly partition [0, recording.duration_s), begin at timeline
    zero and retain speed 1; every interior split must be a checked natural
    boundary outside a word. Numbers are finite numeric seconds, never strings
    or booleans. Unknown metadata is preserved only in source_words/provenance;
    it cannot substitute for any required evidence. No input is mutated.

    Output sentence_windows describe each passage's source speech span and its
    elapsed timeline speech span. edit_windows partition the entire timeline:
    first begins at zero, later windows at their passage's first word, and each
    ends at the next passage onset (last at runtime). Thus a pause before the
    next passage extends the preceding edit window. Half-open seconds remain
    unquantized; frame_count rounds the total runtime upward at exact fps, with
    output_runtime_s/frame_padding_s explicitly recording the final frame pad.
    """
    _object(timing, "timing", ("recording", "provenance", "words", "segments",
                              "natural_boundaries_s"))
    if not isinstance(passage_ids, (list, tuple)) or not passage_ids:
        _fail("passage_ids must be a nonempty ordered list")
    passage_order = [_identifier(item, "passage_id") for item in passage_ids]
    if len(set(passage_order)) != len(passage_order):
        _fail("passage_ids must be unique")
    passage_positions = {item: index for index, item in enumerate(passage_order)}
    frame_rate = _fps(fps)

    recording = _object(timing["recording"], "recording", ("path", "sha256", "duration_s"))
    path = _text(recording["path"], "recording.path")
    if (PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
            or "\\" in path or ":" in path or "\x00" in path or path == "."):
        _fail("recording.path must be a package-relative file path")
    if not isinstance(recording["sha256"], str) or not _SHA256.fullmatch(recording["sha256"]):
        _fail("recording.sha256 must be a SHA-256 digest")
    duration = _seconds(recording["duration_s"], "recording.duration_s", positive=True)
    provenance = _object(timing["provenance"], "provenance",
                         ("method", "checked_by", "boundaries_checked"))
    _text(provenance["method"], "provenance.method")
    _text(provenance["checked_by"], "provenance.checked_by")
    if provenance["boundaries_checked"] is not True:
        _fail("provenance.boundaries_checked must be true")
    trailing_hold = _seconds(timing.get("trailing_hold_s", 0), "trailing_hold_s")

    source_words = timing["words"]
    if not isinstance(source_words, list) or not source_words:
        _fail("words must contain checked source word timings")
    words = []
    seen_words = set()
    seen_passages = set()
    previous_word_end = Fraction(0)
    previous_passage_position = -1
    for index, item in enumerate(source_words):
        label = f"words[{index}]"
        _object(item, label, ("id", "text", "start_s", "end_s", "passage_id"))
        word_id = _identifier(item["id"], f"{label}.id")
        if word_id in seen_words:
            _fail("word IDs must be unique")
        seen_words.add(word_id)
        _text(item["text"], f"{label}.text")
        passage_id = _identifier(item["passage_id"], f"{label}.passage_id")
        if passage_id not in passage_positions:
            _fail(f"{label}.passage_id is not in the current script")
        position = passage_positions[passage_id]
        if position < previous_passage_position:
            _fail("word passage IDs must follow the current script order")
        previous_passage_position = position
        seen_passages.add(passage_id)
        start = _seconds(item["start_s"], f"{label}.start_s")
        end = _seconds(item["end_s"], f"{label}.end_s", positive=True)
        if end <= start or start < previous_word_end or end > duration:
            _fail(f"{label} must be ordered, nonoverlapping and inside the recording")
        previous_word_end = end
        words.append((item, start, end))
    if seen_passages != set(passage_order):
        _fail("checked words must cover every current script passage")

    boundaries = timing["natural_boundaries_s"]
    if not isinstance(boundaries, list):
        _fail("natural_boundaries_s must be an ordered list")
    checked_boundaries = []
    previous_boundary = Fraction(0)
    for index, value in enumerate(boundaries):
        boundary = _seconds(value, f"natural_boundaries_s[{index}]", positive=True)
        if boundary <= previous_boundary or boundary >= duration:
            _fail("natural boundaries must be unique, ordered and inside the recording")
        if any(start < boundary < end for _, start, end in words):
            _fail("a natural boundary cannot split a word")
        previous_boundary = boundary
        checked_boundaries.append(boundary)

    supplied_segments = timing["segments"]
    if not isinstance(supplied_segments, list) or not supplied_segments:
        _fail("segments must retain the complete recorded audio")
    segments = []
    pauses = []
    seen_segments = set()
    previous_source_end = Fraction(0)
    previous_timeline_end = Fraction(0)
    for index, item in enumerate(supplied_segments):
        label = f"segments[{index}]"
        _object(item, label, ("id", "source_start_s", "source_end_s", "timeline_start_s"))
        segment_id = _identifier(item["id"], f"{label}.id")
        if segment_id in seen_segments:
            _fail("segment IDs must be unique")
        seen_segments.add(segment_id)
        start = _seconds(item["source_start_s"], f"{label}.source_start_s")
        end = _seconds(item["source_end_s"], f"{label}.source_end_s", positive=True)
        timeline_start = _seconds(item["timeline_start_s"], f"{label}.timeline_start_s")
        if start != previous_source_end or end <= start or end > duration:
            _fail("segments must partition the complete source audio once, in order")
        if (index == 0 and timeline_start != 0) or timeline_start < previous_timeline_end:
            _fail("timeline segments must begin at zero and never overlap")
        if index > 0 and start not in checked_boundaries:
            _fail("each narration split must be a checked natural boundary")
        if timeline_start > previous_timeline_end:
            pauses.append({
                "kind": "inserted_pause", "after_segment_id": segments[-1][0]["id"],
                "source_boundary_s": _as_seconds(start),
                "timeline_start_s": _as_seconds(previous_timeline_end),
                "timeline_end_s": _as_seconds(timeline_start),
                "duration_s": _as_seconds(timeline_start - previous_timeline_end),
            })
        timeline_end = timeline_start + end - start
        # Optional supplied derived fields cannot silently request stretching.
        if "timeline_end_s" in item and _seconds(item["timeline_end_s"], f"{label}.timeline_end_s") != timeline_end:
            _fail("segment timeline_end_s must preserve natural speed")
        if "speed" in item and _seconds(item["speed"], f"{label}.speed", positive=True) != 1:
            _fail("narration speed must remain 1")
        segment = {
            "id": segment_id, "source_start_s": _as_seconds(start),
            "source_end_s": _as_seconds(end), "timeline_start_s": _as_seconds(timeline_start),
            "timeline_end_s": _as_seconds(timeline_end), "duration_s": _as_seconds(end - start),
            "speed": 1,
        }
        segments.append((segment, start, end, timeline_start))
        previous_source_end, previous_timeline_end = end, timeline_end
    if previous_source_end != duration:
        _fail("segments must retain the end of the source recording")
    runtime = previous_timeline_end + trailing_hold
    if trailing_hold:
        pauses.append({
            "kind": "trailing_hold", "after_segment_id": segments[-1][0]["id"],
            "source_boundary_s": _as_seconds(duration),
            "timeline_start_s": _as_seconds(previous_timeline_end),
            "timeline_end_s": _as_seconds(runtime), "duration_s": _as_seconds(trailing_hold),
        })

    mapped_words = []
    mapped_fractions = []
    segment_index = 0
    for word, start, end in words:
        while segment_index < len(segments) and start >= segments[segment_index][2]:
            segment_index += 1
        if segment_index >= len(segments):
            _fail("word falls outside retained narration")
        segment, source_start, source_end, timeline_start = segments[segment_index]
        if start < source_start or end > source_end:
            _fail("a narration segment cannot split a word")
        mapped_start = timeline_start + start - source_start
        mapped_end = timeline_start + end - source_start
        mapped = {
            "id": word["id"], "text": word["text"], "passage_id": word["passage_id"],
            "source_start_s": _as_seconds(start), "source_end_s": _as_seconds(end),
            "timeline_start_s": _as_seconds(mapped_start), "timeline_end_s": _as_seconds(mapped_end),
            "segment_id": segment["id"],
        }
        mapped_words.append(mapped)
        mapped_fractions.append((word, start, end, mapped_start, mapped_end))

    sentence_windows = []
    for passage_id in passage_order:
        rows = [row for row in mapped_fractions if row[0]["passage_id"] == passage_id]
        source_start, source_end = rows[0][1], rows[-1][2]
        timeline_start, timeline_end = rows[0][3], rows[-1][4]
        sentence_windows.append({
            "passage_id": passage_id, "word_ids": [row[0]["id"] for row in rows],
            "source_start_s": _as_seconds(source_start), "source_end_s": _as_seconds(source_end),
            "source_speech_span_s": _as_seconds(source_end - source_start),
            "timeline_start_s": _as_seconds(timeline_start), "timeline_end_s": _as_seconds(timeline_end),
            "elapsed_s": _as_seconds(timeline_end - timeline_start),
            "spoken_duration_s": _as_seconds(sum((row[2] - row[1] for row in rows), Fraction(0))),
        })
    edit_windows = []
    for index, window in enumerate(sentence_windows):
        start = 0.0 if index == 0 else window["timeline_start_s"]
        end = (sentence_windows[index + 1]["timeline_start_s"]
               if index + 1 < len(sentence_windows) else _as_seconds(runtime))
        edit_windows.append({
            "passage_id": window["passage_id"], "timeline_start_s": start,
            "timeline_end_s": end, "duration_s": _as_seconds(Fraction(str(end)) - Fraction(str(start))),
        })
    frame_count = math.ceil(runtime * frame_rate)
    output_runtime = Fraction(frame_count, 1) / frame_rate
    return {
        "recording": deepcopy(recording), "provenance": deepcopy(provenance),
        "source_words": deepcopy(source_words), "mapped_words": mapped_words,
        "segments": [row[0] for row in segments], "sentence_windows": sentence_windows,
        "edit_windows": edit_windows, "pauses": pauses,
        "natural_boundaries_s": deepcopy(boundaries), "trailing_hold_s": _as_seconds(trailing_hold),
        "runtime_s": _as_seconds(runtime), "frame_count": frame_count,
        "fps": {"numerator": frame_rate.numerator, "denominator": frame_rate.denominator},
        "output_runtime_s": _as_seconds(output_runtime),
        "frame_padding_s": _as_seconds(output_runtime - runtime),
        "endpoint_convention": "half-open [start,end); seconds unquantized; final frame rounded upward",
    }
