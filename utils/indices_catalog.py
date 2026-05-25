"""
indices_catalog.py

Climate Indices Map Tool - Master Catalog of Indices
=====================================================

SOURCE OF TRUTH for all 69 indices used in the tool. Everything the UI,
COG converter, and downstream analytics need to know about an index lives
here - display names, units, descriptions, formulas, categories.

DO NOT read metadata from NetCDF files at runtime. NetCDF attribute
inconsistencies make this module the authority. New indices should be
added here; NetCDF attributes can be corrected later.

USAGE
-----
    from utils.indices_catalog import INDICES_CATALOG, get_indices_by_subcategory

    pcd = INDICES_CATALOG["PCD"]
    print(pcd["long_name"])        # "Passive Comfort Days"
    print(pcd["short_description"])

    temp_indices = get_indices_by_subcategory("TEMPERATURE")

STRUCTURE
---------
Each entry has these fields:

  Identity:
    code              : Catalog key (e.g. "PCD", "UTCI_GT32")
    display_code      : What the UI shows (e.g. "PCD", "UTCI (>32 °C)")
    long_name         : Full English name (e.g. "Passive Comfort Days")
                        For threshold variants: a descriptive variant name,
                        e.g. "Strong Heat Stress Days", "Hot Days (Heat Index)"

  Classification (two-level hierarchy):
    category          : "CLIMATE" | "BIO_CLIMATE"   (top-level sidebar)
    subcategory       : Mid-level sidebar group

  Unit:
    unit              : Clean unit string (e.g. "days/year", "°C", "mm",
                        "0-1" for dimensionless)

  Documentation:
    formula           : Single-line clean math (e.g. "TN < 0 °C").
                        "(TBD)" for indices whose method is not yet
                        documented here.
    short_description : ~150 chars, what it measures (hover tooltip)
    long_description  : 2-4 sentences, why it matters (info button)

  Computation:
    source_variables  : Which raw climate vars feed this index

  Threshold variant relationship (for sub-indices):
    is_threshold_variant : True for the *_GT## / *_LT## / *_BW## entries
    parent_code          : Parent index code (None for main indices)
    threshold            : {"operator": ">"|"<"|"between",
                            "value": float or tuple, "unit": ...}

NOTES
-----
- typical_range was REMOVED in v2. Slider defaults come from per-file
  stats (stats.json), not from a hardcoded range here.
- All degree-Celsius notations use the proper ° symbol (e.g. "°C")
  rather than "deg C".

UTCI VARIANTS (ISO 15743 / Brode 2012 thermal stress categories)
----------------------------------------------------------------
The UTCI parent index has SEVEN threshold variants spanning the full
cold-to-hot stress spectrum:
    UTCI_LTM13   (< -13 °C)   strong cold stress
    UTCI_LT0     (< 0 °C)     moderate cold stress
    UTCI_BW0_9   (0 to 9 °C)  slight cold stress
    UTCI_BW9_26  (9 to 26 °C) no thermal stress (comfort zone)
    UTCI_GT26    (> 26 °C)    moderate heat stress
    UTCI_GT32    (> 32 °C)    strong heat stress
    UTCI_GT38    (> 38 °C)    very strong heat stress

NAMING CONVENTIONS IN FORMULAS
------------------------------
- TG = daily mean temperature (tas)
- TX = daily max temperature (tasmax)
- TN = daily min temperature (tasmin)
- TA = air temperature (used in bioclimate formulas)
- PR = daily precipitation flux (pr)
- HURS = relative humidity (hurs)
- MRT = mean radiant temperature
- Tdp = dew-point temperature
"""

# ---------------------------------------------------------------------------
# Category & subcategory enums
# ---------------------------------------------------------------------------

CATEGORIES = ["CLIMATE", "BIO_CLIMATE"]

SUBCATEGORIES = {
    "CLIMATE": [
        "TEMPERATURE",      # 14 indices
        "PRECIPITATION",    # 10 indices
        "DROUGHT",          # 4 indices
        "ENERGY",           # 5 indices (heating/cooling demand)
        "AGRICULTURE",      # 3 indices (plant growth)
    ],
    "BIO_CLIMATE": [
        "HUMAN_COMFORT",    # 22 indices (UTCI now has 7 ISO variants)
        "LIVESTOCK",        # 6 indices (THI family)
        "ATMOSPHERIC",      # 5 indices (empirical wind/humidity combined)
    ],
}

# Pretty labels for UI rendering
CATEGORY_LABELS = {
    "CLIMATE":     "Climate Indices",
    "BIO_CLIMATE": "Bio-Climate Indices",
}

SUBCATEGORY_LABELS = {
    "TEMPERATURE":   "Temperature",
    "PRECIPITATION": "Precipitation",
    "DROUGHT":       "Drought",
    "ENERGY":        "Energy (Heating & Cooling)",
    "AGRICULTURE":   "Agriculture (Growing)",
    "HUMAN_COMFORT": "Human Comfort",
    "LIVESTOCK":     "Agriculture & Livestock",
    "ATMOSPHERIC":   "Atmospheric Comfort",
}


# ---------------------------------------------------------------------------
# THE CATALOG
# ---------------------------------------------------------------------------
# 69 indices total:
#   CLIMATE:     14 + 10 + 4 + 5 + 3 = 36
#   BIO_CLIMATE: 22 + 6 + 5            = 33
# ---------------------------------------------------------------------------

