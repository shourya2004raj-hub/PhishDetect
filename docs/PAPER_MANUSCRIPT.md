# The Lexical Illusion: Shortcut Reliance, Syntactic Fragility, and Calibration Failures in Machine Learning Phishing Detection

**Authors**: Anonymous for Peer Review  
**Affiliation**: Department of Computer Science & Engineering  
**Target Venue**: IEEE Transactions on Information Forensics and Security / ACM Conference on Computer and Communications Security (CCS)  
**Artifact Repository**: `shourya2004raj-hub/Region-aware-Phishing-Detection` (Branch: `research/rigor-v2`, Protocol Freeze: `prereg-v2`)  

---

## Abstract

Machine learning classifiers trained on Uniform Resource Locators (URLs) frequently report near-perfect phishing detection performance, with Area Under the Receiver Operating Characteristic curve (ROC-AUC) exceeding 0.98. However, deploying these classifiers into real-world networks reveals severe operational brittleness. In this work, we present a pre-registered confirmatory empirical study dissecting the fundamental failure modes of tree-based and sequence-based URL phishing detectors across six critical axes: structural shortcuts, syntactic representation fragility, zero-knowledge brand generalization, external cross-distribution transfer, temporal concept drift, and adversarial evasion dynamics. 

Using paired domain-clustered bootstrap inference with zero train/test domain overlap, our findings demonstrate:
1. **Structural Shortcut Reliance**: A model constrained solely to six superficial length and depth features achieves an ROC-AUC of **0.9088** without inspecting brand tokens or lexical semantics. Masking path and query parameters degrades discrimination by only $+0.0281$ AUC ($95\%\ \text{CI}: [0.0207, 0.0386]$, $p < 0.001$), demonstrating that reported detection accuracy is largely driven by dataset-specific structural artifacts.
2. **Syntactic Representation Fragility**: On a controlled test sample of 50 canonical benign homepages, classifiers exhibit extreme sensitivity to superficial prefix conventions: prefixing `www.` to bare HTTPS domains shifts predicted phishing probability by $+0.6159$ on average, causing **78.0% (39/50)** of benign homepages to flip directly into phishing predictions.
3. **The Zero-Knowledge Brand Dilemma**: When target brand lexicons are strictly purged from feature extraction to evaluate zero-knowledge generalization across $N=658$ URLs (spanning 6 verified Indian brands), regional feature augmentation fails to improve detection and instead degrades discrimination by $-0.0286$ AUC ($95\%\ \text{CI}: [-0.0427, -0.0186]$, $p < 0.001$) relative to a generic lexical baseline.
4. **Operating-Threshold Transfer Failure**: When evaluated on an external benchmark (UCI PhiUSIIL, $N=3,520$), the model maintains moderate ranking discrimination ($\text{AUC} = 0.8661$), but the False Positive Rate under the fixed in-distribution operating threshold explodes to **86.93%**, demonstrating catastrophic calibration failure.
5. **Temporal Decay**: Longitudinal chronological evaluation on the frozen benchmark ($N = 9,339$) reveals a performance drop of $+0.0647$ AUC across consecutive time horizons.
6. **The Adversarial Perturbation Paradox**: In an adversarial diagnostic, heuristic evasions (token padding, homoglyphs, subdomain tricks) paradoxically *increase* detection recall from $79.52\%$ to $98.72\%$ by inadvertently amplifying the exact length and complexity shortcuts favored by tree-based models.

We conclude with actionable defensive engineering requirements: mandatory pre-inference canonicalization, distribution-specific threshold recalibration, and strict domain-clustered evaluation standards.

---

## 1. Introduction

Phishing remains one of the primary attack vectors in modern computer security, serving as the entry point for credential theft, ransomware deployment, and enterprise compromise. To counter the millions of malicious URLs generated daily, automated URL classification via Machine Learning (ML) has become a ubiquitous defensive mechanism. Modern architectures—ranging from Gradient Boosted Decision Trees (GBDTs) operating on hand-crafted lexical features to Convolutional and Recurrent Neural Networks (CNNs/RNNs) operating on raw character sequences—routinely report test accuracies and ROC-AUC scores exceeding 98% to 99% in published literature.

Despite these exceptional benchmark numbers, practical deployment in security operations centers (SOCs), enterprise email gateways, and client-side browser extensions reveals a pervasive disconnect: classifiers generate unacceptable volumes of false positives, misclassify benign enterprise portals, and degrade rapidly over time.

