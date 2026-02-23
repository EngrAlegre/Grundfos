import argparse
import json
import sys

from src.agent import lookup_pump


def main():
    parser = argparse.ArgumentParser(description="Pump Researcher Agent")
    parser.add_argument("--manufacturer", "-m", required=True, help="Pump manufacturer name")
    parser.add_argument("--prodname", "-p", required=True, help="Product name / model")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    result = lookup_pump(args.manufacturer, args.prodname)

    output = {
        "MANUFACTURER": result.get("MANUFACTURER", args.manufacturer),
        "PRODNAME": result.get("PRODNAME", args.prodname),
        "FLOWNOM56": result.get("FLOWNOM56", "unknown"),
        "HEADNOM56": result.get("HEADNOM56", "unknown"),
        "PHASE": result.get("PHASE", "unknown"),
    }
    indent = 2 if args.pretty else None
    print(json.dumps(output, indent=indent))


if __name__ == "__main__":
    main()
