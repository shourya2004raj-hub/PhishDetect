"""Phase 0 Guardrail & Parity Export Script.

1. Exports deterministic Public Suffix List rules from cached tldextract JSON
   to extension/engine/psl_rules.json for exact Python <-> Chrome JS parity.
2. Generates tests/golden_urls.json containing 100 diverse edge-case URLs and
   their reference canonicalization, registered_domain, TLD, and 47-feature outputs.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.extractor import extract_features_dict, get_feature_names
from src.utils.domain import (
    canonicalize_url,
    extract_registered_domain,
    extract_subdomain,
    extract_tld,
    validate_url_syntax,
)


PSL_CACHE_FILE = "data/raw/tld_cache/publicsuffix.org-tlds/de84b5ca2167d4c83e38fb162f2e8738.tldextract.json"

GOLDEN_URL_LIST = [
    # Standard & www variants (Exp A2 sensitivity targets)
    "https://google.com",
    "https://www.google.com",
    "https://www.google.com/",
    "http://google.com",
    "google.com",
    "https://www.google.com/search?q=weather+today",
    "https://github.com/shourya2004raj-hub/PhishDetect/commits?author=shourya2004raj-hub",
    "https://adobe.com",
    "https://www.adobe.com",
    "https://amazon.com/dp/B09V3KXJPB?ref=nav_ya_signin",
    "https://www.amazon.in/s?k=laptop&crid=12345",
    "https://en.wikipedia.org/wiki/Phishing",
    "https://stackoverflow.com/questions/12345/python-fastapi",
    "https://docs.python.org/3/library/urllib.parse.html",
    "https://mail.google.com/mail/u/0/#inbox",
    # Indian official banking & government portals (multi-part ccTLDs)
    "https://www.onlinesbi.sbi/",
    "https://retail.onlinesbi.sbi/retail/login.htm",
    "https://sbi.co.in",
    "https://www.hdfcbank.com/personal/pay/cards",
    "https://netbanking.hdfcbank.com/netbanking/",
    "https://www.icicibank.com/",
    "https://www.axisbank.com/",
    "https://paytm.com/recharge",
    "https://www.phonepe.com/",
    "https://uidai.gov.in/en/",
    "https://myaadhaar.uidai.gov.in/",
    "https://incometax.gov.in/iec/foportal/",
    "https://www.irctc.co.in/nget/train-search",
    "https://parivahan.gov.in/parivahan/",
    "https://epfindia.gov.in/site_en/index.php",
    # Phishing: Brand-TLD misalignment & Indian lures
    "http://sbi-login.top/verify.php",
    "https://sbi-kyc-update-login.top/account/verify.php",
    "https://www.sbi-netbanking-secure.xyz/login",
    "http://hdfc-kyc-update.site/pan/auth.html",
    "https://icici-reward-points-claim.cloud/verify?id=8812",
    "https://paytm-cashback-rewards-free.xyz/claim",
    "http://uidai-aadhaar-link-portal-12.net/biometric",
    "https://irctc-ticket-refund-portal.buzz/cancel/auth",
    "http://phonepe-kyc-blocked-account.info/unlock",
    "https://axisbank-pan-verify.click/login.jsp",
    # Multi-tenant cloud hosts (LOTS phishing vs legit cloud apps)
    "https://my-portfolio-app.vercel.app/",
    "https://phish-detect-delta.vercel.app/",
    "https://sbi-kyc-portal-991.vercel.app/login",
    "https://auth-microsoft-login-821.workers.dev/",
    "https://api-docs-preview.workers.dev/v1/health",
    "https://hdfc-verify-now.netlify.app/otp",
    "https://open-source-blog.netlify.app/posts/intro",
    "https://user-page.github.io/project-docs/",
    "https://login-office-365-secure.pages.dev/auth",
    "https://payment-receipt-view.firebaseapp.com/login.html",
    "https://sweetigeminidays.blogspot.com/?m=1",
    "https://geminiloginqm.gitbook.io/us",
    "https://docs.google.com/forms/d/e/1FAIpQLScExample/viewform",
    # Technical edge cases: IPs, ports, redirects, encoding, Punycode, homoglyphs
    "http://192.168.1.1/admin/login.php",
    "http://45.133.1.99:8080/secure/update",
    "https://example.com:443/path",
    "http://example.com:80/index.html",
    "https://[::1]:8443/dashboard",
    "http://203.0.113.45/bank/verify",
    "https://xn--sbi-9ta.com/login",
    "https://sb\u0456-online.com/auth",
    "https://paypal.com@evil-login.xyz/signin",
    "https://legit.com//https://evil-redirect.top/login",
    "https://example.com/a/b/c/d/e/f/g/verify.php?u=1&t=2&s=3",
    "http://secure%2Dlogin.example.com/%7Euser/verify%20account",
    # Subdomain stacking & typosquatting
    "https://login.verify.account.sbi.secure-portal.xyz/auth",
    "https://www.paypal.com.account-update-id992.top/webapps",
    "https://paytmm-rewards-india.com/claim",
    "https://hdfcbamk-netbanking.xyz/login",
    "https://onlinesbi-verify.com/otp",
    # Diverse legitimate deep-path & SaaS URLs (avoiding false positives)
    "https://www.bbc.com/news/technology-68412345",
    "https://www.nytimes.com/2026/11/25/technology/ai-security.html",
    "https://arxiv.org/abs/2507.10854",
    "https://huggingface.co/datasets/phreshphish/phreshphish",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://scholar.google.com/scholar?hl=en&q=phishing+detection",
    "https://portal.azure.com/#home",
    "https://console.cloud.google.com/bigquery?project=demo-123",
    "https://www.npmjs.com/package/lightgbm",
    "https://pypi.org/project/tldextract/",
    "https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webNavigation",
    "https://chrome.google.com/webstore/category/extensions",
    "https://www.linkedin.com/in/example-profile-123/",
    "https://www.reddit.com/r/netsec/comments/abc123/analysis/",
    "https://support.microsoft.com/en-us/windows",
    "https://support.apple.com/en-in/HT201232",
    "https://www.cloudflare.com/learning/security/threats/phishing-attack/",
    "https://www.usenix.org/conference/usenixsecurity22/presentation/arp",
    "https://www.sciencedirect.com/science/article/pii/S0167404823004558",
    "https://ieeexplore.ieee.org/document/9650412",
    # International multi-part TLDs & tricky hosts
    "https://www.bbc.co.uk/sport/cricket",
    "https://www.gov.uk/check-uk-visa",
    "https://www.abc.net.au/news",
    "https://portal.nic.in/",
    "https://www.iitb.ac.in/en/academics",
    "https://example.edu/admissions?year=2026",
    "https://sub.domain.co.jp/items/view?id=42",
    "https://UPPERCASE-HOST.COM/Path/With/Case?Key=Val",
    "  https://trimmed-url.org/test  ",
    "http://long-random-dga-token-9a8b7c6d5e4f3210.info/gate/init.php",
]


def export_psl_rules(out_path: str = "extension/engine/psl_rules.json") -> dict:
    if not os.path.exists(PSL_CACHE_FILE):
        raise FileNotFoundError(f"Cached PSL file not found: {PSL_CACHE_FILE}")

    with open(PSL_CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    icann_raw, private_raw = data[0], data[1]

    def split_rules(rules):
        exact = []
        wildcards = []
        exceptions = []
        for r in rules:
            r = r.strip().lower()
            if not r:
                continue
            if r.startswith("!"):
                exceptions.append(r[1:])
            elif r.startswith("*."):
                wildcards.append(r[2:])
            else:
                exact.append(r)
        return {"exact": exact, "wildcards": wildcards, "exceptions": exceptions}

    psl_payload = {
        "source": "publicsuffix.org (tldextract snapshot)",
        "icann": split_rules(icann_raw),
        "private": split_rules(private_raw),
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(psl_payload, f, separators=(",", ":"))
    return psl_payload


def export_golden_urls(out_path: str = "tests/golden_urls.json") -> dict:
    assert len(GOLDEN_URL_LIST) == 100, f"Expected 100 golden URLs, got {len(GOLDEN_URL_LIST)}"
    feature_names = get_feature_names(include_regional=True)

    records = []
    for raw_url in GOLDEN_URL_LIST:
        is_valid, err = validate_url_syntax(raw_url)
        canonical, scheme_assumed = canonicalize_url(raw_url)
        reg_domain = extract_registered_domain(canonical)
        tld = extract_tld(canonical)
        subdomain = extract_subdomain(canonical)
        feats = extract_features_dict(canonical, include_regional=True, include_path_query=True)

        records.append({
            "raw_url": raw_url,
            "is_valid": is_valid,
            "validation_error": err,
            "canonical_url": canonical,
            "scheme_assumed": scheme_assumed,
            "registered_domain": reg_domain,
            "tld": tld,
            "subdomain": subdomain,
            "features": {k: float(feats.get(k, 0.0)) for k in feature_names},
        })

    payload = {
        "version": "phase0_v1",
        "count": len(records),
        "feature_names": feature_names,
        "records": records,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


if __name__ == "__main__":
    psl = export_psl_rules()
    golden = export_golden_urls()
    print(
        f"Exported PSL rules (icann exact={len(psl['icann']['exact'])}, "
        f"private exact={len(psl['private']['exact'])}) -> extension/engine/psl_rules.json"
    )
    print(f"Exported {golden['count']} golden test URLs ({len(golden['feature_names'])} features) -> tests/golden_urls.json")