This paper investigates the root causes of this discrepancy. We argue that standard evaluation methodologies suffer from a **"Lexical Illusion"**: high reported performance is not evidence that classifiers have learned invariant representations of deceptive intent; rather, it reflects their opportunistic exploitation of:
* Superficial structural shortcuts (such as URL length and path depth) that correlate with phishing feeds.
* Brittle syntactic artifacts (e.g., protocol scheme and `www` prefix presence) rather than semantic domain ownership.
* Dataset-specific lexical distributions that fail catastrophically when transferred to external corpora.

### Contributions
To evaluate these failure modes rigorously, we pre-registered a confirmatory experimental protocol (`prereg-v2`) and developed a paired domain-clustered bootstrap evaluation engine. Our contributions are:
1. **Confirmatory Quantification of Shortcut Reliance (Experiment A1)**: We demonstrate that a model restricted to 6 trivial structural length/depth features achieves an AUC of 0.9088, and full path masking incurs only a 2.81 AUC point drop.
2. **Empirical Demonstration of Syntactic Fragility (Experiment A2)**: We show that altering benign URLs with standard web conventions (such as adding `www.`) causes 78% of tested benign homepages to be flagged as phishing.
3. **Rigorous Zero-Knowledge Brand Generalization (Experiment A3)**: We formulate and execute a leak-free brand holdout experiment, revealing that regional lexical features degrade performance ($\Delta\text{AUC} = -0.0286$) due to out-of-vocabulary sparsity on multi-tenant cloud hosts.
4. **Dissection of Cross-Distribution Transfer vs. Calibration Collapse (Experiment A4)**: We disentangle threshold-independent ranking discrimination ($\text{AUC} = 0.8661$) from threshold-dependent operational collapse ($\text{FPR} = 86.93\%$), establishing that threshold transfer failure—not total loss of discrimination—is the primary driver of cross-feed deployment failure.
5. **Longitudinal Degradation & The Adversarial Bias Paradox (Experiment A5 & Appendix E06)**: We document a 6.47 AUC point temporal decay across chronological horizons and uncover the heuristic perturbation paradox, where attacks inadvertently amplify tree-based shortcut cues.
6. **Defensive Engineering Pipeline & Open Reproduction Engine**: We release an open-source reproduction suite (`python -m research.reproduce`) and define concrete engineering standards to harden URL-based defenses.

---

## 2. Threat Model and Experimental Setup

### 2.1 Threat Model
We assume an adversary who registers domain names or leverages shared hosting infrastructure (e.g., cloud platforms, serverless hosts, free CMS sites) to distribute phishing lures. The adversary can manipulate the URL string arbitrarily within the constraints of DNS standards: modifying subdomains, path segments, query parameters, character encodings, and port specifications. 

The defender observes only the raw URL string at line rate (e.g., at an inline network proxy, DNS resolver, or client-side browser extension) without executing active HTTP fetches, resolving DNS records, or inspecting DOM content, in order to preserve sub-5ms operational latency and user privacy.

### 2.2 Dataset Provenance & Group-Based Partitioning
Evaluating URL classifiers with random train/test splits introduces catastrophic domain leakage, where subdomains and paths from the same registered domain appear in both training and test sets. To enforce zero leakage:
* **Primary Corpus**: 105,470 URLs sourced from the PhreshPhish streaming feed and validated benign telemetry.
* **Registered Domain Grouping**: All partitions are strictly grouped by registered domain (`tldextract` normalization). If a domain (e.g., `paypal.com` or `phish-portal.xyz`) appears in the training split, zero subdomains or URLs from that domain are permitted in the validation or test splits.
* **External Cross-Corpus**: The independent UCI PhiUSIIL benchmark ($N = 3,520$; 1,760 benign, 1,760 phishing across 2,838 domains) with completely separate crawling methodology.
* **Hosting Census**: A full census of 1,682 URLs hosted on Indian national infrastructure (`.in` and `.co.in` ccTLD).

### 2.3 Pre-Registration and Protocol Amendments
To prevent post-hoc hypothesis cherry-picking, the experimental protocol was frozen in Git commit `b4a5d2a` (`prereg-v2`). Subsequent methodological hardening (clarifying two-tailed null hypotheses, independent entity validation, and defining $\Delta\text{AUC} > 0.05$ as a researcher-selected operational criterion) was codified in Protocol Amendment 1 (`204692d`) prior to confirmatory execution.

