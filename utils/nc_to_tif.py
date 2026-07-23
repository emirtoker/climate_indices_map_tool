#!/usr/bin/env python3
"""
nc_to_tif.py - v3

Climate Indices Map Tool - NetCDF to Cloud-Optimized GeoTIFF Converter
=======================================================================

v3 change
---------
COG output is now written in EPSG:3857 (Web Mercator) instead of
EPSG:4326. This matches the basemap (OSM tiles, LCZ raster, Web Mercator
viewers like Folium/Leaflet) so the rendered raster aligns perfectly with
the Türkiye shapefile and OSM background. The previous 4326 output was
metrically correct but visually skewed northward when laid over a Mercator
basemap.

The source NetCDFs are unchanged (they stay in 4326). Reprojection happens
on-the-fly inside this converter using rioxarray. The COG's internal CRS
attribute is set to EPSG:3857; map_engine reads it and overlays with the
correct bounds.

Notes
-----
- Folium ImageOverlay expects bounds in [[bottom_lat, left_lon], [top_lat,
  right_lon]] (4326 lat/lon). map_engine still derives those by calling
  transform_bounds("EPSG:4326") on the raster, which works regardless of
  the raster's internal CRS.
- Pixel size after reprojection is approximately the same effective
  resolution (~1km near 38°N latitude), but the array shape will differ
  slightly from the input.

Earlier fixes preserved
-----------------------
- v2 latitude flip (south->north -> north->south) is no longer strictly
  needed after reprojection (reproject normalizes orientation), but kept
  defensively so re-running on already-3857 inputs still works.

Pipeline overview
-----------------
For each .nc file:
  1. Parse filename -> kind, scenario, period, indice_code
  2. Look up indice in INDICES_CATALOG (skip if not found)
  3. Open NetCDF, extract main data variable, drop time/band/percentiles
  4. Write CRS=EPSG:4326 (NetCDF's native CRS)
  5. *** Reproject to EPSG:3857 (Web Mercator) ***
  6. Compute statistics (min, max, mean, median, q25, q75)
  7. Write tiled GeoTIFF in 3857, wipe NetCDF tags, apply catalog tags
  8. Translate to COG with overviews
  9. Place in canonical output layout

Usage
-----
    python utils/nc_to_tif.py
    python utils/nc_to_tif.py --dry-run
    python utils/nc_to_tif.py --limit 5
    python utils/nc_to_tif.py --skip-existing
    python utils/nc_to_tif.py --verbose
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Make utils package importable when running directly
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from utils.indices_catalog import INDICES_CATALOG
except ImportError:
    try:
        from indices_catalog import INDICES_CATALOG
    except ImportError:
        print(
            "ERROR: cannot import indices_catalog. Place this script next to "
            "indices_catalog.py inside utils/.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Hard-coded paths
# ---------------------------------------------------------------------------

INPUT_ROOT = Path(
    "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/"
    "Data/Climate_Indices/regional/TR"
)

OUTPUT_ROOT = Path(
    "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/"
    "Script/Python/climate_indices_map_tool/data/indices"
)

# Output projection (Web Mercator, same as OSM tiles and LCZ)
OUTPUT_CRS = "EPSG:3857"

# ---- TR sinir maskesi (deniz/tasma temizligi) --------------------------
# reproject'ten sonra bu shapefile ile clip edilir; disi NaN olur.
# Yol app veri klasorune gore; degisirse burayi guncelle.
TR_SHP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "shapefiles", "tur_adm_2025_ab_shp", "tur_admbnda_adm0_2025.shp",
)
_TR_GEOM_3857 = None  # lazy: ilk kullanimda 3857'ye yeniden projekte edilip tutulur


def _get_tr_geom_3857():
    """TR ADM0 geometrisini EPSG:3857'de (OUTPUT_CRS) bir kez yukle ve onbellekle."""
    global _TR_GEOM_3857
    if _TR_GEOM_3857 is None:
        import geopandas as gpd
        if not os.path.isfile(TR_SHP_PATH):
            raise FileNotFoundError(
                f"TR shapefile bulunamadi: {TR_SHP_PATH}\n"
                f"  -> TR_SHP_PATH'i dogru .shp'ye ayarla."
            )
        gdf = gpd.read_file(TR_SHP_PATH)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        _TR_GEOM_3857 = gdf.to_crs(OUTPUT_CRS)
    return _TR_GEOM_3857


# ---------------------------------------------------------------------------
# Filename parser
# ---------------------------------------------------------------------------

