"""
==============================================================================================================================================
SCRIPT : build_merged_netcdf.py
PROJE  : Climatic Suitability Analysis for Turkiye
KURUM  : Eurasia Institute of Earth Sciences, Istanbul Technical University
ASAMA  : Kaynak NetCDF'leri (historical + sum) tek dosyalarda birlestir (yayin paketi)
==============================================================================================================================================

CIKTI (9 dosya):
  TR_CHELSA_historical_1995_2014.nc                       (CHELSA historical, 81 var)
  TR_CHELSA_GCMs_future_{ssp}_{period}.nc                 (6 dosya: 3 SSP x 2 donem, UHI haric)
  TR_CHELSA_GCMs_future_ssp245_{period}_UHI_UTCI.nc       (2 dosya: UHI UTCI)

YAPILANLAR:
  - Tum indisler ortak 1km referans grid'e hizalanir (climate grid; bio grid kenarlari NaN)
  - TR shapefile ile maskelenir
  - Kisa variable adlari (prcptot, pet_gt29, utci_bw9_26, uhi_05_utci_gt32)
  - Ayirt edici long_name (esik varyantlari icin kosul + "days per year")
  - units / approach / stat_* kaynaktan tasinir
  - Global attrs: title, source (3 kaynak), method, period, scenario, baseline
  - WSDI/CSDI approach'ine percentile referans donemi eklenir
  - *_pct long_name'lerine "(percentage-change scaled)" eklenir

CALISTIRMA (Mac, climate env):
  conda activate climate
  python build_merged_netcdf.py
==============================================================================================================================================
"""

import os
import re
import sys
import glob
import datetime
import warnings

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401  (da.rio icin gerekli)
import geopandas as gpd

# Yayin adlari katalogdan alinir (merged <-> tif <-> app tutarliligi)
_APP = ("/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/"
        "Script/Python/climate_indices_map_tool")
if _APP not in sys.path:
    sys.path.insert(0, _APP)
from utils.indices_catalog import INDICES_CATALOG

warnings.filterwarnings("ignore")


# ==============================================================================
# AYARLAR
# ==============================================================================

BASE    = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Data/Climate_Indices/regional/TR"
OUT_DIR = "/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Data/Climate_Indices/merged_netcdf"
SHP_PATH = ("/Users/emirtoker/Desktop/Proje_Tubitak_Bap/Iklim_Mimarlik_Projesi/Data/shapefiles/"
            "tur_adm_2025_ab_shp/tur_admbnda_adm0_2025.shp")

CHELSA_DIR = os.path.join(BASE, "historical/clim/1km/CHELSA")
SUM_DIR    = os.path.join(BASE, "sum_CHELSA_GCMs/clim/1km")

HIST_PERIOD = "1995_2014"
SCENARIOS   = ["ssp126", "ssp245", "ssp585"]
PERIODS     = ["2041_2060", "2081_2100"]

# Referans grid: climate indisi (en genis grid)
REF_PATTERN = os.path.join(CHELSA_DIR, "*PRCPTOT_annual_total_precip.nc")


# ==============================================================================
# GLOBAL ATTRIBUTES
# ==============================================================================

GCM_MODELS = ("CanESM5, CNRM-CM6-1, CNRM-ESM2-1, EC-Earth3, GFDL-ESM4, "
              "IPSL-CM6A-LR, MIROC6, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL")

SOURCE_HIST = ("CHELSA-W5E5 v1.0 (tas, tasmax, tasmin, pr, rsds; ~1 km); "
               "CHELSA v2.1 (hurs, sfcWind, ps; ~1 km); "
               "W5E5 v2.0 (rlds; 0.5 degree interpolated to ~1 km)")

SOURCE_FUT = (f"Baseline: CHELSA-W5E5 v1.0 (tas, tasmax, tasmin, pr, rsds), "
              f"CHELSA v2.1 (hurs, sfcWind, ps), W5E5 v2.0 (rlds, interpolated); "
              f"Projection: ISIMIP3b bias-adjusted GCM ensemble (10 models: {GCM_MODELS})")

COMMON_ATTRS = {
    "institution":        "Eurasia Institute of Earth Sciences, Istanbul Technical University",
    "project":            "Climatic Suitability Analysis for Turkiye",
    "contact":            "tokerem@itu.edu.tr",
    "spatial_resolution": "30 arc-second (~1 km)",
}


