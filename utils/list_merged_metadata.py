"""
list_merged_metadata.py
Merged NetCDF dosyalarindaki tum degiskenlerin metadata tablosunu yazar.
Konsola tablo + CSV cikti (rapor/yayin icin).

    conda activate climate
    python list_merged_metadata.py
"""

import os
import csv
import glob
import xarray as xr

MERGED = ("/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/"
          "Data/Climate_Indices/merged_netcdf")
OUT_CSV = os.path.join(MERGED, "metadata_table.csv")

# Tabloyu hangi dosyadan cikaralim (historical = 81 var, en genis set)
MAIN = "TR_CHELSA_historical_1995_2014.nc"


def dump_table(path):
    ds = xr.open_dataset(path)
    rows = []
    for v in sorted(ds.data_vars):
        a = ds[v].attrs
        rows.append({
            "variable":   v,
            "short_name": a.get("short_name", ""),
            "long_name":  a.get("long_name", ""),
            "units":      a.get("units", ""),
            "approach":   a.get("approach", ""),
        })
    ds.close()
    return rows


def main():
    main_path = os.path.join(MERGED, MAIN)
    rows = dump_table(main_path)

    # ---- konsol tablosu ----
    print("=" * 150)
    print(f"  {MAIN}  |  {len(rows)} degisken")
    print("=" * 150)
    print(f"{'variable':<22}{'short_name':<24}{'units':<16}long_name")
    print("-" * 150)
    for r in rows:
        print(f"{r['variable']:<22}{r['short_name']:<24}{r['units']:<16}{r['long_name']}")

    print()
    print("=" * 150)
    print("  APPROACH (metodoloji)")
    print("=" * 150)
    for r in rows:
        print(f"\n{r['variable']}  [{r['units']}]")
        print(f"   {r['approach']}")

    # ---- CSV ----
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variable", "short_name", "long_name", "units", "approach"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n\nCSV yazildi: {OUT_CSV}  ({len(rows)} satir)")

    # ---- diger dosyalarin degisken sayilari + farklar ----
    print("\n" + "=" * 150)
    print("  DOSYALAR")
    print("=" * 150)
    main_vars = {r["variable"] for r in rows}
    for p in sorted(glob.glob(os.path.join(MERGED, "*.nc"))):
        ds = xr.open_dataset(p)
        vs = set(ds.data_vars)
        ds.close()
        bn = os.path.basename(p)
        extra = sorted(vs - main_vars)
        missing = sorted(main_vars - vs)
        print(f"\n  {bn:<52} {len(vs):>3} var")
        if extra:
            print(f"     historical'da OLMAYAN ({len(extra)}): {extra[:8]}{' ...' if len(extra) > 8 else ''}")
        if missing:
            print(f"     historical'da olup burada YOK ({len(missing)}): {missing[:8]}{' ...' if len(missing) > 8 else ''}")


if __name__ == "__main__":
    main()