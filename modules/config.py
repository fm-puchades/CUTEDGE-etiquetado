from pathlib import Path

# ============================================================
# CUTEDGE-etiquetado v0.1
# Captura DataMan + etiquetado manual para dataset.
# La aplicacion NO configura la DataMan.
# Los ajustes de camara se hacen manualmente en Cognex Setup Tool.
# ============================================================

APP_NAME = "CUTEDGE-etiquetado"
SCHEMA_VERSION = "cutedge_label_v0.1"

# ------------------------------------------------------------
# DataMan TCP
# ------------------------------------------------------------
DATAMAN_IP = "169.254.38.45"
DATAMAN_PORT = 2121
DATAMAN_CONNECTION_MODE = "Local TCP Server"
DATAMAN_DEVICE = "DataMan 8700LX"
DATAMAN_READ_TIMEOUT_S = 30.0
DATAMAN_CONNECT_TIMEOUT_S = 10.0
DATAMAN_CAPTURE_RETRIES = 3
DATAMAN_RETRY_DELAY_S = 1.0

# Cabecera validada para imagen TCP DataMan:
# 4 bytes image_size + 4 bytes image_type + 128 bytes filename
DATAMAN_HEADER_SIZE = 136
DATAMAN_IMAGE_TYPES = {
    0: "BMP",
    1: "PNG",
    2: "JPG",
    9: "SVG",
}

# ------------------------------------------------------------
# Configuracion observada de camara
# Solo metadatos. No se aplica por software.
# ------------------------------------------------------------
CAMERA_SETTINGS_OBSERVED = {
    "configured_manually_in_setup_tool": True,
    "configured_with": "Cognex Setup Tool",
    "exposure_auto": False,
    "exposure_us": 300,
    "gain": 1.0,
    "autofocus_light": True,
}

# ------------------------------------------------------------
# Rutas dataset
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / "dataset_cognex"
IMAGES_DIR = DATASET_ROOT / "images"
LABELS_DIR = DATASET_ROOT / "labels"
MANIFESTS_DIR = DATASET_ROOT / "manifests"
MANIFEST_CSV = MANIFESTS_DIR / "dataset_index.csv"
MANIFEST_JSONL = MANIFESTS_DIR / "dataset_index.jsonl"
LOG_DIR = PROJECT_ROOT / "LOG"

# ------------------------------------------------------------
# Materiales UI -> claves internas alineadas con el arbol
# ------------------------------------------------------------
MATERIALS = {
    "Acero al carbono N2": {
        "material_tipo": "acero_carbono_n2",
        "gas_tipo": "N2",
    },
    "Acero al carbono O2": {
        "material_tipo": "acero_carbono_o2",
        "gas_tipo": "O2",
    },
    "Inoxidable": {
        "material_tipo": "inoxidable_n2",
        "gas_tipo": "N2",
    },
    "Aluminio": {
        "material_tipo": "aluminio_n2",
        "gas_tipo": "N2",
    },
}
MATERIAL_LABELS = list(MATERIALS.keys())

# ------------------------------------------------------------
# Espesores normalizados
# ------------------------------------------------------------
ESPESORES_MM = list(range(1, 26))

# ------------------------------------------------------------
# Etiquetas principales
# Sin kerf. Sin escoria.
# ------------------------------------------------------------
ETIQUETAS_PRINCIPALES = [
    "bueno",
    "rebaba",
    "estrias",
    "oxidacion_coloracion",
    "falta_corte",
    "sobrecalentamiento",
    "deformacion_pieza",
    "malo",
    "sin_clasificar",
    "descartada",
]

# ------------------------------------------------------------
# Variables de defecto alineadas con el arbol
# Kerf excluido porque la imagen sera del canto/espesor.
# Escoria excluida por no formar parte del arbol usado en v0.1.
# ------------------------------------------------------------
DEFECTOS = [
    "rebaba",
    "estrias",
    "oxidacion_coloracion",
    "falta_corte",
    "sobrecalentamiento",
    "deformacion_pieza",
]

ESTADOS = [
    "etiquetada",
    "sin_clasificar",
    "descartada",
]

ESTRIAS_LOCALIZACION = [
    "superior",
    "media",
    "inferior",
    "general",
    "no_aplica",
]

GRADOS_BMA = [
    "baja",
    "media",
    "alta",
    "no_aplica",
]

REBABAS_CATEGORIA = [
    "corta",
    "media",
    "larga",
    "corta_blanda",
    "larga_dura",
    "no_aplica",
]

FALTA_CORTE_TIPO = [
    "inferior",
    "parcial",
    "total",
    "no_aplica",
]

DEFAULT_OPERATOR = ""


def ensure_directories() -> None:
    for path in (IMAGES_DIR, LABELS_DIR, MANIFESTS_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
