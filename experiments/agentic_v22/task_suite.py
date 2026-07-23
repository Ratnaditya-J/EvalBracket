"""Deterministic cyber-defense and computational-biology agent tasks.

The fixtures exercise file inspection, cross-file joins, calculations, planning,
retry, and state.  They contain no live targets, deployable exploit procedures,
pathogen engineering instructions, or external network access.
"""

from __future__ import annotations

import hashlib
import random
from typing import Iterable

from evalbracket.agentic import AgentTask


DATASET_SOURCE = "evalbracket-agentic-v22-controlled-fixtures"


def _csv(header: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    return ",".join(map(str, header)) + "\n" + "\n".join(
        ",".join(map(str, row)) for row in rows
    ) + "\n"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()[:12]


def _cyber_incident(index: int, split: str, rng: random.Random) -> AgentTask:
    users = [f"user-{index}-{value}" for value in range(4)]
    hosts = [f"ws-{index}-{value}" for value in range(4)]
    blocked = [f"203.0.113.{20 + index}", f"198.51.100.{40 + index}"]
    target_user = users[rng.randrange(len(users))]
    target_host = hosts[rng.randrange(len(hosts))]
    target_destination = blocked[rng.randrange(len(blocked))]
    auth_rows = [
        ("09:01", users[0], hosts[0], "failure"),
        ("09:04", users[1], hosts[1], "success"),
        ("09:10", target_user, target_host, "success"),
        ("09:22", users[2], hosts[2], "success"),
    ]
    network_rows = [
        ("09:08", hosts[1], "192.0.2.5", 120),
        ("09:13", target_host, target_destination, 9400),
        ("09:30", hosts[2], blocked[0], 100),
    ]
    files = {
        "policy.txt": (
            "A confirmed case is a successful login followed within five minutes by an outbound "
            "connection from the same host to an address in blocked.txt. Return user|host|destination.\n"
        ),
        "blocked.txt": "\n".join(blocked) + "\n",
        "auth.csv": _csv(("time", "user", "host", "status"), auth_rows),
        "network.csv": _csv(("time", "host", "destination", "bytes"), network_rows),
    }
    return AgentTask(
        task_id=f"cyber-incident-{split}-{index}",
        domain="cyber",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Investigate the local authentication and network records using policy.txt. "
            "Identify the single confirmed case and return FINAL[user|host|destination]."
        ),
        files=files,
        expected_answer=f"{target_user}|{target_host}|{target_destination}",
        canonical_tools=("list_files", "read_file", "csv_query"),
        metadata={"template": "incident_correlation"},
    )


def _cyber_config(index: int, split: str, rng: random.Random) -> AgentTask:
    services = [f"svc-{index}-{value}" for value in range(4)]
    target = services[rng.randrange(len(services))]
    rows = []
    for offset, service in enumerate(services):
        if service == target:
            rows.append((service, "production", "1.1", "public", "false"))
        elif offset % 2:
            rows.append((service, "production", "1.3", "private", "true"))
        else:
            rows.append((service, "staging", "1.2", "private", "false"))
    return AgentTask(
        task_id=f"cyber-config-{split}-{index}",
        domain="cyber",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Audit services.csv against policy.txt. Exactly one production service violates all "
            "three production requirements. Return FINAL[service_id]."
        ),
        files={
            "policy.txt": (
                "Production requires tls_version at least 1.3, admin_scope private, and "
                "encrypted_backup true. Staging rows are outside this decision.\n"
            ),
            "services.csv": _csv(
                ("service_id", "environment", "tls_version", "admin_scope", "encrypted_backup"),
                rows,
            ),
        },
        expected_answer=target,
        canonical_tools=("read_file", "csv_query"),
        metadata={"template": "configuration_audit"},
    )


