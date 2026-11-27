"""Phase 1 Dataset Repair & TESSERACT Benchmark Builder (PhishDetect v3.0).

Fixes all v2.x dataset defects enforced by `research/verify_splits.py`:
  1. Rebuilds `data/benchmark/a1_path_matched.csv` with strictly ZERO registered-domain
     overlap against `global_train`, `v3_train`, `v3_val`, and `indian_train`.
  2. Builds `data/processed/v3_train.csv`, `v3_val.csv`, and `v3_test.csv` eliminating
     bare-domain and 0%-query benign biases via deep-path/query/cloud enrichment.
  3. Builds TESSERACT chronological monthly benchmark (`a5_temporal_monthly.csv`,
     spanning 2025-01..2025-12 + 2026-11, disjoint from `a5_temporal_train.csv`).
  4. Builds imbalanced realistic operational benchmarks: `a5_base_rate_1pct.csv` (1%)
     and `a5_base_rate_5pct.csv` (5%).
"""

import hashlib
import json
import os
import sys
from urllib.parse import urlparse

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.domain import extract_registered_domain


ENRICH_DIR = "data/raw/v3_enrichment"
PARQUET_PATH = "audit/results/phreshphish_metadata_streamed.parquet"


def _parse_url_flags(u: str):
    try:
        s = str(u).strip()
        p = urlparse(s if "://" in s else f"https://{s}")
        has_pq = (len(p.path) > 1) or bool(p.query)
        p_depth = len([x for x in p.path.split("/") if x])
        is_https = s.lower().startswith("https://")
        has_q = bool(p.query)
        is_bare = (p.path in ("", "/")) and not p.query
        return has_pq, p_depth, is_https, len(s), has_q, is_bare
    except Exception:
        return False, 0, False, len(str(u)), False, False


def _domain_grouped_split(df: pd.DataFrame, ratios=(0.70, 0.15, 0.15), seed: int = 42):
    """Split DataFrame by registered_domain with zero overlap, stratifying query domains and bare domains evenly."""
    rng = np.random.RandomState(seed)
    dom_stats = df.groupby("registered_domain").agg(
        count=("url", "count"),
        has_q=("url", lambda s: s.astype(str).str.contains(r"\?", regex=True).any()),
        is_tranco=("source", lambda s: (s == "tranco_bare").all()),
    )
    large_q_doms = rng.permutation(dom_stats[(dom_stats["has_q"]) & (dom_stats["count"] >= 5)].index.values)
    tranco_doms = rng.permutation(dom_stats[dom_stats["is_tranco"]].index.values)
    mask_other = ~((dom_stats["has_q"]) & (dom_stats["count"] >= 5)) & (~dom_stats["is_tranco"])
    other_doms = rng.permutation(dom_stats[mask_other].index.values)

    def _split_arr(arr):
        n = len(arr)
        n_tr = int(n * ratios[0])
        n_vl = int(n * ratios[1])
        return set(arr[:n_tr]), set(arr[n_tr : n_tr + n_vl]), set(arr[n_tr + n_vl :])

    # Ensure query domains distribute >=1 into val and test when count >= 3
    if len(large_q_doms) >= 3:
        n_vl_q = max(2, int(len(large_q_doms) * ratios[1]))
        n_te_q = max(2, int(len(large_q_doms) * ratios[2]))
        vl1 = set(large_q_doms[:n_vl_q])
        te1 = set(large_q_doms[n_vl_q : n_vl_q + n_te_q])
        tr1 = set(large_q_doms[n_vl_q + n_te_q :])
    else:
        tr1, vl1, te1 = _split_arr(large_q_doms)

    tr_t, vl_t, te_t = _split_arr(tranco_doms)
    tr2, vl2, te2 = _split_arr(other_doms)

    tr_set = tr1 | tr_t | tr2
    vl_set = vl1 | vl_t | vl2
    te_set = te1 | te_t | te2

    df_tr = df[df["registered_domain"].isin(tr_set)].copy().reset_index(drop=True)
    df_vl = df[df["registered_domain"].isin(vl_set)].copy().reset_index(drop=True)
    df_te = df[df["registered_domain"].isin(te_set)].copy().reset_index(drop=True)
    return df_tr, df_vl, df_te


