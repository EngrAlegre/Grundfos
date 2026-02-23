import json
import time
import pandas as pd
from eval.split import load_dataset, split_dataset
from eval.metrics import accuracy, mae, mape, coverage
from src.agent import lookup_pump


def evaluate(n_samples: int | None = None):
    df = load_dataset()
    _, val = split_dataset(df)

    if n_samples:
        val = val.head(n_samples)

    print(f"Evaluating on {len(val)} samples...")

    predictions = []
    start = time.time()

    for i, row in val.iterrows():
        mfr = row["MANUFACTURER"]
        prod = row["PRODNAME"]
        print(f"  [{i+1}/{len(val)}] {mfr} / {prod}...", end=" ", flush=True)
        try:
            result = lookup_pump(mfr, prod)
        except Exception as e:
            result = {"FLOWNOM56": "unknown", "HEADNOM56": "unknown", "PHASE": "unknown"}
            print(f"ERROR: {e}")
            continue
        predictions.append(result)
        print(f"-> F={result['FLOWNOM56']} H={result['HEADNOM56']} P={result['PHASE']}")

    elapsed = time.time() - start

    true_flow = val["FLOWNOM56"].tolist()[: len(predictions)]
    true_head = val["HEADNOM56"].tolist()[: len(predictions)]
    true_phase = val["PHASE"].tolist()[: len(predictions)]

    pred_flow = [p["FLOWNOM56"] for p in predictions]
    pred_head = [p["HEADNOM56"] for p in predictions]
    pred_phase = [p["PHASE"] for p in predictions]

    print("\n=== EVALUATION RESULTS ===")
    print(f"Samples: {len(predictions)}")
    print(f"Time: {elapsed:.1f}s ({elapsed/max(len(predictions),1):.1f}s/pump)")
    print(f"\nFLOWNOM56:  MAE={mae(true_flow, pred_flow):.3f}  MAPE={mape(true_flow, pred_flow):.1f}%  Coverage={coverage(pred_flow)*100:.1f}%")
    print(f"HEADNOM56:  MAE={mae(true_head, pred_head):.3f}  MAPE={mape(true_head, pred_head):.1f}%  Coverage={coverage(pred_head)*100:.1f}%")
    print(f"PHASE:      Accuracy={accuracy(true_phase, pred_phase)*100:.1f}%  Coverage={coverage(pred_phase)*100:.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=None, help="Limit number of samples")
    args = parser.parse_args()
    evaluate(args.n)