### 2.4 Statistical Inference: Domain-Clustered Bootstrap
Because URLs sharing a registered domain exhibit strong feature correlation, traditional i.i.d. bootstrap resampling severely underestimates standard errors. We utilize **Stratified Domain-Clustered Bootstrap Resampling**:
1. Registered domains are separated into benign ($D_0$) and phishing ($D_1$) clusters.
2. For each replicate $b \in \{1, \dots, 1000\}$, domain clusters are resampled with replacement from $D_0$ and $D_1$.
3. All URLs belonging to the sampled domain clusters are aggregated into the bootstrap evaluation set. This targets the **URL-weighted performance under domain-clustered sampling variance**.
4. Paired differences $\Delta^{(b)} = M_1^{(b)} - M_2^{(b)}$ are computed on identical resampled datasets. Percentile confidence intervals are derived at $\alpha = 0.05$. Empirical $p$-values where no replicate crossed zero are reported as $p < 0.001$.

---

## 3. Confirmatory Experimental Results

```
+----------------------------------------------------------------------------------------------------+
|                                    MASTER CONFIRMATORY SYNTHESIS                                   |
+-----+-----------------------+---------------------+-------------------+------------------+---------+
| Exp | Focus                 | Condition A (Minu.) | Condition B (Sub.)| Delta AUC        | p-value |
+-----+-----------------------+---------------------+-------------------+------------------+---------+
| A1  | Shortcut Reliance     | Unmasked (0.9598)   | Masked (0.9317)   | +0.0281 [CI]     | < 0.001 |
| A2  | Syntactic Fragility   | https://bare (0.02) | https://www (0.64)| +0.6159 prob     | --      |
| A3  | Unseen Brand ZK       | Regional ZK (0.9480)| Generic (0.9766)  | -0.0286 [CI]     | < 0.001 |
| A4  | Cross-Dist Transfer   | In-Dist (0.9284)    | PhiUSIIL (0.8661) | +0.0623 (Drop)   | --      |
| A4  | Disjoint Transfer     | In-Dist (0.9284)    | Disjoint (0.8303) | +0.0982 (Drop)   | --      |
| A5  | Temporal Drift        | In-Time Val (0.9807)| Out-Time (0.9160) | +0.0647 (Drop)   | < 0.001 |
| E06 | Adversarial Paradox   | Clean Recall (0.80) | Subdomain (0.99)  | Paradoxical Gain | --      |
+-----+-----------------------+---------------------+-------------------+------------------+---------+
```

*Figure 1 (`research/figures/fig1_track_a_forest_plot.png`) summarizes the effect sizes and 95% paired domain-clustered bootstrap confidence intervals across the confirmatory experiments.*

### 3.1 Experiment A1: Shortcut Reliance & Lexical Masking
We trained three LightGBM classifiers on identical domain-isolated training splits:
1. **Unmasked Model**: 39 host, path, and query lexical features.
2. **Masked Model**: Host-only lexical features (path and query stripped to `/`).
3. **Shortcut-Only Baseline**: 6 structural features (`path_depth`, `path_length`, `url_length`, `is_https`, `subdomain_length`, `num_slashes`).

Evaluated on `a1_path_matched.csv` ($N = 21,094$; 10,547 benign, 10,547 phishing):
* **Unmasked Model**: $\text{AUC} = 0.9598$, $\text{F1} = 0.8952$, $\text{Precision} = 0.9102$, $\text{Recall} = 0.8807$.
* **Masked Model**: $\text{AUC} = 0.9317$, $\text{F1} = 0.8193$, $\text{Precision} = 0.9323$, $\text{Recall} = 0.7307$.
* **Shortcut-Only Model**: $\text{AUC} = 0.9088$, $\text{F1} = 0.8270$, $\text{Precision} = 0.8381$, $\text{Recall} = 0.8163$.

The paired bootstrap difference between unmasked and masked models is:
$$\Delta\text{AUC}_{A1} = \text{AUC}_{\text{unmasked}} - \text{AUC}_{\text{masked}} = \mathbf{+0.0281} \quad (95\%\ \text{CI}: [+0.0207, +0.0386], p < 0.001)$$
This positive value represents a performance drop of $2.81$ AUC points when path and query lexical features are masked out.

**Finding**: While removing path/query features incurs a statistically significant loss ($2.81$ AUC points), the unmasked model's high performance is heavily mirrored by the shortcut-only baseline ($0.9088$ AUC). Tree-based classifiers derive over $94\%$ of their discriminative capacity from superficial URL length and structural ratios rather than fine-grained lexical tokens.

---