def make_global_attrs(kind, scenario=None, period=None, is_uhi=False):
    a = dict(COMMON_ATTRS)
    a["history"] = "Created " + datetime.datetime.now().strftime("%Y-%m-%d")

    if kind == "historical":
        a["title"]  = ("Climate and Bio-Climate Indices for Turkiye "
                       "- CHELSA Historical (1995-2014)")
        a["source"] = SOURCE_HIST
        a["period"] = "1995-2014"
        a["method"] = "Indices computed directly from CHELSA daily data (1995-2014)"
    else:
        tag = "UHI-adjusted UTCI" if is_uhi else "GCM ensemble projection"
        a["title"]    = (f"Climate and Bio-Climate Indices for Turkiye "
                         f"- {tag}, {scenario.upper()} ({period})")
        a["source"]   = SOURCE_FUT
        a["period"]   = period
        a["baseline"] = "1995-2014"
        a["scenario"] = scenario
        m = (f"CHELSA (1995-2014) + GCM ensemble-mean delta ({period} minus 1995-2014), "
             f"10-model mean")
        if is_uhi:
            m += (". Urban heat island effect applied as hypothetical temperature offsets "
                  "(+0.5, +1.0, +1.5, +2.0 degC) added before threshold counting")
            a["uhi_note"] = ("UTCI recomputed with urban heat island offsets: "
                             "+0.5, +1.0, +1.5, +2.0 degC")
        else:
            m += (". Precipitation *_pct variables: CHELSA x (1 + delta_pct/100)")
        a["method"] = m
    return a


# ==============================================================================
# ISIM HARITASI (uzun dosya soneki -> kisa variable adi)
# ==============================================================================

LONG_TO_SHORT = {
    "ai_aridity_index": "ai",
    "at_apparent_temperature": "at",
    "cd_cooling_days": "cd",
    "cdd_a_cooling_degree_days_approx": "cdd_a",
    "cdd_cooling_degree_days": "cdd",
    "cdd_p_consecutive_dry_days": "cdd_p",
    "csdi_cold_spell_duration_index": "csdi",
    "cw_cold_wave_index": "cw",
    "cwd_consecutive_wet_days": "cwd",
    "di_discomfort_index": "di",
    "dtr_diurnal_temperature_range": "dtr",
    "esi_environmental_stress_index": "esi",
    "et_normal_effective_temperature": "et",
    "fd_frost_days": "fd",
    "gd_growing_days": "gd",
    "gdd_growing_degree_days": "gdd",
    "gsl_growing_season_length": "gsl",
    "hd_heating_days": "hd",
    "hdd_heating_degree_days": "hdd",
    "hi_heat_index": "hi",
    "hmx_humidex": "hmx",
    "hw_heat_wave_index": "hw",
    "id_ice_days": "id",
    "mrt_mean_radiant_temperature": "mrt",
    "pcd_passive_comfort_days": "pcd",
    "pet_physiologically_equivalent_temperature": "pet",
    "pmv_predicted_mean_vote": "pmv",
    "pnp_percent_of_normal_precip": "pnp",
    "ppd_predicted_percentage_of_dissatisfied": "ppd",
    "prcptot_annual_total_precip": "prcptot",
    "r10mm_heavy_precip_days": "r10mm",
    "r20mm_very_heavy_precip_days": "r20mm",
    "r95p_very_wet_days": "r95p",
    "r99p_extremely_wet_days": "r99p",
    "rx1day_max_1day_precip": "rx1day",
    "rx5day_max_5day_precip": "rx5day",
    "sdii_daily_intensity_index": "sdii",
    "set_standard_effective_temperature": "set",
    "spei12_standardized_pet_index_12": "spei12",
    "spi12_standardized_precip_index_12": "spi12",
    "su_summer_days": "su",
    "thi_c_temperature_humidity_index_crop": "thi_c",
    "thi_h_temperature_humidity_index_human": "thi_h",
    "thi_l_temperature_humidity_index_livestock": "thi_l",
    "tnn_min_daily_min_temp": "tnn",
    "tnx_max_daily_min_temp": "tnx",
    "tr_ext_extended_tropical_nights": "tr_ext",
    "tr_tropical_nights": "tr",
    "txn_min_daily_max_temp": "txn",
    "txx_max_daily_max_temp": "txx",
    "utci_universal_thermal_climate_index": "utci",
    "utci": "utci",
    "vd_ventilation_potential": "vd",
    "wbgt_wet_bulb_globe_temperature": "wbgt",
    "wci_wind_chill_index": "wci",
    "wsdi_warm_spell_duration_index": "wsdi",
}

