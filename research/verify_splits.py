"""Zero-Leakage Split Verifier & Sampling Bias Gatekeeper.

Enforces Arp et al. (USENIX Security 2022) Pitfalls P1 (Sampling Bias) and P3 (Data Snooping)
and Pendlebury et al. (USENIX Security 2019) chronological separation invariants across all
training, validation, and benchmark splits.

Usage:
    python research/verify_splits.py           # Audit mode (prints report + saves JSON)
    python research/verify_splits.py --strict  # CI/Phase Gate mode (exits non-zero on violation)
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.data_loader import split_train_val_grouped
from src.utils.domain import extract_registered_domain


SPLIT_PATHS: Dict[str, str] = {
    "global_train": "data/processed/global_train.csv",
    "global_test": "data/processed/global_test.csv",
    "indian_train": "data/processed/indian_train.csv",
    "indian_test": "data/processed/indian_test.csv",
    "phiusiil_train": "data/processed/phiusiil_train.csv",
    "phiusiil_test": "data/processed/phiusiil_test.csv",
    "a1_path_matched": "data/benchmark/a1_path_matched.csv",
    "a3_unseen_brands": "data/benchmark/a3_unseen_brands.csv",
    "a4_cross_distribution": "data/benchmark/a4_cross_distribution.csv",
    "a4_domain_disjoint": "data/benchmark/a4_domain_disjoint.csv",
    "a5_temporal_train": "data/benchmark/a5_temporal_train.csv",
    "a5_temporal_test": "data/benchmark/a5_temporal_test.csv",
}

# Pairs that MUST have strictly zero overlapping registered domains in strict gate mode
STRICT_ZERO_OVERLAP_PAIRS: List[Tuple[str, str]] = [
    ("global_train", "global_test"),
    ("indian_train", "indian_test"),
    ("phiusiil_train", "phiusiil_test"),
    ("a5_temporal_train", "a5_temporal_test"),
    ("global_train", "a1_path_matched"),
    ("global_train", "a4_domain_disjoint"),
]

# Pairs monitored for shared multi-tenant / natural cross-corpus overlap (informational)
MONITORED_OVERLAP_PAIRS: List[Tuple[str, str]] = [
    ("global_train", "a3_unseen_brands"),
    ("global_train", "a4_cross_distribution"),
]


def _load_domains(df: pd.DataFrame) -> pd.Series:
    if "registered_domain" in df.columns and df["registered_domain"].notna().all():
        return df["registered_domain"].astype(str).str.lower().str.strip()
    return df["url"].astype(str).apply(extract_registered_domain)


def _label_col(df: pd.DataFrame) -> str:
    if "label" in df.columns:
        return "label"
    if "label_num" in df.columns:
        return "label_num"
    raise ValueError("Dataset missing both 'label' and 'label_num' columns")


def _compute_bare_root_rates(df: pd.DataFrame) -> Dict[str, float]:
    """Measure fraction of URLs that are bare root homepages (path empty/'/' and no query)."""
    lbl = _label_col(df)

    def is_bare(u: str) -> bool:
        try:
            p = urlparse(str(u) if "://" in str(u) else f"https://{u}")
            return p.path in ("", "/") and not p.query
        except Exception:
            return False

    bare_flags = df["url"].astype(str).apply(is_bare)
    benign_mask = df[lbl].astype(int) == 0
    phish_mask = df[lbl].astype(int) == 1

    benign_bare = float(bare_flags[benign_mask].mean()) if benign_mask.any() else 0.0
    phish_bare = float(bare_flags[phish_mask].mean()) if phish_mask.any() else 0.0
    gap = abs(benign_bare - phish_bare)

    return {
        "benign_bare_rate": round(benign_bare, 4),
        "phishing_bare_rate": round(phish_bare, 4),
        "bare_rate_gap": round(gap, 4),
        "bias_warning": gap > 0.25,
    }


def check_pair_overlap(
    dfs: Dict[str, pd.DataFrame],
    domain_sets: Dict[str, set],
    left: str,
    right: str,
) -> Dict:
    if left not in dfs or right not in dfs:
        return {"pair": f"{left} vs {right}", "status": "missing"}
    overlap = domain_sets[left].intersection(domain_sets[right])
    right_doms = _load_domains(dfs[right])
    affected_rows = int(right_doms.isin(overlap).sum())
    total_right = len(dfs[right])
    return {
        "pair": f"{left} vs {right}",
        "left_domains": len(domain_sets[left]),
        "right_domains": len(domain_sets[right]),
        "overlap_domains": len(overlap),
        "affected_right_rows": affected_rows,
        "affected_right_pct": round((affected_rows / total_right) * 100.0, 2) if total_right else 0.0,
        "sample_overlaps": sorted(overlap)[:10],
        "is_clean": len(overlap) == 0,
    }


def run_verification(strict: bool = False) -> Tuple[Dict, bool]:
    dfs: Dict[str, pd.DataFrame] = {}
    domain_sets: Dict[str, set] = {}

    for name, rel_path in SPLIT_PATHS.items():
        if os.path.exists(rel_path):
            df = pd.read_csv(rel_path)
            dfs[name] = df
            domain_sets[name] = set(_load_domains(df).unique()) - {""}

    strict_results = [check_pair_overlap(dfs, domain_sets, a, b) for a, b in STRICT_ZERO_OVERLAP_PAIRS]
    monitored_results = [check_pair_overlap(dfs, domain_sets, a, b) for a, b in MONITORED_OVERLAP_PAIRS]

    # Internal grouped train/val invariant check
    val_check = {"status": "missing", "is_clean": False}
    if "global_train" in dfs:
        df_tr, df_vl = split_train_val_grouped(dfs["global_train"], val_domain_ratio=0.15, random_state=42)
        tr_doms = set(_load_domains(df_tr).unique())
        vl_doms = set(_load_domains(df_vl).unique())
        ov = tr_doms.intersection(vl_doms)
        val_check = {
            "train_rows": len(df_tr),
            "val_rows": len(df_vl),
            "overlap_domains": len(ov),
            "is_clean": len(ov) == 0,
        }

    # Sampling bias audit (bare homepage vs deep path imbalance)
    bias_audit = {}
    for split_name in ["global_train", "global_test", "a1_path_matched", "a5_temporal_train", "a5_temporal_test"]:
        if split_name in dfs:
            bias_audit[split_name] = _compute_bare_root_rates(dfs[split_name])

    all_strict_clean = all(r.get("is_clean", False) for r in strict_results) and val_check.get("is_clean", False)
    no_bias_warnings = not any(v.get("bias_warning", False) for v in bias_audit.values())

    report = {
        "strict_zero_overlap_checks": strict_results,
        "monitored_overlap_checks": monitored_results,
        "internal_train_val_grouped_check": val_check,
        "sampling_bias_bare_root_audit": bias_audit,
        "summary": {
            "all_strict_overlaps_zero": all_strict_clean,
            "no_bare_root_bias_warnings": no_bias_warnings,
            "gate_passed": all_strict_clean and no_bias_warnings,
        },
    }

    os.makedirs("research/results", exist_ok=True)
    out_path = "research/results/split_integrity_audit.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 72)
    print("  PHISHDETECT ZERO-LEAKAGE & SAMPLING BIAS VERIFICATION REPORT")
    print("=" * 72)
    print("\n[1] Strict Zero-Overlap Domain Checks:")
    for r in strict_results:
        status = "PASS (0)" if r.get("is_clean") else f"FAIL ({r.get('overlap_domains')} domains / {r.get('affected_right_pct')}% rows)"
        print(f"  - {r['pair']:<38} -> {status}")

    print("\n[2] Monitored Cross-Corpus / Shared-Host Checks (Informational):")
    for r in monitored_results:
        print(f"  - {r['pair']:<38} -> {r.get('overlap_domains')} domains ({r.get('affected_right_pct')}% rows)")

    print(f"\n[3] Grouped Train/Val Check: overlap={val_check.get('overlap_domains')} ({'PASS' if val_check.get('is_clean') else 'FAIL'})")

    print("\n[4] Bare-Root Sampling Bias Audit (Arp et al. Pitfalls P1 & P4):")
    for k, v in bias_audit.items():
        flag = "WARN (Bias > 0.25)" if v["bias_warning"] else "OK"
        print(
            f"  - {k:<20} benign_bare={v['benign_bare_rate']:.2%}, "
            f"phish_bare={v['phishing_bare_rate']:.2%}, gap={v['bare_rate_gap']:.2%} [{flag}]"
        )

    print(f"\nSaved audit JSON -> {out_path}")
    passed = report["summary"]["gate_passed"] if strict else True
    return report, passed


def main():
    parser = argparse.ArgumentParser(description="Verify dataset zero-leakage and sampling balance.")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if any gate fails.")
    args = parser.parse_args()

    report, passed = run_verification(strict=args.strict)
    if args.strict and not passed:
        print("\n[GATE FAILED] Strict split integrity gate did not pass.")
        sys.exit(1)


if __name__ == "__main__":
    main()
