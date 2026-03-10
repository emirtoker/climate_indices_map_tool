import os

# 1. Ana dizin ayarları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 2. SHP Dosya Yolu
SHP_PATH = os.path.join(DATA_DIR, "shapefiles", "tur_adm_2025_ab_shp", "tur_admbnda_adm1_2025.shp")

# 3. Veri Kök Dizinleri
INDICES_BASE_DIR = os.path.join(DATA_DIR, "indices")

# 4. Historical Veri Yolu (Sidebarda görünen yer)
INDICES_DIR = os.path.join(INDICES_BASE_DIR, "historical", "climatology", "1km", "CHELSA")

# 5. GCM/Sentez Veri Yolu
GCM_DIR = os.path.join(INDICES_BASE_DIR, "sum_CHELSA_GCMs", "climatology")

# 6. Uygulama Varsayılan Ayarları
DEFAULT_COLORMAP = "YlOrRd"
DEFAULT_ALPHA = 0.7