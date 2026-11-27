# Repository Architecture & Teammate Handover Guide

This project is built cleanly end-to-end on `main` with strict modular boundaries so that once the core system and research pipeline are complete, teammates can clone the repository and take over maintenance, testing, or future extensions immediately without friction.

---

## 1. Quick-Start Onboarding for Teammates

Once core development is complete, any teammate can run and verify the entire project in 3 commands:

```bash
# 1. Clone and install dependencies
git clone https://github.com/shourya2004raj-hub/PhishDetect.git
cd PhishDetect
pip install -r requirements.txt
pip install -r requirements-research.txt  # Optional: needed for running research/benchmarks & pytest

# 2. Verify dataset zero-leakage & Python-JS parity tests (built in Phase 0)
python research/verify_splits.py
pytest tests/

# 3. Load the standalone Chrome Extension (zero Python server needed once Phase 3 completes)
# Open chrome://extensions -> Developer Mode ON -> Load unpacked -> select extension/
```

See [`MASTER_PLAN.md`](MASTER_PLAN.md) and [`RESEARCH_FOUNDATION_AND_METHODOLOGY.md`](RESEARCH_FOUNDATION_AND_METHODOLOGY.md) for the full technical design and verified literature references.

---

## 2. Clean Modular Structure (Where Everything Lives)

| Directory | Purpose | Handover / Maintenance Tasks |
| :--- | :--- | :--- |
| **`src/`** | Feature extraction, canonicalization, calibration & model export | Retrain or tune Stage 1 / Stage 2 models and re-export `extension/engine/model_trees.json`. |
| **`colab/`** | GPU training notebooks (`DistilBERT`, `Char-CNN`, `BiLSTM`) | Re-run heavy deep-learning benchmarks on free Colab T4 GPUs with reproducible seeds. |
| **`extension/`** | 100% standalone Chrome Manifest V3 Pre-Navigation Firewall | UI refinements on `blocked.html` / `popup.html` and Stage 2 DOM guard testing. |
| **`research/`** | Pre-registered confirmatory experiments (`A1`–`A6`), stats & figures | Re-run `python -m research.reproduce run --all` and regenerate paper plots. |
| **`data/`** | Leakage-free URL & offline HTML datasets (`verify_splits.py`) | Append newer chronological threat feeds (e.g., future months) for temporal drift tracking. |
| **`web/`** | React 19 + Vite dashboard (Vercel live demo) | Frontend UI updates and interactive result displays. |

---

## 3. Standard Git Workflow Once Handed Over

After taking over, teammates should avoid pushing untested changes directly to `main`:
1. Pull latest `main`: `git checkout main && git pull origin main`
2. Create a short task branch: `git checkout -b task/<short-name>`
3. Verify tests pass (`pytest tests/` + `python research/verify_splits.py`)
4. Push & open a Pull Request into `main`.
