"""
Task 1: cheating latency (E_leaves -> first_cheat) and window coverage.
Task 2: temporal features (mean / std / slope) for 52 blendshapes across
        13 phases x 3 windows (2s/5s/10s).

Inputs:  output n120_UPDATE2.csv, mediapipe_segmentsoutput/blendshapes/
Outputs: results/tables/{latency_distribution,latency_summary,window_coverage}.csv
         results/figures/latency_distribution.png
         data/processed/{temporal_window_tests,temporal_slopes,coverage_report}.csv
Run:     python scripts/01_latency_and_extraction.py
"""
import argparse
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from tqdm import tqdm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_CSV = ROOT / "output n120_UPDATE2.csv"
BS_DIR = ROOT / "mediapipe_segmentsoutput" / "blendshapes"
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
PROC = ROOT / "data" / "processed"

for d in (TABLES, FIGS, PROC):
    d.mkdir(parents=True, exist_ok=True)


# --- Task 1: latency ----------------------------------------------------------

def compute_latency():
    df = pd.read_csv(BEHAVIOR_CSV)

    # per-id cheater label and T5 / E_leaves / first_cheat timestamps from the event log
    cheater_label = df.groupby("ID")["Cheated or not"].first()
    cheaters = cheater_label[cheater_label == 1].index.tolist()

    e_leaves = df[df["Behavior"] == "E leaves"].groupby("ID")["Start (s)"].min()
    t5_start = df[df["Behavior"] == "Trial 5"].groupby("ID")["Start (s)"].min()
    e_returns = df[df["Behavior"] == "E returns"].groupby("ID")["Start (s)"].min()
    first_cheat = df[df["Behavior"] == "Cheating"].groupby("ID")["Start (s)"].min()

    rows = []
    for pid in cheaters:
        alone_start = e_leaves.get(pid, np.nan)
        src = "E_leaves"
        if pd.isna(alone_start):
            alone_start = t5_start.get(pid, np.nan)
            src = "T5_start_fallback"

        # only count cheats within the alone window
        er = e_returns.get(pid, np.nan)
        cheat_rows = df[(df["ID"] == pid) & (df["Behavior"] == "Cheating")]
        if pd.notna(alone_start) and pd.notna(er):
            in_alone = cheat_rows[(cheat_rows["Start (s)"] >= alone_start) &
                                  (cheat_rows["Start (s)"] < er)]
            fc = in_alone["Start (s)"].min() if len(in_alone) else np.nan
        else:
            fc = first_cheat.get(pid, np.nan)

        rows.append({
            "ID": int(pid),
            "latency_s": float(fc - alone_start) if pd.notna(fc) and pd.notna(alone_start) else np.nan,
            "alone_source": src,
        })

    return pd.DataFrame(rows).sort_values("ID")


def summarize_latency(lat_df):
    valid = lat_df.dropna(subset=["latency_s"])
    x = valid["latency_s"]
    return pd.DataFrame([{
        "n": len(valid),
        "n_fallback": int((valid["alone_source"] == "T5_start_fallback").sum()),
        "n_missing_cheat_event": int(lat_df["latency_s"].isna().sum()),
        "min": x.min(),
        "Q1": x.quantile(0.25),
        "median": x.median(),
        "Q3": x.quantile(0.75),
        "max": x.max(),
        "mean": x.mean(),
        "std": x.std(),
        "IQR": x.quantile(0.75) - x.quantile(0.25),
        "skewness": stats.skew(x),
    }]).round(3)


def window_coverage(lat_df, windows):
    valid = lat_df.dropna(subset=["latency_s"])
    n = len(valid)
    out = []
    for w in windows:
        covered = int((valid["latency_s"] >= w).sum())
        out.append({
            "window_s": w,
            "n_total_cheaters": n,
            "n_covered": covered,
            "coverage_rate": round(covered / n, 3) if n else 0,
            "n_contaminated": n - covered,
        })
    return pd.DataFrame(out)


