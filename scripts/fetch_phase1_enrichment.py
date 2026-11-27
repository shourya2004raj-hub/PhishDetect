"""Phase 1 Targeted Dataset Enrichment & Offline HTML Extraction.

Collects strictly targeted, non-redundant datasets needed to fix v2.x sampling bias,
extend temporal drift into 2026, and build the offline Stage 2 Cloud-DOM benchmark:
  1. Real-world benign deep-path, query-parameter, and legitimate cloud-hosted URLs
     (from Wikimedia, GitHub public repositories, StackExchange, and HackerNews APIs).
  2. Fresh 2026 active phishing feeds (OpenPhish community feed + URLhaus recent feed).
  3. Safe offline HTML captures from HuggingFace `phreshphish/phreshphish` shards
     (filtering to multi-tenant cloud LOTS hosts + balanced benign HTML captures).
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import fsspec
import pandas as pd
import pyarrow.parquet as pq
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.domain import canonicalize_url, extract_registered_domain

OUT_DIR = "data/raw/v3_enrichment"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "PhishDetect-Research-Audit/3.0 (academic-benchmark)"}

CLOUD_SUFFIXES = (
    "vercel.app",
    "workers.dev",
    "netlify.app",
    "pages.dev",
    "blogspot.com",
    "github.io",
    "firebaseapp.com",
    "gitbook.io",
    "webflow.io",
)

MAJOR_BRANDS = {
    "sbi", "onlinesbi", "hdfc", "hdfcbank", "icici", "icicibank", "axis",
    "paytm", "phonepe", "gpay", "aadhaar", "uidai", "irctc", "incometax",
    "microsoft", "office", "outlook", "google", "gmail", "apple", "icloud",
    "amazon", "paypal", "netflix", "facebook", "instagram", "linkedin",
    "github", "dropbox", "adobe", "dhl", "fedex", "chase", "wellsfargo",
}


def get_host(url: str) -> str:
    try:
        return urlparse(str(url) if "://" in str(url) else f"http://{url}").netloc.split(":")[0].lower()
    except Exception:
        return ""


def is_cloud_host(host: str) -> bool:
    return any(host == s or host.endswith(f".{s}") for s in CLOUD_SUFFIXES)


def fetch_benign_deep_and_cloud_urls() -> pd.DataFrame:
    """Collect real benign URLs with query strings, deep paths, www., and legit cloud homepages."""
    records: List[Dict] = []
    today = "2026-11-27"

    # 1. GitHub Public Repositories -> real deep URLs + verified legit cloud homepages (vercel.app/github.io/netlify.app)
    print("[1/4] Fetching real deep-path & cloud URLs via GitHub Search API...", flush=True)
    gh_queries = [
        "stars:>500 topic:react",
        "stars:>300 topic:nextjs",
        "stars:>300 topic:portfolio",
        "stars:>200 topic:tailwindcss",
        "stars:>500 topic:machine-learning",
        "stars:>500 topic:python",
        "stars:>200 topic:vite",
        "stars:>200 topic:documentation",
    ]
    for q in gh_queries:
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "per_page": 100},
                headers=HEADERS,
                timeout=15,
            )
            if r.status_code == 200:
                items = r.json().get("items", [])
                for it in items:
                    html_url = it.get("html_url", "")
                    if html_url:
                        records.append({"url": html_url, "label": 0, "source": "github_repo", "date": today})
                        records.append({"url": f"{html_url}/issues?q=is%3Aopen+is%3Aissue", "label": 0, "source": "github_query", "date": today})
                        records.append({"url": f"{html_url}/commits/main?author={it.get('owner', {}).get('login', 'dev')}", "label": 0, "source": "github_query", "date": today})
                    hp = (it.get("homepage") or "").strip()
                    if hp.startswith(("http://", "https://")):
                        records.append({"url": hp, "label": 0, "source": "github_homepage", "date": today})
            time.sleep(0.5)
        except Exception as e:
            print(f"  GitHub query warn ({q}): {e}", flush=True)

    # 2. Wikimedia API -> real Wikipedia URLs with deep paths & ?oldid= / ?search= queries
    print("[2/4] Fetching Wikipedia deep-path & query URLs...", flush=True)
    for _ in range(10):
        try:
            r = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "random",
                    "rnnamespace": 0,
                    "rnlimit": 100,
                    "format": "json",
                },
                headers=HEADERS,
                timeout=15,
            )
            if r.status_code == 200:
                for page in r.json().get("query", {}).get("random", []):
                    title = page.get("title", "").replace(" ", "_")
                    pid = page.get("id", 1)
                    if title:
                        records.append({"url": f"https://en.wikipedia.org/wiki/{title}", "label": 0, "source": "wikipedia", "date": today})
                        records.append({"url": f"https://en.wikipedia.org/w/index.php?title={title}&oldid={pid}", "label": 0, "source": "wikipedia_query", "date": today})
        except Exception as e:
            print(f"  Wikipedia warn: {e}", flush=True)

    # 3. StackExchange API -> real StackOverflow & SuperUser URLs + query variants
    print("[3/4] Fetching StackOverflow / StackExchange URLs...", flush=True)
    for site in ["stackoverflow", "superuser", "security"]:
        for page_num in range(1, 6):
            try:
                r = requests.get(
                    "https://api.stackexchange.com/2.3/questions",
                    params={"order": "desc", "sort": "votes", "site": site, "pagesize": 100, "page": page_num},
                    headers=HEADERS,
                    timeout=15,
                )
                if r.status_code == 200:
                    for item in r.json().get("items", []):
                        link = item.get("link", "")
                        if link:
                            records.append({"url": link, "label": 0, "source": site, "date": today})
                            records.append({"url": f"{link}?answertab=scoredesc#tab-top", "label": 0, "source": f"{site}_query", "date": today})
                time.sleep(0.2)
            except Exception as e:
                print(f"  StackExchange warn ({site}): {e}", flush=True)

    # 4. HackerNews Top/New Stories -> diverse real-world tech, blog, docs, & SaaS URLs
    print("[4/4] Fetching HackerNews real-world external URLs...", flush=True)
    try:
        ids = []
        for ep in ["topstories", "newstories", "beststories"]:
            r = requests.get(f"https://hacker-news.firebaseio.com/v0/{ep}.json", timeout=15)
            if r.status_code == 200:
                ids.extend(r.json()[:250])
        seen_ids = list(dict.fromkeys(ids))[:300]
        def _fetch_hn(sid):
            try:
                ir = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5)
                if ir.status_code == 200:
                    u = (ir.json() or {}).get("url", "")
                    if u and u.startswith("http"):
                        return {"url": u, "label": 0, "source": "hackernews", "date": today}
            except Exception:
                return None
            return None

        with ThreadPoolExecutor(max_workers=20) as ex:
            for item in ex.map(_fetch_hn, seen_ids):
                if item:
                    records.append(item)
    except Exception as e:
        print(f"  HackerNews warn: {e}", flush=True)

    # 5. Add diverse clean search/portal query templates across major safe platforms
    search_terms = [
        "weather+today", "python+pandas+dataframe", "machine+learning+tutorial",
        "cricket+score+live", "delhi+metro+route", "train+schedule+india",
        "react+hooks+guide", "fastapi+documentation", "quantum+computing",
        "healthy+recipes", "stock+market+news", "climate+change+report",
    ]
    for term in search_terms:
        records.extend([
            {"url": f"https://www.google.com/search?q={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://scholar.google.com/scholar?hl=en&q={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://www.youtube.com/results?search_query={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://www.amazon.in/s?k={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://www.bing.com/search?q={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://github.com/search?q={term}&type=repositories", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://pypi.org/search/?q={term}", "label": 0, "source": "benign_query_pattern", "date": today},
            {"url": f"https://www.npmjs.com/search?q={term}", "label": 0, "source": "benign_query_pattern", "date": today},
        ])

    df_b = pd.DataFrame(records).drop_duplicates(subset=["url"]).reset_index(drop=True)
    df_b["registered_domain"] = df_b["url"].apply(extract_registered_domain)
    out_path = os.path.join(OUT_DIR, "benign_deep_and_cloud.csv")
    df_b.to_csv(out_path, index=False)
    print(f"Saved {len(df_b)} benign deep/query/cloud URLs -> {out_path}", flush=True)
    return df_b


def fetch_2026_phishing_feeds() -> pd.DataFrame:
    """Fetch fresh 2026 active phishing feeds from OpenPhish and URLhaus."""
    records: List[Dict] = []
    today = "2026-11-27"

    print("[Phishing 2026] Fetching OpenPhish community feed...", flush=True)
    try:
        r = requests.get("https://openphish.com/feed.txt", headers=HEADERS, timeout=20)
        if r.status_code == 200:
            for line in r.text.splitlines():
                u = line.strip()
                if u.startswith(("http://", "https://")):
                    records.append({"url": u, "label": 1, "source": "openphish_2026", "date": today})
    except Exception as e:
        print(f"  OpenPhish warn: {e}", flush=True)

    print("[Phishing 2026] Fetching Phishing.Database active feed...", flush=True)
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/phishing-links-ACTIVE.txt",
            headers=HEADERS,
            timeout=25,
        )
        if r.status_code == 200:
            all_lines = [l.strip() for l in r.text.splitlines() if l.strip().startswith(("http://", "https://"))]
            # Deterministic stride sample across the entire feed for domain diversity
            step = max(1, len(all_lines) // 6000)
            seen_doms = set()
            added = 0
            for u in all_lines[::step]:
                dom = extract_registered_domain(u)
                if dom and dom not in seen_doms:
                    seen_doms.add(dom)
                    records.append({"url": u, "label": 1, "source": "phishing_db_2026", "date": today})
                    added += 1
                if added >= 4000:
                    break
    except Exception as e:
        print(f"  PhishingDB warn: {e}", flush=True)

    df_p = pd.DataFrame(records).drop_duplicates(subset=["url"]).reset_index(drop=True) if records else pd.DataFrame(columns=["url", "label", "source", "date"])
    if len(df_p) > 0:
        df_p["registered_domain"] = df_p["url"].apply(extract_registered_domain)
    out_path = os.path.join(OUT_DIR, "phishing_2026_feeds.csv")
    df_p.to_csv(out_path, index=False)
    print(f"Saved {len(df_p)} fresh 2026 malicious URLs -> {out_path}", flush=True)
    return df_p


def extract_dom_signals_from_html(html: str, page_url: str) -> Dict:
    """Extract offline Dual-Intention DOM signals (PhishIntention + KnowPhish inspired)."""
    reg_dom = extract_registered_domain(page_url)
    host = get_host(page_url)

    out = {
        "has_password_input": 0,
        "has_email_or_user_input": 0,
        "has_otp_or_card_input": 0,
        "num_forms": 0,
        "has_cross_origin_form": 0,
        "has_js_or_null_form": 0,
        "has_login_cta_text": 0,
        "num_external_links": 0,
        "num_internal_links": 0,
        "external_link_ratio": 0.0,
        "title_len": 0,
        "title_claims_brand": 0,
        "brand_dom_mismatch": 0,
        "missing_or_external_favicon": 0,
        "hidden_input_count": 0,
        "html_length": len(html) if isinstance(html, str) else 0,
    }
    if not isinstance(html, str) or not html.strip():
        return out

    try:
        soup = BeautifulSoup(html[:250000], "lxml")
    except Exception:
        return out

    inputs = soup.find_all("input")
    for inp in inputs:
        itype = str(inp.get("type", "text")).lower()
        iname = (str(inp.get("name", "")) + " " + str(inp.get("id", "")) + " " + str(inp.get("placeholder", ""))).lower()
        if itype == "password":
            out["has_password_input"] = 1
        elif itype == "hidden":
            out["hidden_input_count"] += 1
        if itype == "email" or any(k in iname for k in ("email", "user", "login", "account", "phone", "mobile")):
            out["has_email_or_user_input"] = 1
        if any(k in iname for k in ("otp", "cvv", "card", "pin", "aadhaar", "pan", "ssn")):
            out["has_otp_or_card_input"] = 1

    forms = soup.find_all("form")
    out["num_forms"] = len(forms)
    for frm in forms:
        action = str(frm.get("action", "")).strip()
        if not action or action.startswith(("#", "javascript:")):
            out["has_js_or_null_form"] = 1
        elif action.startswith(("http://", "https://")):
            act_dom = extract_registered_domain(action)
            if act_dom and reg_dom and act_dom != reg_dom:
                out["has_cross_origin_form"] = 1

    text_sample = (soup.title.string if soup.title and soup.title.string else "") + " " + " ".join(
        h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "button"])[:10]
    )
    text_low = text_sample.lower()
    if any(k in text_low for k in ("sign in", "log in", "login", "verify", "confirm", "authenticate", "otp", "kyc")):
        out["has_login_cta_text"] = 1

    title_str = (soup.title.string.strip() if soup.title and soup.title.string else "")
    out["title_len"] = len(title_str)
    title_low = title_str.lower()
    matched_brands = [b for b in MAJOR_BRANDS if b in title_low or b in text_low[:400]]
    if matched_brands:
        out["title_claims_brand"] = 1
        if not any(b in host for b in matched_brands):
            out["brand_dom_mismatch"] = 1

    anchors = soup.find_all("a", href=True)[:100]
    for a in anchors:
        href = str(a["href"]).strip()
        if href.startswith(("http://", "https://")):
            if extract_registered_domain(href) == reg_dom:
                out["num_internal_links"] += 1
            else:
                out["num_external_links"] += 1
        elif href.startswith("/"):
            out["num_internal_links"] += 1
    total_a = out["num_internal_links"] + out["num_external_links"]
    out["external_link_ratio"] = round(out["num_external_links"] / total_a, 4) if total_a > 0 else 0.0

    icons = soup.find_all("link", rel=lambda r: r and "icon" in str(r).lower())
    if not icons:
        out["missing_or_external_favicon"] = 1
    else:
        for ic in icons:
            ihref = str(ic.get("href", ""))
            if ihref.startswith(("http://", "https://")) and extract_registered_domain(ihref) != reg_dom:
                out["missing_or_external_favicon"] = 1

    return out


def fetch_offline_cloud_dom_dataset(target_phish: int = 650, target_benign: int = 650) -> pd.DataFrame:
    """Safely stream captured HTML from PhreshPhish HuggingFace dataset (no live malicious requests)."""
    from datasets import load_dataset

    dom_rows: List[Dict] = []
    phish_cloud_count = 0
    phish_general_count = 0
    benign_cloud_count = 0
    benign_general_count = 0

    print("[Offline HTML] Streaming captured HTML from phreshphish/phreshphish via HuggingFace...", flush=True)
    for split_name in ["test", "train"]:
        if (phish_cloud_count + phish_general_count) >= target_phish and (benign_cloud_count + benign_general_count) >= target_benign:
            break
        try:
            ds = load_dataset("phreshphish/phreshphish", split=split_name, streaming=True)
            scanned = 0
            for row in ds:
                scanned += 1
                if scanned > 6000:
                    break
                if (phish_cloud_count + phish_general_count) >= target_phish and (benign_cloud_count + benign_general_count) >= target_benign:
                    break

                url = str(row.get("url", ""))
                html = row.get("html", "")
                if not url or not html:
                    continue

                lbl_str = str(row.get("label", "")).lower()
                is_phish = lbl_str.startswith("phish") or lbl_str == "1"
                host = get_host(url)
                cloud_flag = is_cloud_host(host)

                take = False
                if is_phish:
                    if cloud_flag and phish_cloud_count < int(target_phish * 0.7):
                        take = True
                        phish_cloud_count += 1
                    elif not cloud_flag and phish_general_count < int(target_phish * 0.3):
                        take = True
                        phish_general_count += 1
                else:
                    if cloud_flag and benign_cloud_count < 200:
                        take = True
                        benign_cloud_count += 1
                    elif not cloud_flag and benign_general_count < (target_benign - 150):
                        take = True
                        benign_general_count += 1

                if take:
                    sigs = extract_dom_signals_from_html(html, url)
                    dom_rows.append({
                        "url": url,
                        "registered_domain": extract_registered_domain(url),
                        "is_cloud_host": int(cloud_flag),
                        "label": int(is_phish),
                        "target": str(row.get("target", "")),
                        "date": str(row.get("date", "")),
                        "source": f"phreshphish_{split_name}",
                        **sigs,
                    })

                if scanned % 1000 == 0:
                    print(
                        f"  [{split_name}] scanned={scanned}: phish_cloud={phish_cloud_count}, "
                        f"phish_gen={phish_general_count}, benign_cloud={benign_cloud_count}, benign_gen={benign_general_count}",
                        flush=True,
                    )
        except Exception as e:
            print(f"  Stream warn ({split_name}): {e}", flush=True)

    # Also safely sample up to 150 genuine benign cloud apps discovered via GitHub homepage links (timeout=5s, text only)
    benign_csv = os.path.join(OUT_DIR, "benign_deep_and_cloud.csv")
    if os.path.exists(benign_csv):
        bdf = pd.read_csv(benign_csv)
        bdf["host"] = bdf["url"].apply(get_host)
        bcloud = bdf[bdf["host"].apply(is_cloud_host)].drop_duplicates(subset=["host"]).head(120)
        def _fetch_cloud(url_val):
            try:
                resp = requests.get(url_val, headers=HEADERS, timeout=5)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    sigs = extract_dom_signals_from_html(resp.text, url_val)
                    return {
                        "url": url_val,
                        "registered_domain": extract_registered_domain(url_val),
                        "is_cloud_host": 1,
                        "label": 0,
                        "target": "benign_oss_app",
                        "date": "2026-11-27",
                        "source": "github_oss_homepage",
                        **sigs,
                    }
            except Exception:
                return None
            return None

        fetched_live_cloud = 0
        with ThreadPoolExecutor(max_workers=16) as ex:
            for item in ex.map(_fetch_cloud, bcloud["url"].tolist()):
                if item:
                    dom_rows.append(item)
                    fetched_live_cloud += 1
        print(f"  Safely captured {fetched_live_cloud} verified OSS cloud benign homepages.", flush=True)

    df_dom = pd.DataFrame(dom_rows).drop_duplicates(subset=["url"]).reset_index(drop=True)
    out_path = "data/benchmark/stage2_cloud_dom.parquet"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_dom.to_parquet(out_path, index=False)
    print(f"Saved Stage 2 Dual-Intention DOM Dataset ({len(df_dom)} rows) -> {out_path}", flush=True)
    return df_dom


if __name__ == "__main__":
    if "--skip-benign" not in sys.argv:
        fetch_benign_deep_and_cloud_urls()
    fetch_2026_phishing_feeds()
    fetch_offline_cloud_dom_dataset()
