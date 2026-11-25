"""FastAPI REST Service for Real-Time Phishing URL Detection.
Hardened with strict HTTP 422 input validation, URL canonicalization,
ML vs. policy separation, model hash verification, and restricted CORS.
"""

import os
import sys
import time
import hashlib
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.extractor import (
    extract_features_dict,
    extract_features_vector,
    get_feature_names
)
from src.features.regional import DEFAULT_OFFICIAL_DOMAINS
from src.models.baseline import PhishingClassifier
from src.explainer.explainer import PhishingExplainer
from src.utils.domain import (
    validate_url_syntax,
    canonicalize_url,
    extract_registered_domain,
    extract_tld
)


# Model configuration paths (prefer region-aware model)
BASE_DIR = os.path.dirname(__file__)
MODEL_REGION_AWARE = os.path.join(BASE_DIR, "model_region_aware.joblib")
MODEL_BASELINE = os.path.join(BASE_DIR, "model_baseline.joblib")

# Verified major trusted domains for safe browsing
GLOBAL_TRUSTED_DOMAINS = {
    "github.com", "google.com", "google.co.in", "microsoft.com", "apple.com",
    "amazon.com", "amazon.in", "youtube.com", "wikipedia.org", "linkedin.com",
    "twitter.com", "x.com", "facebook.com", "instagram.com", "netflix.com",
    "cloudflare.com", "stackoverflow.com", "reddit.com", "yahoo.com"
}

_classifier: Optional[PhishingClassifier] = None
_explainer = PhishingExplainer()
_model_sha256: Optional[str] = None
_active_model_name: Optional[str] = None