def plot_latency(lat_df, windows, out_path):
    valid = lat_df.dropna(subset=["latency_s"])["latency_s"].values
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    # left: histogram + KDE
    ax1.hist(valid, bins=20, density=True, alpha=0.6, color="steelblue", edgecolor="white")
    kde = stats.gaussian_kde(valid)
    xs = np.linspace(valid.min(), valid.max(), 200)
    ax1.plot(xs, kde(xs), color="darkblue", lw=1.5)
    ax1.axvline(np.median(valid), color="red", linestyle="--", lw=1, label=f"median {np.median(valid):.1f}s")
    ax1.set_xlabel("latency (s)"); ax1.set_ylabel("density")
    ax1.set_title(f"cheating latency (n={len(valid)})")
    ax1.legend()

    # right: ECDF with window markers
    sorted_x = np.sort(valid)
    ecdf = np.arange(1, len(sorted_x) + 1) / len(sorted_x)
    ax2.step(sorted_x, ecdf, where="post", color="darkblue")
    for w in windows:
        frac = (valid >= w).mean()
        ax2.axvline(w, linestyle="--", color="gray", alpha=0.6)
        ax2.annotate(f"{w}s\n{frac*100:.0f}% covered",
                     xy=(w, 1 - frac), xytext=(w + 2, 1 - frac),
                     fontsize=9, color="darkred")
    ax2.set_xlabel("latency (s)"); ax2.set_ylabel("ECDF")
    ax2.set_title("coverage of pre-cheating windows")
    ax2.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# --- Task 2: temporal features ------------------------------------------------

FNAME_RE = re.compile(r"ID(\d+)__([A-Za-z0-9_]+?)_inst\d+_blendshapes\.csv$")

# discover blendshape list from first file
def discover_blendshapes():
    sample = next(BS_DIR.glob("*_blendshapes.csv"))
    cols = pd.read_csv(sample, nrows=1).columns.tolist()
    return [c for c in cols if c not in ("Frame_Index", "Timestamp", "Face_ID")]


def extract_window_features(bs_df, window_s, blendshapes):
    """Return dict of {feature_name: value} for the first window_s seconds."""
    t0 = bs_df["Timestamp"].iloc[0]
    sub = bs_df[bs_df["Timestamp"] - t0 <= window_s]
    if len(sub) < 2:
        return None

    t = sub["Timestamp"].values - t0
    out = {}
    for bs in blendshapes:
        y = sub[bs].values.astype(float)
        out[f"{bs}_mean"] = float(np.mean(y))
        out[f"{bs}_std"] = float(np.std(y))
        # slope via scipy linregress
        if np.std(y) == 0 or len(t) < 3:
            out[f"{bs}__slope"] = 0.0
        else:
            out[f"{bs}__slope"] = float(stats.linregress(t, y).slope)
    return out


def extract_all_features(windows, blendshapes, cheater_label):
    files = sorted(BS_DIR.glob("*_blendshapes.csv"))
    wt_rows, slope_rows, skip_rows = [], [], []

    for fp in tqdm(files, desc="extracting features", unit="file"):
        m = FNAME_RE.search(fp.name)
        if not m:
            continue
        pid = int(m.group(1))
        phase = m.group(2)
        cheated = int(cheater_label.get(pid, 0))

        try:
            df = pd.read_csv(fp, usecols=["Timestamp"] + blendshapes)
        except Exception as e:
            skip_rows.append({"phase": phase, "window_s": None, "ID": pid,
                              "reason": f"read_error: {type(e).__name__}"})
            continue

        if len(df) < 2:
            for w in windows:
                skip_rows.append({"phase": phase, "window_s": w, "ID": pid,
                                  "reason": "file_too_short"})
            continue

        duration = df["Timestamp"].iloc[-1] - df["Timestamp"].iloc[0]
        for w in windows:
            if duration < w:
                skip_rows.append({"phase": phase, "window_s": w, "ID": pid,
                                  "reason": f"phase_duration_{duration:.2f}s_lt_{w}s"})
                continue

            feats = extract_window_features(df, w, blendshapes)
            if feats is None:
                skip_rows.append({"phase": phase, "window_s": w, "ID": pid,
                                  "reason": "too_few_frames"})
                continue

            base = {"ID": pid, "cheated": cheated, "phase": phase, "window_s": w}

            # static features file
            wt_rows.append({**base, **{k: v for k, v in feats.items()
                                        if k.endswith("_mean") or k.endswith("_std")}})
            # slope-only file
            slope_rows.append({**base, **{k: v for k, v in feats.items() if k.endswith("__slope")}})

    return pd.DataFrame(wt_rows), pd.DataFrame(slope_rows), pd.DataFrame(skip_rows)


