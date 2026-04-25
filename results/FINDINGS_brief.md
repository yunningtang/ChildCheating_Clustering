# Findings: team update

Quick summary of what came out of the re-run. Full numbers + figures in `results/`.

---

## TL;DR (3 lines)

- 4 baseline-trial clusters and 1 T5_alone cluster show a meaningful concentration of cheaters (Fisher p < 0.05 uncorrected; multiple-comparison correction not applied yet).
- The strongest hit is **T4_pre 2 s** (18 kids, 83% cheater, p = 0.004), at the start of a baseline trial, before E even leaves the room.
- A separate cluster in **T5_alone 5 s** (26 kids, 69%, p = 0.045) is statistically comparable; together they suggest cheater-typical facial dynamics show up in **both** baseline and test trials, not exclusively at the cheating moment.

---

## Pipeline status

| Task | Status |
|---|---|
| Cheating latency + window choice | done |
| 52-blendshape feature extraction (mean / std / slope) across 13 phases × 2/5/10 s windows | done |
| 3-mode UMAP + HDBSCAN/k-means clustering | done (105 / 117 combos) |
| Tiered video-verification list | done (76 IDs across 4 tiers) |
| Statistical tests (per-feature group comparisons) | **on hold**, waiting on report spec |
| Predictive modeling (5-fold CV) | **on hold**, waiting on report spec |

---

## Latency

For the 59 cheaters who had a coded cheating event in the alone window:

- median **12.4 s**, range 0.1 to 80 s, long right tail (skew 2.1)
- 6 cheaters fall back to Trial 5 start (no `E leaves` event); 1 has no in-window cheating event
- 2-s pre-cheat window covers 97 % of cheaters; 5-s covers 85 %; 10-s drops to 66 %
- We do not have a non-cheater latency baseline, so what these 12 seconds *mean* (deliberation? environment scanning? task engagement?) cannot be inferred from the data alone

→ 2 s and 5 s are the safe windows; 10 s loses too many participants on `T5_precheating` and on `T3_post`.

![latency distribution](figures/latency_distribution.png)

---

## Clustering (slope features only)

105 of 117 (mode × phase × window) combinations clustered; 12 skipped because n < 30 after filtering.

### Pooled mode (all kids)

5 clusters with cheater_rate ≥ 65 % and Fisher p < 0.10:

| phase | window | n | cheaters | rate | Fisher p |
|---|---|---|---|---|---|
| **T4_pre** | 2 s | 18 | 15 | **83 %** | **0.004** |
| T2_post | 2 s | 13 | 11 | 85 % | 0.017 |
| T2_pre | 10 s | 6 | 5 | 83 % | 0.091 |
| **T5_alone** | 5 s | 26 | 18 | **69 %** | **0.045** |
| T3_post | 5 s | 15 | 11 | 73 % | 0.100 |

T5_alone 5 s is interesting because it is the largest significant cluster (n = 26) and the only T5 hit. The remaining T5 clusters (T5_Epre 2 s 71 %, T5_Epost 2 s 71 %) did not reach significance (small n).

These p-values are **uncorrected**. With 117 clusterings, Bonferroni would push only T4_pre 0.004 toward survival. Treat all of these as exploratory signals to chase, not as confirmed effects.

![T4_pre 2s pooled UMAP](figures/umap_pooled_T4_pre_2s.png)

### Cheater-only mode (subtypes)

Cheaters split into multiple small subgroups in several phases. Clearest example: `T1_post 10 s` splits cheaters into 4 subgroups of 5 to 9 kids each. Subgroup *content* (i.e. what behavioral pattern defines each subtype) has not been characterized yet, that is part of the video-verification step.

![cheater-only UMAP for T1_post 10s](figures/umap_cheaters_only_T1_post_10s.png)

### Non-cheater-only mode

Used as a control space; by construction, no cheater-rate concept applies.

---

## Video-verification list (the deliverable)

`results/tables/video_verification_list.csv`: 76 unique IDs, four priority tiers:

| tier | count | what to look for |
|---|---|---|
| 1 high-risk cheaters | 32 | check whether the high-risk cluster pattern is visually real |
| 2 cheater subtypes | 27 | describe what behaviorally distinguishes the cheater subgroups |
| **3 false-negative candidates** | **10** | non-cheaters who clustered with cheaters; could be (a) coding misses, (b) trait-similar non-cheaters, or (c) UMAP artifacts |
| 4 contrast control | 7 | random non-cheaters from low-cheater clusters |

**Priority IDs to start with:** `76`, `313`, `408`. All three are non-cheaters who landed inside the strongest cluster (T4_pre 2 s, p = 0.004). Whether their video shows visible cheater-like behavior is the most discriminating single check we can do right now.

**For the video reviewer:** [`results/VIDEO_GUIDE.md`](VIDEO_GUIDE.md) lists the exact timestamp and what to watch for, per ID, per cluster.

---

## What I do not yet know

- Whether the baseline-trial signal reflects a stable trait or an anticipatory state (children may already be evaluating the cheating opportunity in T1 to T4)
- Whether the cluster boundaries are stable to feature choice (slope-only vs mean+slope) or random seeds; needs bootstrap / resampling
- Whether the 10 tier-3 candidates are real false negatives or stochastic UMAP artifacts (proximity in 2-D does not imply similarity in 156-D feature space)
- The 70 % threshold for high-risk is arbitrary; at 65 % T5_alone joins the list, at 80 % only T2_post and T4_pre survive

A sensitivity analysis on the threshold + a multiple-comparison correction pass are the obvious next steps.

---

## Files in `results/`

- `tables/latency_distribution.csv`, `latency_summary.csv`, `window_coverage.csv`: Task 1
- `tables/cluster_summary.csv`, `cluster_skipped.csv`: Task 5
- `tables/video_verification_list.csv`: Task 7
- `figures/latency_distribution.png` + 105 UMAP plots (one per mode × phase × window)
