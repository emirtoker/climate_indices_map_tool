"""
utils/naming.py

Index file discovery + catalog merging layer.

This is the BACKBONE between the static catalog (indices_catalog.py)
and the actual TIF files on disk (data/indices/). The UI and the data
loader both talk to THIS module, not to the filesystem or the catalog
directly.

WHAT IT DOES
------------
1. Scans data/indices/{historical, future/ssp*}/ for .tif files.
2. Parses each filename -> kind, scenario, period, indice_code.
3. Merges with the catalog entry for that indice_code.
4. Merges with per-file stats from stats.json.
5. Returns a list of `IndexFile` objects, each carrying everything
   the UI needs about ONE tif file.

THE UI THEN FILTERS this list to render the sidebar:
    - by category    -> "Climate Indices" vs "Bio-Climate Indices"
    - by subcategory -> "Temperature", "Human Comfort", etc.
    - by scenario    -> "ssp245", or "all" (historical)
    - by indice_code -> when the user selects one specific index

USAGE
-----
    from utils.naming import load_all_index_files, filter_files

    files = load_all_index_files()
    temp_hist = filter_files(files, kind="historical", subcategory="TEMPERATURE")

KEY DESIGN CHOICES
------------------
- Catalog is SOURCE OF TRUTH for metadata. We never read NetCDF/TIF tags.
- stats.json is SOURCE OF TRUTH for per-file value ranges (used for sliders).
- One `IndexFile` per TIF (so a single indice may have multiple IndexFiles:
  one historical + 6 future versions = 7 IndexFiles for the same indice).

SUPPORTED THRESHOLD-SUFFIX FORMATS
----------------------------------
The regex `THRESHOLD_SUFFIX_RE` recognizes three operator families plus
an optional `_count` tail (used by the UTCI ISO-15743 variants):

    Operator       Catalog key example   Filename suffix example
    ----------     -------------------   --------------------------------
    gt<n>          UTCI_GT32             _gt32_hot_days
                                         _gt32_strong_heat_days_count
    lt<n>          PET_LT8               _lt8_cold_days
                                         _lt0_cold_days_count
    ltm<n>         UTCI_LTM13            _ltm13_cold_days
                                         _ltm13_strong_cold_days_count
    bw<a>_<b>      UTCI_BW9_26           _bw9_26_comfort_days_count
                                         _bw0_9_slight_cold_days_count
"""

from __future__ import annotations
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Make project root importable when running this module directly:
#   python utils/naming.py
# Without this, `from utils.indices_catalog import ...` fails because the
# current dir is utils/ and Python cannot see the utils package.
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils.indices_catalog import (
    INDICES_CATALOG,
    CATEGORY_LABELS,
    SUBCATEGORY_LABELS,
)
from config.settings import (
    INDICES_DIR_HISTORICAL,
    INDICES_DIR_FUTURE,
    FUTURE_SCENARIOS,
    STATS_PATH,
)


# ---------------------------------------------------------------------------
# IndexFile dataclass — represents ONE .tif file on disk
# ---------------------------------------------------------------------------

