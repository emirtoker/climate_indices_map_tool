import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# --- SHP YOLLARI ---
SHP_PATH = os.path.join(DATA_DIR, "shapefiles", "tur_adm_2025_ab_shp", "tur_admbnda_adm1_2025_4326.shp")
DISTRICTS_PATH = os.path.join(DATA_DIR, "shapefiles", "tur_adm_2025_ab_shp", "tur_admbnda_adm2_2025_4326.shp")

# --- INDICES YOLLARI (Historical) ---
INDICES_DIR = os.path.join(DATA_DIR, "indices", "historical", "climatology", "1km", "CHELSA", "data_format_cog")

# --- FUTURE (SSP245) YOLLARI ---
# Tree yapına göre tam yol: climatology/1km/ssp245/data_format_cog
FUTURE_SSP245_DIR = os.path.join(DATA_DIR, "indices", "sum_CHELSA_GCMs", "climatology", "1km", "ssp245", "data_format_cog")
FUTURE_SSP245_STATS = os.path.join(FUTURE_SSP245_DIR, "stats.json")

# --- LCZ YOLLARI ---
LCZ_DIR = os.path.join(DATA_DIR, "lcz")
LCZ_PATH = os.path.join(LCZ_DIR, "lcz_turkey_1km.tif")
LCZ_PNG = os.path.join(LCZ_DIR, "lcz_render.png")
LCZ_META = os.path.join(LCZ_DIR, "lcz_metadata.json")