# Esik soneki: _gt29_hot_days, _lt8_cold_days, _ltm10_cold_days, _bw9_26_comfort_days
THRESH_RE = re.compile(r"_(gt\d+|lt\d+|ltm\d+|bw\d+_\d+)_[a-z_]+_days$", re.IGNORECASE)

# Esik varyantinin long_name'i icin ana indis adi
PARENT_LONG = {
    "at": "Apparent Temperature",
    "di": "Discomfort Index",
    "esi": "Environmental Stress Index",
    "et": "Normal Effective Temperature",
    "hi": "Heat Index",
    "hmx": "Humidex",
    "pet": "Physiologically Equivalent Temperature",
    "pmv": "Predicted Mean Vote",
    "ppd": "Predicted Percentage of Dissatisfied",
    "set": "Standard Effective Temperature",
    "thi_c": "Temperature-Humidity Index (Crop)",
    "thi_h": "Temperature-Humidity Index (Human)",
    "thi_l": "Temperature-Humidity Index (Livestock)",
    "utci": "Universal Thermal Climate Index",
    "wbgt": "Wet-Bulb Globe Temperature",
    "wci": "Wind Chill Index",
}

# Esik degerinin birim sembolu (long_name icinde gosterilir).
# Esik dosyasinin kendi birimi days_per_year oldugu icin ANA indisin dogal birimi kullanilir.
PARENT_SYMBOL = {
    "at": "°C", "di": "°C", "esi": "°C", "et": "°C", "hi": "°C",
    "hmx": "°C", "pet": "°C", "set": "°C", "thi_h": "°C",
    "utci": "°C", "wbgt": "°C", "wci": "°C",
    "ppd": "%",
    "pmv": "", "thi_c": "", "thi_l": "",
}

# ==============================================================================
# APPROACH (metodoloji) - yayin dili: Ingilizce, esik etiketi ve ic terminoloji yok
# ==============================================================================