PCT_SUFFIX_RE = re.compile(r"_pct$", re.IGNORECASE)
THRESHOLD_SUFFIX_RE = re.compile(
    r"_(gt\d+|lt\d+|ltm\d+|bw\d+_\d+)_([a-z_]+_days)(_count)?$",
    re.IGNORECASE,
)

_INDICE_CODES_FROM_CATALOG = {
    v["parent_code"] if v["is_threshold_variant"] else v["code"]
    for v in INDICES_CATALOG.values()
}
_INDICE_CODES_SORTED = sorted(_INDICE_CODES_FROM_CATALOG, key=len, reverse=True)


def parse_filename(filename: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "kind": "",
        "scenario": None,
        "period": "",
        "ref_period": None,
        "indice_code_fname": "",
        "threshold_suffix": "",
        "catalog_code": "",
        "is_pct": False,
        "is_calibration_leftover": False,
    }

    name = filename.replace(".nc", "")

    if PCT_SUFFIX_RE.search(name):
        out["is_pct"] = True
        name = PCT_SUFFIX_RE.sub("", name)

    m = THRESHOLD_SUFFIX_RE.search(name)
    if m:
        out["threshold_suffix"] = m.group(0).lstrip("_")
        name_for_indice = name[: m.start()]
    else:
        name_for_indice = name

    if "sum_Ensemble_GCMs" in name:
        out["kind"] = "future"
        m_ssp = re.search(r"(ssp\d{3})", name, re.IGNORECASE)
        if m_ssp:
            out["scenario"] = m_ssp.group(1).lower()
        m_periods = re.findall(r"(\d{4})_(\d{4})", name)
        if len(m_periods) >= 2:
            out["ref_period"] = f"{m_periods[0][0]}-{m_periods[0][1]}"
            out["period"] = f"{m_periods[1][0]}-{m_periods[1][1]}"
    else:
        out["kind"] = "historical"
        m_p = re.search(r"_clim_(\d{4})_(\d{4})_", name)
        if m_p:
            out["period"] = f"{m_p.group(1)}-{m_p.group(2)}"

    if out["kind"] == "historical" and out["period"] == "1995-1996":
        out["is_calibration_leftover"] = True

    found_code = ""
    if out["kind"] == "future":
        all_pers = list(re.finditer(r"_(\d{4})_(\d{4})_", name_for_indice))
        search_start = all_pers[1].end() - 1 if len(all_pers) >= 2 else 0
    else:
        m_per = re.search(r"_\d{4}_\d{4}_", name_for_indice)
        search_start = m_per.end() - 1 if m_per else 0

    suffix = name_for_indice[search_start:]
    for code in _INDICE_CODES_SORTED:
        if re.search(rf"_{re.escape(code)}(_|$)", suffix):
            found_code = code
            break

    out["indice_code_fname"] = found_code

    if found_code:
        if out["threshold_suffix"]:
            ts = out["threshold_suffix"]
            m_ts = re.match(r"(gt|lt|ltm)(\d+)", ts, re.IGNORECASE)
            m_bw = re.match(r"bw(\d+)_(\d+)", ts, re.IGNORECASE)
            if m_ts:
                op = m_ts.group(1).upper()
                val = m_ts.group(2)
                candidate = f"{found_code}_{op}{val}"
                if candidate in INDICES_CATALOG:
                    out["catalog_code"] = candidate
            elif m_bw:
                candidate = f"{found_code}_BW{m_bw.group(1)}_{m_bw.group(2)}"
                if candidate in INDICES_CATALOG:
                    out["catalog_code"] = candidate
        else:
            if found_code in INDICES_CATALOG:
                out["catalog_code"] = found_code

    return out


# ---------------------------------------------------------------------------
# Output path resolver
# ---------------------------------------------------------------------------

def resolve_output_path(filename: str, parsed: Dict[str, Any]) -> Path:
    out_name = filename.replace(".nc", ".tif")
    kind = parsed["kind"]
    scenario = parsed["scenario"]

    if kind == "historical":
        return OUTPUT_ROOT / "historical" / out_name
    elif kind == "future":
        if not scenario:
            raise ValueError(f"Future file has no scenario: {filename}")
        return OUTPUT_ROOT / "future" / scenario / out_name
    else:
        raise ValueError(f"Unknown kind '{kind}' for: {filename}")


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def compute_stats(arr) -> Dict[str, float]:
    import numpy as np

    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return {
            "min": None, "max": None, "mean": None,
            "median": None, "q25": None, "q75": None,
        }

    def _round_half(x: float) -> float:
        return round(x * 2) / 2

    return {
        "min":    _round_half(float(valid.min())),
        "max":    _round_half(float(valid.max())),
        "mean":   _round_half(float(valid.mean())),
        "median": _round_half(float(np.median(valid))),
        "q25":    _round_half(float(np.quantile(valid, 0.25))),
        "q75":    _round_half(float(np.quantile(valid, 0.75))),
    }