def build_v3_core_splits():
    """Construct clean, deep-path & query-balanced v3_train / v3_val / v3_test splits."""
    print("\n[1/4] Building bias-corrected v3_train / v3_val / v3_test...", flush=True)
    df_pp = pd.read_parquet(PARQUET_PATH)
    df_pp["label"] = df_pp["label"].apply(lambda x: 1 if str(x).lower().startswith("phish") or x == 1 else 0)
    df_pp["registered_domain"] = df_pp["url"].astype(str).apply(extract_registered_domain)
    df_pp = df_pp[df_pp["registered_domain"] != ""].copy()

    # Keep clean sample from PhreshPhish (balanced across 2024-2025, avoiding duplicate URLs)
    df_pp = df_pp.drop_duplicates(subset=["url"]).copy()
    pp_b_all = df_pp[df_pp["label"] == 0]
    # Include all 68 rare benign ?query URLs from PhreshPhish + 16k deep/general benign
    pp_b_q = pp_b_all[pp_b_all["url"].astype(str).str.contains(r"\?", regex=True)]
    pp_b_rest = pp_b_all[~pp_b_all.index.isin(pp_b_q.index)].sample(n=min(15000, len(pp_b_all) - len(pp_b_q)), random_state=42)
    pp_benign = pd.concat([pp_b_q, pp_b_rest], ignore_index=True)
    pp_phish = df_pp[df_pp["label"] == 1].sample(n=min(22000, (df_pp["label"] == 1).sum()), random_state=42)

    pp_benign_df = pp_benign[["url", "label", "date", "registered_domain"]].copy()
    pp_benign_df["source"] = "phreshphish_benign"
    pp_phish_df = pp_phish[["url", "label", "date", "registered_domain"]].copy()
    pp_phish_df["source"] = "phreshphish_phish"

    # Load Phase 1 enrichments (benign deep/query/cloud + 2026 phishing)
    b_path = os.path.join(ENRICH_DIR, "benign_deep_and_cloud.csv")
    p_path = os.path.join(ENRICH_DIR, "phishing_2026_feeds.csv")
    parts = [pp_benign_df, pp_phish_df]

    # Balance benign bare-root rate (~38%) with Tranco bare domains (disjoint from PhreshPhish)
    tranco_path = "data/raw/tranco_global_legit.csv"
    if os.path.exists(tranco_path):
        df_tranco = pd.read_csv(tranco_path)
        df_tranco["label"] = 0
        df_tranco["registered_domain"] = df_tranco["url"].astype(str).apply(extract_registered_domain)
        pp_doms = set(df_pp["registered_domain"])
        df_tranco = df_tranco[~df_tranco["registered_domain"].isin(pp_doms)].sample(n=9000, random_state=42)
        df_tranco["source"] = "tranco_bare"
        parts.append(df_tranco[["url", "label", "date", "registered_domain", "source"]])
        print(f"  + Added {len(df_tranco)} domain-disjoint Tranco bare homepages for bare-rate parity", flush=True)

    if os.path.exists(b_path):
        df_b_enr = pd.read_csv(b_path)
        df_b_enr["label"] = 0
        df_b_enr["registered_domain"] = df_b_enr["url"].astype(str).apply(extract_registered_domain)
        # Cap any single domain at 250 URLs so giant domains (wikipedia/github) don't skew one split
        df_b_enr = (
            df_b_enr.sample(frac=1.0, random_state=42)
            .groupby("registered_domain", group_keys=False)
            .head(250)
            .reset_index(drop=True)
        )
        parts.append(df_b_enr[["url", "label", "date", "registered_domain", "source"]])
        print(f"  + Added {len(df_b_enr)} benign deep-path/query/cloud enrichment URLs (capped <=250/domain)", flush=True)

    if os.path.exists(p_path):
        df_p_enr = pd.read_csv(p_path)
        if len(df_p_enr) > 0:
            df_p_enr["label"] = 1
            df_p_enr["registered_domain"] = df_p_enr["url"].astype(str).apply(extract_registered_domain)
            parts.append(df_p_enr[["url", "label", "date", "registered_domain", "source"]])
            print(f"  + Added {len(df_p_enr)} fresh 2026 phishing URLs", flush=True)

    # Also add clean PhreshPhish benign & phish from global_test so v3_test respects existing splits?
    # Better: ensure zero domain overlap with existing `global_train` test-reserved domains too!
    df_all = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)
    df_all = df_all[df_all["registered_domain"] != ""].copy()

    # Keep global_test domains strictly out of v3_train and v3_val so backward checks remain clean
    reserved_test_doms = set()
    if os.path.exists("data/processed/global_test.csv"):
        reserved_test_doms = set(pd.read_csv("data/processed/global_test.csv")["registered_domain"].dropna())

    df_pool_trainval = df_all[~df_all["registered_domain"].isin(reserved_test_doms)].copy()
    df_tr, df_vl, df_te_new = _domain_grouped_split(df_pool_trainval, ratios=(0.72, 0.14, 0.14), seed=42)

    # Combine held-out df_te_new with reserved global_test domains (zero overlap with df_tr or df_vl)
    df_te_reserved = df_all[df_all["registered_domain"].isin(reserved_test_doms)].copy()
    df_te = pd.concat([df_te_new, df_te_reserved], ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)

    # Double-check zero domain leakage invariant
    tr_d = set(df_tr["registered_domain"])
    vl_d = set(df_vl["registered_domain"])
    te_d = set(df_te["registered_domain"])
    assert len(tr_d & vl_d) == 0, "Leakage: v3_train & v3_val share domains!"
    assert len(tr_d & te_d) == 0, "Leakage: v3_train & v3_test share domains!"
    assert len(vl_d & te_d) == 0, "Leakage: v3_val & v3_test share domains!"

    os.makedirs("data/processed", exist_ok=True)
    df_tr.to_csv("data/processed/v3_train.csv", index=False)
    df_vl.to_csv("data/processed/v3_val.csv", index=False)
    df_te.to_csv("data/processed/v3_test.csv", index=False)

    for name, d in [("v3_train", df_tr), ("v3_val", df_vl), ("v3_test", df_te)]:
        flags = [_parse_url_flags(u) for u in d["url"]]
        d_q = pd.Series([x[4] for x in flags])
        b_q = d_q[d["label"] == 0].mean()
        p_q = d_q[d["label"] == 1].mean()
        print(
            f"  {name}: {len(d)} URLs ({d['registered_domain'].nunique()} domains) | "
            f"label_dist={d['label'].value_counts().to_dict()} | "
            f"benign_query={b_q:.2%}, phish_query={p_q:.2%}",
            flush=True,
        )
    return df_tr, df_vl, df_te