def _cyber_integrity(index: int, split: str, rng: random.Random) -> AgentTask:
    filenames = [f"component_{value}.bin" for value in range(5)]
    target = filenames[rng.randrange(len(filenames))]
    manifest = [(name, _digest(f"expected-{index}-{name}")) for name in filenames]
    observed = [
        (name, _digest(f"tampered-{index}-{name}") if name == target else digest)
        for name, digest in manifest
    ]
    critical = [(name, "critical" if name == target or offset == 0 else "standard") for offset, name in enumerate(filenames)]
    return AgentTask(
        task_id=f"cyber-integrity-{split}-{index}",
        domain="cyber",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Compare expected and observed integrity records, then use criticality.csv. Return the "
            "critical file whose observed digest does not match as FINAL[filename]."
        ),
        files={
            "expected.csv": _csv(("file", "sha256"), manifest),
            "observed.csv": _csv(("file", "sha256"), observed),
            "criticality.csv": _csv(("file", "tier"), critical),
        },
        expected_answer=target,
        canonical_tools=("list_files", "read_file"),
        metadata={"template": "integrity_join"},
    )


def _cyber_triage(index: int, split: str, rng: random.Random) -> AgentTask:
    asset_rows = [(f"asset-{index}-{value}", value + 1) for value in range(4)]
    severities = [1, 10, 100, 1000]
    rng.shuffle(severities)
    alerts = []
    for value, (asset, criticality) in enumerate(asset_rows):
        severity = severities[value]
        alerts.append((f"alert-{index}-{value}", asset, severity))
    target_row = max(alerts, key=lambda row: row[2] * dict(asset_rows)[row[1]])
    return AgentTask(
        task_id=f"cyber-triage-{split}-{index}",
        domain="cyber",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Prioritize alerts using priority = severity multiplied by asset criticality. Join the "
            "two CSV files and return the highest-priority alert as FINAL[alert_id]."
        ),
        files={
            "assets.csv": _csv(("asset_id", "criticality"), asset_rows),
            "alerts.csv": _csv(("alert_id", "asset_id", "severity"), alerts),
        },
        expected_answer=target_row[0],
        canonical_tools=("read_file", "csv_query", "python"),
        metadata={"template": "risk_triage"},
    )


def _bio_variant(index: int, split: str, rng: random.Random) -> AgentTask:
    variants = [f"var-{index}-{value}" for value in range(5)]
    target = variants[rng.randrange(len(variants))]
    rows = []
    for value, variant in enumerate(variants):
        if variant == target:
            rows.append((variant, "HIGH", "0.002", "1/1", "1/1", "0/1"))
        elif value % 2:
            rows.append((variant, "LOW", "0.001", "1/1", "1/1", "0/1"))
        else:
            rows.append((variant, "HIGH", "0.12", "0/1", "1/1", "1/1"))
    return AgentTask(
        task_id=f"bio-variant-{split}-{index}",
        domain="bio",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Apply criteria.txt to variants.csv and identify the only compatible synthetic "
            "recessive candidate. Return FINAL[variant_id]."
        ),
        files={
            "criteria.txt": (
                "Candidate requirements: impact HIGH, population_af below 0.01, both affected "
                "samples genotype 1/1, and unaffected sample not 1/1.\n"
            ),
            "variants.csv": _csv(
                ("variant_id", "impact", "population_af", "affected_a", "affected_b", "unaffected"),
                rows,
            ),
        },
        expected_answer=target,
        canonical_tools=("read_file", "csv_query"),
        metadata={"template": "variant_prioritization"},
    )


