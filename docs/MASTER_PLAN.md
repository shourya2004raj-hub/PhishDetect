# Final Master Plan (v3.4): PhishDetect — Serverless Two-Stage Browser Firewall & Empirical Security Study

> [!IMPORTANT]
> **Finalized, Zero-Shortcut Blueprint:**  
> Designed for **solo end-to-end execution first** on `main`, followed by clean handover to teammates via [`docs/TEAM_COLLABORATION_WORKFLOW.md`](TEAM_COLLABORATION_WORKFLOW.md).  
> Every architectural choice is backed by verified 2017–2026 peer-reviewed literature in [`docs/RESEARCH_FOUNDATION_AND_METHODOLOGY.md`](RESEARCH_FOUNDATION_AND_METHODOLOGY.md).

---

## 1. Core Architecture: Distilled Pre-Navigation Firewall + Dual-Intention Cloud Guard

```
User Clicks / Navigates to URL (Main Frame: frameId === 0)
       │
       ▼
[Stage 1: Pre-Navigation Firewall] (MV3 chrome.webNavigation.onBeforeNavigate)
  ├── Guards: Ignore chrome://, chrome-extension://, sub-frames (frameId !== 0), & session bypasses
  ├── Runs 100% locally in Chrome Service Worker (< 1 ms, ZERO Python server, ZERO WASM bloat)
  ├── Deterministic Canonicalizer + PSL Resolver (psl_rules.json) + Signed Feature-Hashed N-Grams
  ├── Runs Knowledge-Distilled LightGBM Student (from DistilBERT Teacher) + Isotonic Calibration
  ├── High Risk (≥ τ_block tuned for FPR ≤ 0.5%) ──► Redirects to blocked.html BEFORE page render
  └── Multi-Tenant Cloud Host (vercel.app / workers.dev / netlify.app) or Borderline ──► Stage 2
       │
       ▼
[Stage 2: Dual-Intention Cloud-Host DOM Guard] (content.js — PhishIntention + KnowPhish principles)
  ├── Completely dormant on normal websites (zero visual clutter or DOM distortion)
  ├── Credential-Taking Intention (CRP): <input type="password">, OTP/card inputs, cross-origin form action
  ├── HTML Brand-Claim Intention: <title> / <h1> / meta brand claims vs registered_domain
  └── Combined URL + Dual-Intention Risk ≥ τ_dom ──► Freezes form & raises Credential Warning Shield
```

---

## 2. Five Critical Edge Cases Pre-Solved Before Coding

Reviewing the existing codebase prevented five traps that would otherwise waste weeks later:

1. **Public Suffix Parity (`tldextract` vs Chrome JS):** Chrome JS has no `tldextract` library. We will export a deterministic `extension/engine/psl_rules.json` directly from Python's PSL snapshot and verify multi-part ccTLDs (`.co.in`, `.gov.in`, `.org.uk`) via `tests/golden_urls.json` so Python and JS never disagree on `registered_domain`.
2. **MV3 Redirect Loop & Iframe Protection:** `onBeforeNavigate` MUST filter `details.frameId === 0` (preventing broken OAuth/Stripe payment iframes), ignore `chrome-extension://` and `blocked.html`, handle HTTP redirects (`onBeforeRedirect`), and persist session bypasses in `chrome.storage.session`.
3. **Pure-JS Trees vs ONNX/WASM CSP Bloat:** Exporting LightGBM trees via `booster.dump_model()` + Isotonic bins into pure ES modules avoids multi-MB `.wasm` binaries and Manifest V3 `wasm-unsafe-eval` CSP relaxation while executing in `< 0.5 ms`. *(We will benchmark Pure-JS vs ONNX Runtime Web WASM empirically in Phase 3).*
4. **Compute Realism (`torch` CPU locally vs Colab T4 GPU):** Local PyTorch (`2.14.1+cpu`) lacks CUDA. All heavy deep models (`DistilBERT` Teacher, 30-epoch `BiLSTM`, `Char-CNN`) will run via reproducible notebooks in `colab/` on free **Colab T4 GPU**, keeping local execution fast.
5. **Backward Compatibility During Transition:** Existing `backend/` FastAPI endpoints, `web/` Vercel demo, and 23 `tests/` remain intact and passing while Stage 1/Stage 2 pure-JS components are built cleanly alongside them.

---

## 3. Execution Phases & Automated Verification Gates

### Phase 0: Guardrails, Parity Harness & Dependencies
1. Split optional heavy research packages cleanly (`requirements-research.txt`: `beautifulsoup4`, `pyarrow`, `fsspec`, `pytest`, `onnx`, `onnxruntime`, `onnxmltools`) while keeping `requirements.txt` lean.
2. Build `research/verify_splits.py` asserting **0 `registered_domain` overlap** across all train/val/test/A1–A5 splits (*Arp et al.* Pitfall P3).
3. Build `tests/golden_urls.json` (100 nasty edge-case URLs: Punycode/IDN, IPv4/IPv6, non-standard ports, `.co.in`, deep queries, `www.`) + `extension/engine/psl_rules.json`.
* **Gate 0:** `research/verify_splits.py` runs cleanly and rejects overlaps automatically.

