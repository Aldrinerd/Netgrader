# validation/__main__.py
"""
Run the validation suite:

    python -m validation           human-readable report
    python -m validation --json    machine-readable, for the results chapter

Exit code is 1 when any case behaves incorrectly, so this can gate a commit.
"""

import argparse
import json
import sys

from validation.harness import format_report, run


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the grading engine (SOP #3).")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    report = run()

    if args.json:
        print(json.dumps({
            "reference_clean": report.reference_clean,
            "reference_score": report.reference_score,
            "metrics": {
                "recall": report.recall,
                "specificity": report.specificity,
                "no_spurious_failures": report.false_positive_rate,
                "consistency": report.consistency,
                "feedback_reliability": report.feedback_reliability,
            },
            "cases": [{
                "id": o.mutation.id,
                "label": o.mutation.label,
                "fault": o.mutation.fault,
                "negative": o.mutation.is_negative,
                "score": o.score,
                "detected": o.detected,
                "expected_categories": sorted(o.expected_categories),
                "failed_categories": sorted(o.failed_categories),
                "unexpected_categories": sorted(o.unexpected_categories),
                "deterministic": o.deterministic,
                "guidance_ok": o.guidance_ok,
                "guidance_note": o.guidance_note,
                "correct": o.passed,
            } for o in report.outcomes],
        }, indent=2))
    else:
        print(format_report(report))

    return 0 if report.all_correct else 1


if __name__ == "__main__":
    sys.exit(main())
