"""Tests for data/status.json, stale-run tracking and the blocked-run exit code."""

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from visa_pipeline.publish import build_status
from visa_pipeline.run import BLOCKED_ALERT_RUNS, update_stale_state
from visa_pipeline.validate import load_schema, validate_index_file, validate_status_file
from test_run import _run_two, _two_page_env

SCHEMA_DIR = Path(__file__).parent.parent / "src" / "visa_pipeline" / "schema"
NOW = datetime(2026, 11, 9, 4, 17, 31, tzinfo=timezone.utc)
ENV = {"DE": {"revid": 100}, "FR": {"revid": 100}, "_parser": {"fingerprint": "old"}}


def _status(env):
    return json.loads((env[0] / "status.json").read_text())


def _stale(env):
    return json.loads((env[1] / "stale.json").read_text())


def test_build_status_ok_and_partial():
    ok = build_status(NOW, 3, [])
    assert ok == {"schema_version": "1.0.0", "last_checked_at": "2026-11-09T04:17:31Z",
                  "last_run_status": "ok", "dataset_version": "data-2026-11-09",
                  "passports_total": 3, "passports_stale": []}
    entry = {"passport": "DE", "reason": "blocked", "latest_seen_revision": 5,
             "data_revision": 4, "consecutive_runs": 1}
    assert build_status(NOW, 3, [entry])["last_run_status"] == "partial"


def test_status_schema_validation():
    schema = load_schema(SCHEMA_DIR / "status.schema.json")
    entry = {"passport": "DE", "reason": "failed", "latest_seen_revision": None,
             "data_revision": None, "consecutive_runs": 1}
    validate_status_file(build_status(NOW, 1, [entry]), schema)
    bad = build_status(NOW, 1, [dict(entry, reason="weird")])
    with pytest.raises(jsonschema.ValidationError):
        validate_status_file(bad, schema)
    with pytest.raises(jsonschema.ValidationError):
        validate_status_file(dict(build_status(NOW, 1, []), extra=1), schema)


def test_index_schema_accepts_committed_index():
    index = json.loads((Path(__file__).parent.parent / "data" / "index.json").read_text())
    validate_index_file(index, load_schema(SCHEMA_DIR / "index.schema.json"))


def test_status_ok_written_when_nothing_changed(tmp_path):
    env = _two_page_env(tmp_path, ENV)
    code, _ = _run_two(env, now=NOW)
    assert code == 0
    status = _status(env)
    assert status["last_run_status"] == "ok" and status["passports_stale"] == []
    assert status["passports_total"] == 2 and status["last_checked_at"] == "2026-11-09T04:17:31Z"
    # second run with nothing to do still rewrites status.json
    later = datetime(2026, 11, 16, 4, 0, 0, tzinfo=timezone.utc)
    _run_two(env, now=later)
    assert _status(env)["last_checked_at"] == "2026-11-16T04:00:00Z"
    assert _stale(env) == {}


def test_status_partial_blocked_and_failed(tmp_path):
    env = _two_page_env(tmp_path, ENV)
    code, _ = _run_two(env, flip=("DE",), fail=("FR",), now=NOW)
    assert code == 1
    status = _status(env)
    assert status["last_run_status"] == "partial"
    assert status["passports_stale"] == [
        {"passport": "DE", "reason": "blocked", "latest_seen_revision": 100,
         "data_revision": 100, "consecutive_runs": 1},
        {"passport": "FR", "reason": "failed", "latest_seen_revision": 100,
         "data_revision": 100, "consecutive_runs": 1},
    ]


def test_consecutive_runs_count_and_reset(tmp_path):
    env = _two_page_env(tmp_path, ENV)
    _run_two(env, flip=("DE",), now=NOW)
    _run_two(env, flip=("DE",), now=NOW)
    assert _status(env)["passports_stale"][0]["consecutive_runs"] == 2
    assert _stale(env)["DE"]["consecutive_runs"] == 2
    code, _ = _run_two(env, now=NOW)  # DE parses cleanly again
    assert code == 0
    assert _status(env)["passports_stale"] == [] and _stale(env) == {}


def test_exit_code_after_three_blocked_runs(tmp_path):
    env = _two_page_env(tmp_path, ENV)
    codes = [_run_two(env, flip=("DE",), now=NOW)[0] for _ in range(BLOCKED_ALERT_RUNS)]
    assert codes == [0] * (BLOCKED_ALERT_RUNS - 1) + [1]
    # everything was still written
    assert _status(env)["passports_stale"][0]["consecutive_runs"] == BLOCKED_ALERT_RUNS
    assert (env[0] / "index.json").exists()


def test_update_stale_state_reason_change_and_only():
    prev = {"DE": {"reason": "blocked", "consecutive_runs": 4, "latest_seen_revision": 1},
            "FR": {"reason": "failed", "consecutive_runs": 2, "latest_seen_revision": 1},
            "XX": {"reason": "failed", "consecutive_runs": 2, "latest_seen_revision": 1}}
    new = update_stale_state(
        prev, {"DE": {"reason": "failed", "latest_seen_revision": 2}},
        processed={"DE"}, known={"DE", "FR"})
    assert new["DE"]["consecutive_runs"] == 1 and new["DE"]["reason"] == "failed"
    assert new["FR"] == prev["FR"]  # not processed (--only): carried over
    assert "XX" not in new  # no longer a known passport