# --- sanity checks ------------------------------------------------------------

def sanity_checks(lat_df, wt_df, slope_df, blendshapes):
    msgs = []

    n = lat_df["latency_s"].notna().sum()
    if not 55 <= n <= 65:
        msgs.append(f"n_cheaters={n} outside expected 55-65")
    med = lat_df["latency_s"].median()
    if not 5 <= med <= 25:
        msgs.append(f"median latency={med:.2f}s outside expected 5-25s")

    # ID 103 T5_Epre 2s browDownLeft_mean should be 0.005745 (from original reference)
    target = wt_df[(wt_df["ID"] == 103) & (wt_df["phase"] == "T5_Epre") & (wt_df["window_s"] == 2)]
    if len(target):
        got = target["browDownLeft_mean"].iloc[0]
        if abs(got - 0.005745) > 1e-4:
            msgs.append(f"ID 103 T5_Epre 2s browDownLeft_mean={got:.6f}, expected 0.005745")
    else:
        msgs.append("ID 103 T5_Epre 2s not in feature matrix (expected for sanity check)")

    # no slope column entirely NaN
    slope_cols = [f"{bs}__slope" for bs in blendshapes]
    all_nan = [c for c in slope_cols if slope_df[c].isna().all()]
    if all_nan:
        msgs.append(f"slope columns all-NaN: {all_nan[:5]}{'...' if len(all_nan) > 5 else ''}")

    # each (phase, window) should have >= 30 rows
    counts = slope_df.groupby(["phase", "window_s"]).size()
    low = counts[counts < 30]
    if len(low):
        msgs.append(f"(phase, window) combos with <30 rows:\n{low.to_string()}")

    if msgs:
        print("\n[SANITY WARNINGS]")
        for m in msgs:
            print(f"  ! {m}")
    else:
        print("\n[SANITY] all checks passed")


# --- main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", nargs="+", type=int, default=[2, 5, 10])
    args = parser.parse_args()
    windows = sorted(set(args.windows))

    print("[Script 01] Starting...")
    print(f"  windows = {windows}")

    # Task 1
    print("[1/2] computing latency...")
    lat = compute_latency()
    summary = summarize_latency(lat)
    cov = window_coverage(lat, windows)
    lat.to_csv(TABLES / "latency_distribution.csv", index=False)
    summary.to_csv(TABLES / "latency_summary.csv", index=False)
    cov.to_csv(TABLES / "window_coverage.csv", index=False)
    plot_latency(lat, windows, FIGS / "latency_distribution.png")
    print(f"  n_cheaters={int(summary['n'].iloc[0])}  median={summary['median'].iloc[0]:.2f}s  "
          f"Q1={summary['Q1'].iloc[0]:.2f}  Q3={summary['Q3'].iloc[0]:.2f}")
    print("  window coverage:")
    for _, r in cov.iterrows():
        print(f"    {int(r['window_s'])}s: {int(r['n_covered'])}/{int(r['n_total_cheaters'])} "
              f"({r['coverage_rate']*100:.0f}%)")

    # Task 2
    print("[2/2] extracting temporal features...")
    cheater_label = pd.read_csv(BEHAVIOR_CSV).groupby("ID")["Cheated or not"].first().astype(int).to_dict()
    blendshapes = discover_blendshapes()
    print(f"  {len(blendshapes)} blendshapes x {len(windows)} windows")

    wt, sl, skip = extract_all_features(windows, blendshapes, cheater_label)
    wt.to_csv(PROC / "temporal_window_tests.csv", index=False)
    sl.to_csv(PROC / "temporal_slopes.csv", index=False)
    skip.to_csv(PROC / "coverage_report.csv", index=False)
    print(f"  temporal_window_tests.csv: {wt.shape}")
    print(f"  temporal_slopes.csv:       {sl.shape}")
    print(f"  coverage_report.csv:       {skip.shape}  (skipped combos)")

    # sanity
    sanity_checks(lat, wt, sl, blendshapes)

    print("\n[DONE] Outputs:")
    for p in [TABLES / "latency_distribution.csv",
              TABLES / "latency_summary.csv",
              TABLES / "window_coverage.csv",
              FIGS / "latency_distribution.png",
              PROC / "temporal_window_tests.csv",
              PROC / "temporal_slopes.csv",
              PROC / "coverage_report.csv"]:
        print(f"  {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