def rebuild_leak_free_a1(v3_train_doms: set, v3_val_doms: set):
    """Rebuild A1 Path-Matched Benchmark strictly disjoint from ALL training/val domains."""
    print("\n[2/4] Rebuilding leak-free A1 Path-Matched Benchmark...", flush=True)
    df = pd.read_parquet(PARQUET_PATH)
    df["label_num"] = df["label"].apply(lambda x: 1 if str(x).lower().startswith("phish") or x == 1 else 0)
    df["registered_domain"] = df["url"].astype(str).apply(extract_registered_domain)

    # Exclude ALL training/validation domains (both legacy global_train and new v3_train/v3_val)
    excluded_doms = set(v3_train_doms) | set(v3_val_doms)
    for train_file in ["data/processed/global_train.csv", "data/processed/indian_train.csv"]:
        if os.path.exists(train_file):
            tdf = pd.read_csv(train_file)
            if "registered_domain" in tdf.columns:
                excluded_doms |= set(tdf["registered_domain"].dropna().astype(str))

    df_heldout = df[(df["registered_domain"] != "") & (~df["registered_domain"].isin(excluded_doms))].copy()
    print(f"  Held-out PhreshPhish candidates (0 training overlap): {len(df_heldout)}", flush=True)

    flags = [_parse_url_flags(u) for u in df_heldout["url"]]
    df_heldout["has_path_query"] = [x[0] for x in flags]
    df_heldout["path_depth"] = [x[1] for x in flags]
    df_heldout["is_https"] = [x[2] for x in flags]
    df_heldout["url_len"] = [x[3] for x in flags]

    df_heldout["len_bin"] = pd.qcut(df_heldout["url_len"], q=5, labels=False, duplicates="drop")
    df_heldout["stratum"] = (
        df_heldout["has_path_query"].astype(str)
        + "_"
        + df_heldout["len_bin"].astype(str)
        + "_"
        + df_heldout["is_https"].astype(str)
    )

    matched = []
    for _, grp in df_heldout.groupby("stratum"):
        g0 = grp[grp["label_num"] == 0]
        g1 = grp[grp["label_num"] == 1]
        nm = min(len(g0), len(g1))
        if nm > 0:
            matched.extend([g0.sample(n=nm, random_state=42), g1.sample(n=nm, random_state=42)])

    df_matched = pd.concat(matched, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    # Cap cleanly around 20,000 rows while preserving strata balance
    if len(df_matched) > 20000:
        b = df_matched[df_matched["label_num"] == 0].sample(n=10000, random_state=42)
        p = df_matched[df_matched["label_num"] == 1].sample(n=10000, random_state=42)
        df_matched = pd.concat([b, p], ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)

    out_path = "data/benchmark/a1_path_matched.csv"
    df_matched[["url", "label_num", "date", "registered_domain", "has_path_query", "path_depth", "is_https", "stratum"]].to_csv(
        out_path, index=False
    )
    print(f"  Saved Zero-Overlap A1 -> {out_path} ({len(df_matched)} rows, {df_matched['registered_domain'].nunique()} domains)", flush=True)


def build_tesseract_monthly_and_imbalanced(df_v3_test: pd.DataFrame):
    """Build TESSERACT monthly drift slices (2025..2026) and realistic 1% & 5% base-rate test splits."""
    print("\n[3/4] Building TESSERACT Monthly AUT & Base-Rate Splits...", flush=True)
    df = pd.read_parquet(PARQUET_PATH)
    df["label_num"] = df["label"].apply(lambda x: 1 if str(x).lower().startswith("phish") or x == 1 else 0)
    df["registered_domain"] = df["url"].astype(str).apply(extract_registered_domain)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).copy()

    # Exclude all domains in `a5_temporal_train.csv`
    a5_tr_doms = set()
    if os.path.exists("data/benchmark/a5_temporal_train.csv"):
        a5_tr_doms = set(pd.read_csv("data/benchmark/a5_temporal_train.csv")["registered_domain"].dropna())

    df_future = df[(df["date_dt"] >= pd.Timestamp("2025-01-01")) & (~df["registered_domain"].isin(a5_tr_doms))].copy()
    df_future["year_month"] = df_future["date_dt"].dt.strftime("%Y-%m")

    # Add 2026 enrichment slices (disjoint from a5_temporal_train)
    parts = [df_future[["url", "label_num", "date", "year_month", "registered_domain"]]]
    for enr_name, lbl in [("benign_deep_and_cloud.csv", 0), ("phishing_2026_feeds.csv", 1)]:
        p = os.path.join(ENRICH_DIR, enr_name)
        if os.path.exists(p):
            edf = pd.read_csv(p)
            if len(edf) > 0:
                edf["label_num"] = lbl
                edf["registered_domain"] = edf["url"].astype(str).apply(extract_registered_domain)
                edf = edf[~edf["registered_domain"].isin(a5_tr_doms)].copy()
                edf["year_month"] = "2026-11"
                parts.append(edf[["url", "label_num", "date", "year_month", "registered_domain"]])

    df_monthly = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)
    # Sample up to 2,500 rows per month to keep TESSERACT AUT fast and consistent
    sampled_months = []
    for ym, grp in sorted(df_monthly.groupby("year_month")):
        if len(grp) >= 200:
            sampled_months.append(grp.sample(n=min(2500, len(grp)), random_state=42))
    df_aut = pd.concat(sampled_months, ignore_index=True)
    df_aut.to_csv("data/benchmark/a5_temporal_monthly.csv", index=False)
    print(f"  Saved TESSERACT Monthly AUT ({len(df_aut)} rows across {df_aut['year_month'].nunique()} months)", flush=True)

    # Realistic imbalanced base-rate benchmarks (1% and 5% phishing prevalence) strictly from v3_test
    te_b = df_v3_test[df_v3_test["label"] == 0].copy()
    te_p = df_v3_test[df_v3_test["label"] == 1].copy()
    te_b["label_num"] = 0
    te_p["label_num"] = 1

    # 1% base rate: e.g. 80 phish + 7920 benign (or scaled to available benign)
    n_b_1 = min(len(te_b), 8000)
    n_p_1 = max(1, int(round(n_b_1 * (0.01 / 0.99))))
    if n_p_1 <= len(te_p):
        df_1pct = pd.concat(
            [te_b.sample(n=n_b_1, random_state=42), te_p.sample(n=n_p_1, random_state=42)],
            ignore_index=True,
        ).sample(frac=1.0, random_state=42)
        df_1pct[["url", "label_num", "date", "registered_domain"]].to_csv("data/benchmark/a5_base_rate_1pct.csv", index=False)
        print(f"  Saved Base-Rate 1% Benchmark: {len(df_1pct)} rows ({n_p_1} phish / {n_b_1} benign)", flush=True)

    # 5% base rate: e.g. 421 phish + 8000 benign
    n_b_5 = min(len(te_b), 8000)
    n_p_5 = max(1, int(round(n_b_5 * (0.05 / 0.95))))
    if n_p_5 <= len(te_p):
        df_5pct = pd.concat(
            [te_b.sample(n=n_b_5, random_state=43), te_p.sample(n=n_p_5, random_state=43)],
            ignore_index=True,
        ).sample(frac=1.0, random_state=43)
        df_5pct[["url", "label_num", "date", "registered_domain"]].to_csv("data/benchmark/a5_base_rate_5pct.csv", index=False)
        print(f"  Saved Base-Rate 5% Benchmark: {len(df_5pct)} rows ({n_p_5} phish / {n_b_5} benign)", flush=True)


