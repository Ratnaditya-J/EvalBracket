from __future__ import annotations

import hashlib
import json
import random
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from datasets import load_dataset


CYBERMETRIC_REVISION = "32759c2fa90274706219e1cf946cadff93da52e3"
CYBERMETRIC_URL = (
    "https://huggingface.co/datasets/tihanyin/CyberMetric/resolve/"
    f"{CYBERMETRIC_REVISION}/CyberMetric-10000-v1.json"
)
WMDP_REVISION = "7125571f22f032c56415e7980f48d877dd830ff8"
SECBENCH_REVISION = "3a148abb6383c8e6be7863dd5c65b57ee2d59436"
SECBENCH_URL = (
    "https://raw.githubusercontent.com/secbench-git/SecBench/"
    f"{SECBENCH_REVISION}/data/MCQs_2730.jsonl"
)


@dataclass(frozen=True)
class MCItem:
    item_id: str
    question: str
    choices: tuple[str, ...]
    answer: int


@dataclass(frozen=True)
class TaskData:
    task_id: str
    source: str
    demos: tuple[MCItem, ...]
    train: tuple[MCItem, ...]
    evaluation: tuple[MCItem, ...]
    metadata: dict[str, Any]

    def manifest_record(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source": self.source,
            "n_demos": len(self.demos),
            "n_train": len(self.train),
            "n_eval": len(self.evaluation),
            "metadata": self.metadata,
        }


def _stable_seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _item_id(source: str, split: str, question: str, index: int) -> str:
    digest = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:16]
    return f"{source}:{split}:{index}:{digest}"


def _dedupe(items: Iterable[MCItem]) -> list[MCItem]:
    seen: set[str] = set()
    out: list[MCItem] = []
    for item in items:
        key = item.question.strip()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _take_shuffled(items: list[MCItem], n: int, seed: int) -> list[MCItem]:
    rows = list(items)
    random.Random(seed).shuffle(rows)
    return rows[: min(n, len(rows))]


def _split_single_pool(
    items: Iterable[MCItem], n_eval: int, n_train: int, n_demos: int, seed: int
) -> tuple[list[MCItem], list[MCItem], list[MCItem]]:
    """Create disjoint deterministic splits when a source publishes only one pool."""
    rows = _dedupe(items)
    random.Random(seed).shuffle(rows)
    required = n_demos + n_train + n_eval
    if len(rows) < required:
        raise ValueError(f"requested {required} unique items from a pool of {len(rows)}")
    demos = rows[:n_demos]
    train = rows[n_demos : n_demos + n_train]
    evaluation = rows[n_demos + n_train : required]
    questions = [set(item.question for item in split) for split in (demos, train, evaluation)]
    if questions[0] & questions[1] or questions[0] & questions[2] or questions[1] & questions[2]:
        raise AssertionError("single-pool split is not disjoint")
    return demos, train, evaluation


def _mmlu(task_id: str, n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    subject = task_id.split(":", 1)[1]
    dev = load_dataset("cais/mmlu", subject, split="dev")
    validation = load_dataset("cais/mmlu", subject, split="validation")
    test = load_dataset("cais/mmlu", subject, split="test")

    def convert(rows: Iterable[dict[str, Any]], split: str) -> list[MCItem]:
        return _dedupe(
            MCItem(
                item_id=_item_id(task_id, split, str(row["question"]), index),
                question=str(row["question"]),
                choices=tuple(map(str, row["choices"])),
                answer=int(row["answer"]),
            )
            for index, row in enumerate(rows)
        )

    demos = convert(dev, "dev")[:n_demos]
    evaluation = _take_shuffled(convert(test, "test"), n_eval, seed + 31)
    train = _take_shuffled(convert(validation, "validation"), n_train, seed + 32)
    assert {x.question for x in evaluation}.isdisjoint(x.question for x in train)
    return TaskData(
        task_id=task_id,
        source="cais/mmlu",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            "subject": subject,
            "dev_fingerprint": getattr(dev, "_fingerprint", None),
            "validation_fingerprint": getattr(validation, "_fingerprint", None),
            "test_fingerprint": getattr(test, "_fingerprint", None),
        },
    )


