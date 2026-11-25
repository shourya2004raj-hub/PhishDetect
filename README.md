# PhishDetect: AI-Driven Phishing URL Detection

### Robust Generalization Across Geographic, Temporal, and Adversarial Distribution Shifts

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev/)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live_Demo-black?logo=vercel)](https://phish-detect-delta.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🚀 **Live Interactive Demo**: [https://phish-detect-delta.vercel.app](https://phish-detect-delta.vercel.app)

An ultra-lightweight, zero-network phishing detection architecture designed to tackle generalization collapse in real-world phishing detection. By introducing region-aware threat indicators alongside lexical and structural signals, this system mitigates domain transfer decay on Indian-targeted financial and citizen traffic while defending against adversarial evasion, unseen brands, and AI-generated phishing attacks.

---

## Key Highlights

- **Zero-Network Static URL Analysis**: Sub-millisecond ($1.5\text{--}3.5\text{ ms}$) client-side feature extraction. Never resolves DNS, issues HTTP requests, or queries WHOIS records.
- **Leakage-Free Domain Group Partitioning**: Strict registered domain isolation (`tldextract.registered_domain`) guarantees zero domain leakage between training, validation, and test sets.
- **Universal URL Canonicalization**: Transparently standardizes bare domains, scheme defaults, and trailing slashes to prevent representation shift artifacts across all incoming web traffic.
- **Region-Aware Threat Signatures**: Captures brand-TLD misalignment, deceptive banking tokens, urgent vernacular lures, and homoglyphs specific to the Indian threat landscape.
- **Explainability Layer**: Converts numeric risk factors into plain-English threat summaries for non-technical end users.
- **Production Delivery**: Includes a FastAPI REST API, a React 19 + Vite dashboard, and a Chrome Manifest V3 browser extension with inline link inspection and real-time intercept dialogs.

> [!NOTE]
> For an in-depth architectural walkthrough, empirical standing, research gaps, and novelty analysis, see [docs/PROJECT_RESEARCH_DOCUMENTATION.md](docs/PROJECT_RESEARCH_DOCUMENTATION.md) and the academic manuscript [docs/PAPER_MANUSCRIPT.md](docs/PAPER_MANUSCRIPT.md).

---

## Pre-Registered Confirmatory Study (Track A: A1–A5, E06 Appendix)

To address the **Lexical Illusion** in ML phishing detection and establish leak-free empirical rigor, a confirmatory study was pre-registered under tag `prereg-v2` (`b4a5d2a758223f1d7895b722ef6650087ef33a27`) and executed with domain-clustered bootstrap statistics. 

- **Full Confirmatory Report**: [`research/CONFIRMATORY_REPORT.md`](research/CONFIRMATORY_REPORT.md)
- **Academic Manuscript**: [`docs/PAPER_MANUSCRIPT.md`](docs/PAPER_MANUSCRIPT.md)
- **Comprehensive Project Standing & Novelty**: [`docs/PROJECT_RESEARCH_DOCUMENTATION.md`](docs/PROJECT_RESEARCH_DOCUMENTATION.md)
- **Protocol Amendments**: [`research/EXPERIMENT_PROTOCOL_AMENDMENT_1.md`](research/EXPERIMENT_PROTOCOL_AMENDMENT_1.md)

### Confirmatory Findings at a Glance

| Exp | Focus | Benchmark ($N$) | Minuend vs. Subtrahend | Metric Value | 95% Bootstrap CI | Key Empirical Takeaway |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A1** | Shortcut Reliance | `a1_path_matched` (21,094) | Unmasked vs Masked | $\Delta\text{AUC} = \mathbf{+0.0281}$ | [+0.0207, +0.0386] ($p < 0.001$) | Shortcut-only model achieves 0.9088 AUC using only 6 length/depth features. |
| **A2** | Syntactic Fragility | 50 Benign Homepages | `https://bare` vs `https://www` | $\Delta\text{Prob} = \mathbf{+0.6159}$ | — | 78% (39/50) of benign homepages flip to phishing simply by adding `www.`. |
| **A3** | Unseen Brands ZK | `a3_unseen_brands` (658) | Regional ZK vs Generic | $\Delta\text{AUC} = \mathbf{-0.0286}$ | [-0.0427, -0.0186] ($p < 0.001$) | Zero-knowledge regional features degrade discrimination due to out-of-vocabulary sparsity on multi-tenant hosts. |
| **A4** | Cross-Dist Transfer | `phiusiil_test` (3,520) | In-Dist vs PhiUSIIL | $\Delta\text{AUC} = \mathbf{+0.0623}$ (Drop) | Exceeds $>0.05$ op. criterion | Severe threshold transfer failure: FPR explodes to 86.93% at in-distribution threshold. |
| **A5** | Temporal Drift | `a5_temporal_test` (9,339) | In-Time vs Out-of-Time | $\Delta\text{AUC} = \mathbf{+0.0647}$ (Drop) | Test AUC: [0.8987, 0.9319] ($p < 0.001$) | Significant temporal degradation over chronological splits. |
| **E06** | Adversarial Paradox | `global_test` Perturbed | Clean vs Subdomain Trick | $\text{Recall}: 79.5\% \to 98.7\%$ | — | Heuristic perturbations paradoxically amplify length/depth shortcuts, boosting recall. |

### CLI Reproduction Tool

```bash
# 1. Inspect calibrated empirical summary:
python -m research.reproduce inspect

# 2. Verify all benchmark datasets and split manifests:
python -m research.reproduce verify

# 3. Re-run an individual experiment (e.g. A1, A3, A4):
python -m research.reproduce run --experiment a1

# 4. Re-run full confirmatory suite (A1-A5, E06 appendix):
python -m research.reproduce run --all
```

---

## Experimental Benchmark Results (E01 - E09)

All metrics report 5-fold cross-seed averages ($\text{Seeds} = [42, 43, 44, 45, 46]$) on domain-isolated test sets.

| Experiment | Focus / Task | Best Model | Features | Precision | Recall | F1-Score | ROC-AUC | Latency | Model Size |
|---|---|---|---|---|---|---|---|---|---|
| **E01** | Standard Global Benchmark | LightGBM | Lexical + Structural | 91.17% | 78.32% | **84.22%** | 0.9283 | 2.64 ms | 0.50 MB |
| **E01** | Source Bias Audit | LightGBM | No Path/Query | 91.19% | 77.64% | **83.87%** | 0.9225 | 2.75 ms | 0.50 MB |
| **E02** | Regional Transfer Gap | LightGBM | Lexical + Structural | 100.0% | 92.16% | **95.92%** | 0.9983 | 2.73 ms | 0.50 MB |
| **E03** | Feature Ablation (Lexical) | LightGBM | Lexical Only (24) | 91.24% | 72.64% | **80.66%** | 0.9431 | 2.77 ms | 0.50 MB |
| **E03** | Feature Ablation (Structural) | LightGBM | Lex + Struct (39) | 99.99% | 94.48% | **97.16%** | 0.9993 | 2.90 ms | 0.50 MB |
| **E03** | Feature Ablation (Full Region) | LightGBM | Full Region-Aware (47)| **99.96%** | **98.09%** | **99.02%** | **0.9996** | 3.52 ms | 0.50 MB |
| **E04** | Cross-Dataset (Phresh $\to$ Phi) | LightGBM | Conventional (39) | 51.73% | 91.83% | **66.14%** | 0.8469 | 1.42 ms | 0.50 MB |
| **E04** | Cross-Dataset (Phresh $\to$ Phi) | BiLSTM | Character Sequence | 98.02% | 47.75% | **64.19%** | 0.7766 | 55.44 ms | 0.22 MB |
| **E04** | Cross-Dataset (Phi $\to$ Phresh) | LightGBM | Conventional (39) | 48.80% | 86.75% | **62.46%** | 0.5494 | 1.63 ms | 0.47 MB |
| **E04** | Cross-Dataset (Phi $\to$ Phresh) | BiLSTM | Character Sequence | 53.74% | 89.13% | **67.04%** | 0.6771 | 54.67 ms | 0.22 MB |
| **E05** | Temporal Drift ($T_1 \to T_2$) | LightGBM | Conventional (39) | 86.64% | 89.60% | **87.92%** | 0.9565 | 1.58 ms | 0.50 MB |
| **E06** | Adversarial Defense (Clean) | LightGBM | Clean Model on Adv | 99.96% | 98.38% | **99.16%** | 0.9995 | 1.61 ms | 0.50 MB |
| **E06** | Adversarial Retrained | LightGBM | Adv Model on Adv | **99.95%** | **100.0%** | **99.97%** | **1.0000** | 1.46 ms | 0.50 MB |
| **E07** | Zero-Shot Unseen Brands ($N=600$)| LightGBM | 12 Withheld Brands | 100.0% | **99.80%** | **99.90%** | 0.9999 | 2.76 ms | 0.50 MB |
| **E08** | Synthetic AI Phishing ($N=500$)| LightGBM | Full Region-Aware (47)| 100.0% | **100.0%** | **100.0%** | 1.0000 | 1.47 ms | 0.50 MB |
| **E09** | Compound Multi-Shift Stress | LightGBM | Full Region-Aware (47)| **99.96%** | **98.44%** | **99.19%** | **0.9997** | 1.63 ms | 0.50 MB |

---

## System Architecture

```
Static URL String
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│              URLFeatureExtractor (47 Features)            │
│  ├── Lexical (24): Entropies, length, ratios, symbols    │
│  ├── Structural (15): Scheme, IP, subdomains, path depth │
│  └── Regional (8): Brand-TLD mismatch, lures, homoglyphs │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│         Region-Aware LightGBM Classifier (0.50 MB)        │
│          P(Phishing | x) >= Optimal Threshold             │
└──────────────┬────────────────────────────┬──────────────┘
               │                            │
               ▼                            ▼
┌──────────────────────────────┐ ┌─────────────────────────┐
│     Rule-Based Explainer     │ │   FastAPI Backend / API │
│  - Threat factor attribution │ │  - /predict             │
│  - Plain-English warnings    │ │  - /explain             │
│  - Official domain matching  │ │  - /health              │
└──────────────┬───────────────┘ └──────────┬──────────────┘
               │                            │
               └──────────────┬─────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
   React 19 + Vite Web App       Chrome Extension (MV3)
  (Interactive Threat Meter)   (Badges & Intercept Dialog)
```

---

## Directory Structure

```
.
├── backend/                  # FastAPI prediction & explanation service
│   ├── main.py               # API routes, URL canonicalization, and policy layer
│   ├── model_baseline.joblib # Trained global baseline model
│   └── model_region_aware.joblib # Production region-aware model
├── data/
│   ├── benchmark/            # Confirmatory datasets (A1–A5, census)
│   ├── raw/                  # Downloaded raw corpora & caches
│   └── processed/            # Domain-isolated train/test splits
├── docs/                     # Comprehensive research & academic documentation
│   ├── PROJECT_RESEARCH_DOCUMENTATION.md # Full project standing, architecture, novelty, & roadmap
│   └── PAPER_MANUSCRIPT.md   # Complete peer-reviewed academic manuscript
├── experiments/              # Benchmark reproduction scripts (E01 - E09)
│   ├── E01_standard.py ... E09_combined.py
├── extension/                # Chrome Manifest V3 extension
│   ├── manifest.json, background.js, content.js, popup.html, popup.js
├── research/                 # Confirmatory empirical protocol & reproduction suite
│   ├── figures/              # Publication figures (PDF & PNG)
│   ├── results/              # Confirmatory JSON metrics & verification logs
│   ├── CONFIRMATORY_REPORT.md # Pre-registered Gate G3 empirical evaluation
│   ├── EXPERIMENT_PROTOCOL.md # Track A / Track B pre-registered design
│   ├── reproduce.py          # Unified CLI reproduction & verification tool
│   └── run_bilstm.py         # Character-level BiLSTM training with Lion optimizer
├── results/                  # Consolidated benchmark summary and neural evaluation
│   ├── SUMMARY.md            # Master experimental table (E01–E09)
│   └── bilstm_lion_eval.json # Saved BiLSTM Lion test metrics
├── scripts/                  # Data collection & AI generation pipelines
│   ├── download_data.py, download_phiusiil.py, generate_ai_urls.py
├── src/                      # Core feature extraction & model library
│   ├── explainer/            # Plain-English risk explainer
│   ├── features/             # Lexical, structural, regional extractors
│   ├── models/               # Baseline tree models & BiLSTM neural network
│   └── utils/                # Metrics, domain canonicalization, and data loaders
├── tests/                    # Automated unit & integration test suites (23 tests)
│   ├── test_phase1.py, test_phase1_rigor.py, test_phase2.py, test_phase3.py, test_verification_pass.py
└── web/                      # React 19 + Vite web dashboard
```

---

## Quickstart & Installation

### 1. Python Environment Setup

```bash
# Clone the repository
git clone https://github.com/shourya2004raj-hub/PhishDetect.git
cd PhishDetect

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Data Acquisition & Split Construction

```bash
# Downloads PhreshPhish, Tranco, and Indian phishing feeds with leakage-free splitting
python scripts/download_data.py

# Download and preprocess UCI PhiUSIIL dataset
python scripts/download_phiusiil.py
```

### 3. Run Experiments (E01 to E09)

Execute any individual experiment script:
```bash
python experiments/E01_standard.py
python experiments/E02_regional_transfer.py
python experiments/E03_regional_augmentation.py
python experiments/E04_cross_dataset.py
python experiments/E05_temporal.py
python experiments/E06_adversarial.py
python experiments/E07_unseen_brands.py
python experiments/E08_ai_generated.py
python experiments/E09_combined.py
```

### 4. Neural Deep Learning Baseline (BiLSTM with Lion Optimizer)

Train or evaluate the character-level BiLSTM baseline:
```bash
python research/run_bilstm.py
```

---

## Serving & User Interfaces

### 1. Launch FastAPI Backend

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

#### Example API Request:
```bash
curl -X POST "http://127.0.0.1:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"url": "http://sbi-kyc-update-portal-urgent.xyz/login.php", "include_regional": true}'
```

#### Example Response:
```json
{
  "url": "http://sbi-kyc-update-portal-urgent.xyz/login.php",
  "canonical_url": "http://sbi-kyc-update-portal-urgent.xyz/login.php",
  "scheme_assumed": false,
  "registered_domain": "sbi-kyc-update-portal-urgent.xyz",
  "tld": "xyz",
  "is_phishing": true,
  "verdict": "phishing",
  "risk_score": 0.9982,
  "ml_risk_score": 0.9982,
  "final_risk_score": 0.9982,
  "policy_override": "none",
  "confidence": 0.9968,
  "decision_threshold": 0.4409,
  "latency_ms": 2.14,
  "reasons": [
    "Target brand token 'sbi' found in hostname, but the registered domain 'sbi-kyc-update-portal-urgent.xyz' is not an official domain.",
    "Urgent or deceptive action lure detected: 'kyc', 'update', 'login'.",
    "Insecure HTTP connection used for sensitive financial transaction."
  ],
  "key_signals": {
    "url_length": 51.0,
    "num_subdomains": 0.0,
    "has_ip": false,
    "is_https": false,
    "suspicious_keyword_count": 3.0,
    "url_entropy": 3.91,
    "brand_tld_misalignment": true,
    "has_indian_brand_token": true,
    "has_indian_lure": true,
    "max_brand_similarity": 1.0,
    "has_homoglyph_or_punycode": false
  }
}
```

---

### 2. Launch React 19 Web Dashboard

```bash
cd web
npm install
npm run dev
```
Open `http://localhost:5173` to access the interactive web interface.

To build for production:
```bash
npm run build
```

---

### 3. Chrome Browser Extension (Manifest V3)

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked** and select the `extension/` directory from this repository.
4. The extension automatically:
   - Scans URLs in the active tab.
   - Places risk badges next to suspicious links.
   - Intercepts clicks on high-risk links with a plain-English warning modal.

---

## Running the Automated Test Suite

```bash
pytest tests/ -v
```
All **23 unit and integration tests** across data processing, feature extraction, input validation, URL canonicalization, baseline models, neural BiLSTM, and FastAPI endpoints will execute and pass.

To verify dataset and split integrity:
```bash
python -m research.reproduce verify
```

---

## Ethical Disclosure & Research Methodology

1. **Safety Guarantee**: URLs are treated exclusively as static text sequences. The system never resolves DNS, establishes network connections, or retrieves webpage payloads from malicious domains.
2. **Defensive Intent**: Synthetic lures and adversarial perturbations were generated strictly to benchmark detector resilience and train defensive classifiers.
3. **No Domain Memorization**: Zero-shot experiments with strictly held-out brand entities ($N=600$) confirm that classification decisions depend on generalized structural patterns, not static domain whitelists.
