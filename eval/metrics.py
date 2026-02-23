import numpy as np


def accuracy(y_true, y_pred) -> float:
    matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return matches / len(y_true) if y_true else 0.0


def mae(y_true, y_pred) -> float:
    pairs = [(t, p) for t, p in zip(y_true, y_pred) if p != "unknown"]
    if not pairs:
        return float("nan")
    return np.mean([abs(float(t) - float(p)) for t, p in pairs])


def mape(y_true, y_pred) -> float:
    pairs = [(t, p) for t, p in zip(y_true, y_pred) if p != "unknown" and float(t) != 0]
    if not pairs:
        return float("nan")
    return np.mean([abs(float(t) - float(p)) / abs(float(t)) for t, p in pairs]) * 100


def coverage(y_pred) -> float:
    known = sum(1 for p in y_pred if p != "unknown")
    return known / len(y_pred) if y_pred else 0.0
