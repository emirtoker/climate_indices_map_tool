#!/usr/bin/env python3
"""
rebuild_stats.py

Rebuild data/indices/stats.json from all existing .tif files in
data/indices/{historical,future/ssp*}/.

When does this matter?
----------------------
nc_to_tif.py overwrites stats.json on every run. If you used
`--skip-existing` (or `--limit N`), stats.json will only contain the
files that were re-converted in that run, not all of them. This script
restores the full stats.json by reading every .tif on disk.

USAGE
-----
    python utils/rebuild_stats.py
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Hard-coded path (matches nc_to_tif.py)
# ---------------------------------------------------------------------------

INDICES_ROOT = Path(
    "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/"
    "Script/Python/climate_indices_map_tool/data/indices"
)


def compute_stats(arr) -> dict:
    """Same rounding as nc_to_tif.py (nearest 0.5 step, NaN-excluded)."""
    import numpy as np

    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return {"min": None, "max": None, "mean": None,
                "median": None, "q25": None, "q75": None}

    def r(x: float) -> float:
        return round(x * 2) / 2

    return {
        "min":    r(float(valid.min())),
        "max":    r(float(valid.max())),
        "mean":   r(float(valid.mean())),
        "median": r(float(np.median(valid))),
        "q25":    r(float(np.quantile(valid, 0.25))),
        "q75":    r(float(np.quantile(valid, 0.75))),
    }


def main():
    import rasterio

    if not INDICES_ROOT.exists():
        print(f"ERROR: indices root does not exist: {INDICES_ROOT}",
              file=sys.stderr)
        sys.exit(1)

    all_tifs = sorted(INDICES_ROOT.rglob("*.tif"))
    if not all_tifs:
        print(f"ERROR: no .tif files found under {INDICES_ROOT}",
              file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(all_tifs)} .tif files under {INDICES_ROOT}")
    print("Computing stats from full-resolution arrays...")
    print()

    stats: dict = {}
    t0 = time.time()
    errors = 0

    for i, tif in enumerate(all_tifs, 1):
        try:
            with rasterio.open(tif) as src:
                arr = src.read(1, masked=True).filled(float("nan"))
            stats[tif.name] = compute_stats(arr)
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {tif.name}: {e!r}")
            continue

        if i % 50 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(all_tifs) - i) / rate if rate > 0 else 0
            print(f"  [{i:4d}/{len(all_tifs)}]  {rate:.1f} files/s, ETA {eta:.0f}s")

    out_path = INDICES_ROOT / "stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"Done in {time.time() - t0:.1f}s")
    print(f"Wrote {len(stats)} entries to {out_path}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()