@dataclass
class IndexFile:
    """
    A single climate-index TIF file, enriched with catalog and stats.

    Identity fields (from filename parsing):
        path            : absolute filesystem path
        filename        : basename of the file
        catalog_code    : matched entry in INDICES_CATALOG (e.g. "UTCI_GT32")
        kind            : "historical" | "future"
        scenario        : "ssp126" | "ssp245" | "ssp585" | None (historical)
        period          : analysis period, e.g. "1995-2014" or "2041-2060"
        ref_period      : reference baseline, e.g. "1995-2014" (future only)

    Catalog fields (from INDICES_CATALOG[catalog_code]):
        display_code, long_name, category, subcategory, unit,
        formula, short_description, long_description,
        is_threshold_variant, parent_code, threshold

    Stats fields (from stats.json[filename]):
        stat_min, stat_max, stat_mean, stat_median, stat_q25, stat_q75
        Any may be None if stats.json is missing this file.
    """
    # Identity
    path: str
    filename: str
    catalog_code: str
    kind: str
    scenario: Optional[str] = None
    period: str = ""
    ref_period: Optional[str] = None
    uhi_level: Optional[str] = None  # None=Default(UHI yok), "05"/"10"/"15"/"20" = +0.5/+1/+1.5/+2C

    # Catalog fields (filled by post-init)
    display_code: str = ""
    long_name: str = ""
    category: str = ""
    subcategory: str = ""
    unit: str = ""
    formula: str = ""
    short_description: str = ""
    long_description: str = ""
    is_threshold_variant: bool = False
    parent_code: Optional[str] = None
    threshold: Optional[Dict[str, Any]] = None

    # Stats (filled by load step)
    stat_min: Optional[float] = None
    stat_max: Optional[float] = None
    stat_mean: Optional[float] = None
    stat_median: Optional[float] = None
    stat_q25: Optional[float] = None
    stat_q75: Optional[float] = None

    def merge_catalog(self) -> None:
        """Populate catalog fields from INDICES_CATALOG[self.catalog_code]."""
        entry = INDICES_CATALOG[self.catalog_code]
        self.display_code = entry["display_code"]
        self.long_name = entry["long_name"]
        self.category = entry["category"]
        self.subcategory = entry["subcategory"]
        self.unit = entry["unit"]
        self.formula = entry["formula"]
        self.short_description = entry["short_description"]
        self.long_description = entry["long_description"]
        self.is_threshold_variant = entry["is_threshold_variant"]
        self.parent_code = entry["parent_code"]
        self.threshold = entry["threshold"]

    def merge_stats(self, stats_dict: Dict[str, Any]) -> None:
        """Populate stat_* fields from stats.json entry for this filename."""
        s = stats_dict.get(self.filename)
        if not s:
            return
        self.stat_min = s.get("min")
        self.stat_max = s.get("max")
        self.stat_mean = s.get("mean")
        self.stat_median = s.get("median")
        self.stat_q25 = s.get("q25")
        self.stat_q75 = s.get("q75")

    # ----- Convenience display helpers --------------------------------------

    @property
    def period_label(self) -> str:
        """Compact period prefix for UI labels.
        Historical: '[1995-2014]' or '[2000-2006]' (real period from filename)
        Future:     '[SSP245 | 2041-2060]'
        """
        if self.kind == "historical":
            return f"[{self.period}]"
        return f"[{(self.scenario or '').upper()} | {self.period}]"

    @property
    def display_label(self) -> str:
        """Full UI label, e.g.
        '[1995-2014] UTCI (> 32 °C) - Strong Heat Stress Days'.
        """
        return f"{self.period_label} {self.display_code} - {self.long_name}"


# ---------------------------------------------------------------------------
# Filename parser
# ---------------------------------------------------------------------------
# Reuses the same logic as nc_to_tif.py, adapted for .tif filenames.
#
# Historical:
#   CHELSA_TR_clim_<startY>_<endY>_<INDICE>_<longname>[_<thresh>_<days>[_count]].tif
#
# Future:
#   CHELSA_TR_clim_<refS>_<refE>_sum_Ensemble_GCMs_<ssp>_<futS>_<futE>_<INDICE>_<longname>[_<thresh>_<days>[_count]].tif
#
# Threshold suffix examples that must match:
#   _gt32_hot_days                           (legacy)
#   _ltm13_cold_days                         (legacy)
#   _gt32_strong_heat_days_count             (UTCI ISO variant)
#   _gt38_very_strong_heat_days_count        (UTCI ISO variant)
#   _lt0_cold_days_count                     (UTCI ISO variant)
#   _ltm13_strong_cold_days_count            (UTCI ISO variant)
#   _bw0_9_slight_cold_days_count            (UTCI ISO variant, "between")
#   _bw9_26_comfort_days_count               (UTCI ISO variant, "between")

THRESHOLD_SUFFIX_RE = re.compile(
    r"_(gt\d+|lt\d+|ltm\d+|bw\d+_\d+)_([a-z_]+_days)(_count)?$",
    re.IGNORECASE,
)

# Known parent indice codes from the catalog, sorted by length DESC so that
# multi-token codes (TR_EXT, THI_C, CDD_A...) match before single-token codes.
_PARENT_CODES = sorted(
    {v["parent_code"] if v["is_threshold_variant"] else v["code"]
     for v in INDICES_CATALOG.values()},
    key=len,
    reverse=True,
)