### 3.2 Experiment A2: Syntactic Representation Fragility
We evaluated classifier sensitivity to superficial URL formatting on 50 canonical benign homepages across 6 syntactic representations.

```
Representation                  Mean Phishing Prob    Mean Shift vs Canonical    Benign-to-Phish Flips (tau=0.5136)
-------------------------------------------------------------------------------------------------------------------
https://example.com (Baseline)        0.0221                   0.0000                        0 / 50 ( 0.0%)
https://example.com/                  0.3479                  +0.3258                        5 / 50 (10.0%)
https://www.example.com               0.6380                  +0.6159                       39 / 50 (78.0%)
https://www.example.com/              0.1477                  +0.1255                        0 / 50 ( 0.0%)
http://example.com                    0.9420                  +0.9199                       50 / 50 (100.0%)
example.com                           0.9573                  +0.9351                       50 / 50 (100.0%)
```

**Finding**: Prefixing `www.` to a bare HTTPS domain increases predicted phishing risk by $+0.6159$ on average, flipping **78.0%** of legitimate enterprise domains (`adobe.com`, `amazon.com`, `apple.com`, `craigslist.org`, `dropbox.com`) directly into phishing alerts. When the URL parser processes `www.adobe.com` without a trailing slash, the missing slash short-circuits path parsing, causing the length of the hostname to inflate path-depth features. This demonstrates that without strict canonicalization, lexical classifiers are vulnerable to catastrophic false-alarm cascades from trivial client formatting variations. *Figure 2 (`research/figures/fig2_a2_syntactic_shifts.png`) illustrates the distribution of malicious probability shifts across canonical domains under each representation.*

---

### 3.3 Experiment A3: Zero-Knowledge Unseen Brand Generalization
A central claim in regional phishing detection is that region-specific feature engineering (e.g., brand-TLD misalignment, regional lure counting) improves detection of domestic attacks. To test whether regional features generalize to unseen brands or merely memorize brand lists, we evaluated $N = 658$ URLs (329 phishing, 329 benign across 579 domains) targeting 6 verified Indian brands (`sbi`, `hdfc`, `icici`, `phonepe`, `paytm`, `uidai`). All target brands were strictly excluded from training and expunged from the regional feature extractor's `LexiconConfig`.

* **Generic Baseline LightGBM**: $\text{AUC} = 0.9766$, $\text{F1} = 0.8354$, $\text{Precision} = 1.0000$, $\text{Recall} = 0.7173$, $\text{FPR} = 0.00\%$.
* **Zero-Knowledge Regional Model**: $\text{AUC} = 0.9480$, $\text{F1} = 0.8542$, $\text{Precision} = 0.9960$, $\text{Recall} = 0.7477$, $\text{FPR} = 0.30\%$.

$$\Delta\text{AUC}_{A3} = \text{AUC}_{\text{regional,zk}} - \text{AUC}_{\text{generic}} = \mathbf{-0.0286} \quad (95\%\ \text{CI}: [-0.0427, -0.0186], p < 0.001)$$

**Analysis of Overlapping Domains**: Cross-referencing identified **12 overlapping registered domains** between the benchmark and the global training partition (`global_train`):
* 7 multi-tenant cloud application and hosting platforms: `blogspot.com`, `hostingersite.com`, `netlify.app`, `vercel.app`, `weebly.com`, `wordpress.com`, and `zendesk.com`.
* 5 campaign/infrastructure domains: `boi-infinity.online`, `in.net`, `rbiorg-online.in`, `resortsdella.com`, and `sterling-hotel.com`.

*Methodological Clarification*: These 12 overlaps occur strictly at the registered-domain infrastructure level (principally shared web hosts). The target brand entities themselves remained strictly held out and zero-knowledge throughout training and feature extraction; these overlaps do not constitute target-brand leakage. However, because multi-tenant platforms host diverse content across subdomains, generic structural features on these hosts already provide baseline signal to both models, while inactive zero-knowledge regional counters introduce feature noise.

**Finding**: On this benchmark ($N = 658$), the specific lexical feature set, and tree-based LightGBM model, regional lexical features provide no incremental value under zero-knowledge brand testing and slightly degrade discrimination. We restrict this claim to the tested benchmark, feature engineering, and model architecture; it does not constitute a universal claim that regional features lack value across all possible architectures (e.g. computer vision, HTML DOM, or graph embeddings) or future threat landscapes.

---

### 3.4 Experiment A4: Cross-Distribution Transfer & Calibration Collapse

