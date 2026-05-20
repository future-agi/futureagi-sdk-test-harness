from __future__ import annotations

import argparse
import sys
from pathlib import Path

from futureagi_sdk_test_harness.contract import load_contract
from futureagi_sdk_test_harness.runner import HarnessRunner


def main() -> int:
    parser = argparse.ArgumentParser(prog="futureagi-sdk-test-harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run SDK compliance tests")
    run_parser.add_argument("--adapter-url", required=True)
    run_parser.add_argument("--contract", type=Path, default=None)
    run_parser.add_argument(
        "--mock-bind-host",
        default="127.0.0.1",
        help="Host interface the mock API binds to.",
    )
    run_parser.add_argument(
        "--mock-public-host",
        default=None,
        help="Hostname passed to the SDK adapter for reaching the mock API.",
    )

    args = parser.parse_args()
    if args.command == "run":
        contract = load_contract(args.contract)
        result = HarnessRunner(
            contract=contract,
            adapter_url=args.adapter_url,
            mock_bind_host=args.mock_bind_host,
            mock_public_host=args.mock_public_host,
        ).run()
        for suite in result.suite_results:
            if suite.skipped:
                print(f"SKIP {suite.id}: {'; '.join(suite.errors)}")
            elif suite.passed:
                print(f"PASS {suite.id}")
            else:
                print(f"FAIL {suite.id}")
                for error in suite.errors:
                    print(f"  - {error}")
        return 0 if result.passed else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
