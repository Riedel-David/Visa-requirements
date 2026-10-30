"""Tests for main pipeline run."""

from pathlib import Path

from visa_pipeline.run import needs_update, compute_parser_fingerprint


def test_needs_update_force():
    """Test needs_update with force flag."""
    assert needs_update("DE", 123, {}, Path("."), force=True)


def test_needs_update_missing_output():
    """Test needs_update when output file missing."""
    tmp = Path("/tmp/nonexistent")
    assert needs_update("DE", 123, {}, tmp, force=False)


def test_needs_update_revid_changed():
    """Test needs_update when revid changed."""
    stored = {"DE": {"revid": 122, "timestamp": "2024-01-01T00:00:00Z"}}
    assert needs_update("DE", 123, stored, Path("."), force=False)


def test_needs_update_unchanged(tmp_path):
    """Test needs_update when unchanged."""
    # Create output file
    output_dir = tmp_path / "passports"
    output_dir.mkdir()
    (output_dir / "DE.json").write_text("{}")

    stored = {"DE": {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}}
    assert not needs_update("DE", 123, stored, tmp_path, force=False)


def test_compute_parser_fingerprint():
    """Test parser fingerprint computation."""
    # Should return a valid SHA256 hex string
    fingerprint = compute_parser_fingerprint()
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64
    assert all(c in "0123456789abcdef" for c in fingerprint)

    # Should be deterministic
    fingerprint2 = compute_parser_fingerprint()
    assert fingerprint == fingerprint2


def test_parser_fingerprint_forces_reparse(tmp_path):
    """Test that parser fingerprint mismatch forces reparse."""
    from visa_pipeline.run import run

    # Create a mock client
    class MockClient:
        def __init__(self):
            self.calls = []

        def revisions(self, titles):
            self.calls.append(("revisions", titles))
            return {
                "Test page": {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"}
            }

        def page_wikitext(self, title):
            self.calls.append(("page_wikitext", title))
            return "== Test ==\nSome content", 100

    # Create a mock parse_page
    def mock_parse_page(wikitext, *, passport, title, revid, transclusions):
        from visa_pipeline.extract_main import ParseResult
        return ParseResult(
            records=[{"passport": passport, "destination": "US", "destination_name": "United States",
                     "area": None, "status": "visa_free", "alternative_statuses": [],
                     "allowed_stay_days": None, "allowed_stay_raw": None, "notes": None,
                     "is_territory_or_restricted": False}],
            unmapped_statuses=[],
            unmapped_destinations=[],
            warnings=[]
        )

    # Setup directories
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"
    state_dir.mkdir(parents=True)

    # Create pages.json with proper format (use recent date to avoid cache expiration)
    from datetime import datetime, timezone
    pages_file = state_dir / "pages.json"
    import json
    with open(pages_file, 'w') as f:
        json.dump({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "pages": [{"title": "Test page", "passport": "DE"}]
        }, f)

    # Create revisions.json with old fingerprint
    revisions_file = state_dir / "revisions.json"
    revisions_file.write_text('{"DE": {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"}, "_parser": {"fingerprint": "0000000000000000000000000000000000000000000000000000000000000000"}}')

    # Create existing output file
    output_dir = data_dir / "passports"
    output_dir.mkdir(parents=True)
    (output_dir / "DE.json").write_text('{"passport": "DE", "records": [], "source_revision": "100", "source_timestamp": "2024-01-01T00:00:00Z", "source_title": "Test page", "source_url": "", "generated_at": "2024-01-01T00:00:00Z", "schema_version": "1.0.0", "license": "", "attribution": ""}')

    # Run pipeline
    client = MockClient()
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir,
        parse_page=mock_parse_page, client=client, refresh_pages=False)

    # Check that page was reparsed even though revid is the same
    assert any(call[0] == "page_wikitext" and call[1] == "Test page" for call in client.calls)

    # Check that new fingerprint was stored
    import json
    with open(revisions_file) as f:
        revisions = json.load(f)
    assert "_parser" in revisions
    assert revisions["_parser"]["fingerprint"] != "0000000000000000000000000000000000000000000000000000000000000000"


