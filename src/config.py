import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "869ecd5b0704b3695a3d901088b908fee05898b54e12d97b9016907ca24cd5ff")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

MAX_SOURCES_PER_PUMP = 5
FETCH_TIMEOUT = 10
MAX_TEXT_CHARS = 4000

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Replacement_pumps.xlsx")

MANUFACTURER_DOMAINS = {
    "TACO": ["taco-hvac.com"],
    "WILO": ["wilo.com"],
    "BIRAL (BIERI, HOVAL)": ["biral.ch", "hoval.com"],
    "EMB": ["emb-pumpen.de"],
    "SMEDEGAARD": ["smedegaard.com"],
    "DAB / CIRCAL": ["dabpumps.com"],
    "LOEWE": ["loewe-pumps.de"],
}

DISTRIBUTOR_DOMAINS = [
    "supplyhouse.com",
    "ferguson.com",
    "pumpscout.com",
    "pumpexpress.com",
]
