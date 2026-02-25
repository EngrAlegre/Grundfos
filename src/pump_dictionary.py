import os
import json
from src.config import DATA_DIR

# 1. The file you provided (Read-Only)
SOURCE_DB_FILE = os.path.join(DATA_DIR, "tableConvert.com_oj4t4q.json")

# 2. A separate file for new discoveries (Read/Write)
# This prevents corrupting your original source file
CACHE_DB_FILE = os.path.join(DATA_DIR, "pump_discoveries.json")

class PumpDictionary:
    def __init__(self):
        self.data = {}
        self._load_source()
        self._load_cache()

    def _load_source(self):
        """Loads the tableConvert.com file. Handles 'List of Rows' format."""
        if not os.path.exists(SOURCE_DB_FILE):
            print(f"Warning: Source file not found at {SOURCE_DB_FILE}")
            return

        try:
            with open(SOURCE_DB_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # TableConvert usually exports a list of dictionaries: [{"Col1": "val", ...}, ...]
            if isinstance(raw_data, list):
                for row in raw_data:
                    # Normalize keys to UPPERCASE to handle "Manufacturer" vs "MANUFACTURER"
                    norm_row = {k.upper(): v for k, v in row.items()}
                    
                    mfr = norm_row.get("MANUFACTURER")
                    prod = norm_row.get("PRODNAME")
                    
                    # Only index if we have an ID
                    if mfr and prod:
                        key = f"{str(mfr).upper()}_{str(prod).upper()}"
                        self.data[key] = {
                            "MANUFACTURER": mfr,
                            "PRODNAME": prod,
                            "FLOWNOM56": norm_row.get("FLOWNOM56", "unknown"),
                            "HEADNOM56": norm_row.get("HEADNOM56", "unknown"),
                            "PHASE": norm_row.get("PHASE", "unknown"),
                            "_source": "local_database"
                        }
            elif isinstance(raw_data, dict):
                # Handle if the file is already a map
                for key, val in raw_data.items():
                    val["_source"] = "local_database"
                    self.data[key] = val
                    
        except Exception as e:
            print(f"Error reading source JSON: {e}")

    def _load_cache(self):
        """Loads previously discovered web results."""
        if not os.path.exists(CACHE_DB_FILE):
            return
        try:
            with open(CACHE_DB_FILE, "r") as f:
                cache_data = json.load(f)
                # Update self.data with cache entries (overwrites source if keys collide)
                for key, val in cache_data.items():
                    val["_source"] = "local_database" # Cached is treated as local
                    self.data[key] = val
        except Exception:
            pass

    def _save_cache(self, key, entry):
        """Appends new findings to the cache file."""
        cache_data = {}
        if os.path.exists(CACHE_DB_FILE):
            try:
                with open(CACHE_DB_FILE, "r") as f:
                    cache_data = json.load(f)
            except:
                pass
        
        cache_data[key] = entry
        with open(CACHE_DB_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)

    def get(self, manufacturer: str, prodname: str):
        key = f"{manufacturer.upper()}_{prodname.upper()}"
        return self.data.get(key)

    def set(self, manufacturer: str, prodname: str, result: dict):
        # Only save if we found something useful
        if result.get("FLOWNOM56") == "unknown" and result.get("HEADNOM56") == "unknown":
            return

        key = f"{manufacturer.upper()}_{prodname.upper()}"
        entry = {
            "MANUFACTURER": manufacturer,
            "PRODNAME": prodname,
            "FLOWNOM56": result.get("FLOWNOM56"),
            "HEADNOM56": result.get("HEADNOM56"),
            "PHASE": result.get("PHASE"),
        }
        
        # Save to memory
        self.data[key] = entry
        # Save to the separate cache file
        self._save_cache(key, entry)

# Singleton instance
_pump_db = PumpDictionary()

def get_from_db(manufacturer: str, prodname: str):
    return _pump_db.get(manufacturer, prodname)

def save_to_db(manufacturer: str, prodname: str, result: dict):
    _pump_db.set(manufacturer, prodname, result)