def test_parser_fingerprint_matching_skips(tmp_path):
    """Test that matching parser fingerprint still skips unchanged pages."""
    from visa_pipeline.run import run, compute_parser_fingerprint

    # Create a mock client
    class MockClient:
        def __init__(self):
            self.calls = []

        def revisions(self, titles):
            self.calls.append(("revisions", titles))
            return {
                "Test page": {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"}
            }

        def page_wikitext(self, title):
            self.calls.append(("page_wikitext", title))
            return "== Test ==\nSome content", 100

    # Create a mock parse_page
    def mock_parse_page(wikitext, *, passport, title, revid, transclusions):
        from visa_pipeline.extract_main import ParseResult
        return ParseResult(
            records=[{"passport": passport, "destination": "US", "destination_name": "United States",
                     "area": None, "status": "visa_free", "alternative_statuses": [],
                     "allowed_stay_days": None, "allowed_stay_raw": None, "notes": None,
                     "is_territory_or_restricted": False}],
            unmapped_statuses=[],
            unmapped_destinations=[],
            warnings=[]
        )

    # Setup directories
    data_dir = tmp_path / "data"
    state_dir = tmp_path / "state"
    out_dir = tmp_path / "out"
    state_dir.mkdir(parents=True)

    # Create pages.json with proper format (use recent date to avoid cache expiration)
    from datetime import datetime, timezone
    pages_file = state_dir / "pages.json"
    import json
    with open(pages_file, 'w') as f:
        json.dump({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "pages": [{"title": "Test page", "passport": "DE"}]
        }, f)

    # Get current fingerprint
    current_fingerprint = compute_parser_fingerprint()

    # Create revisions.json with current fingerprint
    revisions_file = state_dir / "revisions.json"
    import json
    with open(revisions_file, 'w') as f:
        json.dump({
            "DE": {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"},
            "_parser": {"fingerprint": current_fingerprint}
        }, f)

    # Create existing output file
    output_dir = data_dir / "passports"
    output_dir.mkdir(parents=True)
    (output_dir / "DE.json").write_text('{"passport": "DE", "records": [], "source_revision": "100", "source_timestamp": "2024-01-01T00:00:00Z", "source_title": "Test page", "source_url": "", "generated_at": "2024-01-01T00:00:00Z", "schema_version": "1.0.0", "license": "", "attribution": ""}')

    # Run pipeline
    client = MockClient()
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir,
        parse_page=mock_parse_page, client=client, refresh_pages=False)

    # Check that page was NOT reparsed since fingerprint matches
    assert not any(call[0] == "page_wikitext" and call[1] == "Test page" for call in client.calls)


CODES = ["AD", "AE", "AF", "AG", "AL", "AM", "AO", "AR", "AT", "AU",
         "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ"]


def _record(code, status):
    return {"passport": "DE", "destination": code, "destination_name": code, "area": None,
            "status": status, "alternative_statuses": [], "allowed_stay_days": None,
            "allowed_stay_raw": None, "notes": None, "is_territory_or_restricted": False,
            "source_url": "", "source_revision": "100"}


def _run_with_status_flip(tmp_path, revisions, **kwargs):
    """Previous file has 20 visa_required rows; the reparse turns all of them visa_free."""
    import json
    from datetime import datetime, timezone
    from visa_pipeline.extract_main import ParseResult
    from visa_pipeline.run import run

    class MockClient:
        def __init__(self):
            self.fetched = []

        def revisions(self, titles):
            return {"Test page": {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"}}

        def page_wikitext(self, title):
            self.fetched.append(title)
            return "== Test ==", 100

    def parse_page(wikitext, *, passport, title, revid, transclusions):
        return ParseResult(records=[_record(c, "visa_free") for c in CODES],
                           unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    state_dir, data_dir, out_dir = tmp_path / "state", tmp_path / "data", tmp_path / "out"
    state_dir.mkdir()
    (state_dir / "pages.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pages": [{"title": "Test page", "passport": "DE"}]}))
    (state_dir / "revisions.json").write_text(json.dumps(revisions))
    (data_dir / "passports").mkdir(parents=True)
    (data_dir / "passports" / "DE.json").write_text(json.dumps({
        "schema_version": "1.0.0", "passport": "DE", "source_title": "Test page",
        "source_url": "", "source_revision": "100", "source_timestamp": "2024-01-01T00:00:00Z",
        "generated_at": "2024-01-01T00:00:00Z", "license": "", "attribution": "",
        "records": [_record(c, "visa_required") for c in CODES]}))

    client = MockClient()
    run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir,
        parse_page=parse_page, client=client, refresh_pages=False, **kwargs)
    statuses = {r["status"] for r in
                json.loads((data_dir / "passports" / "DE.json").read_text())["records"]}
    return client, statuses


def test_missing_parser_fingerprint_forces_reparse(tmp_path):
    client, _ = _run_with_status_flip(tmp_path, {"DE": {"revid": 100}})
    assert client.fetched == ["Test page"]


def test_parser_change_reparse_still_applies_safety_thresholds(tmp_path):
    client, statuses = _run_with_status_flip(
        tmp_path, {"DE": {"revid": 100}, "_parser": {"fingerprint": "old"}})
    assert client.fetched == ["Test page"]
    assert statuses == {"visa_required"}  # blocked: 20 status changes > 15


def test_force_bypasses_safety_thresholds(tmp_path):
    _, statuses = _run_with_status_flip(
        tmp_path, {"DE": {"revid": 100}, "_parser": {"fingerprint": "old"}}, force=True)
    assert statuses == {"visa_free"}


def _two_page_env(tmp_path, revisions):
    """DE and FR pages, both with published files at revid 100."""
    import json
    from datetime import datetime, timezone
    state_dir, data_dir, out_dir = tmp_path / "state", tmp_path / "data", tmp_path / "out"
    state_dir.mkdir()
    (state_dir / "pages.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pages": [{"title": "DE page", "passport": "DE"},
                  {"title": "FR page", "passport": "FR"}]}))
    (state_dir / "revisions.json").write_text(json.dumps(revisions))
    (data_dir / "passports").mkdir(parents=True)
    for iso2 in ("DE", "FR"):
        recs = [dict(_record(c, "visa_required"), passport=iso2) for c in CODES]
        (data_dir / "passports" / f"{iso2}.json").write_text(json.dumps({
            "schema_version": "1.0.0", "passport": iso2, "source_title": f"{iso2} page",
            "source_url": "", "source_revision": "100",
            "source_timestamp": "2024-01-01T00:00:00Z",
            "generated_at": "2024-01-01T00:00:00Z", "license": "", "attribution": "",
            "records": recs}))
    return data_dir, state_dir, out_dir