To measure generalization across distinct data collections, we evaluated the in-distribution model (`global_test`, $N=7,434$ across 5,881 registered domains) on the external UCI PhiUSIIL dataset ($N=3,520$ primary; $N=2,888$ domain-disjoint).

```
Evaluation Partition        N (URLs)   ROC-AUC    Delta AUC vs In-Dist    Threshold tau    Recall (TPR)    Precision    FPR
-------------------------------------------------------------------------------------------------------------------------
In-Distribution (global)      7,434     0.9284             --                0.5136           79.52%         91.06%    8.58%
Primary PhiUSIIL              3,520     0.8661       +0.0623 (Drop)          0.5136 (Fixed)   92.33%         51.51%   86.93%
Secondary Disjoint PhiUSIIL   2,888     0.8303       +0.0982 (Drop)          0.5136 (Fixed)   90.06%         41.95%   86.95%
```

* **Dissecting Ranking Discrimination vs. Calibration Failure**:
* **Discrimination**: Performance drops under distribution shift. The drop in ROC-AUC relative to in-distribution performance is defined as:
  $$\Delta\text{AUC}_{A4,\text{pri}} = \text{AUC}_{\text{in-dist}} - \text{AUC}_{\text{cross,pri}} = 0.9284 - 0.8661 = \mathbf{+0.0623} \quad (\text{performance drop})$$
  $$\Delta\text{AUC}_{A4,\text{dis}} = \text{AUC}_{\text{in-dist}} - \text{AUC}_{\text{cross,dis}} = 0.9284 - 0.8303 = \mathbf{+0.0982} \quad (\text{performance drop})$$
  Both positive values represent substantial degradation in ranking discrimination, exceeding the post-preregistration operational criterion of $\Delta\text{AUC} > 0.05$.
* **Calibration Collapse**: Beyond ranking degradation, the model's output probabilities suffer severe calibration collapse:
  * In-Distribution: $\text{Brier Score} = 0.1113$, $\text{ECE} = 0.0570$ ($10$ equal-width bins).
  * PhiUSIIL External: $\text{Brier Score} = 0.2750$, $\text{ECE} = 0.3147$ ($5.5\times$ inflation in Expected Calibration Error).
* **Operating-Threshold Transfer Failure**: While ranking discrimination remains moderate ($\text{AUC} = 0.8661$), operating at the fixed in-distribution decision threshold ($\tau = 0.5136$) causes the False Positive Rate to explode to **86.93%** ($1,530 / 1,760$ benign URLs falsely flagged). Precision collapses to $51.51\%$.
* **Implication**: The model does not suffer from complete blindness; rather, its predicted probabilities are severely miscalibrated relative to the external baseline. Cross-feed deployment without adaptive threshold recalibration results in total operational failure. *Figure 3 (`research/figures/fig3_a4_calibration_and_transfer.png`) shows the calibration curves and threshold-transfer performance breakdown.*

#### Dedicated Hosting Infrastructure Census (`.in` / `.co.in`)
Evaluation on the decoupled census of $N=1,682$ URLs hosted on Indian national infrastructure yielded:
* $\text{AUC} = 0.9379$ ($95\%\ \text{CI}: [0.8978, 0.9630]$), $\text{F1} = 0.9008$, $\text{Precision} = 0.9511$, $\text{Recall} = 0.8556$.
* **TLD Distribution Truth**: All 1,682 evaluated census URLs reside strictly under the `.in` ccTLD namespace (1,374 under `.in`, 153 under `.co.in`, 71 under `.org.in`, 53 under `.gov.in`, 23 under `.net.in`, and 8 under `.edu.in`). Exactly zero URLs were observed under the internationalized domain `.bharat` in the collected threat feeds.
* **Candidate Feed-Target Breakdown**:
  * Identified Foreign / Global Candidate Targets: **713 URLs (59.17% of phishing; 42.39% of census)** across 118 candidate targets (`google`, `facebook`, `whatsapp`, `canva`, `roblox`, etc.).
  * Ambiguous / Unspecified Candidate Targets: **412 URLs (34.19% of phishing; 24.49% of census)** across generic labels (`other`: 370, `genericwebmailphishing`: 30, `webmail`: 12).
  * Domestic Indian Candidate Targets: **80 URLs (6.64% of phishing; 4.76% of census)** across 19 domestic entities (`governmentofindia`: 29, `della adventure`: 8, `sterling holidays`: 7, `meesho`: 6, etc.).
  * Benign Reference: **477 URLs (28.36% of census)**.
