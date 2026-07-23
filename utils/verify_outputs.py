"""
verify_outputs.py — SON DOGRULAMA
Merged NetCDF + TIF + katalog tutarliligini tek raporda kontrol eder.

    conda activate climate
    python verify_outputs.py
"""

import os
import re
import sys
import glob
import json
from collections import Counter

import xarray as xr

APP = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Script/Python/climate_indices_map_tool"
MERGED = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Data/Climate_Indices/merged_netcdf"
TIF_DIR = os.path.join(APP, "data", "indices")

sys.path.insert(0, APP)
from utils.indices_catalog import INDICES_CATALOG  # noqa: E402

# Turkce / ic-terminoloji isaretleri
TR_WORDS = ["yaklasim", "esik", "tabanli", "donusturulmus", "gunluk", "yillik",
            "ardisik", "sayisi", "yalnizca", "islak", "yuzdelik", "pencere",
            "dagilimi", "dengesi", "baslangic", "bitis", "polinom", "gunlerde"]
INTERNAL = ["scaling", "clim mean of", "clim count", "variant=", "(TBD)", "TBD"]

fail = 0


def flag(text):
    if not text:
        return ""
    low = text.lower()
    out = ""
    if any(re.search(r"\b" + w + r"\b", low) for w in TR_WORDS):
        out += " [TR]"
    if any(w.lower() in low for w in INTERNAL):
        out += " [IC]"
    if re.search(r"\b(hot|cold)\s*[<>]", low):
        out += " [ESIK-ETIKET]"
    return out


print("=" * 92)
print("  1) MERGED NetCDF")
print("=" * 92)

files = sorted(glob.glob(os.path.join(MERGED, "*.nc")))
print(f"  dosya sayisi: {len(files)}  (9 bekleniyor)")
if len(files) != 9:
    fail += 1

req = ["units", "long_name", "short_name", "approach"]
for f in files:
    ds = xr.open_dataset(f)
    bn = os.path.basename(f)
    problems, missing, badunit = [], [], []
    for v in ds.data_vars:
        a = ds[v].attrs
        for k in req:
            if not a.get(k):
                missing.append(f"{v}.{k}")
        fl = flag(str(a.get("approach", ""))) + flag(str(a.get("long_name", "")))
        if fl:
            problems.append((v, fl, str(a.get("approach", ""))[:60]))
        # esik varyanti -> days_per_year olmali
        if re.search(r"_(gt|lt|ltm)\d+$|_bw\d+_\d+$", v) and a.get("units") != "days_per_year":
            badunit.append(f"{v}={a.get('units')}")
    # global attrs
    gmiss = [k for k in ("title", "source", "method", "institution", "project", "period")
             if not ds.attrs.get(k)]
    ds.close()

    status = "OK" if not (problems or missing or badunit or gmiss) else "SORUN"
    print(f"\n  {bn:<52} {len(xr.open_dataset(f).data_vars):>3} var  [{status}]")
    if missing:
        fail += 1; print(f"     eksik attr ({len(missing)}): {missing[:6]}")
    if badunit:
        fail += 1; print(f"     esik birimi yanlis: {badunit[:6]}")
    if gmiss:
        fail += 1; print(f"     global attr eksik: {gmiss}")
    if problems:
        fail += 1
        print(f"     metin sorunu ({len(problems)}):")
        for v, fl, ap in problems[:8]:
            print(f"       {v:<20}{fl:<18}{ap}")

print("\n" + "=" * 92)
print("  2) KATALOG")
print("=" * 92)

cat_bad = []
for code, e in INDICES_CATALOG.items():
    for k in ("display_code", "long_name", "unit", "formula", "short_description"):
        val = str(e.get(k, ""))
        if not val.strip():
            cat_bad.append(f"{code}.{k} BOS")
        elif flag(val):
            cat_bad.append(f"{code}.{k}{flag(val)}: {val[:50]}")
print(f"  girdi: {len(INDICES_CATALOG)}")
print(f"  sorun: {len(cat_bad)}")
for c in cat_bad[:15]:
    print("    ", c)
if cat_bad:
    fail += 1

print("\n  birim dagilimi:")
for u, c in sorted(Counter(e["unit"] for e in INDICES_CATALOG.values()).items(), key=lambda x: -x[1]):
    print(f"    {u:<14} {c}")

print("\n" + "=" * 92)
print("  3) TIF")
print("=" * 92)

try:
    import rasterio
except ImportError:
    print("  rasterio yok, tif kontrolu atlandi")
    rasterio = None

if rasterio:
    tifs = sorted(glob.glob(os.path.join(TIF_DIR, "**", "*.tif"), recursive=True))
    print(f"  tif sayisi: {len(tifs)}  (571 bekleniyor)")
    if len(tifs) != 571:
        fail += 1

    from utils.naming import parse_tif_filename

    tag_missing, unit_mismatch, unparsed = [], [], []
    REQ_TAGS = ["INDICE_CODE", "DISPLAY_CODE", "LONG_NAME", "UNIT", "CATEGORY", "FORMULA"]
    for t in tifs:
        with rasterio.open(t) as src:
            tags = src.tags()
        bn = os.path.basename(t)
        for k in REQ_TAGS:
            if not tags.get(k):
                tag_missing.append(f"{bn}:{k}")
        p = parse_tif_filename(bn)
        code = p.get("catalog_code")
        if not code:
            unparsed.append(bn)
        elif code in INDICES_CATALOG:
            want = INDICES_CATALOG[code]["unit"]
            if tags.get("UNIT") != want:
                unit_mismatch.append(f"{bn}: tag={tags.get('UNIT')} katalog={want}")

    print(f"  eksik etiket    : {len(tag_missing)}")
    for x in tag_missing[:6]:
        print("     ", x)
    print(f"  birim uyusmazlik: {len(unit_mismatch)}")
    for x in unit_mismatch[:8]:
        print("     ", x)
    print(f"  parse edilemeyen: {len(unparsed)}")
    for x in unparsed[:6]:
        print("     ", x)
    if tag_missing or unit_mismatch or unparsed:
        fail += 1

    sp = os.path.join(TIF_DIR, "stats.json")
    if os.path.exists(sp):
        st = json.load(open(sp))
        print(f"  stats.json      : {len(st)} girdi  ({'OK' if len(st) == len(tifs) else 'EKSIK -> rebuild_stats.py'})")
        if len(st) != len(tifs):
            fail += 1
    else:
        print("  stats.json      : YOK")
        fail += 1

print("\n" + "=" * 92)
print("  SONUC:", "TEMIZ - yayina hazir" if fail == 0 else f"{fail} bolumde sorun var")
print("=" * 92)