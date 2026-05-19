#!/usr/bin/env python3
"""
inventory_netcdfs.py

Climate Indices Map Tool — NetCDF Inventory Script
====================================================

Scans a directory tree of NetCDF (.nc) climate-index files, reads each file's
attributes, and produces a single CSV report so we can review the metadata
landscape BEFORE writing the NetCDF -> COG converter.

USAGE
-----
    python inventory_netcdfs.py \
        --root "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Data/Climate_Indices/regional/TR" \
        --out  "inventory_TR.csv"

Optional flags:
    --skip-stats       : do NOT compute min/max/mean from data (much faster).
                         By default we only READ stat_* attributes if present;
                         we do not recompute from the array unless explicitly
                         requested with --compute-stats.
    --compute-stats    : if stat_* attributes are missing, compute from data.
                         Slower (loads each array) but fills the gap.
    --verbose          : print per-file progress
    --include-pct      : include _pct files (default: excluded, per user note)

OUTPUT
------
A CSV with one row per .nc file. Columns:

  File / location:
    path, filename, rel_path, file_size_mb

  From filename parsing:
    kind            -> "historical" | "future"
    source          -> "CHELSA" | "CHELSA_sum_Ensemble_GCMs" | ...
    scenario        -> "" (historical) | "ssp126" | "ssp245" | "ssp585"
    period          -> "1995-2014" | "2041-2060" | "2081-2100"
    ref_period      -> "" (historical) | "1995-2014" (future)
    indice_code_fname  -> "FD", "PCD", "DI", ... (from filename)
    long_token_fname   -> "frost_days", "passive_comfort_days", ...
    is_threshold_variant -> True if filename has _gt##_/_lt##_/_ltm##_ suffix
    threshold_suffix     -> e.g. "gt32_hot_days", "ltm13_cold_days"
    is_pct_variant       -> True if filename ends with _pct

  From NetCDF dataset-level attributes:
    title, institution, project, source_attr, spatial_resolution,
    period_attr, mask, history_ds, geospatial_bounds

  From data variable attributes:
    variable_name, units, standard_name, long_name, description,
    approach, used_variables, freq, cell_methods, history_var

  Pre-computed stats (from variable attributes, NOT from re-computing):
    stat_min, stat_max, stat_mean, stat_median, stat_q25, stat_q75

  Computed (only if --compute-stats and stat_* attributes missing):
    computed_min, computed_max, computed_mean, computed_nan_pct

  Shape & coords:
    shape, dims, has_time_dim, has_band_dim, crs_wkt_present

  Sanity flags (red flags to inspect):
    flag_no_attrs, flag_no_units, flag_no_description, flag_no_long_name,
    flag_no_stats, flag_indice_mismatch, flag_unit_unusual

"""

from __future__ import annotations
import argparse
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

# Patterns we expect:
#
# Historical:
#   CHELSA_TR_clim_1995_2014_FD_frost_days.nc
#   CHELSA_TR_clim_1995_2014_TR_tropical_nights.nc
#   CHELSA_TR_clim_2000_2006_DI_discomfort_index.nc
#   CHELSA_TR_clim_2000_2006_THI_C_temperature_humidity_index_crop.nc
#   CHELSA_TR_clim_2000_2006_PET_..._gt29_hot_days.nc
#
# Future (sum_CHELSA_GCMs):
#   CHELSA_TR_clim_1995_2014_sum_Ensemble_GCMs_ssp245_2041_2060_FD_frost_days.nc
#   CHELSA_TR_clim_1995_2014_sum_Ensemble_GCMs_ssp585_2081_2100_AI_aridity_index_pct.nc
#   CHELSA_TR_clim_1995_2014_sum_Ensemble_GCMs_ssp126_2081_2100_THI_C_temperature_humidity_index_crop_gt60_hot_days.nc

# Known indice codes (from the project report). Multi-letter codes go FIRST
# so that e.g. "TR_EXT" is matched before "TR". This is a *known set* —
# the script will also report any token that is uppercase + isolated but not
# in this set, so we discover unknowns.
KNOWN_INDICE_CODES = {
    # Multi-token / suffixed codes (must be tested first — longest match wins)
    "TR_EXT", "CDD_A", "CDD_P", "THI_C", "THI_H", "THI_L",
    # Standard codes
    "FD", "ID", "SU", "TR", "TXX", "TNN", "TNX", "TXN",
    "HW", "CW", "WSDI", "CSDI",
    "PRCPTOT", "RX1DAY", "RX5DAY", "SDII", "R10MM", "R20MM", "R95P", "R99P",
    "CWD",
    "HD", "HDD", "CD", "CDD", "GD", "GDD", "GSL", "PCD", "DTR",
    "PNP", "SPI12", "SPEI12", "AI",
    "PET", "UTCI", "PMV", "SET", "DI", "WBGT", "WCI", "HI", "ET", "HMX", "TS",
    "OPT", "TOP", "MRT", "VD",
    "AT", "ESI", "PPD", "THI",
}