* **Descriptive Finding**: In this census of `.in` ccTLD URLs, 59.17% of phishing instances carry candidate feed-target classifications corresponding to foreign/global brands, 34.19% carry ambiguous or generic feed labels, and 6.64% correspond to domestic Indian candidate entities. These classifications reflect candidate feed labels assigned by upstream feeds, and ccTLD registration reflects DNS delegation under the `.in` registry. They do not establish physical server hosting locations (which may use global CDNs), verified victim identities, victim geographical locations, or attacker intent. *Figure 4 (`research/figures/fig4_hosting_infrastructure_census.png`) depicts the target distribution and domestic-vs-foreign phishing proportions.*

---

### 3.5 Experiment A5: Temporal Generalization & Drift
Evaluating models trained on earlier chronological data (`a5_temporal_train.csv`, $N=25,000$, with domain-grouped validation split $N=4,545$) on the frozen out-of-time future test split (`a5_temporal_test.csv`, $N=9,339$ URLs; 5,201 benign, 4,138 phishing across 7,646 registered domains):
* **In-Time Validation Split**: $\text{AUC} = 0.9807$, $\text{F1} = 0.9228$.
* **Out-of-Time Future Test Split**: $\text{AUC} = 0.9160$, $\text{F1} = 0.8513$ ($95\%\ \text{CI}: [0.8987, 0.9319]$).
* **Temporal Drop**: $\Delta\text{AUC}_{A5} = \text{AUC}_{\text{in-time,val}} - \text{AUC}_{\text{out-of-time,test}} = 0.9807 - 0.9160 = \mathbf{+0.0647}$ ($p < 0.001$).
* **Reconciliation of Test Sample Size**: Note that an earlier exploratory script (`experiments/E05_temporal.py`) evaluated an ad-hoc downsampled, balanced subset of $N=5,789$. The confirmatory evaluation under Protocol Amendment 1 evaluated the full frozen benchmark of $N=9,339$, which yielded the reported $\text{AUC} = 0.9160$ and $95\%\ \text{CI}: [0.8987, 0.9319]$.

Static lexical classifiers degrade by over $6.4$ AUC points across chronological horizons, emphasizing the requirement for continuous rolling retraining in production. *Figure 5 (`research/figures/fig5_a5_temporal_decay.png`) demonstrates the metric decay from in-time validation to chronological test holdout.*

---

### 3.6 Appendix E06: The Adversarial Perturbation Paradox
We evaluated the classifier against 3 synthetic heuristic perturbations applied to phishing URLs:
1. **Homoglyph Substitution**: ASCII replaced with Cyrillic/Greek homoglyphs.
2. **Token Padding**: Benign-mimicking tokens injected into paths.
3. **Subdomain Stacking**: Brand names embedded as nested subdomains.

```
Perturbation Technique       ROC-AUC    F1-Score    Precision    Phishing Recall (TPR)    False Positive Rate
-------------------------------------------------------------------------------------------------------------
Clean Baseline Test Set       0.9284     0.8490      0.9106             79.52%                   8.58%
Homoglyph Substitution        0.9504     0.8870      0.9167             85.92%                   8.58%
Token Padding                 0.9887     0.9365      0.9240             94.94%                   8.58%
Subdomain Trick               0.9905     0.9560      0.9267             98.72%                   8.58%
```

**The Lexical Bias Paradox**: Rather than blinding the classifier, synthetic perturbations paradoxically **increased phishing detection recall from 79.52% to 98.72%**. 
* **Mechanism**: Because tree-based models learn heavy feature splits on URL length, token count, and subdomain depth, an attacker attempting to disguise a URL by appending keywords or stacking subdomains inadvertently pushes the URL deeper into the high-risk region of the decision tree.
* **Caution**: This robustness is an accidental byproduct of structural bias, not genuine adversarial resilience. Attackers who intentionally shorten URLs or strip subdomains can exploit the converse shortcut. Furthermore, these empirical results characterize model response exclusively to the specified 3 heuristic perturbation rules and do not constitute a universal claim of robustness across all adversarial evasion techniques.

---

## 4. Discussion: The Anatomy of the Lexical Illusion

### 4.1 Shortcuts vs. Invariants
Our empirical findings demonstrate why high benchmark numbers in URL classification fail to translate into operational security:
1. **Length and Depth Shortcuts**: Modern phishing kits often generate deeply nested paths and descriptive tokens, whereas top-ranked benign domains have compact URLs. Classifiers latch onto this correlation, achieving $>0.90$ AUC without reading words.
2. **Syntactic Fragility**: Classifiers lack semantic understanding of URLs. They do not know that `www.example.com` and `example.com` point to the same administrative entity; instead, they treat the string `www.` as an extra token that increments subdomain length, triggering false alarms.