def parse_tif_filename(filename: str) -> Dict[str, Any]:
    """
    Parse a .tif filename and return identity dict.

    Returns:
        {
          "kind": "historical" | "future" | "",
          "scenario": "ssp126" | "ssp245" | "ssp585" | None,
          "period": "YYYY-YYYY",
          "ref_period": "YYYY-YYYY" | None,
          "catalog_code": "FD" | "UTCI_GT32" | "UTCI_BW9_26" | "" if no match
        }
    """
    out: Dict[str, Any] = {
        "kind": "",
        "scenario": None,
        "period": "",
        "ref_period": None,
        "catalog_code": "",
        "uhi_level": None,
        "is_pct": False,
    }

    name = filename.replace(".tif", "")

    # YAGIS yuzde-degisim varyanti: "..._PRCPTOT_annual_total_precip_pct"
    # _pct'yi CIKAR, sonra catalog_code'a "_PCT" ekleyerek ayri katman yap.
    is_pct = False
    if name.lower().endswith("_pct"):
        is_pct = True
        name = name[:-4]  # "_pct" kaldir
    out["is_pct"] = is_pct

    # UHI etiketi: "..._{ssp}_{futS}_{futE}_UHI05_UTCI_..." -> uhi_level="05"
    # UHI'yi isimden CIKAR ki geri kalan normal UTCI gibi parse edilsin.
    m_uhi = re.search(r"_UHI(\d{2})_", name)
    if m_uhi:
        out["uhi_level"] = m_uhi.group(1)
        name = name.replace(f"_UHI{m_uhi.group(1)}_", "_", 1)

    # Threshold suffix (gt32_hot_days, gt32_strong_heat_days_count,
    # bw9_26_comfort_days_count, etc.). We strip the WHOLE matched suffix
    # so the parent indice code is searched only in the leading part of
    # the filename.
    m_ts = THRESHOLD_SUFFIX_RE.search(name)
    threshold_part = ""
    if m_ts:
        # group(1) = "gt32" | "bw9_26" | "ltm13" | ...
        threshold_part = m_ts.group(1).lower()
        name_for_indice = name[: m_ts.start()]
    else:
        name_for_indice = name

    # kind / scenario / periods
    if "sum_Ensemble_GCMs" in name:
        out["kind"] = "future"
        m_ssp = re.search(r"(ssp\d{3})", name, re.IGNORECASE)
        if m_ssp:
            out["scenario"] = m_ssp.group(1).lower()
        periods = re.findall(r"(\d{4})_(\d{4})", name)
        if len(periods) >= 2:
            out["ref_period"] = f"{periods[0][0]}-{periods[0][1]}"
            out["period"] = f"{periods[1][0]}-{periods[1][1]}"
    else:
        out["kind"] = "historical"
        m_per = re.search(r"_clim_(\d{4})_(\d{4})_", name)
        if m_per:
            out["period"] = f"{m_per.group(1)}-{m_per.group(2)}"

    # Indice code: search AFTER the period segment so we don't match
    # the "TR_" country code at the start of every filename.
    if out["kind"] == "future":
        # Find the SECOND occurrence of <YYYY>_<YYYY>_ (futS_futE)
        all_pers = list(re.finditer(r"_(\d{4})_(\d{4})_", name_for_indice))
        search_start = all_pers[1].end() - 1 if len(all_pers) >= 2 else 0
    else:
        m_per = re.search(r"_\d{4}_\d{4}_", name_for_indice)
        search_start = m_per.end() - 1 if m_per else 0

    suffix = name_for_indice[search_start:]
    found_code = ""
    for code in _PARENT_CODES:
        if re.search(rf"_{re.escape(code)}(_|$)", suffix):
            found_code = code
            break

    # Map to final catalog code (parent or threshold variant)
    if found_code:
        if threshold_part:
            # Two threshold operator families:
            #   1) gt<N>, lt<N>, ltm<N>     ->  candidate = <PARENT>_<OP><N>
            #      e.g. "gt32"  -> "UTCI_GT32"
            #           "ltm13" -> "UTCI_LTM13"
            #           "lt0"   -> "UTCI_LT0"
            #   2) bw<A>_<B>                 ->  candidate = <PARENT>_BW<A>_<B>
            #      e.g. "bw9_26"  -> "UTCI_BW9_26"
            #           "bw0_9"   -> "UTCI_BW0_9"
            m_bw = re.match(r"bw(\d+)_(\d+)$", threshold_part)
            m_sided = re.match(r"(gt|lt|ltm)(\d+)$", threshold_part)
            candidate = ""
            if m_bw:
                a, b = m_bw.group(1), m_bw.group(2)
                candidate = f"{found_code}_BW{a}_{b}"
            elif m_sided:
                op = m_sided.group(1).upper()
                val = m_sided.group(2)
                candidate = f"{found_code}_{op}{val}"
            if candidate and candidate in INDICES_CATALOG:
                out["catalog_code"] = candidate
        else:
            if found_code in INDICES_CATALOG:
                out["catalog_code"] = found_code

    # YAGIS _pct: catalog_code'a "_PCT" ekle (ayri katman: PRCPTOT_PCT vs)
    if out.get("is_pct") and out["catalog_code"]:
        pct_code = f"{out['catalog_code']}_PCT"
        if pct_code in INDICES_CATALOG:
            out["catalog_code"] = pct_code
        else:
            # _PCT katalog'da yoksa bu tif'i eslesmez say (gorunmez)
            out["catalog_code"] = ""

    return out


