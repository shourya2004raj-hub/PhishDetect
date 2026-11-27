"""Phase 1 Dataset Integrity, Zero-Leakage & Sampling Balance Gate Tests."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.verify_splits import run_verification


def test_phase1_artifacts_exist():
    required = [
        "data/processed/v3_train.csv",
        "data/processed/v3_val.csv",
        "data/processed/v3_test.csv",
        "data/benchmark/a1_path_matched.csv",
        "data/benchmark/a5_temporal_monthly.csv",
        "data/benchmark/a5_base_rate_1pct.csv",
        "data/benchmark/a5_base_rate_5pct.csv",
        "data/benchmark/stage2_cloud_dom.parquet",
    ]
    for p in required:
        assert os.path.exists(p), f"Missing Phase 1 dataset: {p}"


def test_strict_zero_leakage_gate():
    report, passed = run_verification(strict=True)
    assert passed is True, f"Strict verification gate failed: {report['summary']}"
    assert report["summary"]["all_strict_overlaps_zero"] is True
    assert report["summary"]["no_bare_root_bias_warnings"] is True


def test_v3_benign_query_representation():
    """Verify v3_train no longer has the 0% benign query-string defect."""
    df_tr = pd.read_csv("data/processed/v3_train.csv")
    b = df_tr[df_tr["label"] == 0]
    b_query_rate = b["url"].astype(str).str.contains(r"\?", regex=True).mean()
    assert b_query_rate >= 0.03, f"Benign query rate still too low: {b_query_rate:.2%}"


def test_stage2_cloud_dom_schema():
    df = pd.read_parquet("data/benchmark/stage2_cloud_dom.parquet")
    assert len(df) >= 1000
    assert (df["label"] == 1).sum() >= 400
    assert (df["label"] == 0).sum() >= 400
    for col in ("has_password_input", "has_cross_origin_form", "brand_dom_mismatch", "is_cloud_host"):
        assert col in df.columns