# Sort by length DESC so e.g. "PRCPTOT" matches before "PR" hypothetically
_INDICE_CODES_SORTED = sorted(KNOWN_INDICE_CODES, key=len, reverse=True)

# Threshold-variant suffix patterns
THRESHOLD_SUFFIX_RE = re.compile(
    r"_(gt\d+|lt\d+|ltm\d+)_([a-z_]+_days)$",
    re.IGNORECASE,
)

# _pct suffix
PCT_SUFFIX_RE = re.compile(r"_pct$", re.IGNORECASE)


def parse_filename(filename: str) -> Dict[str, Any]:
    """
    Parse a .nc filename to extract kind/source/scenario/period/indice etc.

    Returns a dict with everything we could figure out from the name alone.
    Robust to unexpected formats — fields default to "" if we can't tell.
    """
    out: Dict[str, Any] = {
        "kind": "",
        "source": "",
        "scenario": "",
        "period": "",
        "ref_period": "",
        "indice_code_fname": "",
        "long_token_fname": "",
        "is_threshold_variant": False,
        "threshold_suffix": "",
        "is_pct_variant": False,
    }

    name = filename.replace(".nc", "")

    # 1. _pct check
    if PCT_SUFFIX_RE.search(name):
        out["is_pct_variant"] = True
        name = PCT_SUFFIX_RE.sub("", name)

    # 2. Threshold suffix check (e.g. "_gt32_hot_days", "_ltm13_cold_days")
    m = THRESHOLD_SUFFIX_RE.search(name)
    if m:
        out["is_threshold_variant"] = True
        out["threshold_suffix"] = m.group(0).lstrip("_")
        # Strip the suffix so we can extract the underlying indice code
        name_for_indice = name[: m.start()]
    else:
        name_for_indice = name

    # 3. kind / scenario
    if "sum_Ensemble_GCMs_ssp" in name or "ssp" in name.lower():
        out["kind"] = "future"
        m_ssp = re.search(r"(ssp\d{3})", name, re.IGNORECASE)
        if m_ssp:
            out["scenario"] = m_ssp.group(1).lower()
    else:
        out["kind"] = "historical"

    # 4. source
    if "sum_Ensemble_GCMs" in name:
        out["source"] = "CHELSA_sum_Ensemble_GCMs"
    elif name.startswith("CHELSA"):
        out["source"] = "CHELSA"
    else:
        out["source"] = "UNKNOWN"

    # 5. Period & ref_period
    # Historical: CHELSA_TR_clim_<startY>_<endY>_<INDICE>_<longname>
    # Future:     CHELSA_TR_clim_<refS>_<refE>_sum_Ensemble_GCMs_ssp###_<futS>_<futE>_<INDICE>_<longname>
    if out["kind"] == "future":
        # ref period = first _####_####_ after "_clim_"
        m_periods = re.findall(r"(\d{4})_(\d{4})", name)
        if len(m_periods) >= 2:
            out["ref_period"] = f"{m_periods[0][0]}-{m_periods[0][1]}"
            out["period"] = f"{m_periods[1][0]}-{m_periods[1][1]}"
    else:
        m_p = re.search(r"_clim_(\d{4})_(\d{4})_", name)
        if m_p:
            out["period"] = f"{m_p.group(1)}-{m_p.group(2)}"

    # 6. Indice code — look for the longest known code that appears
    #    as a "_CODE_" boundary in the name_for_indice string.
    found_code = ""
    found_long_token = ""
    for code in _INDICE_CODES_SORTED:
        # Build a regex like "_CODE_" — must have underscores on both sides
        pattern = rf"_{re.escape(code)}_"
        m_code = re.search(pattern, name_for_indice)
        if m_code:
            found_code = code
            # Everything after this code is the long_token
            after = name_for_indice[m_code.end():]
            found_long_token = after
            break

    if not found_code:
        # Fallback: try positional — split by underscore, look for an uppercase
        # token that's NOT in our future-marker tokens
        skip_tokens = {
            "CHELSA", "TR", "CLIM", "SUM", "ENSEMBLE", "GCMS",
            "SSP126", "SSP245", "SSP585",
        }
        parts = name_for_indice.split("_")
        for i, tok in enumerate(parts):
            if (
                tok.isupper()
                and tok not in skip_tokens
                and not tok.isdigit()
                and len(tok) >= 2
            ):
                found_code = tok
                found_long_token = "_".join(parts[i + 1:])
                break

    out["indice_code_fname"] = found_code
    out["long_token_fname"] = found_long_token

    return out