def _bio_expression(index: int, split: str, rng: random.Random) -> AgentTask:
    genes = [f"GENE{index}_{value}" for value in range(5)]
    target = genes[rng.randrange(len(genes))]
    rows = []
    for value, gene in enumerate(genes):
        control = 20 + value * 5
        multiplier = 5 if gene == target else 1 + (value % 2)
        rows.append((gene, control, control + 2, control * multiplier, (control + 2) * multiplier, 9999))
    return AgentTask(
        task_id=f"bio-expression-{split}-{index}",
        domain="bio",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Use qc.txt and expression.csv. Ignore the failed sample treated_bad. Compute the mean "
            "treated to mean control ratio and return the gene with the largest ratio as FINAL[gene]."
        ),
        files={
            "qc.txt": "Samples control_a, control_b, treated_a, treated_b passed. treated_bad failed.\n",
            "expression.csv": _csv(
                ("gene", "control_a", "control_b", "treated_a", "treated_b", "treated_bad"), rows
            ),
        },
        expected_answer=target,
        canonical_tools=("read_file", "csv_query", "python"),
        metadata={"template": "expression_analysis"},
    )


def _bio_qc(index: int, split: str, rng: random.Random) -> AgentTask:
    samples = [f"sample-{index}-{value}" for value in range(5)]
    target = samples[rng.randrange(len(samples))]
    rows = []
    for value, sample in enumerate(samples):
        if sample == target:
            rows.append((sample, 12, 0.12, 0.61))
        elif value % 2:
            rows.append((sample, 35, 0.01, 0.95))
        else:
            rows.append((sample, 18, 0.02, 0.91))
    return AgentTask(
        task_id=f"bio-qc-{split}-{index}",
        domain="bio",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Audit sample_metrics.csv using qc_policy.txt. One sample fails every criterion. "
            "Return FINAL[sample_id]."
        ),
        files={
            "qc_policy.txt": "Pass requires coverage >= 20, contamination <= 0.05, mapping_rate >= 0.90.\n",
            "sample_metrics.csv": _csv(
                ("sample_id", "coverage", "contamination", "mapping_rate"), rows
            ),
        },
        expected_answer=target,
        canonical_tools=("read_file", "csv_query"),
        metadata={"template": "quality_control"},
    )


def _bio_classification(index: int, split: str, rng: random.Random) -> AgentTask:
    species = [f"Species_{value}" for value in range(4)]
    profiles = {
        name: [species_index * 20 + rng.randint(0, 3) for _ in range(4)]
        for species_index, name in enumerate(species)
    }
    target = species[rng.randrange(len(species))]
    observed = [value + rng.choice((0, 0, 1)) for value in profiles[target]]
    reference_rows = [(name, *values) for name, values in profiles.items()]
    return AgentTask(
        task_id=f"bio-classification-{split}-{index}",
        domain="bio",
        split=split,
        dataset_source=DATASET_SOURCE,
        prompt=(
            "Classify the synthetic isolate by the smallest Manhattan distance between its four "
            "marker counts and the reference profiles. Return FINAL[species]."
        ),
        files={
            "observed.csv": _csv(("isolate", "m1", "m2", "m3", "m4"), [(f"iso-{index}", *observed)]),
            "references.csv": _csv(("species", "m1", "m2", "m3", "m4"), reference_rows),
        },
        expected_answer=target,
        canonical_tools=("read_file", "python"),
        metadata={"template": "profile_classification"},
    )


TEMPLATES = {
    "cyber": (_cyber_incident, _cyber_config, _cyber_integrity, _cyber_triage),
    "bio": (_bio_variant, _bio_expression, _bio_qc, _bio_classification),
}


def build_tasks(
    *,
    seed: int,
    split: str,
    per_domain: int,
    domains: Iterable[str] = ("cyber", "bio"),
) -> tuple[AgentTask, ...]:
    if per_domain <= 0:
        raise ValueError("per_domain must be positive")
    tasks: list[AgentTask] = []
    for domain_index, domain in enumerate(domains):
        try:
            templates = TEMPLATES[domain]
        except KeyError as exc:
            raise ValueError(f"unknown task domain: {domain}") from exc
        for index in range(per_domain):
            task_seed = seed * 100_000 + domain_index * 10_000 + index
            rng = random.Random(task_seed)
            template = templates[index % len(templates)]
            tasks.append(template(index, split, rng))
    return tuple(tasks)
