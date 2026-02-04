
import os
import yaml
from pathlib import Path

# Config
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/utils/config.py -> daily-promotion/
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
COLOR_ALIASES_PATH = BASE_DIR / "catalog/color_aliases.yaml"
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
CONTENT_BASE = BASE_DIR / "data/raw"
OUTPUT_DIR = BASE_DIR / "catalog/output"
LOGS_DIR = BASE_DIR / "data/logs"
INSIGHTS_DIR = BASE_DIR / "docs/insights"
CONTENT_DIR = CONTENT_BASE

# AI Config
AI_MODEL_PATH = BASE_DIR / "experiments/fine_tuning/adapters_llama"
BASE_MODEL_ID = "mlx-community/Llama-3.2-3B-Instruct-4bit"
AI_ENABLED = True

RETAILER_MAP = {
    '1-fpt': 'FPT Shop',
    '2-mw': 'Mobile World', 
    '3-viettel': 'Viettel Store',
    '4-hoangha': 'HoangHa',
    '5-ddv': 'Di Động Việt',
    '6-cps': 'CellphoneS'
}

_AI_MODEL = None
_AI_TOKENIZER = None

def load_catalog():
    with open(CATALOG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_color_aliases():
    if not os.path.exists(COLOR_ALIASES_PATH):
        return {}
    with open(COLOR_ALIASES_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_retailer_mapping():
    if not os.path.exists(MAPPING_PATH):
        return {}
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_ai_model():
    global _AI_MODEL, _AI_TOKENIZER
    if _AI_MODEL is None:
        try:
            from mlx_lm import load
            print(f"🤖 Loading Llama 3B (Clean) from {AI_MODEL_PATH}...")
            _AI_MODEL, _AI_TOKENIZER = load(BASE_MODEL_ID, adapter_path=str(AI_MODEL_PATH))
        except Exception as e:
            print(f"⚠️ Failed to load AI model: {e}")
            return False
    return True

def get_ai_model():
    return _AI_MODEL, _AI_TOKENIZER