# ---------------------------------------------------------------------------
# Catalog tag builder
# ---------------------------------------------------------------------------

def build_cog_tags(parsed: Dict[str, Any], catalog_entry: Dict[str, Any]) -> Dict[str, str]:
    tags: Dict[str, str] = {
        "INDICE_CODE":          catalog_entry["code"],
        "DISPLAY_CODE":         catalog_entry["display_code"],
        "LONG_NAME":            catalog_entry["long_name"],
        "UNIT":                 catalog_entry["unit"],
        "CATEGORY":             catalog_entry["category"],
        "SUBCATEGORY":          catalog_entry["subcategory"],
        "KIND":                 parsed["kind"],
        "PERIOD":               parsed["period"],
        "FORMULA":              catalog_entry["formula"],
        "SHORT_DESCRIPTION":    catalog_entry["short_description"],
        "IS_THRESHOLD_VARIANT": str(catalog_entry["is_threshold_variant"]),
    }
    if parsed.get("is_pct"):
        tags["IS_PCT"] = "True"
    if parsed.get("scenario"):
        tags["SCENARIO"] = parsed["scenario"]
    if parsed.get("ref_period"):
        tags["REF_PERIOD"] = parsed["ref_period"]
    if catalog_entry["parent_code"]:
        tags["PARENT_CODE"] = catalog_entry["parent_code"]
    if catalog_entry["threshold"]:
        th = catalog_entry["threshold"]
        tags["THRESHOLD"] = f"{th['operator']} {th['value']} {th['unit']}".strip()
    return tags


# ---------------------------------------------------------------------------
# Single-file converter
# ---------------------------------------------------------------------------