APPROACH_EN = {
    # --- Climate: sicaklik ---
    "fd":     "Count of days with TN < 0 °C",
    "id":     "Count of days with TX < 0 °C",
    "su":     "Count of days with TX > 25 °C",
    "tr":     "Count of days with TN > 20 °C",
    "tr_ext": "Count of days with TN > 25 °C",
    "txx":    "Maximum of daily maximum temperature",
    "txn":    "Minimum of daily maximum temperature",
    "tnx":    "Maximum of daily minimum temperature",
    "tnn":    "Minimum of daily minimum temperature",
    "dtr":    "Mean of (TX - TN)",
    "hw":     "TX > 30 °C for at least 3 consecutive days",
    "cw":     "TN < 0 °C for at least 3 consecutive days",
    "wsdi":   ("TX > 90th percentile for at least 6 consecutive days "
               "(5-day moving window; percentile reference period 1995-2014)"),
    "csdi":   ("TN < 10th percentile for at least 6 consecutive days "
               "(5-day moving window; percentile reference period 1995-2014)"),
    # --- Climate: yagis ---
    "prcptot": "Sum of PR over wet days (PR >= 1 mm/day)",
    "rx1day":  "Maximum daily precipitation",
    "rx5day":  "Maximum 5-day cumulative precipitation",
    "sdii":    "Sum of PR divided by number of wet days (PR >= 1 mm/day)",
    "r10mm":   "Count of days with PR >= 10 mm/day",
    "r20mm":   "Count of days with PR >= 20 mm/day",
    "r95p":    "Count of days with PR above the 95th percentile (reference 1995-2014 wet days)",
    "r99p":    "Count of days with PR above the 99th percentile (reference 1995-2014 wet days)",
    "cdd_p":   "Maximum number of consecutive days with PR < 1 mm/day",
    "cwd":     "Maximum number of consecutive days with PR >= 1 mm/day",
    # --- Climate: kuraklik ---
    "ai":     "Aridity Index: annual PR divided by annual PET (UNEP 1992; PET after Hargreaves 1985)",
    "pnp":    "Annual PR divided by climatological annual PR, expressed as percentage",
    "spi12":  "Standardized Precipitation Index, 12-month window (Gamma distribution, xclim)",
    "spei12": ("Standardized Precipitation-Evapotranspiration Index, 12-month window "
               "(PR - PET water balance, Fisk distribution, xclim)"),
    # --- Climate: enerji / tarim ---
    "cd":    "Count of days with TG > 21 °C",
    "cdd":   "Sum of (TG - 21) over days with TG > 21 °C",
    "cdd_a": "Cooling degree days, sinusoidal approximation with 21 °C threshold (Spinoni et al. 2018)",
    "hd":    "Count of days with TG < 18 °C",
    "hdd":   "Sum of (18 - TG) over days with TG < 18 °C",
    "gd":    "Count of days with TG > 5 °C",
    "gdd":   "Sum of (TG - 5) over days with TG > 5 °C",
    "gsl":   "Growing season length between the first and last 6-day spell of TG > 5 °C",
    # --- Bio-climate ---
    "at":    "Apparent Temperature (Steadman 1984; Blazejczyk 2012; pythermalcomfort)",
    "di":    "Discomfort Index: DI = Tdb - 0.55 (1 - RH/100) (Tdb - 14.5) (Thom 1959)",
    "esi":   "Environmental Stress Index (Moran et al. 2001; pythermalcomfort)",
    "et":    "Normal Effective Temperature (Missenard 1933)",
    "hi":    "Heat Index, NWS polynomial regression (Rothfusz 1990)",
    "hmx":   "Humidex (Masterton and Richardson 1979)",
    "mrt":   ("Mean Radiant Temperature: MRT = ((Rlds + 0.5 Rsds) / sigma)^0.25 - 273.15 "
              "(Thorsson et al. 2007)"),
    "pcd":   "Count of days with 18 °C <= TG < 25 °C",
    "pet":   ("Physiologically Equivalent Temperature, steady-state solution "
              "(met = 1.1, clo = 0.5; pythermalcomfort)"),
    "pmv":   "Predicted Mean Vote (ISO 7730; met = 1.1, clo = 0.5; pythermalcomfort)",
    "ppd":   "Predicted Percentage of Dissatisfied (ISO 7730; met = 1.1, clo = 0.5; pythermalcomfort)",
    "set":   "Standard Effective Temperature (met = 1.1, clo = 0.5; pythermalcomfort)",
    "thi_c": "Temperature-Humidity Index for crops: THI = Tdb + 0.36 Tdp + 41.2 (Yousef 1985; Tdp via Magnus formula)",
    "thi_h": "Temperature-Humidity Index for humans, converted to °C (Berry 1964)",
    "thi_l": "Temperature-Humidity Index for livestock: THI = 0.8 Tdb + (RH/100)(Tdb - 14.4) + 46.4 (Bianca 1962)",
    "utci":  "Universal Thermal Climate Index, 56-term polynomial approximation (Brode et al. 2012)",
    "wbgt":  "Wet-Bulb Globe Temperature: WBGT = 0.7 Twb + 0.2 MRT + 0.1 Ta (ISO 7933, outdoor)",
    "wci":   "Wind Chill Index (NWS / MSC 2001)",
    "vd":    "Ventilation potential: VD = sfcWind x tas (project-specific proxy)",
}

# *_pct degiskenleri icin acik long_name
PCT_LONGNAME = {
    "prcptot_pct": "Annual Total Precipitation (percentage-change scaled)",
    "rx1day_pct":  "Max 1-Day Precipitation (percentage-change scaled)",
    "rx5day_pct":  "Max 5-Day Precipitation (percentage-change scaled)",
    "sdii_pct":    "Simple Daily Intensity Index (percentage-change scaled)",
}


# ==============================================================================
# ISIM COZUMLEME
# ==============================================================================

def parse_filename(filename):
    """Dosya adindan (variable_adi, parent_kisa_kod, esik_kodu, uhi_seviyesi, pct_mi)."""
    name = filename.replace(".nc", "")

    # UHI seviyesi (UHI05 -> "05")
    m_uhi = re.search(r"UHI(\d{2})", name)
    uhi = m_uhi.group(1) if m_uhi else None

    # donem sonrasi kisim (son _YYYY_YYYY_ eslesmesinden sonrasi)
    parts = re.split(r"_(\d{4})_(\d{4})_", name)
    idx = parts[-1].lower()

    # UHI on-ekini temizle
    idx = re.sub(r"^uhi\d{2}_", "", idx)

    # _pct soneki
    is_pct = idx.endswith("_pct")
    if is_pct:
        idx = idx[:-4]

    # esik soneki
    thr = None
    m = THRESH_RE.search(idx)
    if m:
        thr = m.group(1).lower()
        idx = idx[:m.start()]

    parent = LONG_TO_SHORT.get(idx, idx)

    var = parent
    if thr:
        var = f"{parent}_{thr}"
    if uhi:
        var = f"uhi_{uhi}_{var}"
    if is_pct:
        var = f"{var}_pct"

    return var, parent, thr, uhi, is_pct