### Phase 1: Dataset Repair & Safe Offline Cloud-HTML Benchmark
1. **Fix Experiment A1 Leakage:** Rebuild `data/benchmark/a1_path_matched.csv` strictly from held-out `global_test` domains (eliminating the current 2,777 overlapping domains / 56.83% overlap against `global_train`).
2. **Eliminate Bare-Domain Bias (*Arp* P1/P4):** Replace un-pathed `tranco_global_legit` training rows with real deep-path benign URLs (real subpaths, `?query=` strings, `www.` variants, and legitimate `vercel.app`/`github.io`/`netlify.app` apps).
3. **Add 2026 Chronological Slice & Monthly Bins (*TESSERACT*):** Construct monthly time slices (`2024 → 2025 → 2026`) and imbalanced operational base-rate test splits (**1% and 5% phishing prevalence**) per *TESSERACT (2019)* and *PhreshPhish (2025)*.
4. **Build Offline Dual-Intention HTML Benchmark (`~1,500–2,000 pages`):** Stream `url`, `html`, `label`, `target` safely offline from `phreshphish/phreshphish` shards for multi-tenant cloud hosts (`workers.dev`, `vercel.app`, `netlify.app`, `blogspot.com`) — zero live malware crawling.
* **Gate 1:** `research/verify_splits.py` passes with 0 overlap, balanced benign path depths, and verified monthly strata.

### Phase 2: Knowledge Distillation, Calibration & Converged Multi-Model Suite
1. **Feature Upgrade (`src/features/`):** Canonicalization + `www.`/scheme invariant augmentation + signed Murmur/FNV-1a hashed 3–5 character and word n-grams (*Weinberger et al., ICML 2009*) so the model distinguishes `?q=weather` from `?verify=sbi-kyc`.
2. **Colab T4 GPU Teacher & Fair Baselines (`colab/`):**
   * Fine-tune **DistilBERT / URLTran-style Transformer** on full canonicalized URLs (Teacher + upper bound).
   * Train **fully converged BiLSTM** (full 40k+ data, up to 30 epochs with true `val_loss` `EarlyStopping`) and **1D Char-CNN (`URLNet`)**.
   * Audit **1–2 existing public HuggingFace phishing URL models** on `A1`, `A2`, `A4`, `A5`.
3. **Distill into Stage 1 Pure-JS LightGBM Student:**
   * Train **LightGBM Student** using Teacher Transformer soft targets + structural + hashed n-gram features.
   * Fit **Isotonic Calibration** strictly on `df_val` (*Guo et al., ICML 2017*) tuned for **$\text{FPR} \le 0.5\%$** under realistic base rates.
   * Export via `booster.dump_model()` directly to `extension/engine/model_trees.json` (< 1 MB).
4. **Train Stage 2 Dual-Intention DOM Classifier:** Calibrated Logistic Regression / shallow GBDT combining `Stage 1 risk + local CRP + HTML Brand-Claim cues`.
* **Gate 2:** Stage 1 achieves $\le 0.5\%$–$1.0\%$ FPR across 1,000 real everyday benign deep-path URLs (without blind root-domain allowlists) AND Python $\leftrightarrow$ JS feature/prediction parity passes within $\le 10^{-5}$.

### Phase 3: Serverless MV3 Pre-Navigation Firewall & WASM Benchmark
1. **Pure-JS Evaluation Engine (`extension/engine/`):** `canonicalizer.js`, `psl_domains.js`, `feature_extractor.js`, `tree_evaluator.js` (< 0.5 ms per URL).
2. **Stage 1 Pre-Navigation Interceptor (`extension/background.js` + `blocked.html`):** Update `manifest.json` with `webNavigation`, `storage`, `tabs`. Intercept `onBeforeNavigate` & `onBeforeRedirect` (`frameId === 0`), redirect high-risk links *before page render* to `blocked.html` (*Back to Safety* vs *Proceed Anyway* session bypass).
3. **Stage 2 Silent Dual-Intention Guard (`extension/content.js`):** Dormant on standard websites; activates **only** on cloud/LOTS hosts or borderline Stage 1 scores to freeze forms and show a warning shield when password/OTP inputs + brand mismatches appear.
4. **Empirical Runtime Benchmark (*Arp* P9):** Compare Pure-JS Serialized Trees vs **ONNX Runtime Web WASM** inside Chrome MV3 (bundle size, cold start, p95 latency, CSP safety).
* **Gate 3:** Automated Playwright/Chrome test confirms pre-load blocking of phishing links in `< 5 ms`, Stage 2 protection on mock cloud credential pages, and `< 1%` FPR on normal browsing.

### Phase 4: Confirmatory Experiments A1–A6, Manuscript & Teammate Handover
1. Freeze protocol tag `prereg-v3` before final confirmatory test execution.
2. Run `A1`–`A6` across LightGBM Student, Char-CNN, Converged BiLSTM, DistilBERT Teacher, and audited HuggingFace models:
   * **`A1`:** Zero-overlap shortcut reliance & n-gram lexical value.
   * **`A2`:** Syntactic (`www.`, HTTP, trailing slash) fragility before & after invariant distillation.
   * **`A3`:** Zero-knowledge brands & cloud/LOTS infrastructure analysis.
   * **`A4`:** Cross-corpus transfer on UCI PhiUSIIL (*Prasad & Chandra, 2024*) — AUC vs calibration collapse.
   * **`A5`:** **TESSERACT AUT** (`2024 → 2025 → 2026` monthly decay) + **1% & 5% base-rate evaluations**.
   * **`A6` (Mitigation Proof):** Quantifies exact improvements from Canonicalization + Distillation (`A2`), Validation/Few-Shot Calibration (`A4`), and Stage 2 Dual-Intention DOM Guard on cloud phishing.
3. Update `docs/PAPER_MANUSCRIPT.md` (with verified citations and exact JSON-backed numbers), verify `pytest tests/`, and hand over clean `main` to teammates via [`docs/TEAM_COLLABORATION_WORKFLOW.md`](TEAM_COLLABORATION_WORKFLOW.md).