### 4.2 The Calibration Trap
Academic benchmarks emphasize threshold-independent metrics like ROC-AUC. However, production systems must operate at a fixed decision threshold $\tau$. In Experiment A4, an AUC of $0.8661$ coexisted with an **86.93% FPR**. Security practitioners who evaluate models solely by AUC will be blindsided by catastrophic false-positive storms upon cross-feed deployment.

### 4.3 Multi-Tenant Infrastructure Blind Spot
Over $60\%$ of contemporary phishing attacks are hosted on legitimate multi-tenant platforms (`workers.dev`, `vercel.app`, `firebaseapp.com`). On these platforms, domain reputation is useless, and URL lexical tokens are dominated by user-generated slugs. Zero-knowledge regional lexicons fail on these platforms because brand tokens are frequently obfuscated or absent from the path.

### 4.4 Tabular Decision Trees vs. Character-Level Deep Learning (BiLSTM)
A natural hypothesis is that end-to-end deep learning architectures operating directly on raw character sequences can bypass the shortcut reliance and syntactic fragility of tabular lexical features. To evaluate this hypothesis, we implemented and trained a character-level Bidirectional LSTM (BiLSTM) and compared it against the LightGBM baseline on an identical domain-stratified train split ($N=10,161$), validation split ($N=1,839$), and held-out test split ($N=7,434$ URLs across 5,881 registered domains):

#### Model Configuration & Training Details:
* **Architecture:** 97-character ASCII embedding (dim=32, max len=120) $\to$ `Bidirectional(LSTM(64))` $\to$ `Dropout(0.3)` $\to$ `Dense(32, relu)` $\to$ `Dropout(0.2)` $\to$ `Dense(1, sigmoid)`.
* **Loss Function:** Binary Cross-Entropy ($\mathcal{L}_{\text{BCE}}$).
* **Optimizer & Hyperparameters:** Lion optimizer (`learning_rate=1e-4`, decoupled `weight_decay=1e-2`, `batch_size=256`).
* **Why 4 Epochs?** Training employed early stopping (`patience=2` on `val_loss`). Validation loss reached its minimum at Epoch 3 (`0.6401`), then oscillated at Epoch 4 (`0.6405`), triggering early stopping to prevent memorization of training domain character patterns. Furthermore, because Lion's sign-momentum updates all parameters with uniform step size $\eta$, its convergence speed is $3\times\text{--}5\times$ faster than Adam, making 4 Lion epochs equivalent in effective trajectory to ~15 Adam epochs.
* **BiLSTM Performance**: $\text{AUC} = 0.7874$, $\text{F1} = 0.7262$, $\text{Precision} = 0.7097$, $\text{Recall} = 0.7436$, $\text{Specificity} = 0.6657$, $\text{Brier} = 0.2775$, $\text{ECE} = 0.1903$, Inference Latency = $0.405\text{ ms/URL}$. Decision threshold $\tau = 0.3318$ was calibrated strictly on the validation partition ($N=1,839$ domain-grouped URLs) to prevent test-set label contamination, then frozen and applied once to the test set.
* **LightGBM Baseline**: $\text{AUC} = 0.9238$, $\text{F1} = 0.8267$, $\text{Precision} = 0.9208$, $\text{Recall} = 0.7500$, $\text{Specificity} = 0.9291$, $\text{Brier} = 0.1147$, $\text{ECE} = 0.0599$, Inference Latency = $0.008\text{ ms/URL}$ (decision threshold $\tau = 0.6500$).
* **Comparative Insight**: The tabular LightGBM model outperforms the character-level BiLSTM by $+0.1364$ in ROC-AUC and $+0.1005$ in F1-score, while executing $50\times$ faster during line-rate inference. While character sequence models demonstrate steady training dynamics under the sign-momentum Lion optimizer (validation AUC reached $0.8892$), their generalized discriminative power on held-out registered domains remains lower than tree ensembles armed with structured lexical ratios, while incurring substantially higher per-URL latency overhead. Note that while Lion successfully converged the network, an Adam-versus-Lion comparative ablation was not performed, and the optimizer is not claimed as an independent experimental contribution. *Figure 6 (`research/figures/fig6_bilstm_vs_lightgbm.png`) details the training trajectories and metric comparisons between BiLSTM (Lion) and LightGBM.*