def update_manifest():
    print("\n[4/4] Updating research/split_manifest.json...", flush=True)
    manifest = {}
    for bdir in ["data/benchmark", "data/processed"]:
        if not os.path.exists(bdir):
            continue
        for fname in sorted(os.listdir(bdir)):
            if not fname.endswith((".csv", ".parquet")):
                continue
            fpath = os.path.join(bdir, fname)
            df = pd.read_parquet(fpath) if fname.endswith(".parquet") else pd.read_csv(fpath)
            h = hashlib.sha256()
            with open(fpath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            lbl_col = "label_num" if "label_num" in df.columns else ("label" if "label" in df.columns else None)
            manifest[fname] = {
                "path": fpath.replace("\\", "/"),
                "sha256": h.hexdigest(),
                "rows": len(df),
                "columns": list(df.columns),
                "label_distribution": df[lbl_col].value_counts().to_dict() if lbl_col else "N/A",
            }
    with open("research/split_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("Updated research/split_manifest.json successfully.", flush=True)


if __name__ == "__main__":
    df_tr, df_vl, df_te = build_v3_core_splits()
    rebuild_leak_free_a1(set(df_tr["registered_domain"]), set(df_vl["registered_domain"]))
    build_tesseract_monthly_and_imbalanced(df_te)
    update_manifest()
    print("\nPhase 1 dataset rebuild complete!")