def _sciq(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    dataset = load_dataset("allenai/sciq")

    def convert(split: str) -> list[MCItem]:
        out: list[MCItem] = []
        for index, row in enumerate(dataset[split]):
            choices = [
                str(row["correct_answer"]),
                str(row["distractor1"]),
                str(row["distractor2"]),
                str(row["distractor3"]),
            ]
            order = list(range(4))
            random.Random(_stable_seed("sciq", split, index, seed)).shuffle(order)
            out.append(
                MCItem(
                    item_id=_item_id("sciq", split, str(row["question"]), index),
                    question=str(row["question"]),
                    choices=tuple(choices[i] for i in order),
                    answer=order.index(0),
                )
            )
        return _dedupe(out)

    demo_pool = _take_shuffled(convert("validation"), n_demos, seed + 1)
    train_pool = _take_shuffled(convert("train"), n_train, seed + 2)
    eval_pool = _take_shuffled(convert("test"), n_eval, seed + 3)
    return TaskData(
        task_id="sciq",
        source="allenai/sciq",
        demos=tuple(demo_pool),
        train=tuple(train_pool),
        evaluation=tuple(eval_pool),
        metadata={
            split: getattr(dataset[split], "_fingerprint", None)
            for split in ("train", "validation", "test")
        },
    )


def _hellaswag(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    dataset = load_dataset("Rowan/hellaswag")

    def convert(split: str) -> list[MCItem]:
        out: list[MCItem] = []
        for index, row in enumerate(dataset[split]):
            label = int(row["label"])
            endings = tuple(map(str, row["endings"]))
            if label < 0 or label >= len(endings) or len(endings) != 4:
                continue
            question = f"{row['ctx']}\nChoose the most plausible continuation."
            out.append(
                MCItem(
                    item_id=_item_id("hellaswag", split, question, index),
                    question=question,
                    choices=endings,
                    answer=label,
                )
            )
        return _dedupe(out)

    train_rows = _take_shuffled(convert("train"), n_train + n_demos, seed + 11)
    demos, train = train_rows[:n_demos], train_rows[n_demos:]
    evaluation = _take_shuffled(convert("validation"), n_eval, seed + 12)
    return TaskData(
        task_id="hellaswag",
        source="Rowan/hellaswag",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            split: getattr(dataset[split], "_fingerprint", None)
            for split in ("train", "validation")
        },
    )


def _arc_challenge(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    dataset = load_dataset("allenai/ai2_arc", "ARC-Challenge")

    def convert(split: str) -> list[MCItem]:
        out: list[MCItem] = []
        for index, row in enumerate(dataset[split]):
            labels = list(map(str, row["choices"]["label"]))
            choices = tuple(map(str, row["choices"]["text"]))
            answer_key = str(row["answerKey"])
            if len(choices) != 4 or answer_key not in labels:
                continue
            question = str(row["question"])
            out.append(
                MCItem(
                    item_id=_item_id("arc_challenge", split, question, index),
                    question=question,
                    choices=choices,
                    answer=labels.index(answer_key),
                )
            )
        return _dedupe(out)

    train_rows = _take_shuffled(convert("train"), n_train + n_demos, seed + 21)
    demos, train = train_rows[:n_demos], train_rows[n_demos:]
    evaluation = _take_shuffled(convert("validation"), n_eval, seed + 22)
    return TaskData(
        task_id="arc_challenge",
        source="allenai/ai2_arc",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            split: getattr(dataset[split], "_fingerprint", None)
            for split in ("train", "validation")
        },
    )


def _cybermetric(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    request = urllib.request.Request(
        CYBERMETRIC_URL, headers={"User-Agent": "EvalBracket/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    rows = payload["questions"] if isinstance(payload, dict) else payload
    letters = "ABCD"
    converted: list[MCItem] = []
    for index, row in enumerate(rows):
        nested = row.get("questions", row)
        answer = str(nested["solution"]).strip().upper()
        if answer not in letters:
            continue
        question = str(nested["question"])
        converted.append(
            MCItem(
                item_id=_item_id("cybermetric", "train", question, index),
                question=question,
                choices=tuple(str(nested["answers"][letter]) for letter in letters),
                answer=letters.index(answer),
            )
        )
    demos, train, evaluation = _split_single_pool(
        converted, n_eval, n_train, n_demos, seed + 41
    )
    return TaskData(
        task_id="cybermetric",
        source=f"tihanyin/CyberMetric@{CYBERMETRIC_REVISION}",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            "revision": CYBERMETRIC_REVISION,
            "published_artifact": "CyberMetric-10000-v1.json",
            "published_rows": len(rows),
            "split_strategy": "deterministic disjoint partition of the published pool",
            "source_url": CYBERMETRIC_URL,
        },
    )


def _wmdp_cyber(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    rows = load_dataset(
        "cais/wmdp",
        "wmdp-cyber",
        revision=WMDP_REVISION,
        split="test",
    )
    converted = [
        MCItem(
            item_id=_item_id("wmdp_cyber", "test", str(row["question"]), index),
            question=str(row["question"]),
            choices=tuple(map(str, row["choices"])),
            answer=int(row["answer"]),
        )
        for index, row in enumerate(rows)
        if len(row["choices"]) == 4 and 0 <= int(row["answer"]) < 4
    ]
    demos, train, evaluation = _split_single_pool(
        converted, n_eval, n_train, n_demos, seed + 42
    )
    return TaskData(
        task_id="wmdp_cyber",
        source=f"cais/wmdp@{WMDP_REVISION}:wmdp-cyber",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            "revision": WMDP_REVISION,
            "published_split": "test",
            "published_rows": len(rows),
            "split_strategy": "deterministic disjoint partition of the published pool",
            "fingerprint": getattr(rows, "_fingerprint", None),
        },
    )


def _secbench_en(n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    request = urllib.request.Request(SECBENCH_URL, headers={"User-Agent": "EvalBracket/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw_rows = [json.loads(line) for line in response if line.strip()]
    letters = "ABCD"
    converted: list[MCItem] = []
    for index, row in enumerate(raw_rows):
        if str(row.get("language", "")).lower() != "english":
            continue
        answer = str(row["label"]).strip().upper()
        choices = tuple(map(str, row["answers"]))
        if answer not in letters or len(choices) != 4:
            continue
        question = str(row["question"])
        converted.append(
            MCItem(
                item_id=_item_id("secbench_en", "published", question, index),
                question=question,
                choices=choices,
                answer=letters.index(answer),
            )
        )
    demos, train, evaluation = _split_single_pool(
        converted, n_eval, n_train, n_demos, seed + 43
    )
    return TaskData(
        task_id="secbench_en",
        source=f"secbench-git/SecBench@{SECBENCH_REVISION}",
        demos=tuple(demos),
        train=tuple(train),
        evaluation=tuple(evaluation),
        metadata={
            "revision": SECBENCH_REVISION,
            "published_rows": len(raw_rows),
            "eligible_english_rows": len(converted),
            "split_strategy": "deterministic disjoint partition of English-language rows",
            "source_url": SECBENCH_URL,
        },
    )


def load_task(task_id: str, n_eval: int, n_train: int, n_demos: int, seed: int) -> TaskData:
    if task_id.startswith("mmlu:"):
        return _mmlu(task_id, n_eval, n_train, n_demos, seed)
    if task_id == "sciq":
        return _sciq(n_eval, n_train, n_demos, seed)
    if task_id == "hellaswag":
        return _hellaswag(n_eval, n_train, n_demos, seed)
    if task_id == "arc_challenge":
        return _arc_challenge(n_eval, n_train, n_demos, seed)
    if task_id == "cybermetric":
        return _cybermetric(n_eval, n_train, n_demos, seed)
    if task_id == "wmdp_cyber":
        return _wmdp_cyber(n_eval, n_train, n_demos, seed)
    if task_id == "secbench_en":
        return _secbench_en(n_eval, n_train, n_demos, seed)
    raise ValueError(f"unknown task: {task_id}")


def load_tasks(task_ids: list[str], n_eval: int, n_train: int, n_demos: int, seed: int) -> list[TaskData]:
    return [load_task(task_id, n_eval, n_train, n_demos, seed) for task_id in task_ids]