def threshold_phrase(thr, parent, parent_units):
    """Esik kodunu okunur ifadeye cevir: gt29 -> '> 29 degC'."""
    sym = PARENT_SYMBOL.get(parent, "°C")
    sym = (" " + sym) if sym else ""

    m = re.match(r"^bw(\d+)_(\d+)$", thr)
    if m:
        return f"{m.group(1)} to {m.group(2)}{sym}"
    m = re.match(r"^ltm(\d+)$", thr)
    if m:
        return f"< -{m.group(1)}{sym}"
    m = re.match(r"^lt(\d+)$", thr)
    if m:
        return f"< {m.group(1)}{sym}"
    m = re.match(r"^gt(\d+)$", thr)
    if m:
        return f"> {m.group(1)}{sym}"
    return thr


def build_var_attrs(filename, src_attrs):
    """Variable attribute'lari: units, long_name, short_name, approach, stat_*."""
    var, parent, thr, uhi, is_pct = parse_filename(filename)
    a = {}

    # --- units (kaynaktan; esik varyantlari icin guvenlik agi) ---
    if src_attrs.get("units"):
        a["units"] = src_attrs["units"]
    if thr:
        # Esik varyanti her zaman gun sayisidir; kaynakta yanlis olsa bile duzeltilir
        a["units"] = "days_per_year"

    # --- long_name / short_name (katalog otoritedir) ---
    pcode = parent.upper()
    cat = INDICES_CATALOG.get(pcode)
    parent_long = (cat["long_name"] if cat
                   else (src_attrs.get("long_name") or PARENT_LONG.get(parent, pcode)))
    parent_disp = cat["display_code"] if cat else pcode

    if thr:
        cond = threshold_phrase(thr, parent, src_attrs.get("units"))
        long_name = f"{parent_long} {cond} - days per year"
        thr_code = f"{pcode}_{thr.upper()}"
        short = (INDICES_CATALOG[thr_code]["display_code"]
                 if thr_code in INDICES_CATALOG else f"{parent_disp} ({cond})")
    else:
        long_name = parent_long
        short = parent_disp

    if is_pct:
        short = f"{short} (%)"
    if uhi:
        off = int(uhi) / 10.0
        long_name = f"{long_name} (UHI +{off} °C)"
        short = f"{short} UHI+{off}"

    a["long_name"] = long_name
    a["short_name"] = short

    # --- approach (yayin dili: Ingilizce; kaynak metin kullanilmaz) ---
    base_ap = APPROACH_EN.get(parent)
    if base_ap:
        if thr:
            cond = threshold_phrase(thr, parent, src_attrs.get("units"))
            plong = PARENT_LONG.get(parent, parent.upper())
            a["approach"] = (f"Count of days per year with {plong} {cond}. "
                             f"Underlying index: {base_ap}")
        else:
            a["approach"] = base_ap
    elif src_attrs.get("approach"):
        a["approach"] = src_attrs["approach"]

    # --- UHI ofseti ---
    if uhi:
        off = int(uhi) / 10.0
        a["uhi_offset_degC"] = off
        if a.get("approach"):
            a["approach"] += (f" Air temperature increased by +{off} \u00b0C "
                              f"before index computation to represent urban heat island effect.")

    # --- istatistikler (kaynaktan) ---
    for k in ("stat_min", "stat_max", "stat_mean", "stat_median", "stat_q25", "stat_q75"):
        if k in src_attrs:
            a[k] = src_attrs[k]

    # --- *_pct icin acik long_name ---
    if var in PCT_LONGNAME:
        a["long_name"] = PCT_LONGNAME[var]

    return var, a


# ==============================================================================
# GRID + MASK
# ==============================================================================

print("=" * 90)
print("  build_merged_netcdf.py -- KAYNAK NetCDF'leri BIRLESTIRME")
print("=" * 90)

ref_file = sorted(glob.glob(REF_PATTERN))[0]
_ref = xr.open_dataset(ref_file)
REF_LAT = _ref.lat
REF_LON = _ref.lon
_ref.close()
print(f"[REF ] {len(REF_LAT)} x {len(REF_LON)}  ({os.path.basename(ref_file)})")

SHP = gpd.read_file(SHP_PATH)
print(f"[MASK] {os.path.basename(SHP_PATH)}")


