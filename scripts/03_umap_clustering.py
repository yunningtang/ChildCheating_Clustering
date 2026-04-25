"""
Three-mode UMAP + HDBSCAN/k-means clustering on slope features.
Modes: pooled (all kids), cheaters_only (subtypes), noncheaters_only (false-negative candidates).
Builds the tiered video-verification list as the final deliverable.

Inputs:  data/processed/temporal_slopes.csv, results/tables/latency_distribution.csv
Outputs: results/tables/{cluster_summary,video_verification_list}.csv
         results/figures/umap_{mode}_{phase}_{window}s.png  (one per combo)
Run:     python scripts/03_umap_clustering.py
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import umap
import hdbscan
from tqdm import tqdm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
SLOPES_CSV = ROOT / "data" / "processed" / "temporal_slopes.csv"
LATENCY_CSV = ROOT / "results" / "tables" / "latency_distribution.csv"
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

RNG = 42
MIN_ROWS = 30
HDB_MIN = 5
HIGH_RISK = {"min_size": 5, "min_cheater_rate": 0.70, "max_fisher_p": 0.1}


def cluster_one(df, feature_cols, mode):
    """PCA -> UMAP -> HDBSCAN + best-silhouette k-means. Returns (emb, labels_dict, summary_rows)."""
    n = len(df)
    X = StandardScaler().fit_transform(df[feature_cols].values)
    n_pca = min(20, X.shape[1], n - 1)
    Xp = PCA(n_components=n_pca, random_state=RNG).fit_transform(X)
    n_neighbors = min(15, n - 1)
    emb = umap.UMAP(n_neighbors=n_neighbors, min_dist=0.1,
                    n_components=2, random_state=RNG).fit_transform(Xp)

    labels_dict = {"hdbscan": hdbscan.HDBSCAN(min_cluster_size=HDB_MIN).fit(emb).labels_}

    # k-means across k=2..5, keep highest silhouette
    best = None
    for k in range(2, 6):
        if n < k + 1:
            continue
        labs = KMeans(n_clusters=k, random_state=RNG, n_init=10).fit(emb).labels_
        try:
            sil = silhouette_score(emb, labs)
        except Exception:
            sil = -1.0
        if best is None or sil > best[1]:
            best = (k, sil, labs)
    if best:
        labels_dict[f"kmeans_k{best[0]}"] = best[2]

    return emb, labels_dict


def summarize_clusters(df, labels, method, mode, phase, window, latency_map):
    """One row per cluster in this (method, mode, phase, window)."""
    rows = []
    n_total = len(df)
    n_cheat_total = int(df["cheated"].sum())
    n_non_total = n_total - n_cheat_total

    for cl in sorted(set(labels)):
        mask = labels == cl
        members = df[mask]
        n_members = int(mask.sum())
        n_cheat = int(members["cheated"].sum())
        n_non = n_members - n_cheat

        # cheater_rate / fisher_p only meaningful when both groups exist (Mode A)
        if mode == "pooled":
            cheater_rate = n_cheat / n_members if n_members else np.nan
            outside_cheat = n_cheat_total - n_cheat
            outside_non = n_non_total - n_non
            try:
                _, fisher_p = fisher_exact([[n_cheat, n_non], [outside_cheat, outside_non]])
            except Exception:
                fisher_p = np.nan
            is_high_risk = (
                cl != -1
                and n_members >= HIGH_RISK["min_size"]
                and cheater_rate >= HIGH_RISK["min_cheater_rate"]
                and fisher_p < HIGH_RISK["max_fisher_p"]
            )
        else:
            cheater_rate = np.nan
            fisher_p = np.nan
            is_high_risk = False

        # latency median for cheaters in cluster (Mode A and B)
        latency_median = np.nan
        if mode in ("pooled", "cheaters_only"):
            cheater_ids = members[members["cheated"] == 1]["ID"].astype(int).tolist()
            lats = [latency_map[pid] for pid in cheater_ids if pid in latency_map and not np.isnan(latency_map[pid])]
            if lats:
                latency_median = float(np.median(lats))

        rows.append({
            "phase": phase,
            "window_s": int(window),
            "mode": mode,
            "method": method,
            "cluster_id": int(cl),
            "n_members": n_members,
            "n_cheaters": n_cheat,
            "cheater_rate": cheater_rate,
            "fisher_p": fisher_p,
            "latency_median": latency_median,
            "is_high_risk": bool(is_high_risk),
            "member_ids": ";".join(str(int(i)) for i in members["ID"]),
        })
    return rows


def plot_umap(emb, df, labels_dict, mode, phase, window, out_path):
    """Two-panel UMAP: HDBSCAN clusters (left) + k-means clusters (right)."""
    methods = list(labels_dict.keys())
    fig, axes = plt.subplots(1, len(methods), figsize=(5 * len(methods), 4.5))
    if len(methods) == 1:
        axes = [axes]

    for ax, method in zip(axes, methods):
        labels = labels_dict[method]
        for cl in sorted(set(labels)):
            mask = labels == cl
            color = "lightgray" if cl == -1 else None  # noise gray
            label = "noise" if cl == -1 else f"c{cl} (n={int(mask.sum())})"
            if mode == "pooled":
                # split by cheater within cluster
                cheat_mask = mask & (df["cheated"].values == 1)
                non_mask = mask & (df["cheated"].values == 0)
                ax.scatter(emb[cheat_mask, 0], emb[cheat_mask, 1],
                           c=[color] if color else None, marker="x", s=40, alpha=0.85,
                           label=label if cl != -1 else None)
                ax.scatter(emb[non_mask, 0], emb[non_mask, 1],
                           c=[color] if color else None, marker="o", s=40, alpha=0.55)
            else:
                ax.scatter(emb[mask, 0], emb[mask, 1],
                           c=[color] if color else None, s=40, alpha=0.7,
                           label=label if cl != -1 else None)
        ax.set_title(f"{method}")
        ax.set_xlabel("UMAP 1"); ax.set_ylabel("UMAP 2")
        if len(set(labels)) <= 8:
            ax.legend(fontsize=7, loc="best")

    fig.suptitle(f"{mode} | {phase} | {window}s | n={len(df)}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def build_video_list(summary, slopes, latency_map, n_contrast=10):
    """Tiered list: high-risk members + cheater subtypes + false-negative candidates + controls."""
    rows = []
    seen = {}  # ID -> (priority, tier, source, notes)

    def add(pid, priority, tier, source, notes):
        pid = int(pid)
        if pid in seen and seen[pid][0] <= priority:
            return
        seen[pid] = (priority, tier, source, notes)

    # tier 1: cheaters in Mode A high-risk clusters (confirm the cheater pattern)
    # tier 3: non-cheaters in those same clusters (possible false negatives)
    # split here so the dedup doesn't swallow non-cheaters into tier 1
    high_risk = summary[(summary["mode"] == "pooled") & (summary["is_high_risk"])]
    cheater_lookup = {}
    for _, r in high_risk.iterrows():
        ids = [int(x) for x in r["member_ids"].split(";")]
        key = (r["phase"], int(r["window_s"]))
        if key not in cheater_lookup:
            cheater_lookup[key] = set(slopes[(slopes["phase"] == r["phase"]) &
                                              (slopes["window_s"] == r["window_s"]) &
                                              (slopes["cheated"] == 1)]["ID"].astype(int))
        cheaters_here = cheater_lookup[key]
        src = f"{r['phase']}_{int(r['window_s'])}s_pooled_c{int(r['cluster_id'])}"
        for pid in ids:
            if pid in cheaters_here:
                add(pid, 1, "tier_1_high_risk", src,
                    f"cheater in high-risk cluster (rate={r['cheater_rate']:.0%}, p={r['fisher_p']:.3f})")
            else:
                add(pid, 3, "tier_3_false_negative_candidate", src,
                    f"non-cheater in high-risk cluster (rate={r['cheater_rate']:.0%}, p={r['fisher_p']:.3f})")

    # tier 2: cheater subtypes from Mode B, boundary cases (extreme latency or small clusters)
    chr_clusters = summary[(summary["mode"] == "cheaters_only") & (summary["cluster_id"] != -1)]
    if len(chr_clusters):
        all_lat = pd.Series([v for v in latency_map.values() if not np.isnan(v)])
        q1, q3 = all_lat.quantile(0.25), all_lat.quantile(0.75)
        for _, r in chr_clusters.iterrows():
            small = r["n_members"] < 10
            extreme_lat = (
                pd.notna(r["latency_median"])
                and (r["latency_median"] < q1 or r["latency_median"] > q3)
            )
            if not (small or extreme_lat):
                continue
            ids = [int(x) for x in r["member_ids"].split(";")]
            note_bits = []
            if extreme_lat:
                note_bits.append(f"latency_median={r['latency_median']:.1f}s")
            if small:
                note_bits.append(f"small cluster n={r['n_members']}")
            src = f"{r['phase']}_{int(r['window_s'])}s_cheaters_c{int(r['cluster_id'])}"
            for pid in ids:
                add(pid, 2, "tier_2_cheater_subtype", src, "; ".join(note_bits))

    # tier 4: random non-cheaters from low-cheater-rate clusters (<30%) as control
    low = summary[(summary["mode"] == "pooled")
                  & (summary["cluster_id"] != -1)
                  & (summary["cheater_rate"] < 0.30)
                  & (summary["n_members"] >= 5)]
    candidate_pool = []
    for _, r in low.iterrows():
        ids = [int(x) for x in r["member_ids"].split(";")]
        non_ids = [
            pid for pid in ids
            if not slopes[(slopes["ID"] == pid) & (slopes["cheated"] == 1)].any().any()
        ]
        candidate_pool.extend([(pid, r) for pid in non_ids])
    rng = np.random.default_rng(RNG)
    if candidate_pool:
        idx = rng.choice(len(candidate_pool), size=min(n_contrast, len(candidate_pool)), replace=False)
        for i in idx:
            pid, r = candidate_pool[i]
            src = f"{r['phase']}_{int(r['window_s'])}s_pooled_c{int(r['cluster_id'])}"
            add(pid, 4, "tier_4_contrast_control", src,
                f"random low-rate cluster control (rate={r['cheater_rate']:.0%})")

    for pid, (priority, tier, src, notes) in seen.items():
        cheated = int(slopes[slopes["ID"] == pid]["cheated"].iloc[0]) if (slopes["ID"] == pid).any() else None
        rows.append({
            "ID": pid,
            "tier": tier,
            "priority": priority,
            "cluster_source": src,
            "cheated_label": cheated,
            "notes": notes,
        })

    return pd.DataFrame(rows).sort_values(["priority", "ID"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="+", default=["pooled", "cheaters_only", "noncheaters_only"])
    parser.add_argument("--phases", nargs="+", default=None)
    parser.add_argument("--windows", nargs="+", type=int, default=None)
    args = parser.parse_args()

    print("[Script 03] Starting...")
    slopes = pd.read_csv(SLOPES_CSV)
    latency = pd.read_csv(LATENCY_CSV)
    latency_map = dict(zip(latency["ID"].astype(int), latency["latency_s"]))

    feature_cols = [c for c in slopes.columns if c.endswith("__slope")]
    print(f"  loaded slopes: {slopes.shape}, {len(feature_cols)} features")

    phases = args.phases or sorted(slopes["phase"].unique())
    windows = args.windows or sorted(slopes["window_s"].unique())
    combos = [(m, p, w) for m in args.modes for p in phases for w in windows]
    print(f"  combos to run: {len(combos)} ({len(args.modes)} modes x {len(phases)} phases x {len(windows)} windows)")

    summary_rows = []
    skipped = []

    for mode, phase, window in tqdm(combos, desc="clustering", unit="combo"):
        df = slopes[(slopes["phase"] == phase) & (slopes["window_s"] == window)].copy()
        if mode == "cheaters_only":
            df = df[df["cheated"] == 1]
        elif mode == "noncheaters_only":
            df = df[df["cheated"] == 0]
        df = df.dropna(subset=feature_cols).reset_index(drop=True)

        if len(df) < MIN_ROWS:
            skipped.append({"mode": mode, "phase": phase, "window_s": window,
                            "n": len(df), "reason": f"n<{MIN_ROWS}"})
            continue

        try:
            emb, labels_dict = cluster_one(df, feature_cols, mode)
        except Exception as e:
            skipped.append({"mode": mode, "phase": phase, "window_s": window,
                            "n": len(df), "reason": f"error: {type(e).__name__}: {e}"})
            continue

        for method, labels in labels_dict.items():
            summary_rows.extend(summarize_clusters(df, labels, method, mode, phase, window, latency_map))

        plot_umap(emb, df, labels_dict, mode, phase, window,
                  FIGS / f"umap_{mode}_{phase}_{int(window)}s.png")

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(TABLES / "cluster_summary.csv", index=False)
    pd.DataFrame(skipped).to_csv(TABLES / "cluster_skipped.csv", index=False)

    n_combos_done = len(combos) - len(skipped)
    n_high_risk = int(summary["is_high_risk"].sum()) if "is_high_risk" in summary else 0
    print(f"\n  cluster_summary.csv: {summary.shape}, {n_combos_done}/{len(combos)} combos clustered")
    print(f"  high-risk clusters (Mode A): {n_high_risk}")

    # video verification
    video = build_video_list(summary, slopes, latency_map)
    video.to_csv(TABLES / "video_verification_list.csv", index=False)
    print(f"  video_verification_list.csv: {video.shape}")
    if len(video):
        tier_counts = video.groupby("tier").size().sort_index()
        print("  tier breakdown:")
        for tier, n in tier_counts.items():
            print(f"    {tier}: {n}")

    print("\n[DONE] Outputs:")
    for p in [TABLES / "cluster_summary.csv",
              TABLES / "cluster_skipped.csv",
              TABLES / "video_verification_list.csv",
              FIGS / "umap_*.png (one per (mode, phase, window) combo)"]:
        print(f"  {p.relative_to(ROOT) if p.exists() else p}")


if __name__ == "__main__":
    main()
