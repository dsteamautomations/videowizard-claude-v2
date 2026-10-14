"""Single-attempt Gemini REST/SSE transport; no environment or workspace access.

The caller must persist ``upload_receipt`` events privately: a resumable URL is a
capability, not a printable progress message. A transport instance shares one
terminal wall-clock budget across upload and generation, starting its first
operation. The generation soft-wait event permits independent preparation only.
The terminal supervisor never retries and does not claim remote cancellation.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import http.client
import json
import math
import queue
import re
import socket
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable


def _strict_json(value):
    """Reject JavaScript constants and exponent overflow, not just bad syntax."""
    def reject_constant(_):
        raise ValueError("Non-finite JSON number")

    def finite_float(text):
        number = float(text)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    return json.loads(value, parse_constant=reject_constant, parse_float=finite_float)


class GeminiTransportError(RuntimeError):
    """Safe error suitable for the current source map, never provider raw text."""

    def __init__(self, code: str, message: str, *, http_status=None, metadata=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.metadata = metadata or {}


def classify_failure(error):
    """Shared conservative guidance, not authorization to replay a request.

    Callers must still check attempt identity, partial answers and remote state.
    Unknown completion never becomes safe merely because a backoff is present.
    """
    result = {'category': 'inspect_required', 'scope': 'unknown',
              'retry_candidate': False, 'retry_delay_seconds': None}
    if not isinstance(error, GeminiTransportError):
        return result
    if error.code in {'connection_error', 'terminal_deadline', 'transport_error'}:
        return dict(result, category='remote_completion_unknown')
    if error.code != 'http_error':
        return result
    diagnostic = error.metadata.get('provider_error', {})
    if not isinstance(diagnostic, dict) or diagnostic.get('truncated'):
        return result
    text = json.dumps(diagnostic).lower()
    if any(term in text for term in ('monthly', 'spending cap', 'spend limit', 'spending limit',
                                    'billing', 'payment', 'insufficient_quota')):
        return dict(result, category='spending_or_billing_limit', scope='shared')
    if any(term in text for term in ('perday', 'per_day', 'per day', 'daily')) or re.search(r'(?:limit|quota)[\s:=]+0\b', text):
        return dict(result, category='quota_limit', scope='shared')
    if error.http_status in {401, 403}:
        return dict(result, category='access_denied', scope='shared')
    temporary = error.http_status == 503 and diagnostic.get('status') == 'UNAVAILABLE' and any(
        term in text for term in ('overload', 'high demand', 'capacity', 'temporary', 'temporarily', 'try again'))
    limited = error.http_status == 429 and diagnostic.get('status') == 'RESOURCE_EXHAUSTED' and any(
        term in text for term in ('perminute', 'per_minute', 'per minute', 'persecond', 'per_second', 'per second', 'rate_limit', 'rate limit'))
    if temporary or limited:
        delay = diagnostic.get('retry_delay_seconds')
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not math.isfinite(delay) or delay < 0:
            delay = None
        return dict(result, category='temporary_capacity' if temporary else 'rate_limit', scope='shared',
                    retry_candidate=True, retry_delay_seconds=delay)
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _Operation:
    def __init__(self, transport, name, deadline):
        self.transport = transport
        self.name = name
        self.deadline = deadline
        self.cancelled = threading.Event()
        self.started = time.monotonic()
        self.metadata = {}
        self.stream = None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if self.cancelled.is_set() or remaining <= 0:
            raise GeminiTransportError("terminal_deadline", "Terminal deadline reached; remote cancellation is unverified. Preserve the receipt and wait for user input.")
        return remaining

    def emit(self, event):
        # The supervisor uses the same lock when making timeout terminal. Late
        # worker results cannot overwrite the caller's blocked/error state.
        with self.transport._state_lock:
            self.remaining()
            self.transport._deliver(event)


class GeminiTransport:
    CHUNK_BYTES = 8 * 1024 * 1024
    MAX_RESPONSE_BYTES = 64 * 1024 * 1024
    MAX_HTTP_ERROR_BYTES = 32 * 1024
    MAX_HTTP_ERROR_TEXT = 4096

    def __init__(self, api_key: str, model: str, terminal_deadline_seconds: float,
                 initial_soft_wait_seconds: float, on_update: Callable[[dict], None],
                 api_base="https://generativelanguage.googleapis.com", poll_seconds=3,
                 capture_answer_deltas=False, allow_agentic_video=False,
                 allowed_cache_name=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise GeminiTransportError("configuration", "A nonempty API key is required.")
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise GeminiTransportError("configuration", "Use a plain provider model ID.")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
               for x in (terminal_deadline_seconds, initial_soft_wait_seconds, poll_seconds)):
            raise GeminiTransportError("configuration", "Wait values must be finite numbers.")
        if not 0 <= initial_soft_wait_seconds < terminal_deadline_seconds or poll_seconds <= 0:
            raise GeminiTransportError("configuration", "Require a positive terminal deadline and poll interval, with a shorter nonnegative soft wait.")
        parsed = urllib.parse.urlsplit(api_base)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise GeminiTransportError("configuration", "The API base must be a bare HTTPS origin.")
        if not callable(on_update):
            raise GeminiTransportError("configuration", "A durable update callback is required.")
        if type(allow_agentic_video) is not bool:
            raise GeminiTransportError("configuration", "Agentic video opt-in must be an explicit boolean.")
        if allowed_cache_name is not None and (not isinstance(allowed_cache_name, str)
                or not re.fullmatch(r"cachedContents/[A-Za-z0-9_-]+", allowed_cache_name)):
            raise GeminiTransportError("configuration", "Cache opt-in must bind one exact cachedContents resource name.")
        self.allowed_cache_name = allowed_cache_name
        self._api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._origin = urllib.parse.urlsplit(self.api_base).netloc
        self.terminal_deadline_seconds = float(terminal_deadline_seconds)
        self.initial_soft_wait_seconds = float(initial_soft_wait_seconds)
        self.poll_seconds = float(poll_seconds)
        self.on_update = on_update
        self.capture_answer_deltas = capture_answer_deltas
        self.allow_agentic_video = allow_agentic_video
        self._opener = urllib.request.build_opener(_NoRedirect())
        self._state_lock = threading.RLock()
        self._deadline = None
        self._busy = False
        self._terminal = False

    def _deliver(self, event):
        try:
            self.on_update(copy.deepcopy(event))
        except Exception:
            raise GeminiTransportError("receipt_persistence", "Unable to persist current provider state; stop before further requests.") from None

    def _safe_text(self, value, limit=256):
        value = str(value).replace(self._api_key, "[redacted]")
        value = re.sub(r"https?://[^\s]+", "[url omitted]", value)
        value = re.sub(r'''(?i)(["']?\b(?:api[-_ ]?key|authorization|token|secret|password)["']?\s*[:=]\s*)(?:(?:Bearer|Basic)\s+)?(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
                       r"\1[redacted]", value)
        return value[:limit]

    def _safe_metadata(self, metadata):
        def clean(value, text_limit=256):
            if isinstance(value, str):
                return self._safe_text(value, text_limit)
            if isinstance(value, dict):
                return {self._safe_text(k): clean(v, self.MAX_HTTP_ERROR_TEXT
                        if k == "provider_error" else text_limit) for k, v in value.items()}
            if isinstance(value, list):
                return [clean(v, text_limit) for v in value[:100]]
            if value is None or isinstance(value, (int, float, bool)):
                return value
            return None
        return clean(metadata)

    def _http_error_diagnostic(self, response):
        """Retain bounded Google error fields, never raw bodies or headers."""
        try:
            raw = response.read(self.MAX_HTTP_ERROR_BYTES + 1)
        except (OSError, ValueError, http.client.HTTPException):
            return {"format": "unavailable", "body_read_failed": True}
        if len(raw) > self.MAX_HTTP_ERROR_BYTES:
            return {"format": "oversized", "truncated": True}
        try:
            body = _strict_json(raw)
        except (ValueError, UnicodeError, RecursionError):
            return {"format": "non_json_omitted", "truncated": False}
        # Streaming endpoints may wrap their error object in a one-item array.
        if isinstance(body, list) and len(body) == 1:
            body = body[0]
        diagnostic = self._error_diagnostic(body)
        retry_after = (getattr(response, 'headers', None) or {}).get('Retry-After')
        if isinstance(retry_after, str):
            try:
                seconds = float(retry_after) if re.fullmatch(r'[0-9]+', retry_after) else (
                    parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                if math.isfinite(seconds) and seconds >= 0:
                    diagnostic['retry_delay_seconds'] = max(seconds, diagnostic.get('retry_delay_seconds', 0))
            except (ValueError, TypeError, OverflowError):
                pass
        return diagnostic

    def _error_diagnostic(self, body):
        """Same bounded, redacted diagnostics for HTTP and SSE error envelopes."""
        error = body.get("error") if isinstance(body, dict) else None
        if not isinstance(error, dict):
            return {"format": "unrecognized_json_omitted", "truncated": False}
        diagnostic = {"format": "google_error", "truncated": False}

        def safe(value):
            if len(value) > self.MAX_HTTP_ERROR_TEXT:
                diagnostic["truncated"] = True
            return self._safe_text(value, self.MAX_HTTP_ERROR_TEXT)

        if type(error.get("code")) is int:
            diagnostic["code"] = error["code"]
        for name in ("status", "message"):
            if isinstance(error.get(name), str):
                diagnostic[name] = safe(error[name])
        details = error.get("details", [])
        if isinstance(details, list):
            if len(details) > 8:
                diagnostic["truncated"] = True
            violations, reasons, quota_ids = [], [], []
            for detail in details[:8]:
                if not isinstance(detail, dict):
                    continue
                if isinstance(detail.get("reason"), str):
                    reasons.append(safe(detail["reason"]))
                # These bounded diagnostics let the workflow distinguish a
                # short rate limit from daily/zero quota without retrying here.
                if str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
                    delay = detail.get("retryDelay")
                    if isinstance(delay, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?s", delay):
                        seconds = float(delay[:-1])
                        if math.isfinite(seconds):
                            diagnostic["retry_delay_seconds"] = seconds
                quota_rows = detail.get("violations", [])
                if str(detail.get("@type", "")).endswith("google.rpc.QuotaFailure") and isinstance(quota_rows, list):
                    for row in quota_rows[:16 - len(quota_ids)]:
                        if isinstance(row, dict):
                            names = {key: safe(row[key]) for key in ("quotaId", "quotaMetric", "description")
                                     if isinstance(row.get(key), str)}
                            if names:
                                quota_ids.append(names)
                rows = detail.get("fieldViolations", [])
                if isinstance(rows, list):
                    if len(rows) > 16 - len(violations):
                        diagnostic["truncated"] = True
                    for row in rows[:16 - len(violations)]:
                        if isinstance(row, dict):
                            fields = {name: safe(row[name]) for name in ("field", "description")
                                      if isinstance(row.get(name), str)}
                            if fields:
                                violations.append(fields)
            if violations:
                diagnostic["field_violations"] = violations
            if reasons:
                diagnostic["reasons"] = reasons
            if quota_ids:
                diagnostic["quota_violations"] = quota_ids
        return diagnostic

    def _run(self, name, worker):
        with self._state_lock:
            if self._terminal:
                raise GeminiTransportError("transport_blocked", "This transport has failed or timed out; wait for user-authorised recovery.")
            if self._busy:
                raise GeminiTransportError("already_running", "A request is already running on this transport; do not duplicate it.")
            if self._deadline is None:
                self._deadline = time.monotonic() + self.terminal_deadline_seconds
            self._busy = True
            op = _Operation(self, name, self._deadline)
        result = queue.Queue(maxsize=1)

        def execute():
            try:
                op.remaining()
                result.put((True, worker(op)))
            except BaseException as exc:
                result.put((False, exc))

        thread = threading.Thread(target=execute, name="gemini-single-request", daemon=True)
        thread.start()
        soft_sent = False
        try:
            while True:
                now = time.monotonic()
                if now >= op.deadline:
                    with self._state_lock:
                        op.cancelled.set()
                        self._terminal = True
                        metadata = self._safe_metadata(op.metadata)
                        self._deliver({"event": "terminal_error", "operation": name,
                                       "code": "terminal_deadline", "metadata": metadata,
                                       "remote_cancellation_verified": False})
                    # shutdown() interrupts an available local socket without
                    # blocking on buffered-reader locks held by the worker.
                    try:
                        sock = op.stream.fp.raw._sock
                        sock.shutdown(socket.SHUT_RDWR)
                    except (AttributeError, OSError):
                        pass
                    raise GeminiTransportError("terminal_deadline", "Terminal deadline reached; the remote operation may still exist. Preserve its receipt and wait for user input.", metadata=metadata)
                if name == "generation" and not soft_sent and now - op.started >= self.initial_soft_wait_seconds:
                    op.emit({"event": "soft_wait_elapsed", "operation": name,
                             "elapsed_seconds": round(now - op.started, 3),
                             "independent_preparation_allowed": True,
                             "required_evidence_gate_open": False,
                             "request_still_running": True})
                    soft_sent = True
                wait = min(0.1, op.deadline - now)
                if name == "generation" and not soft_sent:
                    wait = min(wait, max(0.001, self.initial_soft_wait_seconds - (now - op.started)))
                try:
                    success, value = result.get(timeout=wait)
                except queue.Empty:
                    continue
                if success:
                    return value
                if isinstance(value, GeminiTransportError):
                    exc = value
                else:
                    # Keep structural diagnostics, never exception text, locals or
                    # response bytes (IncompleteRead.partial may contain content).
                    diagnostic = self._safe_metadata({
                        'exception_type': type(value).__name__,
                        'errno': value.errno if isinstance(value, OSError) and isinstance(value.errno, int) else None,
                        'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                                   for f in traceback.extract_tb(value.__traceback__)[-8:]],
                    })
                    op.metadata['transport_exception'] = diagnostic
                    exc = GeminiTransportError("transport_error", "Provider operation failed; preserve current evidence and wait for user input.",
                                               metadata={'transport_exception': diagnostic})
                with self._state_lock:
                    self._terminal = True
                    op.cancelled.set()
                    self._deliver({"event": "terminal_error", "operation": name,
                                   "code": exc.code, "http_status": exc.http_status,
                                   "metadata": self._safe_metadata(op.metadata),
                                   "remote_cancellation_verified": False})
                raise exc from None
        except BaseException:
            with self._state_lock:
                op.cancelled.set()
                self._terminal = True
            raise
        finally:
            with self._state_lock:
                self._busy = False

    def _check_url(self, url):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != self._origin or parsed.username or parsed.password or parsed.fragment:
            raise GeminiTransportError("unsafe_upload_url", "The provider returned an unexpected upload origin; no bytes were sent there.")

    def _open(self, op, url, *, body=None, headers=None, method="GET"):
        self._check_url(url)
        hdrs = {"x-goog-api-key": self._api_key, **(headers or {})}
        request = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            response = self._opener.open(request, timeout=max(0.001, op.remaining()))
            op.stream = response
            op.remaining()
            return response
        except urllib.error.HTTPError as exc:
            code = exc.code
            op.stream = exc
            try:
                op.remaining()
                diagnostic = self._http_error_diagnostic(exc)
                op.remaining()
                op.metadata["provider_error"] = diagnostic
            finally:
                exc.close()
            raise GeminiTransportError("http_error", f"Provider HTTP {code}; no automatic retry was made.",
                                       http_status=code, metadata={"provider_error": diagnostic}) from None
        except (urllib.error.URLError, OSError, TimeoutError):
            raise GeminiTransportError("connection_error", "The provider connection failed; remote completion is unknown and no retry was made.") from None

    def _json_request(self, op, url, *, body=None, headers=None, method="GET"):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode("utf-8")
            headers = {"Content-Type": "application/json", **(headers or {})}
        with self._open(op, url, body=body, headers=headers, method=method) as response:
            raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            op.remaining()
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise GeminiTransportError("provider_response_size", "Provider response exceeded the permitted response size.")
            hdrs = {key.lower(): value for key, value in response.headers.items()}
        try:
            value = _strict_json(raw) if raw else {}
        except (ValueError, UnicodeError):
            raise GeminiTransportError("provider_json", "Provider returned malformed JSON; current state is incomplete.") from None
        if not isinstance(value, dict):
            raise GeminiTransportError("provider_json", "Provider returned a non-object response.")
        return value, hdrs

    @staticmethod
    def _remote_hash(remote):
        try:
            value = base64.b64decode(remote["sha256Hash"], validate=True)
            if len(value) == 32:
                return value.hex()
            if len(value) == 64 and re.fullmatch(b"[a-fA-F0-9]{64}", value):
                return value.decode("ascii").lower()
        except (KeyError, ValueError, TypeError):
            pass
        raise GeminiTransportError("upload_identity", "Provider file hash is missing or invalid; source identity is unverified.")

    @staticmethod
    def _expired(value):
        if not value:
            return False
        try:
            expiration = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if expiration.tzinfo is None:
                raise ValueError
            return expiration <= datetime.now(timezone.utc)
        except (ValueError, TypeError, AttributeError):
            raise GeminiTransportError("upload_expiry", "Provider file expiry is invalid; source availability is unverified.") from None

    def _record_upload(self, op, receipt):
        op.emit({"event": "upload_receipt", "receipt": receipt})

    def _active_file(self, op, remote, receipt):
        while True:
            name = remote.get("name")
            if not isinstance(name, str) or not re.fullmatch(r"files/[a-z0-9][a-z0-9-]{0,39}", name):
                raise GeminiTransportError("upload_identity", "Provider file name is missing or invalid.")
            if receipt.get("name") and name != receipt["name"]:
                raise GeminiTransportError("upload_identity", "Provider file identity changed during retrieval.")
            if self._expired(remote.get("expirationTime")):
                raise GeminiTransportError("upload_expired", "The known upload has expired; wait for user-authorised recovery.")
            state = remote.get("state")
            if state not in ("ACTIVE", "PROCESSING"):
                raise GeminiTransportError("upload_state", "Provider file is not ACTIVE or PROCESSING; required media remains unavailable.")
            for key in ("name", "uri", "mimeType", "state", "expirationTime"):
                if key in remote:
                    receipt[key] = remote[key]
            receipt["identity_verified"] = False
            self._record_upload(op, receipt)
            if state == "ACTIVE":
                if self._remote_hash(remote) != receipt["sha256"]:
                    raise GeminiTransportError("upload_identity", "Remote file bytes differ from the expected source; no replacement was created.")
                if remote.get("mimeType") != receipt["mime_type"]:
                    raise GeminiTransportError("upload_identity", "Remote file media type differs from the expected source.")
                if "sizeBytes" in remote and str(remote["sizeBytes"]) != str(receipt["size_bytes"]):
                    raise GeminiTransportError("upload_identity", "Remote file size differs from the expected source.")
                if not isinstance(remote.get("uri"), str):
                    raise GeminiTransportError("upload_identity", "Provider did not return a usable file URI.")
                self._check_url(remote["uri"])
                receipt.update(identity_verified=True, offset=receipt["size_bytes"])
                # A completed upload needs its retrievable file handle, not the
                # expired capability for resuming byte transfer.
                receipt.pop("upload_url", None)
                receipt.pop("pending_end_offset", None)
                self._record_upload(op, receipt)
                return receipt
            op.cancelled.wait(min(self.poll_seconds, op.remaining()))
            op.remaining()
            remote, _ = self._json_request(op, self.api_base + "/v1beta/" + name)

    def upload(self, path: Path, mime_type: str, source_sha256: str, existing_receipt: dict | None = None) -> dict:
        """Upload bounded chunks or resume/retrieve the explicitly supplied receipt.

        A stale receipt is an error, never permission to start a replacement.
        The caller should re-use this instance for its following generation.
        """
        path = Path(path)
        if not isinstance(source_sha256, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", source_sha256):
            raise GeminiTransportError("source_identity", "A valid source SHA-256 is required.")
        if not isinstance(mime_type, str) or not re.fullmatch(r"[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+", mime_type):
            raise GeminiTransportError("source_type", "A valid source MIME type is required.")

        def worker(op):
            try:
                initial_stat = path.stat()
                size = initial_stat.st_size
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    while chunk := source.read(self.CHUNK_BYTES):
                        op.remaining()
                        digest.update(chunk)
            except OSError:
                raise GeminiTransportError("source_unavailable", "The source file cannot be read.") from None
            expected = source_sha256.lower()
            if digest.hexdigest() != expected or size <= 0:
                raise GeminiTransportError("source_identity", "Source bytes do not match the supplied identity or the source is empty.")
            after_hash = path.stat()
            if (after_hash.st_size, after_hash.st_mtime_ns) != (size, initial_stat.st_mtime_ns):
                raise GeminiTransportError("source_changed", "Source changed while its identity was being checked.")
            receipt = copy.deepcopy(existing_receipt) if existing_receipt is not None else {
                "sha256": expected, "size_bytes": size, "mime_type": mime_type,
                "offset": 0, "identity_verified": False,
            }
            if not isinstance(receipt, dict) or receipt.get("sha256") != expected or receipt.get("size_bytes") != size or receipt.get("mime_type") != mime_type:
                raise GeminiTransportError("upload_identity", "The saved upload receipt does not match this source; no replacement was created.")
            if receipt.get("name"):
                if not re.fullmatch(r"files/[a-z0-9][a-z0-9-]{0,39}", receipt["name"]):
                    raise GeminiTransportError("upload_identity", "The saved provider file name is invalid.")
                if self._expired(receipt.get("expirationTime")):
                    raise GeminiTransportError("upload_expired", "The known upload has expired; wait for user-authorised recovery.")
                remote, _ = self._json_request(op, self.api_base + "/v1beta/" + receipt["name"])
                return self._active_file(op, remote, receipt)
            if existing_receipt is not None:
                if not isinstance(receipt.get("upload_url"), str):
                    raise GeminiTransportError("upload_recovery", "The saved upload has no retrievable file or resumable handle; wait for user input.")
                self._check_url(receipt["upload_url"])
                data, headers = self._json_request(op, receipt["upload_url"], body=b"", method="POST",
                                                    headers={"X-Goog-Upload-Command": "query", "Content-Length": "0"})
                status = headers.get("x-goog-upload-status")
                if status == "final" and isinstance(data.get("file"), dict):
                    return self._active_file(op, data["file"], receipt)
                if status != "active":
                    raise GeminiTransportError("upload_recovery", "The saved upload cannot be resumed from its current state; no replacement was created.")
                try:
                    offset = int(headers["x-goog-upload-size-received"])
                    if not 0 <= offset <= size:
                        raise ValueError
                except (KeyError, ValueError, TypeError):
                    raise GeminiTransportError("upload_recovery", "Provider upload offset is unavailable or invalid.") from None
                receipt["offset"] = offset
            else:
                _, headers = self._json_request(op, self.api_base + "/upload/v1beta/files", method="POST",
                    body={"file": {"display_name": "source-" + expected[:20]}}, headers={
                        "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                        "X-Goog-Upload-Header-Content-Length": str(size),
                        "X-Goog-Upload-Header-Content-Type": mime_type})
                url = headers.get("x-goog-upload-url")
                if not isinstance(url, str):
                    raise GeminiTransportError("upload_recovery", "Provider did not return a resumable upload handle.")
                self._check_url(url)
                receipt["upload_url"] = url
            self._record_upload(op, receipt)  # durable capability BEFORE transfer
            with path.open("rb") as source:
                source.seek(receipt["offset"])
                while True:
                    op.remaining()
                    current_stat = path.stat()
                    if (current_stat.st_size, current_stat.st_mtime_ns) != (size, initial_stat.st_mtime_ns):
                        raise GeminiTransportError("source_changed", "Source changed during upload; stop without accepting the upload.")
                    chunk = source.read(min(self.CHUNK_BYTES, size - receipt["offset"]))
                    end = receipt["offset"] + len(chunk)
                    final = end == size
                    if not chunk and not final:
                        raise GeminiTransportError("source_changed", "Source ended before its recorded size.")
                    receipt["pending_end_offset"] = end
                    self._record_upload(op, receipt)
                    data, headers = self._json_request(op, receipt["upload_url"], body=chunk, method="POST", headers={
                        "Content-Length": str(len(chunk)), "X-Goog-Upload-Offset": str(receipt["offset"]),
                        "X-Goog-Upload-Command": ("upload, finalize" if chunk else "finalize") if final else "upload"})
                    if headers.get("x-goog-upload-status") != ("final" if final else "active"):
                        raise GeminiTransportError("upload_recovery", "Provider did not acknowledge the expected upload state; preserve the receipt and wait for user-authorised recovery.")
                    receipt["offset"] = end
                    receipt.pop("pending_end_offset", None)
                    self._record_upload(op, receipt)
                    if final:
                        if not isinstance(data.get("file"), dict):
                            raise GeminiTransportError("upload_recovery", "Final upload response lacks a retrievable file; retain the resumable handle for user-authorised recovery.")
                        return self._active_file(op, data["file"], receipt)

        return self._run("upload", worker)

    def cache_metadata(self, ttl_seconds=None) -> dict:
        """Read the opted-in cache, or extend only its TTL without replacing it."""
        if self.allowed_cache_name is None:
            raise GeminiTransportError("request_policy", "Cache access requires an exact resource opt-in.")
        if ttl_seconds is not None and (type(ttl_seconds) is not int or ttl_seconds <= 0):
            raise GeminiTransportError("configuration", "Cache TTL must be a positive integer number of seconds.")

        def worker(op):
            result, _ = self._json_request(op, self.api_base + "/v1beta/" + self.allowed_cache_name,
                method="GET" if ttl_seconds is None else "PATCH",
                body=None if ttl_seconds is None else {"ttl": str(ttl_seconds) + "s"})
            if result.get("name") != self.allowed_cache_name or result.get("model") != "models/" + self.model:
                raise GeminiTransportError("cache_identity", "Cache identity/model differs from the authorized input.")
            if not result.get("expireTime") or self._expired(result["expireTime"]):
                raise GeminiTransportError("cache_expired", "The authorized cache is unavailable or expired; no replacement was created.")
            return {key: result[key] for key in ("name", "model", "displayName", "createTime",
                "updateTime", "expireTime", "usageMetadata") if key in result}
        return self._run("cache_lookup" if ttl_seconds is None else "cache_ttl_update", worker)

    def generate(self, payload: dict) -> dict:
        """Stream one request and return parsed model JSON plus safe metadata."""
        if not isinstance(payload, dict):
            raise GeminiTransportError("request", "Generation payload must be an object.")
        def forbidden(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if (key.replace("_", "").lower() == "cachedcontent"
                            and (self.allowed_cache_name is None or item != self.allowed_cache_name)):
                        return True
                    if (key.replace("_", "").lower() == "mediaprocessing"
                            and item == "AGENTIC" and not self.allow_agentic_video):
                        return True
                    if forbidden(item):
                        return True
            elif isinstance(value, list):
                return any(forbidden(item) for item in value)
            return False
        if forbidden(payload):
            raise GeminiTransportError("request_policy", "Caching requires the exact opted-in cache; Agentic video processing requires its separate opt-in.")
        try:
            encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise GeminiTransportError("request", "Generation payload is not valid JSON.") from None

        def worker(op):
            metadata = {"finish_reason": None, "response_id": None, "model_version": None,
                        "usage": {}, "stream_events": 0, "candidate_count": 0,
                        "media_processing_calls": 0, "media_processing_responses": 0,
                        "request_sha256": hashlib.sha256(encoded).hexdigest(),
                        "attempt_count": 1, "remote_cancellation_verified": False}
            op.metadata = metadata
            op.emit({"event": "generation_status", "status": "submitting", "metadata": self._safe_metadata(metadata)})
            answer = []
            byte_count = 0
            last_notice = 0.0
            def consume(lines):
                nonlocal byte_count, last_notice
                text = "\n".join(lines)
                if text.strip() == "[DONE]":
                    return
                try:
                    event = _strict_json(text)
                except (ValueError, UnicodeError):
                    raise GeminiTransportError("malformed_stream", "Provider stream contains malformed event JSON.") from None
                if not isinstance(event, dict):
                    raise GeminiTransportError("malformed_stream", "Provider stream event is not an object.")
                metadata["stream_events"] += 1
                previous_id = metadata["response_id"]
                for source, target in (("responseId", "response_id"), ("modelVersion", "model_version"), ("usageMetadata", "usage")):
                    if source in event:
                        metadata[target] = event[source]
                if event.get("promptFeedback", {}).get("blockReason"):
                    metadata["block_reason"] = event["promptFeedback"]["blockReason"]
                if "error" in event:
                    diagnostic = self._error_diagnostic(event)
                    if diagnostic.get('format') != 'google_error':
                        raise GeminiTransportError('malformed_stream', 'Provider stream error envelope is malformed; completion remains unknown.')
                    metadata['provider_error'] = diagnostic
                    metadata['stream_error_received'] = True
                    raise GeminiTransportError("provider_stream_error", "Provider reported an error in its stream; no retry was made.",
                        metadata={'provider_error': diagnostic, 'stream_error_received': True})
                candidates = event.get("candidates", [])
                if not isinstance(candidates, list):
                    raise GeminiTransportError("malformed_stream", "Provider candidate structure is invalid.")
                metadata["candidate_count"] = max(metadata["candidate_count"], len(candidates))
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        raise GeminiTransportError("malformed_stream", "Provider candidate structure is invalid.")
                    if candidate.get("index", 0) != 0:
                        continue
                    if "finishReason" in candidate:
                        metadata["finish_reason"] = candidate["finishReason"]
                    for part in candidate.get("content", {}).get("parts", []):
                        if not isinstance(part, dict):
                            raise GeminiTransportError("malformed_stream", "Provider content part structure is invalid.")
                        # Native video navigation is provider-executed. Retain
                        # only its observed type/count/position, never tool
                        # arguments, results, thought text or signatures.
                        for kind, names, counter in (
                            ("call", ("toolCall", "tool_call"), "media_processing_calls"),
                            ("response", ("toolResponse", "tool_response"), "media_processing_responses"),
                        ):
                            if any(isinstance(part.get(name), dict)
                                   and part[name].get("toolType", part[name].get("tool_type")) == "MEDIA_PROCESSING"
                                   for name in names):
                                metadata[counter] += 1
                                op.emit({"event": "media_processing", "kind": kind,
                                         "stream_event": metadata["stream_events"]})
                        if any(name in part for name in ("toolCall", "tool_call", "toolResponse", "tool_response",
                                                         "functionCall", "function_call", "functionResponse", "function_response")):
                            continue
                        if isinstance(part.get("text"), str) and not part.get("thought"):
                            byte_count += len(part["text"].encode("utf-8"))
                            if byte_count > self.MAX_RESPONSE_BYTES:
                                raise GeminiTransportError("provider_response_size", "Model answer exceeded the permitted response size.")
                            answer.append(part["text"])
                            if self.capture_answer_deltas:
                                op.emit({"event": "answer_delta", "text": part["text"],
                                         "stream_event": metadata["stream_events"]})
                now = time.monotonic()
                if previous_id != metadata["response_id"] or metadata["finish_reason"] or now - last_notice >= 30:
                    op.emit({"event": "generation_status", "status": "streaming", "metadata": self._safe_metadata(metadata)})
                    last_notice = now

            try:
                with self._open(op, self.api_base + "/v1beta/models/" + self.model + ":streamGenerateContent?alt=sse",
                                body=encoded, method="POST", headers={"Content-Type": "application/json", "Accept": "text/event-stream"}) as stream:
                    lines = []
                    event_bytes = 0
                    while True:
                        raw = stream.readline(self.MAX_RESPONSE_BYTES + 1)
                        op.remaining()
                        if not raw:
                            break
                        event_bytes += len(raw)
                        if event_bytes > self.MAX_RESPONSE_BYTES:
                            raise GeminiTransportError("provider_response_size", "Provider stream event exceeded the permitted response size.")
                        try:
                            line = raw.decode("utf-8").rstrip("\r\n")
                        except UnicodeError:
                            raise GeminiTransportError("malformed_stream", "Provider stream is not valid UTF-8.") from None
                        if not line:
                            if lines:
                                consume(lines)
                            lines, event_bytes = [], 0
                        elif line.startswith("data:"):
                            lines.append(line[5:].lstrip(" "))
                    if lines:
                        consume(lines)
            finally:
                metadata["elapsed_seconds"] = round(time.monotonic() - op.started, 3)
                op.emit({"event": "generation_status", "status": "received", "metadata": self._safe_metadata(metadata)})
            safe = self._safe_metadata(metadata)
            if metadata.get("block_reason"):
                raise GeminiTransportError("blocked_response", "Provider blocked the response; required source evidence remains missing.", metadata=safe)
            if metadata["finish_reason"] != "STOP":
                raise GeminiTransportError("incomplete_response", "Provider did not complete with STOP; partial output cannot satisfy intake.", metadata=safe)
            raw_answer = "".join(answer).strip()
            if not raw_answer:
                raise GeminiTransportError("empty_response", "Provider completed without a non-thought answer.", metadata=safe)
            try:
                parsed = _strict_json(raw_answer)
            except (ValueError, UnicodeError):
                raise GeminiTransportError("model_json", "Model answer is not valid JSON; required intake remains incomplete.", metadata=safe) from None
            if not isinstance(parsed, dict):
                raise GeminiTransportError("model_json", "Model answer must be a JSON object.", metadata=safe)
            return {"body": parsed, "metadata": safe, "raw": "".join(answer)}

        return self._run("generation", worker)