def load_aligned(filepath):
    """Dosyayi ac, referans grid'e hizala, TR ile maskele. (DataArray, kaynak_attrs)."""
    d = xr.open_dataset(filepath)
    v = [x for x in d.data_vars if x != "spatial_ref"][0]
    da = d[v].squeeze(drop=True)
    src_attrs = dict(da.attrs)
    da = da.reindex(lat=REF_LAT, lon=REF_LON, method="nearest", tolerance=1e-4)
    d.close()

    # TR maskesi
    try:
        da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)
        da = da.rio.write_crs("EPSG:4326", inplace=False)
        da = da.rio.clip(SHP.geometry, SHP.crs, drop=False, all_touched=True)
    except Exception as e:
        print(f"   [MASK HATA] {os.path.basename(filepath)}: {e}")

    drop = [c for c in da.coords if c not in ("lat", "lon")]
    da = da.drop_vars(drop, errors="ignore")
    return da, src_attrs


# ==============================================================================
# BIRLESTIRME
# ==============================================================================

def build_netcdf(file_list, out_path, global_attrs):
    data_vars = {}
    clash = []
    for fpath in sorted(file_list):
        fn = os.path.basename(fpath)
        da, src_attrs = load_aligned(fpath)
        var, attrs = build_var_attrs(fn, src_attrs)
        if var in data_vars:
            clash.append((var, fn))
            continue
        da.attrs = attrs
        da.name = var
        data_vars[var] = da

    ds = xr.Dataset(data_vars)
    ds.attrs = global_attrs
    ds.lat.attrs = {"units": "degrees_north", "standard_name": "latitude", "long_name": "latitude"}
    ds.lon.attrs = {"units": "degrees_east", "standard_name": "longitude", "long_name": "longitude"}

    enc = {v: {"zlib": True, "complevel": 4, "_FillValue": -9999.0} for v in ds.data_vars}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ds.to_netcdf(out_path, encoding=enc)

    size = os.path.getsize(out_path) / (1024 ** 2)
    print(f"  [YAZILDI] {os.path.basename(out_path):<52} {len(ds.data_vars):>3} var  {size:7.1f} MB")
    if clash:
        print(f"            [CAKISMA] {len(clash)}: {[c[0] for c in clash][:5]}")
    ds.close()
    return len(ds.data_vars)


def run_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = {}

    # ---- 1) CHELSA historical ----
    print("\n--- HISTORICAL ---")
    files = glob.glob(os.path.join(CHELSA_DIR, "*.nc"))
    out = os.path.join(OUT_DIR, f"TR_CHELSA_historical_{HIST_PERIOD}.nc")
    summary["historical"] = build_netcdf(files, out, make_global_attrs("historical"))

    # ---- 2) Future (UHI haric) ----
    print("\n--- FUTURE (GCM ensemble) ---")
    for ssp in SCENARIOS:
        for per in PERIODS:
            files = [f for f in glob.glob(os.path.join(SUM_DIR, ssp, f"*{per}*.nc"))
                     if "UHI" not in os.path.basename(f)]
            if not files:
                print(f"  [ATLANDI] {ssp} {per}: dosya yok")
                continue
            attrs = make_global_attrs("future", scenario=ssp, period=per.replace("_", "-"))
            out = os.path.join(OUT_DIR, f"TR_CHELSA_GCMs_future_{ssp}_{per}.nc")
            summary[f"{ssp}_{per}"] = build_netcdf(files, out, attrs)

    # ---- 3) UHI UTCI (ssp245) ----
    print("\n--- UHI UTCI (ssp245) ---")
    for per in PERIODS:
        files = glob.glob(os.path.join(SUM_DIR, "ssp245", f"*{per}*UHI*.nc"))
        if not files:
            print(f"  [ATLANDI] UHI {per}: dosya yok")
            continue
        attrs = make_global_attrs("future", scenario="ssp245",
                                  period=per.replace("_", "-"), is_uhi=True)
        out = os.path.join(OUT_DIR, f"TR_CHELSA_GCMs_future_ssp245_{per}_UHI_UTCI.nc")
        summary[f"UHI_{per}"] = build_netcdf(files, out, attrs)

    print("\n" + "=" * 90)
    print(f"  TAMAMLANDI | {len(summary)} dosya")
    for k, v in summary.items():
        print(f"    {k:<28} {v:>3} variable")
    print(f"  Cikti: {OUT_DIR}")
    print("=" * 90)


if __name__ == "__main__":
    run_all()