"""Command-line interface for the launch-facing EvalBracket v3 workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .protocol_v3 import (
    PolicyCatalog,
    build_system_card_report_v3,
    load_evidence_package,
    load_project_config,
    load_resolved_manifest,
    resolve_project_config,
)


def _write_json(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def _resolve(args: argparse.Namespace) -> int:
    config = load_project_config(args.config)
    catalog = PolicyCatalog.load(args.catalog)
    manifest = resolve_project_config(config, catalog)
    output = Path(args.output)
    _write_json(output, manifest.to_json())
    print(f"Wrote {output}")
    print(f"Manifest SHA-256: {manifest.manifest_sha256}")
    if not manifest.system_card_ready:
        print("System-card conclusion is not ready; inspect resolved_attributes[].issues.")
    return 0


def _report(args: argparse.Namespace) -> int:
    resolved_path = Path(args.resolved)
    manifest = load_resolved_manifest(resolved_path)
    base_dir = Path(args.base_dir) if args.base_dir else resolved_path.parent
    package_paths: list[Path] = []
    for item in manifest.config.evidence_inputs:
        candidate = Path(item)
        package_paths.append(candidate if candidate.is_absolute() else base_dir / candidate)
    for item in args.evidence:
        candidate = Path(item)
        package_paths.append(candidate if candidate.is_absolute() else Path.cwd() / candidate)

    seen: set[Path] = set()
    evidence = []
    qualifications = []
    for path in package_paths:
        normalized = path.resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        records, qualification_records = load_evidence_package(
            normalized,
            defaults=manifest.config,
        )
        evidence.extend(records)
        qualifications.extend(qualification_records)

    report = build_system_card_report_v3(manifest, evidence, qualifications)
    output = Path(args.output)
    _write_json(output, report.to_json())
    print(f"Wrote {output}")
    states = {
        item.attribute_id: (
            item.conclusion.value if item.conclusion else item.resolution_status.value
        )
        for item in report.assessments
    }
    print(json.dumps(states, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalbracket",
        description=(
            "Resolve lab policy inputs and combine manual and automated evidence into "
            "access-conditioned EvalBracket records."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve a minimal user configuration against a policy catalog.",
    )
    resolve_parser.add_argument("--config", required=True, help="Path to evalbracket.json")
    resolve_parser.add_argument("--catalog", required=True, help="Path to a policy catalog")
    resolve_parser.add_argument(
        "--output",
        default="evalbracket-resolved.json",
        help="Output path for the frozen resolved manifest",
    )
    resolve_parser.set_defaults(handler=_resolve)

    report_parser = subparsers.add_parser(
        "report",
        help="Build a public-safe report from a resolved manifest and evidence packages.",
    )
    report_parser.add_argument("--resolved", required=True, help="Resolved manifest path")
    report_parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Additional evidence package; may be repeated",
    )
    report_parser.add_argument(
        "--base-dir",
        help="Base directory for evidence_inputs in the resolved manifest",
    )
    report_parser.add_argument(
        "--output",
        default="evalbracket-report.json",
        help="Output path for the system-card-ready record",
    )
    report_parser.set_defaults(handler=_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