class _TwoPageClient:
    def __init__(self):
        self.fetched = []

    def revisions(self, titles):
        return {t: {"revid": 100, "timestamp": "2024-01-01T00:00:00Z"} for t in titles}

    def page_wikitext(self, title):
        if not title.startswith("Template:"):
            self.fetched.append(title)
        return "== T ==", 100


def _run_two(env, fail=(), flip=(), **kwargs):
    from visa_pipeline.extract_main import ParseResult
    from visa_pipeline.run import run
    data_dir, state_dir, out_dir = env
    client = _TwoPageClient()

    def parse_page(wikitext, *, passport, title, revid, transclusions):
        if passport in fail:
            raise RuntimeError("boom")
        status = "visa_free" if passport in flip else "visa_required"
        return ParseResult(records=[dict(_record(c, status), passport=passport) for c in CODES],
                           unmapped_statuses=[], unmapped_destinations=[], warnings=[])

    code = run(data_dir=data_dir, state_dir=state_dir, out_dir=out_dir, parse_page=parse_page,
               client=client, refresh_pages=False, **kwargs)
    return code, client


def test_failed_page_is_retried_after_parser_change(tmp_path):
    env = _two_page_env(tmp_path, {"DE": {"revid": 100}, "FR": {"revid": 100},
                                   "_parser": {"fingerprint": "old"}})
    code, client = _run_two(env, fail=("DE",))
    assert code == 1
    assert sorted(client.fetched) == ["DE page", "FR page"]
    # Second run: parser fingerprint is now current, DE page revision unchanged,
    # yet DE must be retried; FR must not.
    code, client = _run_two(env)
    assert code == 0
    assert client.fetched == ["DE page"]


def test_blocked_page_is_retried_after_parser_change(tmp_path):
    env = _two_page_env(tmp_path, {"DE": {"revid": 100}, "FR": {"revid": 100},
                                   "_parser": {"fingerprint": "old"}})
    _run_two(env, flip=("DE",))  # 20 status changes > 15 -> blocked
    _, client = _run_two(env, flip=("DE",))
    assert client.fetched == ["DE page"]


def test_only_does_not_update_global_markers(tmp_path):
    import json
    env = _two_page_env(tmp_path, {"DE": {"revid": 100}, "FR": {"revid": 100},
                                   "_parser": {"fingerprint": "old"}})
    _run_two(env, only=["DE"])
    revs = json.loads((env[1] / "revisions.json").read_text())
    assert revs["_parser"]["fingerprint"] == "old"
    # The full run afterwards still reparses FR
    _, client = _run_two(env)
    assert "FR page" in client.fetched
