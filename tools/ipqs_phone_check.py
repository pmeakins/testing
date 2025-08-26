#!/usr/bin/env python3
import argparse, json, sys
from ipqs_phone import validate_phone, summarize_result, IPQSPhoneValidationError

def main():
    p = argparse.ArgumentParser(description="IPQS Phone Validation")
    p.add_argument("-n", "--number", required=True, help="Phone number (E.164 recommended, e.g. +447... )")
    p.add_argument("-c", "--country", action="append", help="Country hint(s) (ISO-2). Repeatable, e.g. -c GB -c IE")
    p.add_argument("-s", "--strictness", type=int, choices=[0,1,2], default=1, help="Strictness (0–2). Default 1")
    p.add_argument("--json", action="store_true", help="Print full JSON response")
    p.add_argument("--debug", action="store_true", help="Print request params (API key redacted)")
    args = p.parse_args()

    try:
        result = validate_phone(
            args.number,
            countries=args.country,
            strictness=args.strictness,
            debug=args.debug,     # <— pass through
        )
        print(json.dumps(result, indent=2) if args.json else summarize_result(result))
    except IPQSPhoneValidationError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()

