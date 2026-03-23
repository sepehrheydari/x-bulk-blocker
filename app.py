"""
X Bulk Blocker — Web UI
Run with:  python app.py          (local)
       or:  gunicorn app:app       (production)
Then open: http://localhost:7070
"""

import os
import secrets
import threading
import time
import uuid

from flask import Flask, Response, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from x_bulk_block import parse_list_id, run_job

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024  # 4 KB — all three fields are small

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# Job store: job_id -> {"messages": list, "done": bool, "created_at": float}
# Messages are appended by the worker; the poll endpoint reads them by index.
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

MAX_CONCURRENT_JOBS = 5
_JOB_TTL = 1800  # seconds


def _reap_stale_jobs() -> None:
    """Background daemon: evict job entries older than _JOB_TTL."""
    while True:
        time.sleep(60)
        cutoff = time.monotonic() - _JOB_TTL
        with _jobs_lock:
            stale = [jid for jid, v in _jobs.items() if v["created_at"] < cutoff]
            for jid in stale:
                _jobs.pop(jid, None)


threading.Thread(target=_reap_stale_jobs, daemon=True).start()


@app.after_request
def set_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
@limiter.limit("5 per minute")
def start():
    list_url   = request.form.get("list_url",   "").strip()
    auth_token = request.form.get("auth_token", "").strip()
    ct0        = request.form.get("ct0",        "").strip()
    dry_run    = request.form.get("mode") == "dry_run"

    if len(list_url) > 300 or len(auth_token) > 200 or len(ct0) > 200:
        return {"error": "Input too long."}, 400

    if not list_url or not auth_token or not ct0:
        return {"error": "All three fields are required."}, 400

    try:
        list_id = parse_list_id(list_url)
    except ValueError as exc:
        return {"error": str(exc)}, 400

    with _jobs_lock:
        if len(_jobs) >= MAX_CONCURRENT_JOBS:
            return {"error": "Server is busy. Please try again shortly."}, 503
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {
            "messages": [],
            "done": False,
            "created_at": time.monotonic(),
        }

    cookie_str = f"auth_token={auth_token}; ct0={ct0}"

    def worker():
        def log(msg: str):
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]["messages"].append({"type": "log", "msg": msg})

        try:
            run_job(list_id, cookie_str, dry_run=dry_run, log=log)
        except RuntimeError as exc:
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]["messages"].append({"type": "error", "msg": str(exc)})
        except Exception:
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]["messages"].append(
                        {"type": "error", "msg": "An unexpected error occurred. Please try again."}
                    )
        finally:
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id]["done"] = True

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.route("/poll/<job_id>")
def poll(job_id: str):
    """
    Polling endpoint — returns buffered log messages from `cursor` onwards.
    The frontend calls this every 500 ms instead of using SSE/EventSource.
    This avoids all proxy-buffering issues (HF Spaces, Render, Cloudflare, etc.).
    """
    try:
        uuid.UUID(job_id)
    except ValueError:
        return {"messages": [], "done": True}, 404

    cursor = request.args.get("cursor", 0, type=int)

    with _jobs_lock:
        entry = _jobs.get(job_id)
        if not entry:
            # Job finished and was reaped, or never existed
            return {"messages": [], "done": True}
        messages = entry["messages"][cursor:]
        done = entry["done"]

    return {
        "messages": messages,
        "done": done,
        "cursor": cursor + len(messages),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7070))
    print(f"🚀  Open http://localhost:{port} in your browser")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
