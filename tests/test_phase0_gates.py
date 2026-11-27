"""Phase 0 Guardrail & Parity Contract Verification Tests."""

import json
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.verify_splits import run_verification


def test_phase0_artifacts_exist():
    required = [
        "requirements-research.txt",
        "research/verify_splits.py",
        "scripts/export_phase0_artifacts.py",
        "extension/engine/psl_rules.json",
        "tests/golden_urls.json",
    ]
    for path in required:
        assert os.path.exists(path), f"Missing Phase 0 artifact: {path}"


def test_psl_rules_integrity():
    with open("extension/engine/psl_rules.json", encoding="utf-8") as f:
        psl = json.load(f)

    assert "icann" in psl and "private" in psl
    icann_exact = set(psl["icann"]["exact"])
    private_exact = set(psl["private"]["exact"])

    for suffix in ("com", "in", "co.in", "gov.in", "co.uk", "ac.in"):
        assert suffix in icann_exact, f"Missing ICANN suffix '{suffix}'"

    for cloud_host in ("vercel.app", "workers.dev", "netlify.app", "blogspot.com", "github.io", "pages.dev"):
        assert cloud_host in private_exact, f"Missing private cloud suffix '{cloud_host}'"


def test_golden_urls_integrity():
    with open("tests/golden_urls.json", encoding="utf-8") as f:
        golden = json.load(f)

    assert golden["count"] == 100
    assert len(golden["records"]) == 100
    assert len(golden["feature_names"]) == 47

    for rec in golden["records"]:
        assert rec["is_valid"] is True, f"Expected valid syntax for {rec['raw_url']}"
        feats = rec["features"]
        assert len(feats) == 47
        for k, v in feats.items():
            assert isinstance(v, (int, float))
            assert not math.isnan(v) and not math.isinf(v), f"Invalid value for {k} in {rec['raw_url']}"


def test_verify_splits_baseline_audit():
    report, _ = run_verification(strict=False)
    checks = {c["pair"]: c for c in report["strict_zero_overlap_checks"]}

    # Core & temporal splits must already have 0 overlap
    assert checks["global_train vs global_test"]["is_clean"] is True
    assert checks["a5_temporal_train vs a5_temporal_test"]["is_clean"] is True
    assert checks["global_train vs a4_domain_disjoint"]["is_clean"] is True
    assert report["internal_train_val_grouped_check"]["is_clean"] is True

    # All strict zero-overlap splits (including repaired A1) must have 0 overlap
    assert checks["global_train vs a1_path_matched"]["is_clean"] is True
