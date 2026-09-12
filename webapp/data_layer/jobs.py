"""Background job manager.

In-memory state on a worker thread, so the slow Earth Engine pull never
blocks a request. Single-process only by design: two backend instances would
each keep their own job table, which is why this app is not deployed that way.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from . import fetch
from .config import DataLayerError

Status = Literal["pending", "running", "done", "error"]


@dataclass
class Job:
    job_id: str
    pincode: str
    start_year: int
    end_year: int
    status: Status = "pending"
    progress: float = 0.0  # 0..1
    message: str = "Queued"
    rows: int | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _Registry:
    jobs: dict[str, Job] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


_registry = _Registry()
# One worker: concurrent fetches for the same pincode are not deduplicated
# (a settled scope decision), and serialising them keeps Earth Engine quota
# predictable.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fetch")


def _run(job_id: str) -> None:
    with _registry.lock:
        job = _registry.jobs[job_id]
        job.status = "running"
        job.message = "Starting fetch"

    def progress(done: int, total: int, message: str) -> None:
        with _registry.lock:
            job.progress = done / total if total else 0.0
            job.message = message

    try:
        frame = fetch.get_or_fetch_ssrd(
            job.pincode, job.start_year, job.end_year, progress
        )
    except DataLayerError as exc:
        with _registry.lock:
            job.status = "error"
            job.error = str(exc)
            job.message = "Fetch failed"
        return
    except Exception as exc:  # noqa: BLE001 - a worker thread must never die silently
        with _registry.lock:
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "Fetch failed"
        return
    with _registry.lock:
        job.status = "done"
        job.progress = 1.0
        job.rows = int(len(frame))
        job.message = f"Fetched {len(frame):,} daily readings"


def start_fetch_job(pincode: str, start_year: int, end_year: int) -> str:
    """Kick off a background fetch and return immediately with its id."""
    job_id = uuid.uuid4().hex[:12]
    with _registry.lock:
        _registry.jobs[job_id] = Job(
            job_id=job_id, pincode=pincode, start_year=start_year, end_year=end_year
        )
    _executor.submit(_run, job_id)
    return job_id


def get_status(job_id: str) -> dict[str, Any] | None:
    """Pollable status for the frontend's loading indicator."""
    with _registry.lock:
        job = _registry.jobs.get(job_id)
        return job.as_dict() if job else None