# ---------------------------------------------------------------------------
# NetCDF reading
# ---------------------------------------------------------------------------

def read_netcdf_metadata(
    path: Path,
    compute_stats_if_missing: bool = False,
) -> Dict[str, Any]:
    """
    Open a NetCDF file with xarray and pull out everything useful for the
    inventory. Returns a dict; non-fatal errors become empty fields.
    """
    import xarray as xr  # imported here so the script can be parsed even
    import numpy as np   # if xarray isn't installed yet at script-load time

    out: Dict[str, Any] = {
        # Dataset-level
        "title": "",
        "institution": "",
        "project": "",
        "source_attr": "",
        "spatial_resolution": "",
        "period_attr": "",
        "mask": "",
        "history_ds": "",
        "geospatial_bounds": "",
        # Variable-level
        "variable_name": "",
        "units": "",
        "standard_name": "",
        "long_name": "",
        "description": "",
        "approach": "",
        "used_variables": "",
        "freq": "",
        "cell_methods": "",
        "history_var": "",
        # Pre-computed stats
        "stat_min": "",
        "stat_max": "",
        "stat_mean": "",
        "stat_median": "",
        "stat_q25": "",
        "stat_q75": "",
        # Computed (only if requested + missing)
        "computed_min": "",
        "computed_max": "",
        "computed_mean": "",
        "computed_nan_pct": "",
        # Shape & coords
        "shape": "",
        "dims": "",
        "has_time_dim": False,
        "has_band_dim": False,
        "crs_wkt_present": False,
        # Read errors
        "read_error": "",
    }

    try:
        ds = xr.open_dataset(path, decode_coords="all")
    except Exception as e:
        out["read_error"] = f"open_failed: {e!r}"
        return out

    try:
        # ---- Dataset-level attrs ----
        ds_attrs = ds.attrs or {}
        out["title"] = str(ds_attrs.get("title", ""))
        out["institution"] = str(ds_attrs.get("institution", ""))
        out["project"] = str(ds_attrs.get("project", ""))
        out["source_attr"] = str(ds_attrs.get("source", ""))
        out["spatial_resolution"] = str(ds_attrs.get("spatial_resolution", ""))
        out["period_attr"] = str(ds_attrs.get("period", ""))
        out["mask"] = str(ds_attrs.get("mask", ""))
        out["history_ds"] = str(ds_attrs.get("history", ""))
        out["geospatial_bounds"] = str(ds_attrs.get("geospatial_bounds", ""))

        # ---- Identify the main data variable ----
        # Skip coordinate-like / grid-mapping variables
        skip_vars = {"spatial_ref", "crs", "lon", "lat", "longitude", "latitude",
                     "time", "time_bnds", "x", "y"}
        data_vars = [v for v in ds.data_vars if v not in skip_vars]

        if not data_vars:
            out["read_error"] = "no_data_variable_found"
            ds.close()
            return out

        var_name = data_vars[0]
        var = ds[var_name]
        out["variable_name"] = var_name

        # ---- Variable-level attrs ----
        v_attrs = var.attrs or {}
        out["units"] = str(v_attrs.get("units", ""))
        out["standard_name"] = str(v_attrs.get("standard_name", ""))
        out["long_name"] = str(v_attrs.get("long_name", ""))
        out["description"] = str(v_attrs.get("description", ""))
        out["approach"] = str(v_attrs.get("approach", ""))
        out["used_variables"] = str(v_attrs.get("used_variables", ""))
        out["freq"] = str(v_attrs.get("freq", ""))
        out["cell_methods"] = str(v_attrs.get("cell_methods", ""))
        out["history_var"] = str(v_attrs.get("history", ""))

        # ---- Stat attrs ----
        def _fmt(x):
            try:
                return float(x)
            except Exception:
                return ""

        out["stat_min"] = _fmt(v_attrs.get("stat_min", ""))
        out["stat_max"] = _fmt(v_attrs.get("stat_max", ""))
        out["stat_mean"] = _fmt(v_attrs.get("stat_mean", ""))
        out["stat_median"] = _fmt(v_attrs.get("stat_median", ""))
        out["stat_q25"] = _fmt(v_attrs.get("stat_q25", ""))
        out["stat_q75"] = _fmt(v_attrs.get("stat_q75", ""))

        # ---- Shape & coords ----
        out["shape"] = str(tuple(var.shape))
        out["dims"] = str(tuple(var.dims))
        out["has_time_dim"] = "time" in var.dims
        out["has_band_dim"] = "band" in var.dims
        out["crs_wkt_present"] = "spatial_ref" in ds.variables

        # ---- Optional: compute stats from data if missing ----
        if compute_stats_if_missing and out["stat_min"] == "":
            arr = var.values
            valid = arr[~np.isnan(arr)]
            if valid.size > 0:
                out["computed_min"] = float(valid.min())
                out["computed_max"] = float(valid.max())
                out["computed_mean"] = float(valid.mean())
                out["computed_nan_pct"] = float(
                    100.0 * (arr.size - valid.size) / arr.size
                )

    except Exception as e:
        out["read_error"] = f"parse_failed: {e!r}\n{traceback.format_exc()}"
    finally:
        try:
            ds.close()
        except Exception:
            pass

    return out


