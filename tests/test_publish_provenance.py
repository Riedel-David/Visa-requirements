"""Provenance-only changes (new Wikipedia revision, same data) must not rewrite output."""

import copy
import json

from visa_pipeline.publish import format_passport_data, write_passport_file
from visa_pipeline.run import run
from test_run_e2e import FakeParseResult, make_fake_client


def _rec(dest="FR", status="visa_free", notes=None, revid=100):
    return {
        "passport": "DE", "destination": dest, "destination_name": dest, "area": None,
        "status": status, "alternative_statuses": [], "allowed_stay_days": 90,
        "allowed_stay_raw": "90 days", "notes": notes, "is_territory_or_restricted": False,
        "source_url": "https://en.wikipedia.org/wiki/Visa_requirements_for_German_citizens",
        "source_revision": str(revid),
    }


def _fmt(records, revid, ts="2024-01-01T00:00:00Z"):
    return format_passport_data("DE", "Visa requirements for German citizens", revid, ts, records)


def _write_then(tmp_path, old_records, new_records):
    old = _fmt(old_records, 100)
    assert write_passport_file(tmp_path, old) is True
    path = tmp_path / "passports" / "DE.json"
    before = path.read_bytes()
    new = _fmt(new_records, 101, "2024-02-02T00:00:00Z")
    return write_passport_file(tmp_path, new, json.loads(before)), path, before


def test_same_data_new_revision_keeps_bytes(tmp_path):
    changed, path, before = _write_then(tmp_path, [_rec(revid=100)], [_rec(revid=101)])
    assert changed is False
    assert path.read_bytes() == before
    assert json.loads(before)["source_revision"] == "100"


def test_status_change_is_written(tmp_path):
    changed, path, before = _write_then(
        tmp_path, [_rec(revid=100)], [_rec(status="evisa", revid=101)])
    assert changed is True
    assert json.loads(path.read_text())["source_revision"] == "101"


def test_notes_only_change_is_written(tmp_path):
    changed, path, _ = _write_then(
        tmp_path, [_rec(revid=100)], [_rec(notes="new note", revid=101)])
    assert changed is True
    assert json.loads(path.read_text())["records"][0]["notes"] == "new note"


def test_record_order_is_irrelevant(tmp_path):
    old = [_rec("FR", revid=100), _rec("JP", revid=100)]
    new = [_rec("JP", revid=101), _rec("FR", revid=101)]
    changed, _, _ = _write_then(tmp_path, old, new)
    assert changed is False


# --- run() level: index, all.json, state, changelog -------------------------

def _client(de_revid):
    client = make_fake_client()
    base = client.revisions.side_effect

    def revs(titles):
        out = base(titles)
        for t in out:
            if "German" in t:
                out[t] = {"revid": de_revid, "timestamp": f"2024-03-{de_revid % 28 + 1:02d}T00:00:00Z"}
        return out

    client.revisions.side_effect = revs
    client.page_wikitext.side_effect = lambda title: ("x", de_revid if "German" in title else 200)
    return client


def _parser(de_status="visa_free"):
    def parse(wikitext, *, passport, title, revid, transclusions):
        if passport == "DE":
            recs = [_rec(status=de_status, revid=revid)]
        else:
            recs = [dict(_rec(dest="GB", revid=revid), passport=passport)]
        return FakeParseResult(records=recs, unmapped_statuses=[], unmapped_destinations=[], warnings=[])
    return parse


def _load(p):
    return json.loads(p.read_text())


def test_run_provenance_only_edit(tmp_path):
    d, s, o = tmp_path / "data", tmp_path / "state", tmp_path / "out"
    run(data_dir=d, state_dir=s, out_dir=o, client=_client(100), parse_page=_parser())
    de_before = (d / "passports" / "DE.json").read_bytes()
    idx_before = (d / "index.json").read_bytes()
    all_before = (d / "all.json").read_bytes()

    assert run(data_dir=d, state_dir=s, out_dir=o, client=_client(105), parse_page=_parser()) == 0

    # file, index, all.json untouched (incl. generated_at / last_changed)
    assert (d / "passports" / "DE.json").read_bytes() == de_before
    assert (d / "index.json").read_bytes() == idx_before
    assert (d / "all.json").read_bytes() == all_before
    entry = _load(d / "index.json")["passports"]["DE"]
    assert entry["source_revision"] == "100"
    assert _load(d / "passports" / "DE.json")["source_revision"] == entry["source_revision"]
    # state advanced, so the page is skipped next time
    assert _load(s / "revisions.json")["DE"]["revid"] == 105
    summary = _load(o / "summary.json")
    assert summary["pages_parsed"] == 1 and summary["changes"] == 0
    assert "No changes." in (o / "changelog.md").read_text()

    client3 = _client(105)
    run(data_dir=d, state_dir=s, out_dir=o, client=client3, parse_page=_parser())
    client3.page_wikitext.assert_not_called()


def test_run_real_change_updates_everything(tmp_path):
    d, s, o = tmp_path / "data", tmp_path / "state", tmp_path / "out"
    run(data_dir=d, state_dir=s, out_dir=o, client=_client(100), parse_page=_parser())
    old_entry = copy.deepcopy(_load(d / "index.json")["passports"]["DE"])

    run(data_dir=d, state_dir=s, out_dir=o, client=_client(105), parse_page=_parser("evisa"))

    de = _load(d / "passports" / "DE.json")
    entry = _load(d / "index.json")["passports"]["DE"]
    assert de["records"][0]["status"] == "evisa" and de["source_revision"] == "105"
    assert entry["source_revision"] == "105"
    assert entry["last_changed"] == de["generated_at"] != old_entry["last_changed"]
    assert _load(d / "all.json")["passports"]["DE"] == de["records"]
    assert _load(s / "revisions.json")["DE"]["revid"] == 105
    assert _load(o / "summary.json")["changes"] == 1
    assert "| FR |" in (o / "changelog.md").read_text()