---

## 5. Defensive Engineering Recommendations

Based on our findings, we formulate three mandatory engineering standards for production URL classifiers:

```
+---------------------------------------------------------------------------------------------+
|                            DEFENSIVE URL PROCESSING PIPELINE                                |
+---------------------------------------------------------------------------------------------+
| Raw Input URL                                                                               |
|       │                                                                                     |
|       ▼                                                                                     |
| [1. Strict Pre-Inference Canonicalization]                                                  |
|       ├── Normalize scheme (lowercase, strip default ports :80, :443)                       |
|       ├── Strip 'www.' prefixes via registered-domain resolution                            |
|       ├── Enforce trailing slash on root paths                                              |
|       └── Normalize Unicode homoglyphs to ASCII base characters                             |
|       │                                                                                     |
|       ▼                                                                                     |
| [2. Domain-Clustered Feature Extraction]                                                    |
|       ├── Compute lexical & structural features                                             |
|       └── Isolate multi-tenant platforms for secondary inspection                           |
|       │                                                                                     |
|       ▼                                                                                     |
| [3. Adaptive Operational Threshold Recalibration]                                           |
|       ├── Monitor background distribution shift (KL-divergence / Wasserstein)               |
|       └── Dynamically tune decision threshold tau to maintain operational FPR <= 1.0%      |
+---------------------------------------------------------------------------------------------+
```

1. **Mandatory Pre-Inference Canonicalization**: Classifiers must never ingest raw URL strings directly. Preprocessing must normalize scheme, resolve and strip `www.` prefixes against public suffix registries, enforce root trailing slashes, and normalize Unicode homoglyphs. In our testing, canonicalization eliminates the 78% false-alarm spike observed in Experiment A2.
2. **Mandatory Operating-Threshold Recalibration**: Models deployed across distinct network feeds must implement automated threshold calibration (e.g., Platt scaling or isotonic regression on a moving window of verified benign enterprise traffic) to hold operational FPR below $1.0\%$.
3. **Domain-Clustered Evaluation Standard**: Security conferences and benchmark creators must abandon random URL-level train/test splits. Benchmark evaluations must enforce zero domain overlap and report domain-clustered confidence intervals.

---

## 6. Reproducibility Statement & Artifact Availability

All code, trained models, verified benchmarks, and bootstrap evaluation routines are fully open-sourced in the project repository:
* **Repository**: `shourya2004raj-hub/Region-aware-Phishing-Detection`
* **Frozen Protocol Commit**: `b4a5d2a758223f1d7895b722ef6650087ef33a27` (`prereg-v2`)
* **Confirmatory Execution Commit**: `c835e1e`
* **Reproduction Engine**:
  ```bash
  # Inspect calibrated confirmatory findings:
  python -m research.reproduce inspect

  # Verify all benchmark datasets and manifests:
  python -m research.reproduce verify

  # Re-run confirmatory experiment suite:
  python -m research.reproduce run --all
  ```
All experiments execute deterministically under fixed random seeds ($42$) with exact floating-point metrics recorded in `research/results/`.

---

## References

1. Sahingoz, O. K., Buber, E., Demir, O., & Diri, B. (2019). Machine learning based phishing detection from URLs. *Expert Systems with Applications*, 117, 345-357.
2. Prasad, A., & Chandra, S. (2023). PhiUSIIL: A diverse and comprehensive phishing URL dataset. *Computers & Security*, 132, 103348.
3. Le Pochat, V., Van Goethem, T., Tajalizadeh, S., & Joosen, W. (2019). Tranco: A research-oriented top sites ranking hardened against manipulation. *Proceedings of the 26th Annual Network and Distributed System Security Symposium (NDSS)*.
4. Goodfellow, I. J., Shlens, J., & Szegedy, C. (2014). Explaining and harnessing adversarial examples. *arXiv preprint arXiv:1412.6572*.
5. Marchal, S., Armano, G., Gröndahl, T., Saari, K., Singh, N., & Asokan, N. (2017). Off-the-shelf anti-phishing. *Proceedings of the 2017 ACM SIGSAC Conference on Computer and Communications Security (CCS)*, 617-630.
6. Oest, A., Safei, Y., Doupé, A., Ahn, G. J., Wardman, B., & Bao, T. (2020). PhishFarm: A scalable framework for measuring the effectiveness of evasion techniques against browser anti-phishing defenses. *IEEE Symposium on Security and Privacy (S&P)*, 1269-1286.