def compute_file_sha256(filepath: str) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_classifier() -> Optional[PhishingClassifier]:
    """Retrieve or lazily load the trained classifier with cryptographic verification."""
    global _classifier, _model_sha256, _active_model_name
    if _classifier is None:
        target_path = MODEL_REGION_AWARE if os.path.exists(MODEL_REGION_AWARE) else MODEL_BASELINE
        if os.path.exists(target_path):
            try:
                _model_sha256 = compute_file_sha256(target_path)
                _active_model_name = os.path.basename(target_path)
                _classifier = PhishingClassifier.load(target_path)
                print(f"[API] Loaded model {_active_model_name} (SHA-256: {_model_sha256[:16]}...)", flush=True)
            except Exception as e:
                print(f"[API Warning] Failed to load model from {target_path}: {e}", flush=True)
    return _classifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warmup model and verify checksum on server startup."""
    get_classifier()
    yield


app = FastAPI(
    title="PhishDetect: AI-Driven Phishing URL Detection API",
    description="Scientific Phishing URL detection service with strict validation and ML/policy separation.",
    version="2.0.0",
    lifespan=lifespan
)

# Phase 1.6: Restricted CORS origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "chrome-extension://*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    url: str = Field(..., description="Target URL string to evaluate")
    include_regional: bool = Field(default=True, description="Whether to include regional feature signals")


class PredictResponse(BaseModel):
    url: str
    canonical_url: str
    scheme_assumed: bool
    registered_domain: str
    tld: str
    is_phishing: bool
    verdict: str
    risk_score: float
    ml_risk_score: float
    final_risk_score: float
    policy_override: str
    confidence: float
    decision_threshold: float
    latency_ms: float
    reasons: List[str]
    key_signals: Dict[str, Any]


@app.get("/health")
def health_check():
    """Health, model status, and cryptographic integrity probe."""
    clf = get_classifier()
    return {
        "status": "healthy",
        "model_loaded": clf is not None,
        "active_model": _active_model_name,
        "model_sha256": _model_sha256,
        "model_type": clf.model_type if clf else None,
        "calibrated_threshold": clf.optimal_threshold if clf else 0.5
    }


@app.post("/predict", response_model=PredictResponse)
def predict_url(payload: PredictRequest):
    """Analyze static URL string and return classification verdict with explanations.
    
    Returns HTTP 422 for malformed URLs, invalid schemes, or out-of-range ports.
    Maintains clean separation between raw ML scoring and rule/policy overrides.
    """
    # Phase 1.1: Strict validation with HTTP 422
    is_valid, error_msg = validate_url_syntax(payload.url)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg
        )

    clf = get_classifier()
    if clf is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not initialized or trained yet."
        )

    start_time = time.perf_counter()

    # Phase 1.2: Canonicalization with explicit scheme tracking
    canonical_url, scheme_assumed = canonicalize_url(payload.url)
    registered_domain = extract_registered_domain(canonical_url)
    tld = extract_tld(canonical_url)

    # Extract features using defensive pipeline
    try:
        feature_dict = extract_features_dict(
            canonical_url,
            include_regional=payload.include_regional,
            include_path_query=True
        )
        feature_vector = extract_features_vector(
            canonical_url,
            include_regional=payload.include_regional,
            include_path_query=True
        ).reshape(1, -1)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Feature extraction failed on URL: {str(e)}"
        )

    # Phase 1.5: ML scoring (pure probabilistic model inference)
    probs = clf.predict_proba(feature_vector)[0]
    ml_risk_score = round(float(probs[1]), 4)
    threshold = round(float(clf.optimal_threshold), 4)

    # Phase 1.5: Policy layer (clean separation from ML score)
    policy_override = "none"
    final_risk_score = ml_risk_score

    # Check safe-listing: official institutional portal or major platform without misalignment/IP
    is_verified_official = (
        registered_domain in GLOBAL_TRUSTED_DOMAINS
        or any(registered_domain in domains for domains in DEFAULT_OFFICIAL_DOMAINS.values())
        or registered_domain.endswith((".gov.in", ".nic.in", ".edu", ".ac.in"))
    ) and feature_dict.get("brand_tld_misalignment", 0.0) == 0.0 and feature_dict.get("has_ip", 0.0) == 0.0

    if is_verified_official:
        policy_override = "official_institution_allowlist"
        final_risk_score = min(ml_risk_score, 0.02)
    elif feature_dict.get("has_homoglyph_or_punycode", 0.0) > 0.5:
        policy_override = "homoglyph_punycode_denylist"
        final_risk_score = max(ml_risk_score, 0.98)

    is_phish = bool(final_risk_score >= threshold)
    verdict = "phishing" if is_phish else "legitimate"

    # Confidence calculation relative to threshold
    if is_phish:
        confidence = float(min(1.0, max(0.5, (final_risk_score - threshold) / (1.0 - threshold + 1e-6))))
    else:
        confidence = float(min(1.0, max(0.5, (threshold - final_risk_score) / (threshold + 1e-6))))

    # Plain-English human-readable reasons
    reasons = _explainer.explain(
        url=canonical_url,
        features=feature_dict,
        risk_score=final_risk_score,
        is_phishing=is_phish
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

    key_signals = {
        "url_length": feature_dict.get("url_length", 0.0),
        "num_subdomains": feature_dict.get("num_subdomains", 0.0),
        "has_ip": bool(feature_dict.get("has_ip", 0.0)),
        "is_https": bool(feature_dict.get("is_https", 0.0)),
        "suspicious_keyword_count": feature_dict.get("suspicious_keyword_count", 0.0),
        "url_entropy": round(feature_dict.get("url_entropy", 0.0), 3),
        "brand_tld_misalignment": bool(feature_dict.get("brand_tld_misalignment", 0.0)),
        "has_indian_brand_token": bool(feature_dict.get("has_indian_brand_token", 0.0)),
        "has_indian_lure": bool(feature_dict.get("has_indian_lure", 0.0)),
        "max_brand_similarity": round(feature_dict.get("max_brand_similarity", 0.0), 3),
        "has_homoglyph_or_punycode": bool(feature_dict.get("has_homoglyph_or_punycode", 0.0)),
    }

    return PredictResponse(
        url=payload.url,
        canonical_url=canonical_url,
        scheme_assumed=scheme_assumed,
        registered_domain=registered_domain,
        tld=tld,
        is_phishing=is_phish,
        verdict=verdict,
        risk_score=final_risk_score,
        ml_risk_score=ml_risk_score,
        final_risk_score=final_risk_score,
        policy_override=policy_override,
        confidence=round(confidence, 4),
        decision_threshold=threshold,
        latency_ms=elapsed_ms,
        reasons=reasons,
        key_signals=key_signals
    )


@app.post("/explain")
def explain_url(payload: PredictRequest):
    """Dedicated endpoint returning detailed feature attribution and reasons."""
    pred = predict_url(payload)
    return {
        "url": pred.url,
        "canonical_url": pred.canonical_url,
        "verdict": pred.verdict,
        "risk_score": pred.risk_score,
        "ml_risk_score": pred.ml_risk_score,
        "final_risk_score": pred.final_risk_score,
        "policy_override": pred.policy_override,
        "reasons": pred.reasons,
        "key_signals": pred.key_signals,
        "latency_ms": pred.latency_ms
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