def convert_one(
    nc_path: Path,
    parsed: Dict[str, Any],
    catalog_entry: Dict[str, Any],
    output_path: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    import xarray as xr
    import rioxarray  # noqa: F401
    import numpy as np
    import rasterio
    from rasterio.shutil import copy as rio_copy
    from rasterio.enums import Resampling

    info: Dict[str, Any] = {"stats": None, "error": ""}

    try:
        ds = xr.open_dataset(nc_path, decode_coords="all")
    except Exception as e:
        info["error"] = f"open_failed: {e!r}"
        return False, info

    try:
        skip_vars = {
            "spatial_ref", "crs", "lon", "lat", "longitude", "latitude",
            "time", "time_bnds", "x", "y",
        }
        data_vars = [v for v in ds.data_vars if v not in skip_vars]
        if not data_vars:
            info["error"] = "no_data_variable_found"
            ds.close()
            return False, info

        var_name = data_vars[0]
        da = ds[var_name]

        # Drop ancillary dims (time, band, percentiles)
        for dim in ["time", "band", "percentiles"]:
            if dim in da.dims:
                if da.sizes[dim] > 1:
                    if dim == "time":
                        da = da.mean(dim=dim)
                    else:
                        da = da.isel({dim: 0})
                else:
                    da = da.squeeze(dim, drop=True)

        # Rename lon/lat -> x/y for rioxarray
        rename_map = {}
        if "lon" in da.dims:
            rename_map["lon"] = "x"
        elif "longitude" in da.dims:
            rename_map["longitude"] = "x"
        if "lat" in da.dims:
            rename_map["lat"] = "y"
        elif "latitude" in da.dims:
            rename_map["latitude"] = "y"
        if rename_map:
            da = da.rename(rename_map)

        # Defensive coordinate ordering (lat descending, lon ascending)
        # Needed if the NetCDF stores lat ascending - reproject_to_match
        # below will normalize but this is a safety net.
        if "y" in da.dims and da.sizes["y"] >= 2:
            y_vals = da["y"].values
            if y_vals[0] < y_vals[-1]:
                da = da.sortby("y", ascending=False)
        if "x" in da.dims and da.sizes["x"] >= 2:
            x_vals = da["x"].values
            if x_vals[0] > x_vals[-1]:
                da = da.sortby("x", ascending=True)

        # float32 dtype
        if da.dtype != np.float32:
            da = da.astype("float32")

        # Set the native CRS (NetCDF is 4326)
        da.rio.write_crs("EPSG:4326", inplace=True)
        if "x" in da.dims and "y" in da.dims:
            da.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)

        # ----- v3 KEY STEP: reproject to EPSG:3857 (Web Mercator) -----
        # This aligns the output COG with the OSM basemap and the LCZ raster
        # (both 3857). Without this, Folium ImageOverlay placement on a
        # Mercator basemap drifts northward because the 4326 pixels are
        # stretched non-uniformly when projected to web Mercator at render
        # time.
        da = da.rio.reproject(
            OUTPUT_CRS,
            resampling=Resampling.bilinear,
        )
        # rio.reproject can introduce a 'band' dim again on some xarray
        # versions; squeeze if present.
        if "band" in da.dims and da.sizes["band"] == 1:
            da = da.squeeze("band", drop=True)
        # --------------------------------------------------------------

        # ----- TR sinir maskesi: deniz/tasma alanlarini NaN yap -----
        # reproject sonrasi, henuz 3857'de. Kaynak nc TR'ye kesilmemis olsa
        # bile cikti TIF temiz olur.
        try:
            tr_geom = _get_tr_geom_3857()
            da = da.rio.clip(tr_geom.geometry, tr_geom.crs,
                             drop=False, all_touched=True)
        except Exception as _clip_err:
            if verbose:
                print(f"    [WARN] TR clip atlandi: {_clip_err}")
        # --------------------------------------------------------------

        # Stats (after reprojection so they reflect what users will see)
        stats = compute_stats(da.values)
        info["stats"] = stats

        if dry_run:
            if verbose:
                print(f"    [dry-run] would write {output_path}")
            ds.close()
            return True, info

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tags = build_cog_tags(parsed, catalog_entry)

        tmp_path = output_path.with_suffix(".tmp.tif")
        try:
            # Step 1: tiled GeoTIFF (no COG driver, no overviews yet)
            da.rio.to_raster(
                tmp_path,
                tiled=True,
                blockxsize=512,
                blockysize=512,
                compress="DEFLATE",
                BIGTIFF="IF_SAFER",
            )

            # Step 2: wipe NetCDF auto-tags, apply our clean catalog tags
            with rasterio.open(tmp_path, "r+") as ds_tmp:
                existing_keys = list(ds_tmp.tags().keys())
                keys_to_wipe = [k for k in existing_keys if k != "AREA_OR_POINT"]
                if keys_to_wipe:
                    ds_tmp.update_tags(**{k: "" for k in keys_to_wipe})
                existing_band_keys = list(ds_tmp.tags(1).keys())
                if existing_band_keys:
                    ds_tmp.update_tags(1, **{k: "" for k in existing_band_keys})
                ds_tmp.update_tags(**tags)
                ds_tmp.set_band_description(1, catalog_entry["long_name"])
                ds_tmp.update_tags(1, UNIT=catalog_entry["unit"])

            # Step 3: COG translate (adds overviews)
            rio_copy(
                str(tmp_path),
                str(output_path),
                driver="COG",
                BLOCKSIZE=512,
                COMPRESS="DEFLATE",
                OVERVIEW_RESAMPLING="AVERAGE",
                BIGTIFF="IF_SAFER",
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        ds.close()
        return True, info

    except Exception as e:
        info["error"] = f"convert_failed: {e!r}\n{traceback.format_exc()}"
        try:
            ds.close()
        except Exception:
            pass
        return False, info


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Convert all NetCDF climate-index files to COG TIFFs (3857)."
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    if not INPUT_ROOT.exists():
        print(f"ERROR: input directory does not exist:\n  {INPUT_ROOT}",
              file=sys.stderr)
        sys.exit(1)

    print("=" * 72)
    print(f"NC -> COG TIFF Converter (v3 - output CRS: {OUTPUT_CRS})")
    print("=" * 72)
    print(f"Input  : {INPUT_ROOT}")
    print(f"Output : {OUTPUT_ROOT}")
    print(f"Catalog: {len(INDICES_CATALOG)} indices")
    if args.dry_run:
        print("Mode   : DRY-RUN (no files will be written)")
    if args.limit:
        print(f"Limit  : first {args.limit} files only")
    if args.skip_existing:
        print("Skip   : existing TIFFs will be skipped")
    print()

    if OUTPUT_ROOT.exists():
        existing = list(OUTPUT_ROOT.rglob("*.tif"))
        if existing:
            print(f"WARNING: {OUTPUT_ROOT} already contains {len(existing)} .tif files.")
            print("         These will NOT be auto-deleted. Use --skip-existing or")
            print("         clean the directory manually first if you want a fresh run.")
            print()

    all_nc = sorted(INPUT_ROOT.rglob("*.nc"))
    print(f"Found {len(all_nc)} .nc files under input root")

    to_process: List[Tuple[Path, Dict[str, Any]]] = []
    skipped_pct = 0
    skipped_leftover = 0
    skipped_unknown = 0
    unknown_files: List[str] = []

    for nc_path in all_nc:
        parsed = parse_filename(nc_path.name)
        # _pct varyantlari da tif'e cevrilir (yagis yuzde-degisim haritalari)
        # if parsed["is_pct"]:  # ARTIK ATLANMIYOR
        #     skipped_pct += 1
        #     continue
        if parsed["is_calibration_leftover"]:
            skipped_leftover += 1
            continue
        if not parsed["catalog_code"]:
            skipped_unknown += 1
            unknown_files.append(nc_path.name)
            continue
        to_process.append((nc_path, parsed))

    print()
    print("Filter summary:")
    print(f"  total .nc found        : {len(all_nc)}")
    print(f"  _pct variant (tif'e dahil): {skipped_pct} (artik islenir)")
    print(f"  skipped: 1995-1996     : {skipped_leftover}")
    print(f"  skipped: not in catalog: {skipped_unknown}")
    print(f"  -> to process          : {len(to_process)}")
    if unknown_files:
        print()
        print(f"  Unknown indice codes ({len(unknown_files)} files):")
        for f in unknown_files[:10]:
            print(f"    {f}")
        if len(unknown_files) > 10:
            print(f"    ... and {len(unknown_files) - 10} more")
    print()

    if args.limit:
        to_process = to_process[: args.limit]
        print(f"--limit applied: processing only first {len(to_process)} files")
        print()

    if args.skip_existing:
        before = len(to_process)
        to_process = [
            (p, parsed) for (p, parsed) in to_process
            if not resolve_output_path(p.name, parsed).exists()
        ]
        skipped = before - len(to_process)
        if skipped > 0:
            print(f"--skip-existing: skipping {skipped} files already present in output")
            print()

    if not to_process:
        print("Nothing to do.")
        return

    n_ok = 0
    n_err = 0
    errors: List[Tuple[str, str]] = []
    stats_all: Dict[str, Dict[str, float]] = {}

    t0 = time.time()
    for i, (nc_path, parsed) in enumerate(to_process, 1):
        catalog_entry = INDICES_CATALOG[parsed["catalog_code"]]
        out_path = resolve_output_path(nc_path.name, parsed)

        if args.verbose:
            print(f"[{i:3d}/{len(to_process)}] {nc_path.name}")
            print(f"          -> {out_path.relative_to(OUTPUT_ROOT)}")
            print(f"          catalog: {parsed['catalog_code']} ({catalog_entry['unit']})")

        ok, info = convert_one(
            nc_path=nc_path,
            parsed=parsed,
            catalog_entry=catalog_entry,
            output_path=out_path,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        if ok:
            n_ok += 1
            if info["stats"]:
                stats_all[out_path.name] = info["stats"]
            if args.verbose and info["stats"]:
                s = info["stats"]
                print(f"          stats: min={s['min']}, max={s['max']}, mean={s['mean']}")
        else:
            n_err += 1
            errors.append((nc_path.name, info["error"]))
            if args.verbose:
                print(f"          ERROR: {info['error'][:200]}")

        if not args.verbose and i % 25 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(to_process) - i) / rate if rate > 0 else 0
            print(f"  [{i:4d}/{len(to_process)}]  "
                  f"OK={n_ok}, ERR={n_err}, "
                  f"{rate:.1f} files/s, ETA {eta:.0f}s")

    elapsed = time.time() - t0

    stats_path = OUTPUT_ROOT / "stats.json"
    if not args.dry_run and stats_all:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats_all, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 72)
    print("CONVERSION COMPLETE")
    print("=" * 72)
    print(f"Successful : {n_ok}")
    print(f"Errors     : {n_err}")
    print(f"Elapsed    : {elapsed:.1f}s")
    if not args.dry_run:
        print(f"Stats file : {stats_path}")
        if OUTPUT_ROOT.exists():
            total_bytes = sum(p.stat().st_size for p in OUTPUT_ROOT.rglob("*.tif"))
            print(f"Total TIF size: {total_bytes / (1024 * 1024):.1f} MB")
    if errors:
        print()
        print("First few errors:")
        for fname, err in errors[:5]:
            short = err.split("\n")[0][:120]
            print(f"  {fname}: {short}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")


if __name__ == "__main__":
    main()