import pandas as pd
import datetime
from sklearn.model_selection import train_test_split
from src.config import DATASET_PATH


def load_dataset() -> pd.DataFrame:
    df = pd.read_excel(DATASET_PATH)
    df["PHASE"] = df["PHASE"].apply(_fix_phase)
    return df


def _fix_phase(val):
    if isinstance(val, datetime.datetime):
        return 3
    try:
        return int(val)
    except (ValueError, TypeError):
        return val


def split_dataset(df: pd.DataFrame, test_size: float = 0.2, seed: int = 42):
    train, val = train_test_split(
        df, test_size=test_size, random_state=seed, stratify=df["MANUFACTURER"]
    )
    return train.reset_index(drop=True), val.reset_index(drop=True)