# ---------------------------------------------------------------------------
# Sanity flags — quick visual cues in the CSV for what needs attention
# ---------------------------------------------------------------------------

# Acceptable unit patterns (just for sanity checking; we'll see what shows up)
ACCEPTABLE_UNIT_FRAGMENTS = [
    "day", "mm", "kelvin", "celsius", "degc", "degree", "k",
    "percent", "%", "dimensionless", "1", "pa", "ratio", "index",
    "m/s", "ms-1", "mm/day", "mm/year", "kg",
]


def compute_flags(record: Dict[str, Any]) -> Dict[str, Any]:
    flags: Dict[str, Any] = {}

    # No attrs whatsoever
    flags["flag_no_attrs"] = not any([
        record.get("title"), record.get("long_name"), record.get("units"),
    ])
    flags["flag_no_units"] = not record.get("units")
    flags["flag_no_description"] = not record.get("description")
    flags["flag_no_long_name"] = not record.get("long_name")
    flags["flag_no_stats"] = record.get("stat_min", "") == ""

    # Indice code consistency: filename code vs variable name
    fname_code = (record.get("indice_code_fname") or "").lower()
    var_name = (record.get("variable_name") or "").lower()
    # Strip trailing _ext, _a, _p, _c, _h, _l (sub-suffixes in our naming)
    fname_code_norm = re.sub(r"_(ext|a|p|c|h|l)$", "", fname_code)
    flags["flag_indice_mismatch"] = bool(
        fname_code and var_name
        and fname_code_norm != var_name
        and fname_code != var_name
    )

    # Unit "unusual"
    unit = (record.get("units") or "").lower()
    if unit:
        flags["flag_unit_unusual"] = not any(
            frag in unit for frag in ACCEPTABLE_UNIT_FRAGMENTS
        )
    else:
        flags["flag_unit_unusual"] = False  # empty unit already flagged elsewhere

    return flags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Inventory NetCDF climate index files into a CSV."
    )
    ap.add_argument("--root", required=True, type=Path,
                    help="Root directory to scan recursively for .nc files.")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output CSV path.")
    ap.add_argument("--compute-stats", action="store_true",
                    help="If a file has no stat_* attributes, compute from data."
                         " Slower (loads each array).")
    ap.add_argument("--include-pct", action="store_true",
                    help="Include _pct files (default: excluded).")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="Print per-file progress.")
    args = ap.parse_args()

    root: Path = args.root.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    # Late import so the script's help text works even without these installed
    try:
        import pandas as pd
        import xarray as xr  # noqa: F401  (used inside read_netcdf_metadata)
    except ImportError as e:
        print(f"ERROR: missing dependency ({e}). Install with:", file=sys.stderr)
        print("  pip install pandas xarray netcdf4", file=sys.stderr)
        sys.exit(1)

    # Collect .nc files
    nc_files = sorted(root.rglob("*.nc"))
    if not args.include_pct:
        nc_files = [p for p in nc_files if not PCT_SUFFIX_RE.search(p.stem)]

    if not nc_files:
        print(f"No .nc files found under {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(nc_files)} .nc files under {root}")
    if args.compute_stats:
        print("  (will compute stats from data if attrs missing — slower)")

    records: List[Dict[str, Any]] = []
    n_errors = 0

    for i, path in enumerate(nc_files, 1):
        rel = path.relative_to(root)
        record: Dict[str, Any] = {
            "path": str(path),
            "filename": path.name,
            "rel_path": str(rel),
            "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        }

        # Parse filename
        record.update(parse_filename(path.name))

        # Read NetCDF
        meta = read_netcdf_metadata(
            path,
            compute_stats_if_missing=args.compute_stats,
        )
        record.update(meta)

        # Sanity flags
        record.update(compute_flags(record))

        if meta.get("read_error"):
            n_errors += 1
            if args.verbose:
                print(f"  [ERROR] {rel}: {meta['read_error']}")
        elif args.verbose:
            print(f"  [{i:3d}/{len(nc_files)}] {rel}")

        records.append(record)

    # Build DataFrame & write CSV
    df = pd.DataFrame(records)

    # Reorder columns for readability
    preferred_order = [
        # Location
        "rel_path", "filename", "file_size_mb", "path",
        # From filename
        "kind", "source", "scenario", "period", "ref_period",
        "indice_code_fname", "long_token_fname",
        "is_threshold_variant", "threshold_suffix", "is_pct_variant",
        # Identity from NC
        "variable_name", "title", "long_name", "standard_name",
        "units", "description",
        # Computation provenance
        "approach", "used_variables", "freq", "cell_methods",
        # Stats
        "stat_min", "stat_max", "stat_mean",
        "stat_median", "stat_q25", "stat_q75",
        "computed_min", "computed_max", "computed_mean", "computed_nan_pct",
        # Geo / shape
        "shape", "dims", "has_time_dim", "has_band_dim", "crs_wkt_present",
        # Dataset-level
        "institution", "project", "source_attr", "spatial_resolution",
        "period_attr", "geospatial_bounds", "mask", "history_ds", "history_var",
        # Flags
        "flag_no_attrs", "flag_no_units", "flag_no_description",
        "flag_no_long_name", "flag_no_stats",
        "flag_indice_mismatch", "flag_unit_unusual",
        # Errors
        "read_error",
    ]
    cols = [c for c in preferred_order if c in df.columns] + \
           [c for c in df.columns if c not in preferred_order]
    df = df[cols]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")

    # Quick on-screen summary
    print("\n" + "=" * 70)
    print(f"INVENTORY COMPLETE")
    print("=" * 70)
    print(f"Output CSV    : {args.out}")
    print(f"Total files   : {len(df)}")
    print(f"Read errors   : {n_errors}")
    print(f"Historical    : {(df['kind'] == 'historical').sum()}")
    print(f"Future        : {(df['kind'] == 'future').sum()}")
    if "scenario" in df.columns:
        for s in sorted(df["scenario"].dropna().unique()):
            if s:
                print(f"  scenario {s}: {(df['scenario'] == s).sum()}")
    print(f"Threshold variants: {df['is_threshold_variant'].sum()}")
    print(f"Pct variants      : {df['is_pct_variant'].sum()}"
          f" (excluded by default — use --include-pct to include)")
    print()
    print("RED-FLAG TALLY (rows you should look at first in the CSV):")
    for col in [
        "flag_no_attrs", "flag_no_units", "flag_no_description",
        "flag_no_long_name", "flag_no_stats",
        "flag_indice_mismatch", "flag_unit_unusual",
    ]:
        if col in df.columns:
            n = int(df[col].sum())
            if n > 0:
                print(f"  {col:30s} : {n}")
    print()

    # Unique indice codes discovered
    print("INDICE CODES DISCOVERED (from filenames):")
    codes = sorted(df["indice_code_fname"].dropna().unique())
    print(f"  {len(codes)} unique codes: {', '.join(codes)}")
    print()

    # Indice codes that did not match KNOWN_INDICE_CODES
    unknown = [c for c in codes if c and c not in KNOWN_INDICE_CODES]
    if unknown:
        print(f"  >>> UNKNOWN codes (not in KNOWN_INDICE_CODES set): {unknown}")
    else:
        print("  >>> All discovered codes are in the KNOWN_INDICE_CODES set.")
    print()


if __name__ == "__main__":
    main()