# ---------------------------------------------------------------------------
# Discovery — find all TIFs on disk and build IndexFile list
# ---------------------------------------------------------------------------

def _load_stats() -> Dict[str, Any]:
    """Load stats.json (returns empty dict if missing)."""
    if not os.path.exists(STATS_PATH):
        return {}
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _discover_tifs() -> List[Dict[str, str]]:
    """
    Walk the indices directory tree and return a list of dicts:
        [{"path": "...", "filename": "...", "kind_dir": "historical" | "ssp245" | ...}, ...]
    """
    results: List[Dict[str, str]] = []

    # Historical
    hist_dir = Path(INDICES_DIR_HISTORICAL)
    if hist_dir.exists():
        for p in sorted(hist_dir.glob("*.tif")):
            results.append({"path": str(p), "filename": p.name,
                            "kind_dir": "historical"})

    # Future scenarios
    for scenario, scen_dir in FUTURE_SCENARIOS.items():
        sd = Path(scen_dir)
        if sd.exists():
            for p in sorted(sd.glob("*.tif")):
                results.append({"path": str(p), "filename": p.name,
                                "kind_dir": scenario})

    return results


def load_all_index_files() -> List[IndexFile]:
    """
    Main entry point. Discover all TIFs, parse, enrich with catalog + stats,
    and return a list of IndexFile objects.

    Files whose indice_code is not in the catalog are SILENTLY DROPPED
    (e.g. a leftover THI parent file would be skipped). If you want to debug,
    call `load_all_index_files_with_diagnostics()` instead.
    """
    return load_all_index_files_with_diagnostics()[0]


def load_all_index_files_with_diagnostics() -> tuple[List[IndexFile], Dict[str, Any]]:
    """
    Same as load_all_index_files but also returns a diagnostics dict:
        {
          "total_tifs": int,
          "matched": int,
          "unmatched_files": list[str],
        }
    Useful for sanity-checking the catalog against the filesystem.
    """
    stats_dict = _load_stats()
    tifs = _discover_tifs()

    files: List[IndexFile] = []
    unmatched: List[str] = []

    for entry in tifs:
        parsed = parse_tif_filename(entry["filename"])
        if not parsed["catalog_code"]:
            unmatched.append(entry["filename"])
            continue

        ifile = IndexFile(
            path=entry["path"],
            filename=entry["filename"],
            catalog_code=parsed["catalog_code"],
            kind=parsed["kind"],
            scenario=parsed["scenario"],
            period=parsed["period"],
            ref_period=parsed["ref_period"],
            uhi_level=parsed.get("uhi_level"),
        )
        ifile.merge_catalog()
        ifile.merge_stats(stats_dict)
        files.append(ifile)

    diagnostics = {
        "total_tifs": len(tifs),
        "matched": len(files),
        "unmatched_files": unmatched,
    }
    return files, diagnostics


# ---------------------------------------------------------------------------
# Filter helpers — what the UI uses
# ---------------------------------------------------------------------------

_UHI_UNSET = "__unset__"


def filter_files(
    files: List[IndexFile],
    kind: Optional[str] = None,
    scenario: Optional[str] = None,
    period: Optional[str] = None,
    catalog_code: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    uhi_level: Optional[str] = _UHI_UNSET,
) -> List[IndexFile]:
    """
    Apply zero or more filters and return the matching subset.
    All filters use equality; pass None to skip a filter.

    uhi_level:
      - not passed (default _UHI_UNSET) -> no UHI filtering (all pass)
      - None                            -> only Default files (uhi_level is None)
      - "05"/"10"/"15"/"20"             -> only that UHI warming level
    """
    out = files
    if kind is not None:
        out = [f for f in out if f.kind == kind]
    if scenario is not None:
        out = [f for f in out if f.scenario == scenario]
    if period is not None:
        out = [f for f in out if f.period == period]
    if catalog_code is not None:
        out = [f for f in out if f.catalog_code == catalog_code]
    if category is not None:
        out = [f for f in out if f.category == category]
    if subcategory is not None:
        out = [f for f in out if f.subcategory == subcategory]
    if uhi_level != _UHI_UNSET:
        out = [f for f in out if f.uhi_level == uhi_level]
    return out


