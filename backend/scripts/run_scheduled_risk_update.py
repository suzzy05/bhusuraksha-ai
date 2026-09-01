"""Phase 16 — scheduled risk-update worker.

Deliberately NOT a loop inside the FastAPI process: this is a small,
independent script that calls the existing, already-tested
POST /weather/refresh-all endpoint over HTTP, on an interval. It can run:

  - as a one-shot invocation from an external scheduler (cron, a Docker
    healthcheck-style timer, Windows Task Scheduler): `--once`
  - as a long-lived process (e.g. the optional `worker` Docker Compose
    service) that sleeps between runs and exits cleanly on SIGTERM/SIGINT

A failed run is logged and retried on the next interval — it never
crashes the process or the API it's calling.

Usage:
    python scripts/run_scheduled_risk_update.py --once
    python scripts/run_scheduled_risk_update.py --interval-seconds 1800
"""
import argparse
import logging
import signal
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_config import configure_logging  # noqa: E402

configure_logging(service_name="risk-update-worker")
logger = logging.getLogger("risk_update_worker")

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_INTERVAL_SECONDS = 1800
# /weather/refresh-all calls the live weather provider once per zone,
# sequentially. Measured 100-110s normally, but repeated back-to-back
# testing this session (many manual refreshes in a short window) appears
# to have triggered rate-limiting/slowdown on the free Open-Meteo API,
# pushing a real cycle past 300s. 600s leaves real headroom; a production
# deployment triggering this once per --interval-seconds (not repeatedly
# within minutes, the way this session's testing did) shouldn't see this.
REQUEST_TIMEOUT_SECONDS = 600

_shutdown_requested = False


def _handle_shutdown_signal(signum, _frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum} — will exit after the current cycle completes.")
    _shutdown_requested = True


def run_once(api_base_url: str) -> bool:
    """Calls POST /weather/refresh-all. Returns True on success. Never
    raises — a provider/network failure is logged and reported as a
    failed cycle, not a crash."""
    try:
        response = requests.post(f"{api_base_url}/weather/refresh-all", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json()
        logger.info(
            f"Cycle complete: updated={result.get('updated')} risk_updated={result.get('risk_updated')} "
            f"alerts_generated={result.get('alerts_generated')} weather_unavailable={result.get('weather_unavailable')}"
        )
        return True
    except Exception as exc:  # noqa: BLE001 - a bad cycle must never crash the worker
        logger.error(f"Cycle failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Scheduled risk-update worker")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help="Backend base URL")
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit (for external schedulers)")
    args = parser.parse_args()

    if args.once:
        success = run_once(args.api_base_url)
        sys.exit(0 if success else 1)

    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)

    logger.info(f"Starting scheduled risk-update worker: interval={args.interval_seconds}s target={args.api_base_url}")
    while not _shutdown_requested:
        run_once(args.api_base_url)
        for _ in range(args.interval_seconds):
            if _shutdown_requested:
                break
            time.sleep(1)

    logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