INDICES_CATALOG = {

    # =======================================================================
    # CLIMATE / TEMPERATURE (14)
    # =======================================================================

    "FD": {
        "code": "FD",
        "display_code": "FD",
        "long_name": "Frost Days",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TN < 0 °C",
        "short_description": "Number of days per year when daily minimum temperature falls below 0 °C.",
        "long_description": "A primary indicator of cold-season severity. Late frosts can damage early-blooming fruit trees, and freezing nights cause pipe bursts and other infrastructure damage. The index also helps delineate the start and end of the growing season.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "ID": {
        "code": "ID",
        "display_code": "ID",
        "long_name": "Ice Days",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TX < 0 °C",
        "short_description": "Number of days per year when daily maximum temperature stays below 0 °C.",
        "long_description": "Identifies days of persistent sub-freezing conditions, when snow cover does not melt during the day. Critical for road icing, transport safety, and peak heating energy demand.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "SU": {
        "code": "SU",
        "display_code": "SU",
        "long_name": "Summer Days",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TX > 25 °C",
        "short_description": "Number of days per year when daily maximum temperature exceeds 25 °C.",
        "long_description": "A common indicator of warm-season length, relevant to tourism, outdoor activity planning, and the onset of cooling energy demand.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TR": {
        "code": "TR",
        "display_code": "TR",
        "long_name": "Tropical Nights",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TN > 20 °C",
        "short_description": "Number of nights per year when minimum temperature stays above 20 °C.",
        "long_description": "Warm nights prevent the body from cooling and recovering during sleep. A robust indicator of the Urban Heat Island effect and a known risk factor for vulnerable populations such as the elderly.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TR_EXT": {
        "code": "TR_EXT",
        "display_code": "TR_EXT",
        "long_name": "Extended Tropical Nights",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TN > 25 °C",
        "short_description": "Number of nights per year when minimum temperature stays above 25 °C.",
        "long_description": "An extreme threshold associated with significant cardiovascular stress, where outdoor life without active cooling becomes impractical. Used to identify the most heat-exposed regions and periods.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TXX": {
        "code": "TXX",
        "display_code": "TXX",
        "long_name": "Max Daily Max Temperature",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "°C",
        "formula": "max(TX)",
        "short_description": "Annual highest daily maximum temperature - the absolute record day.",
        "long_description": "Indicator of extreme heat events. Drives infrastructure problems (asphalt deformation, rail buckling), peak wildfire risk, and the highest-load day for electrical grids.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TNN": {
        "code": "TNN",
        "display_code": "TNN",
        "long_name": "Min Daily Min Temperature",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "°C",
        "formula": "min(TN)",
        "short_description": "Annual lowest daily minimum temperature - the coldest moment of the year.",
        "long_description": "Defines the survival limit for winter crops (wheat, etc.) and creates hypothermia risk for outdoor livestock. Marks the coldest-day load for energy infrastructure.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TNX": {
        "code": "TNX",
        "display_code": "TNX",
        "long_name": "Max Daily Min Temperature",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "°C",
        "formula": "max(TN)",
        "short_description": "Annual highest daily minimum temperature - the warmest night.",
        "long_description": "Identifies the night when temperatures fail to drop, when heat accumulation is at its maximum. Disrupts the balance of nocturnal species in ecosystems.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "TXN": {
        "code": "TXN",
        "display_code": "TXN",
        "long_name": "Min Daily Max Temperature",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "°C",
        "formula": "min(TX)",
        "short_description": "Annual lowest daily maximum temperature - the coldest daytime.",
        "long_description": "Identifies days when even noon temperatures remain very cold, when snow cover persists, and when the energy grid faces its coldest-daytime load.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "HW": {
        "code": "HW",
        "display_code": "HW",
        "long_name": "Heat Wave Index",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TX > 30 °C for at least 3 consecutive days",
        "short_description": "Days within heat waves: three or more consecutive days with TX above 30 °C.",
        "long_description": "Directly correlates with elevated mortality rates. In agriculture, drives water stress, crop failure, and yield loss at disaster scale.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CW": {
        "code": "CW",
        "display_code": "CW",
        "long_name": "Cold Wave Index",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TN < 0 °C for at least 3 consecutive days",
        "short_description": "Days within cold waves: three or more consecutive days with TN below 0 °C.",
        "long_description": "Sudden, prolonged cold spells cause mortality in migratory birds and disturb the ecological balance of hibernating species.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "WSDI": {
        "code": "WSDI",
        "display_code": "WSDI",
        "long_name": "Warm Spell Duration Index",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TX > 90th percentile (5-day window), for at least 6 consecutive days",
        "short_description": "Days in extended warm spells, relative to the local climate baseline.",
        "long_description": "One of the clearest fingerprints of regional warming. Drives the replacement of native species by heat-tolerant invasives and shifts ecological balance.",
        "source_variables": ["tasmax"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CSDI": {
        "code": "CSDI",
        "display_code": "CSDI",
        "long_name": "Cold Spell Duration Index",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "days/year",
        "formula": "TN < 10th percentile (5-day window), for at least 6 consecutive days",
        "short_description": "Days in extended cold spells, relative to the local climate baseline.",
        "long_description": "Sustained cold periods are required to keep pest insect populations in check. Their decline allows agricultural pests to flourish year-round.",
        "source_variables": ["tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "DTR": {
        "code": "DTR",
        "display_code": "DTR",
        "long_name": "Diurnal Temperature Range",
        "category": "CLIMATE",
        "subcategory": "TEMPERATURE",
        "unit": "°C",
        "formula": "mean(TX - TN)",
        "short_description": "Average difference between daily maximum and minimum temperature.",
        "long_description": "High DTR creates physiological stress on both plants and humans (cardiovascular and respiratory effects). It also drives expansion and cracking in building materials such as concrete and asphalt, and serves as an indicator of climatic harshness.",
        "source_variables": ["tasmax", "tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # CLIMATE / PRECIPITATION (10)
    # =======================================================================

    "PRCPTOT": {
        "code": "PRCPTOT",
        "display_code": "PRCPTOT",
        "long_name": "Annual Total Precipitation",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "mm",
        "formula": "sum(PR) for PR >= 1 mm/day",
        "short_description": "Total annual precipitation, summed over all wet days (PR >= 1 mm).",
        "long_description": "Determines a region's overall water budget. A primary indicator for reservoir fill rates and groundwater reserves.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "RX1DAY": {
        "code": "RX1DAY",
        "display_code": "RX1DAY",
        "long_name": "Max 1-Day Precipitation",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "mm/day",
        "formula": "max(daily PR)",
        "short_description": "Annual maximum precipitation in a single day.",
        "long_description": "A primary driver of flash floods. Determines the capacity limits of urban sewer and stormwater drainage systems.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "RX5DAY": {
        "code": "RX5DAY",
        "display_code": "RX5DAY",
        "long_name": "Max 5-Day Precipitation",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "mm",
        "formula": "max(5-day cumulative PR)",
        "short_description": "Annual maximum precipitation over any 5 consecutive days.",
        "long_description": "Measures soil water saturation. The most critical signal for dam overflow, river flooding, and landslide risk.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "SDII": {
        "code": "SDII",
        "display_code": "SDII",
        "long_name": "Simple Daily Intensity Index",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "mm/day",
        "formula": "sum(PR) / wet_days, where PR >= 1 mm/day",
        "short_description": "Average precipitation amount on wet days (PR >= 1 mm).",
        "long_description": "Indicates the intensity of precipitation events. High values drive soil erosion and increase surface runoff, reducing groundwater infiltration.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "R10MM": {
        "code": "R10MM",
        "display_code": "R10MM",
        "long_name": "Heavy Precipitation Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "count(PR >= 10 mm/day)",
        "short_description": "Number of days per year with precipitation >= 10 mm.",
        "long_description": "Marks heavy rainfall events that disrupt urban traffic, halt outdoor commerce, and reduce urban comfort.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "R20MM": {
        "code": "R20MM",
        "display_code": "R20MM",
        "long_name": "Very Heavy Precipitation Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "count(PR >= 20 mm/day)",
        "short_description": "Number of days per year with precipitation >= 20 mm.",
        "long_description": "Marks very heavy rainfall events that severely disrupt urban traffic, halt outdoor commerce, and may trigger localized flooding.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CDD_P": {
        "code": "CDD_P",
        "display_code": "CDD_P",
        "long_name": "Consecutive Dry Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "max(consecutive days with PR < 1 mm/day)",
        "short_description": "Longest run of consecutive dry days (PR < 1 mm/day) in a year.",
        "long_description": "A leading indicator of agricultural drought and water stress. Defines the length of the fire season and the fragility of natural ecosystems.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CWD": {
        "code": "CWD",
        "display_code": "CWD",
        "long_name": "Consecutive Wet Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "max(consecutive days with PR >= 1 mm/day)",
        "short_description": "Longest run of consecutive wet days (PR >= 1 mm/day) in a year.",
        "long_description": "Prolonged moisture triggers fungal diseases in agriculture, halts construction work, and causes humidity-related damage to buildings.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "R95P": {
        "code": "R95P",
        "display_code": "R95P",
        "long_name": "Very Wet Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "count(PR > 95th percentile of wet days)",
        "short_description": "Days exceeding the 95th percentile of historical wet-day precipitation.",
        "long_description": "Measures the frequency of precipitation extremes relative to the local climate baseline. Used to assess insurance risk, calibrate disaster-management plans, and set infrastructure resilience standards.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "R99P": {
        "code": "R99P",
        "display_code": "R99P",
        "long_name": "Extremely Wet Days",
        "category": "CLIMATE",
        "subcategory": "PRECIPITATION",
        "unit": "days/year",
        "formula": "count(PR > 99th percentile of wet days)",
        "short_description": "Days exceeding the 99th percentile of historical wet-day precipitation.",
        "long_description": "Measures the frequency of the most extreme rainfall events. Used to assess insurance risk, calibrate disaster-management plans, and set infrastructure resilience standards.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # CLIMATE / DROUGHT (4)
    # =======================================================================

    "PNP": {
        "code": "PNP",
        "display_code": "PNP",
        "long_name": "Percent of Normal Precipitation",
        "category": "CLIMATE",
        "subcategory": "DROUGHT",
        "unit": "%",
        "formula": "(PR_annual / PR_climatology) * 100",
        "short_description": "Annual precipitation expressed as a percentage of the long-term mean.",
        "long_description": "The most communicable drought indicator. Below 100% means a drier-than-normal year, above 100% means a wetter-than-normal year. Widely used in public communication.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "SPI12": {
        "code": "SPI12",
        "display_code": "SPI12",
        "long_name": "Standardized Precipitation Index (12-month)",
        "category": "CLIMATE",
        "subcategory": "DROUGHT",
        "unit": "0-1",  # actually z-score, ~(-3,3)
        "formula": "Gamma distribution, 12-month rolling window",
        "short_description": "Standardized z-score of 12-month precipitation, relative to historical baseline.",
        "long_description": "A long-term meteorological drought indicator at the hydrological time scale. Captures impacts on reservoirs, groundwater, and long-duration droughts.",
        "source_variables": ["pr"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "SPEI12": {
        "code": "SPEI12",
        "display_code": "SPEI12",
        "long_name": "Standardized Precipitation-Evapotranspiration Index (12-month)",
        "category": "CLIMATE",
        "subcategory": "DROUGHT",
        "unit": "0-1",  # actually z-score
        "formula": "Water balance (PR - PET), log-logistic distribution, 12-month window",
        "short_description": "Like SPI but also includes evapotranspiration; captures temperature-driven drying.",
        "long_description": "An advanced drought indicator that combines precipitation deficit with atmospheric demand. More sensitive than SPI to climate-change-driven drying.",
        "source_variables": ["pr", "tas", "tasmax", "tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "AI": {
        "code": "AI",
        "display_code": "AI",
        "long_name": "Aridity Index",
        "category": "CLIMATE",
        "subcategory": "DROUGHT",
        "unit": "0-1",
        "formula": "PR_annual / PET_annual",
        "short_description": "Ratio of annual precipitation to potential evapotranspiration (UNEP 1992).",
        "long_description": "Indicates regional aridity and desertification trends. Values below 0.65 indicate arid or semi-arid zones at risk of desertification.",
        "source_variables": ["pr", "tas", "tasmax", "tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # CLIMATE / ENERGY (5) - heating & cooling demand
    # =======================================================================

    "HD": {
        "code": "HD",
        "display_code": "HD",
        "long_name": "Heating Days",
        "category": "CLIMATE",
        "subcategory": "ENERGY",
        "unit": "days/year",
        "formula": "TG < 18 °C",
        "short_description": "Number of days per year that (theoretically) require heating.",
        "long_description": "Indicates the duration of the heating season - how many days central heating would need to operate, regardless of intensity.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "HDD": {
        "code": "HDD",
        "display_code": "HDD",
        "long_name": "Heating Degree Days",
        "category": "CLIMATE",
        "subcategory": "ENERGY",
        "unit": "°C * days",
        "formula": "sum(18 °C - TG), only when TG < 18 °C",
        "short_description": "Cumulative heating energy demand - how much heating is needed, not just how often.",
        "long_description": "Directly predicts natural gas and coal consumption. Rising HDD translates to higher household energy costs and carbon emissions.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CD": {
        "code": "CD",
        "display_code": "CD",
        "long_name": "Cooling Days",
        "category": "CLIMATE",
        "subcategory": "ENERGY",
        "unit": "days/year",
        "formula": "TG > 21 °C",
        "short_description": "Number of days per year that (theoretically) require cooling.",
        "long_description": "Indicates the duration of the cooling season - how many days air conditioning or fans would be needed, regardless of intensity.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CDD": {
        "code": "CDD",
        "display_code": "CDD",
        "long_name": "Cooling Degree Days",
        "category": "CLIMATE",
        "subcategory": "ENERGY",
        "unit": "°C * days",
        "formula": "sum(TG - 21 °C), only when TG > 21 °C",
        "short_description": "Cumulative cooling energy demand - measures both how often and how intensely.",
        "long_description": "Determines the intensity of air-conditioning demand. Reflects the summer load on the electrical grid; higher CDD means greater peak-demand stress.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "CDD_A": {
        "code": "CDD_A",
        "display_code": "CDD_A",
        "long_name": "Cooling Degree Days (Approximated)",
        "category": "CLIMATE",
        "subcategory": "ENERGY",
        "unit": "°C * days",
        "formula": "Sinusoidal approximation (Spinoni 2018), threshold 21 °C",
        "short_description": "A more precise cooling demand estimate using daily TX and TN to capture diurnal variation.",
        "long_description": "Captures cooling demand at peak afternoon temperatures, which can be underestimated when using daily mean alone. Recommended for fine-grained energy planning.",
        "source_variables": ["tas", "tasmax", "tasmin"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # CLIMATE / AGRICULTURE (3) - plant growth
    # =======================================================================

    "GD": {
        "code": "GD",
        "display_code": "GD",
        "long_name": "Growing Days",
        "category": "CLIMATE",
        "subcategory": "AGRICULTURE",
        "unit": "days/year",
        "formula": "TG > 5 °C",
        "short_description": "Number of days when plants are biologically active (above dormancy threshold).",
        "long_description": "The total number of days a plant can grow. Used to predict when crops such as maize or wheat will reach harvest maturity.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "GDD": {
        "code": "GDD",
        "display_code": "GDD",
        "long_name": "Growing Degree Days",
        "category": "CLIMATE",
        "subcategory": "AGRICULTURE",
        "unit": "°C * days",
        "formula": "sum(TG - 5 °C), only when TG > 5 °C",
        "short_description": "Cumulative heat above 5 °C - the thermal energy available for plant growth.",
        "long_description": "Sums the 'useful' temperatures above 5 °C. Higher GDD means crops mature faster; a key planning variable for sowing and harvest dates.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "GSL": {
        "code": "GSL",
        "display_code": "GSL",
        "long_name": "Growing Season Length",
        "category": "CLIMATE",
        "subcategory": "AGRICULTURE",
        "unit": "days/year",
        "formula": "TG > 5 °C for 6 consecutive days (start) to 6 consecutive days with TG < 5 °C (end)",
        "short_description": "Length of the period from first sustained warmth in spring to first sustained cold in autumn.",
        "long_description": "The ecological calendar of the year. Climate change is lengthening this period, allowing the spread of invasive species and shifts in vegetation cover.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # BIO_CLIMATE / HUMAN_COMFORT (22) - UTCI now has 7 ISO-15743 variants
    # =======================================================================

    "PCD": {
        "code": "PCD",
        "display_code": "PCD",
        "long_name": "Passive Comfort Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "18 °C <= TG < 25 °C",
        "short_description": "Days that are comfortable without heating or cooling.",
        "long_description": "Days when outdoor activity is comfortable without supplemental heating or cooling. Important for tourism potential and human well-being, and widely used in passive building design.",
        "source_variables": ["tas"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "UTCI": {
        "code": "UTCI",
        "display_code": "UTCI",
        "long_name": "Universal Thermal Climate Index",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Brode (2012) 56-term polynomial: f(TA, HURS, sfcWind, MRT)",
        "short_description": "Outdoor thermal stress as a felt-temperature, combining heat, humidity, wind and radiation.",
        "long_description": "The most rigorous outdoor thermal-stress indicator, jointly developed by ISB-COST. Used by public-health agencies for heat-warning systems and by urban designers to evaluate microclimates.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # ----- UTCI variants (ISO 15743 / Brode 2012, cold -> hot) -----

    "UTCI_LTM13": {
        "code": "UTCI_LTM13",
        "display_code": "UTCI (< -13 °C)",
        "long_name": "Strong Cold Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(UTCI < -13 °C)",
        "short_description": "Days in the 'strong cold stress' UTCI category (UTCI below -13 °C).",
        "long_description": "Marks days of strong outdoor cold stress where hypothermia risk rises sharply without protective clothing. Critical for outdoor workers and unsheltered populations.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": "<", "value": -13, "unit": "°C"},
    },

    "UTCI_LT0": {
        "code": "UTCI_LT0",
        "display_code": "UTCI (< 0 °C)",
        "long_name": "Moderate Cold Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(UTCI < 0 °C)",
        "short_description": "Days in the 'moderate cold stress' UTCI category (UTCI below 0 °C).",
        "long_description": "Days with noticeable outdoor cold stress. Indicates the demand for warm clothing and indoor heating, and the limits of comfortable outdoor activity.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": "<", "value": 0, "unit": "°C"},
    },

    "UTCI_BW0_9": {
        "code": "UTCI_BW0_9",
        "display_code": "UTCI (0 to 9 °C)",
        "long_name": "Slight Cold Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(0 °C <= UTCI < 9 °C)",
        "short_description": "Days in the 'slight cold stress' UTCI category (UTCI between 0 and 9 °C).",
        "long_description": "Cool but not severely stressful conditions. The transition band between full thermal comfort and the cold-stress zones; relevant to seasonal apparel and outdoor activity planning.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": "between", "value": (0, 9), "unit": "°C"},
    },

    "UTCI_BW9_26": {
        "code": "UTCI_BW9_26",
        "display_code": "UTCI (9 to 26 °C)",
        "long_name": "Thermal Comfort Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(9 °C <= UTCI <= 26 °C)",
        "short_description": "Days in the 'no thermal stress' UTCI category (UTCI between 9 and 26 °C).",
        "long_description": "The core human comfort band on the UTCI scale. A direct indicator of regional livability and outdoor-tourism potential. Climate change shifts this band geographically; tracking its retreat is central to adaptation planning.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": "between", "value": (9, 26), "unit": "°C"},
    },

    "UTCI_GT26": {
        "code": "UTCI_GT26",
        "display_code": "UTCI (> 26 °C)",
        "long_name": "Moderate Heat Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(UTCI > 26 °C)",
        "short_description": "Days in the 'moderate heat stress' UTCI category (UTCI above 26 °C).",
        "long_description": "First level of outdoor heat stress on the UTCI scale. Indicates conditions where prolonged physical activity causes noticeable thermal discomfort and increased water demand.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": ">", "value": 26, "unit": "°C"},
    },

    "UTCI_GT32": {
        "code": "UTCI_GT32",
        "display_code": "UTCI (> 32 °C)",
        "long_name": "Strong Heat Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(UTCI > 32 °C)",
        "short_description": "Days in the 'strong heat stress' UTCI category (UTCI above 32 °C).",
        "long_description": "Marks days when the body cannot regulate temperature outdoors without intervention. A core metric for occupational and public-health heat warnings.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": ">", "value": 32, "unit": "°C"},
    },

    "UTCI_GT38": {
        "code": "UTCI_GT38",
        "display_code": "UTCI (> 38 °C)",
        "long_name": "Very Strong Heat Stress Days",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(UTCI > 38 °C)",
        "short_description": "Days in the 'very strong heat stress' UTCI category (UTCI above 38 °C).",
        "long_description": "Extreme outdoor heat stress where sustained activity is dangerous even for healthy adults. A leading indicator of heat-wave intensity and public-health emergency thresholds.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "UTCI",
        "threshold": {"operator": ">", "value": 38, "unit": "°C"},
    },

    # ----- end UTCI variants -----

    "HI": {
        "code": "HI",
        "display_code": "HI",
        "long_name": "Heat Index",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Rothfusz (1990) NWS polynomial: f(TA, HURS)",
        "short_description": "Apparent temperature combining heat and humidity, as used by the US NWS.",
        "long_description": "How hot it actually feels when humidity is considered. Above 32 °C the body cannot cool itself efficiently through perspiration.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "HI_GT32": {
        "code": "HI_GT32",
        "display_code": "HI (> 32 °C)",
        "long_name": "Hot Days (Heat Index)",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(HI > 32 °C)",
        "short_description": "Days where the apparent temperature (Heat Index) exceeds 32 °C.",
        "long_description": "Marks days when heat and humidity combine to a dangerous level. Used by public-health systems to issue heat advisories.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": True,
        "parent_code": "HI",
        "threshold": {"operator": ">", "value": 32, "unit": "°C"},
    },

    "PET": {
        "code": "PET",
        "display_code": "PET",
        "long_name": "Physiologically Equivalent Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Hoeppe (1999) human energy balance: f(TA, HURS, sfcWind, MRT)",
        "short_description": "Equivalent temperature in a reference indoor setting yielding the same body sensation.",
        "long_description": "Translates outdoor conditions into an equivalent indoor temperature that produces the same thermal sensation. Widely used in urban climate and tourism research.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "PET_GT29": {
        "code": "PET_GT29",
        "display_code": "PET (> 29 °C)",
        "long_name": "Hot Days (PET)",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(PET > 29 °C)",
        "short_description": "Days with strong heat stress on the PET scale.",
        "long_description": "Marks days when outdoor activity becomes physiologically stressful. The 29 °C threshold corresponds to 'strong heat stress' in the PET scale.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "PET",
        "threshold": {"operator": ">", "value": 29, "unit": "°C"},
    },

    "PET_LT8": {
        "code": "PET_LT8",
        "display_code": "PET (< 8 °C)",
        "long_name": "Cold Days (PET)",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "days/year",
        "formula": "count(PET < 8 °C)",
        "short_description": "Days with strong cold stress on the PET scale.",
        "long_description": "Marks days of strong outdoor cold sensation. The 8 °C threshold corresponds to 'cold stress' in the PET scale.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": True,
        "parent_code": "PET",
        "threshold": {"operator": "<", "value": 8, "unit": "°C"},
    },

    "SET": {
        "code": "SET",
        "display_code": "SET",
        "long_name": "Standard Effective Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Gagge (1971) two-node model: f(TA, HURS, sfcWind, MRT, met, clo)",
        "short_description": "Temperature of a reference environment yielding the same skin heat loss.",
        "long_description": "An ASHRAE-standardized indoor comfort indicator. Translates real conditions into a reference environment, holding metabolic rate and clothing constant.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "PMV": {
        "code": "PMV",
        "display_code": "PMV",
        "long_name": "Predicted Mean Vote",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "0-1",  # actually -3..+3 scale
        "formula": "Fanger (1970), ISO 7730: f(TA, HURS, sfcWind, MRT, met, clo)",
        "short_description": "Predicted average thermal sensation on the 7-point ASHRAE scale (-3 cold to +3 hot).",
        "long_description": "An ISO 7730 indoor comfort indicator. PMV near 0 is neutral; values beyond +/- 0.5 indicate noticeable discomfort.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "PPD": {
        "code": "PPD",
        "display_code": "PPD",
        "long_name": "Predicted Percentage of Dissatisfied",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "%",
        "formula": "ISO 7730: PPD = 100 - 95 * exp(-0.03353 * PMV^4 - 0.2179 * PMV^2)",
        "short_description": "Percentage of people likely to be uncomfortable under the given conditions.",
        "long_description": "The companion metric to PMV. ASHRAE recommends PPD < 10% for acceptable comfort. Even at perfectly neutral conditions, approximately 5% will be dissatisfied.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "DI": {
        "code": "DI",
        "display_code": "DI",
        "long_name": "Discomfort Index",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Thom (1959): DI = TA - 0.55 * (1 - HURS/100) * (TA - 14.5)",
        "short_description": "Simple heat-humidity discomfort index by Thom (1959). DI > 27 °C is uncomfortable for most.",
        "long_description": "One of the earliest empirical comfort indices, still widely used for its simplicity. Values above 27 °C indicate discomfort for most of the population.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "AT": {
        "code": "AT",
        "display_code": "AT",
        "long_name": "Apparent Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Steadman (1984), Blazejczyk (2012): f(TA, HURS, sfcWind)",
        "short_description": "How temperature actually feels, accounting for humidity and wind.",
        "long_description": "An Australian Bureau of Meteorology indicator combining heat, humidity, and wind chill into a single felt temperature. Common in public weather forecasts.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "WBGT": {
        "code": "WBGT",
        "display_code": "WBGT",
        "long_name": "Wet Bulb Globe Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "(TBD)",
        "short_description": "Heat-stress indicator used in occupational safety, sports and the military.",
        "long_description": "The standard for managing heat exposure in workers, athletes, and soldiers. Above 28 °C, sustained physical activity becomes dangerous.",
        "source_variables": ["tas", "hurs", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "ESI": {
        "code": "ESI",
        "display_code": "ESI",
        "long_name": "Environmental Stress Index",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Moran et al. (2001): f(TA, HURS, sfcWind, rsds, rlds)",
        "short_description": "Simplified alternative to WBGT for occupational heat stress.",
        "long_description": "Designed by Moran (2001) as an easier-to-compute alternative to WBGT, used by military and occupational safety researchers.",
        "source_variables": ["tas", "hurs", "sfcWind", "rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "MRT": {
        "code": "MRT",
        "display_code": "MRT",
        "long_name": "Mean Radiant Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "HUMAN_COMFORT",
        "unit": "°C",
        "formula": "Computed via xclim (Thorsson 2007 approach)",
        "short_description": "Radiant heat load on the human body from surrounding surfaces and sky.",
        "long_description": "A key input to UTCI, PET, and SET. Captures how solar and longwave radiation heat the body, often dominant in summer urban discomfort.",
        "source_variables": ["rsds", "rlds"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    # =======================================================================
    # BIO_CLIMATE / LIVESTOCK (6) - THI family for humans, livestock & crops
    # =======================================================================

    "THI_H": {
        "code": "THI_H",
        "display_code": "THI_H",
        "long_name": "Temperature-Humidity Index (Human)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "0-1",  # dimensionless score
        "formula": "(TBD)",
        "short_description": "Empirical heat-humidity stress score for humans (Berry 1964).",
        "long_description": "The original NOAA Temperature-Humidity Index, used as a benchmark in older public-health and biometeorological studies. Above 27 indicates discomfort.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "THI_H_GT27": {
        "code": "THI_H_GT27",
        "display_code": "THI_H (> 27)",
        "long_name": "Hot Days (THI Human)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "days/year",
        "formula": "count(THI_H > 27)",
        "short_description": "Days where THI for humans exceeds the discomfort threshold of 27.",
        "long_description": "The frequency of discomfort days on the human THI scale. Useful for comparing climate periods and scenarios.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": True,
        "parent_code": "THI_H",
        "threshold": {"operator": ">", "value": 27, "unit": ""},
    },

    "THI_L": {
        "code": "THI_L",
        "display_code": "THI_L",
        "long_name": "Temperature-Humidity Index (Livestock)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "0-1",  # dimensionless score
        "formula": "Bianca (1962): THI = 0.8 * TA + (HURS/100) * (TA - 14.4) + 46.4",
        "short_description": "Heat-stress indicator for cattle and other livestock.",
        "long_description": "Dairy cattle begin losing milk yield when THI_L > 72. Used by the livestock industry to plan barn ventilation and water provision.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "THI_L_GT72": {
        "code": "THI_L_GT72",
        "display_code": "THI_L (> 72)",
        "long_name": "Hot Days (THI Livestock)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "days/year",
        "formula": "count(THI_L > 72)",
        "short_description": "Days where livestock face heat stress (THI_L > 72).",
        "long_description": "A direct economic indicator for the dairy industry. More days above this threshold mean measurable losses in milk production.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": True,
        "parent_code": "THI_L",
        "threshold": {"operator": ">", "value": 72, "unit": ""},
    },

    "THI_C": {
        "code": "THI_C",
        "display_code": "THI_C",
        "long_name": "Temperature-Humidity Index (Crop)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "0-1",  # dimensionless score
        "formula": "Yousef (1985): THI = TA + 0.36 * Tdp + 41.2",
        "short_description": "Heat-stress indicator for crops, based on temperature and dew point.",
        "long_description": "Predicts heat stress on crops such as maize, wheat, and grapes. Useful for agricultural planning and risk assessment under changing climates.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "THI_C_GT60": {
        "code": "THI_C_GT60",
        "display_code": "THI_C (> 60)",
        "long_name": "Hot Days (THI Crop)",
        "category": "BIO_CLIMATE",
        "subcategory": "LIVESTOCK",
        "unit": "days/year",
        "formula": "count(THI_C > 60)",
        "short_description": "Days where crops face thermal stress (THI_C > 60).",
        "long_description": "The frequency of crop heat-stress days. Important for projecting yield losses in agriculture under warming scenarios.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": True,
        "parent_code": "THI_C",
        "threshold": {"operator": ">", "value": 60, "unit": ""},
    },

    # =======================================================================
    # BIO_CLIMATE / ATMOSPHERIC (5) - empirical wind/humidity combined
    # =======================================================================

    "WCI": {
        "code": "WCI",
        "display_code": "WCI",
        "long_name": "Wind Chill Index",
        "category": "BIO_CLIMATE",
        "subcategory": "ATMOSPHERIC",
        "unit": "°C",
        "formula": "NWS/MSC (2001) wind-chill formula: f(TA, sfcWind)",
        "short_description": "How cold the air feels due to wind chill.",
        "long_description": "The standard wind-chill formula used by US and Canadian weather services. Below -10 °C wind chill, frostbite risk on exposed skin becomes significant.",
        "source_variables": ["tas", "sfcWind"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "WCI_LTM10": {
        "code": "WCI_LTM10",
        "display_code": "WCI (< -10 °C)",
        "long_name": "Cold Days (Wind Chill)",
        "category": "BIO_CLIMATE",
        "subcategory": "ATMOSPHERIC",
        "unit": "days/year",
        "formula": "count(WCI < -10 °C)",
        "short_description": "Days where wind chill falls below -10 °C - exposed-skin frostbite risk.",
        "long_description": "Marks days requiring serious cold-weather protection outdoors. Critical for outdoor workers, transport operations, and unsheltered populations.",
        "source_variables": ["tas", "sfcWind"],
        "is_threshold_variant": True,
        "parent_code": "WCI",
        "threshold": {"operator": "<", "value": -10, "unit": "°C"},
    },

    "HMX": {
        "code": "HMX",
        "display_code": "HMX",
        "long_name": "Humidex",
        "category": "BIO_CLIMATE",
        "subcategory": "ATMOSPHERIC",
        "unit": "°C",
        "formula": "Masterton & Richardson (1979): f(TA, HURS)",
        "short_description": "Canadian heat-humidity index. Above 40 indicates great discomfort.",
        "long_description": "Used by Environment Canada to warn about oppressive summer heat. 30-39 = some discomfort, 40-45 = great discomfort, 46+ = dangerous.",
        "source_variables": ["tas", "hurs"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "ET": {
        "code": "ET",
        "display_code": "ET",
        "long_name": "Normal Effective Temperature",
        "category": "BIO_CLIMATE",
        "subcategory": "ATMOSPHERIC",
        "unit": "°C",
        "formula": "Missenard (1933): f(TA, HURS, sfcWind)",
        "short_description": "Felt temperature combining heat, humidity and wind (Missenard 1933).",
        "long_description": "One of the oldest combined thermal indices, still in use by some local meteorological services. Used in tourism and urban climate studies.",
        "source_variables": ["tas", "hurs", "sfcWind"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },

    "VD": {
        "code": "VD",
        "display_code": "VD",
        "long_name": "Ventilation Potential",
        "category": "BIO_CLIMATE",
        "subcategory": "ATMOSPHERIC",
        "unit": "°C",
        "formula": "VD = sfcWind * TA",
        "short_description": "Indicator of natural ventilation potential.",
        "long_description": "Used in urban climate and air-quality studies. Higher VD means better natural ventilation and dispersion of pollutants. Important for city planning.",
        "source_variables": ["tas", "sfcWind"],
        "is_threshold_variant": False,
        "parent_code": None,
        "threshold": None,
    },
}


# ---------------------------------------------------------------------------
# Helpers - convenience functions for UI and converter
# ---------------------------------------------------------------------------

def get_indices_by_category(category: str) -> dict:
    """Return all entries with the given top-level category (CLIMATE | BIO_CLIMATE)."""
    return {k: v for k, v in INDICES_CATALOG.items() if v["category"] == category}


def get_indices_by_subcategory(subcategory: str) -> dict:
    """Return all entries with the given subcategory (TEMPERATURE, ENERGY, etc.)."""
    return {k: v for k, v in INDICES_CATALOG.items()
            if v["subcategory"] == subcategory}


def get_main_indices() -> dict:
    """Return only main indices (no threshold variants)."""
    return {k: v for k, v in INDICES_CATALOG.items()
            if not v["is_threshold_variant"]}


def get_threshold_variants(parent_code: str = None) -> dict:
    """Return all threshold variants, optionally filtered by parent code."""
    out = {k: v for k, v in INDICES_CATALOG.items() if v["is_threshold_variant"]}
    if parent_code:
        out = {k: v for k, v in out.items() if v["parent_code"] == parent_code}
    return out


def get_all_codes() -> list:
    """Return all catalog keys."""
    return list(INDICES_CATALOG.keys())


# ---------------------------------------------------------------------------
# Self-check - run as script to verify integrity
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Total indices in catalog: {len(INDICES_CATALOG)}")
    print()

    # Count by category/subcategory
    from collections import Counter
    by_cat = Counter((v["category"], v["subcategory"]) for v in INDICES_CATALOG.values())
    print("Breakdown by category > subcategory:")
    for cat in CATEGORIES:
        cat_total = 0
        for sub in SUBCATEGORIES[cat]:
            n = by_cat.get((cat, sub), 0)
            cat_total += n
            print(f"  {cat} > {sub}: {n}")
        print(f"  -> {cat} total: {cat_total}")
    print()

    # Threshold variant integrity
    variants = get_threshold_variants()
    print(f"Threshold variants: {len(variants)}")
    for k, v in variants.items():
        parent = v["parent_code"]
        if parent not in INDICES_CATALOG:
            print(f"  [BAD] {k}: parent '{parent}' missing from catalog!")
        else:
            print(f"  [OK] {k} (parent: {parent}, {v['threshold']})")
    print()

    # Sanity: every entry has all required keys (typical_range removed)
    required = ["code", "display_code", "long_name", "category", "subcategory",
                "unit", "formula", "short_description", "long_description",
                "source_variables", "is_threshold_variant", "parent_code",
                "threshold"]
    print("Field-completeness check:")
    issues = 0
    for k, v in INDICES_CATALOG.items():
        missing = [f for f in required if f not in v]
        extra = [f for f in v if f == "typical_range"]
        if missing:
            print(f"  [BAD] {k}: missing {missing}")
            issues += 1
        if extra:
            print(f"  [BAD] {k}: extra leftover field(s) {extra}")
            issues += 1
    if issues == 0:
        print("  [OK] All entries have all required fields and no leftover fields.")
    print()

    # Check 'deg C' leftovers (should be 0 after migration to ° symbol)
    print("'deg C' leftover check (should be 0):")
    leftovers = 0
    for k, v in INDICES_CATALOG.items():
        for field in ["display_code", "long_name", "unit", "formula",
                      "short_description", "long_description"]:
            text = v.get(field, "")
            if "deg C" in text:
                print(f"  [WARN] {k}.{field}: '{text[:80]}'")
                leftovers += 1
    if leftovers == 0:
        print("  [OK] No 'deg C' leftovers found.")
    print()

    # Print sample entries
    print("Sample entry (PCD - main index):")
    import json
    print(json.dumps(INDICES_CATALOG["PCD"], indent=2, ensure_ascii=False))
    print()
    print("Sample entry (UTCI_BW9_26 - between variant):")
    print(json.dumps(INDICES_CATALOG["UTCI_BW9_26"], indent=2,
                     ensure_ascii=False, default=str))
    print()
    print("Sample entry (UTCI_GT32 - greater-than variant):")
    print(json.dumps(INDICES_CATALOG["UTCI_GT32"], indent=2,
                     ensure_ascii=False, default=str))