def get_periods_for(files: List[IndexFile], catalog_code: str,
                    scenario: Optional[str] = None) -> List[str]:
    """All available periods for a given indice (+ optional scenario filter).
    Useful for: 'user picks UTCI; show them which periods exist'."""
    subset = filter_files(files, catalog_code=catalog_code, scenario=scenario)
    return sorted({f.period for f in subset})


def get_scenarios_for(files: List[IndexFile], catalog_code: str) -> List[str]:
    """All scenarios where this indice has at least one file (future only)."""
    subset = filter_files(files, catalog_code=catalog_code, kind="future")
    return sorted({f.scenario for f in subset if f.scenario})


def get_catalog_codes_in(files: List[IndexFile],
                         subcategory: Optional[str] = None,
                         category: Optional[str] = None,
                         scenario: Optional[str] = None) -> List[str]:
    """List of distinct catalog_code values within filtered set.
    Used to render sidebar item lists."""
    subset = filter_files(files, subcategory=subcategory, category=category,
                          scenario=scenario)
    return sorted({f.catalog_code for f in subset})


# ---------------------------------------------------------------------------
# Self-check — run as script for sanity
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    files, diag = load_all_index_files_with_diagnostics()

    print(f"Total TIFs on disk : {diag['total_tifs']}")
    print(f"Matched to catalog : {diag['matched']}")
    if diag["unmatched_files"]:
        print(f"Unmatched ({len(diag['unmatched_files'])}):")
        for fn in diag["unmatched_files"][:10]:
            print(f"  {fn}")

    # Quick breakdown
    from collections import Counter
    by_kind = Counter(f.kind for f in files)
    by_scen = Counter(f.scenario for f in files if f.scenario)
    by_cat = Counter(f.category for f in files)
    by_sub = Counter(f.subcategory for f in files)

    print()
    print(f"By kind     : {dict(by_kind)}")
    print(f"By scenario : {dict(by_scen)}")
    print(f"By category : {dict(by_cat)}")
    print(f"By subcat   : {dict(by_sub)}")

    # Sample IndexFile
    print()
    print("Sample IndexFile (first one):")
    f = files[0]
    print(f"  path             : {f.path}")
    print(f"  filename         : {f.filename}")
    print(f"  catalog_code     : {f.catalog_code}")
    print(f"  kind             : {f.kind}")
    print(f"  scenario         : {f.scenario}")
    print(f"  period           : {f.period}")
    print(f"  ref_period       : {f.ref_period}")
    print(f"  display_code     : {f.display_code}")
    print(f"  long_name        : {f.long_name}")
    print(f"  unit             : {f.unit}")
    print(f"  category         : {f.category}")
    print(f"  subcategory      : {f.subcategory}")
    print(f"  stats min/max    : {f.stat_min} / {f.stat_max}")
    print(f"  display_label    : {f.display_label}")

    # Filter example
    print()
    print("Filter test — historical TEMPERATURE indices:")
    hist_temp = filter_files(files, kind="historical", subcategory="TEMPERATURE")
    for f in hist_temp:
        print(f"  {f.catalog_code:12s} | {f.long_name}")

    print()
    print("Filter test — all periods/scenarios available for UTCI:")
    for sc in get_scenarios_for(files, "UTCI"):
        periods = get_periods_for(files, "UTCI", scenario=sc)
        print(f"  {sc}: {periods}")
    hist_periods = get_periods_for(files, "UTCI", scenario=None)
    hist_only = [p for p in hist_periods if "1995-2014" in p or "2000-2006" in p]
    print(f"  historical (no scenario filter): {hist_periods}")

    # UTCI variants explicit check
    print()
    print("UTCI variants discovered:")
    utci_codes = sorted({f.catalog_code for f in files
                         if f.catalog_code.startswith("UTCI")})
    for code in utci_codes:
        n_hist = sum(1 for f in files if f.catalog_code == code
                     and f.kind == "historical")
        n_fut = sum(1 for f in files if f.catalog_code == code
                    and f.kind == "future")
        entry = INDICES_CATALOG.get(code, {})
        print(f"  {code:14s} | hist={n_hist} fut={n_fut} | "
              f"{entry.get('display_code', '?')} - "
              f"{entry.get('long_name', '?')}")