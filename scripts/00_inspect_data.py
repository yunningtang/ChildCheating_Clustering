"""
Data inventory: probes CSV columns, blendshape filenames, Timestamp unit/FPS.
Inputs:  output n120_UPDATE2.csv, mediapipe_segmentsoutput/blendshapes/
Outputs: data/processed/data_inventory.json + stdout summary
Run:     python scripts/00_inspect_data.py
"""
import json
import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_CSV = ROOT / "output n120_UPDATE2.csv"
BLENDSHAPES_DIR = ROOT / "mediapipe_segmentsoutput" / "blendshapes"
OUT = ROOT / "data" / "processed" / "data_inventory.json"


def inspect_behavior_csv():
    df = pd.read_csv(BEHAVIOR_CSV)
    cheater_cols = [c for c in df.columns if "cheat" in c.lower()]
    time_cols = [c for c in df.columns if any(k in c.lower() for k in ("time", "start", "stop", "leave", "return"))]
    info = {
        "path": str(BEHAVIOR_CSV),
        "row_count": len(df),
        "unique_ids": int(df["ID"].nunique()) if "ID" in df.columns else None,
        "columns": list(df.columns),
        "cheater_col_candidates": cheater_cols,
        "time_col_candidates": time_cols,
        "na_per_column": {c: int(df[c].isna().sum()) for c in df.columns},
        "first_rows": df.head(3).to_dict(orient="records"),
    }

    print("=== output n120_UPDATE2.csv ===")
    print(f"  rows: {info['row_count']}  unique IDs: {info['unique_ids']}")
    print(f"  columns ({len(info['columns'])}): {info['columns']}")
    print(f"  cheater candidates: {cheater_cols}")
    print(f"  time/event candidates: {time_cols}")
    nonzero_na = {k: v for k, v in info["na_per_column"].items() if v > 0}
    if nonzero_na:
        print(f"  columns with NaN: {nonzero_na}")
    print()
    return info, df


def inspect_blendshape_folder():
    files = sorted(BLENDSHAPES_DIR.glob("*.csv"))
    info = {"path": str(BLENDSHAPES_DIR), "file_count": len(files)}
    if not files:
        print("=== blendshapes/ === EMPTY")
        return info, None

    info["sample_filenames"] = [f.name for f in files[:5]]

    # guess naming scheme from one filename
    # observed earlier: P004_crop__ID4__T1_pre_inst1_blendshapes.csv
    phase_tokens = set()
    id_tokens = set()
    pat = re.compile(r"ID(\d+)__([A-Za-z0-9_]+?)_inst\d+_blendshapes\.csv$")
    for f in files:
        m = pat.search(f.name)
        if m:
            id_tokens.add(int(m.group(1)))
            phase_tokens.add(m.group(2))
    info["inferred_pattern"] = r"P\d+_crop__ID(\d+)__(<phase>)_inst\d+_blendshapes.csv"
    info["unique_ids_in_folder"] = len(id_tokens)
    info["detected_phases"] = sorted(phase_tokens)

    print("=== blendshapes/ ===")
    print(f"  file count: {info['file_count']}")
    print(f"  sample names: {info['sample_filenames']}")
    print(f"  inferred pattern: {info['inferred_pattern']}")
    print(f"  unique IDs: {info['unique_ids_in_folder']}")
    print(f"  detected phases ({len(phase_tokens)}): {sorted(phase_tokens)}")
    print()

    # pick a sample with enough rows for FPS inference (prefer T5_alone or T5_Epre)
    preferred = [f for f in files if "T5_alone" in f.name or "T5_Epre" in f.name]
    sample_file = None
    for f in preferred + files:
        try:
            nrows = sum(1 for _ in open(f, "r", encoding="utf-8")) - 1
        except Exception:
            continue
        if nrows >= 30:
            sample_file = f
            break
    if sample_file is None:
        sample_file = files[0]
    return info, sample_file


def inspect_sample_blendshape_csv(sample_file):
    df = pd.read_csv(sample_file)
    info = {
        "path": str(sample_file),
        "columns": list(df.columns),
        "row_count": len(df),
    }

    ts = df["Timestamp"] if "Timestamp" in df.columns else None
    if ts is not None:
        tmin, tmax = float(ts.min()), float(ts.max())
        info["timestamp_min"] = tmin
        info["timestamp_max"] = tmax
        # unit inference from magnitude: frames in ms will be >= 1000
        info["timestamp_unit_inferred"] = "ms" if tmax > 1000 else "s"
        if len(ts) >= 3:
            diffs = np.diff(ts.values)
            median_dt = float(np.median(diffs))
            info["median_row_dt"] = median_dt
            if info["timestamp_unit_inferred"] == "s":
                info["inferred_fps"] = round(1.0 / median_dt, 2) if median_dt > 0 else None
            else:
                info["inferred_fps"] = round(1000.0 / median_dt, 2) if median_dt > 0 else None

    blendshape_cols = [c for c in df.columns if c not in ("Frame_Index", "Timestamp", "Face_ID")]
    info["blendshape_count"] = len(blendshape_cols)
    info["blendshape_samples"] = blendshape_cols[:8]

    print(f"=== sample CSV: {sample_file.name} ===")
    print(f"  columns ({len(info['columns'])}): first 6 = {info['columns'][:6]}")
    print(f"  blendshape count: {info['blendshape_count']}  (e.g. {blendshape_cols[:5]})")
    print(f"  rows: {info['row_count']}")
    if ts is not None:
        print(f"  Timestamp range: [{info['timestamp_min']:.3f}, {info['timestamp_max']:.3f}]  unit: {info['timestamp_unit_inferred']}")
        if "inferred_fps" in info and info["inferred_fps"]:
            print(f"  inferred FPS: {info['inferred_fps']}")
    print()
    return info


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    inventory = {}

    print("[Script 00] Starting inspection...\n")

    if BEHAVIOR_CSV.exists():
        bhv, _ = inspect_behavior_csv()
        inventory["behavior_csv"] = bhv
    else:
        print(f"MISSING: {BEHAVIOR_CSV}")
        inventory["behavior_csv"] = None

    if BLENDSHAPES_DIR.exists():
        folder, sample = inspect_blendshape_folder()
        inventory["blendshapes_folder"] = folder
        if sample is not None:
            inventory["blendshapes_sample"] = inspect_sample_blendshape_csv(sample)
    else:
        print(f"MISSING: {BLENDSHAPES_DIR}")
        inventory["blendshapes_folder"] = None

    # JSON-safe: coerce numpy / pandas bits
    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_clean(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o) if not np.isnan(o) else None
        if isinstance(o, float) and np.isnan(o):
            return None
        return o

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(_clean(inventory), f, indent=2, ensure_ascii=False, default=str)

    print(f"[DONE] Inventory written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
