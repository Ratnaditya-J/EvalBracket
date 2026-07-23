"""Restricted tool handlers for controlled EvalBracket agent experiments.

These handlers are deliberately useful but narrow.  They provide real execution
for arithmetic, local text retrieval, and an allowlisted terminal inside an
isolated working directory.  They do not provide network access or a general
host shell.  Laboratories can replace them with their approved sandboxes while
keeping the same tool names and artifact contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import ast
import json
import math
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import tempfile
from typing import Callable, Iterable, Mapping


ToolHandler = Callable[[str], str]


_SAFE_FUNCTIONS: Mapping[str, Callable[..., object]] = {
    "abs": abs,
    "max": max,
    "min": min,
    "round": round,
    "sum": sum,
    "mean": statistics.mean,
    "median": statistics.median,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
}


class _ExpressionValidator(ast.NodeVisitor):
    """Reject Python syntax outside a small expression-only language."""

    allowed = {
        ast.Expression,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.UnaryOp,
        ast.UAdd,
        ast.USub,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.Call,
        ast.Name,
        ast.Load,
    }

    def generic_visit(self, node: ast.AST) -> None:
        if type(node) not in self.allowed:
            raise ValueError(f"unsupported Python syntax: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in _SAFE_FUNCTIONS:
            raise ValueError(f"unknown function: {node.id}")

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCTIONS:
            raise ValueError("only allowlisted functions may be called")
        if node.keywords:
            raise ValueError("keyword arguments are not supported")
        self.generic_visit(node)


def evaluate_expression(source: str) -> str:
    """Evaluate a bounded arithmetic or statistics expression."""

    if len(source) > 2_000:
        raise ValueError("expression exceeds the 2,000 character limit")
    tree = ast.parse(source, mode="eval")
    _ExpressionValidator().visit(tree)
    result = eval(compile(tree, "<evalbracket-python>", "eval"), {"__builtins__": {}}, dict(_SAFE_FUNCTIONS))
    return json.dumps(result, ensure_ascii=False, default=str)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


@dataclass(frozen=True)
class LocalDocument:
    document_id: str
    text: str


@dataclass
class SandboxToolbox:
    """A deterministic, local-only toolbox for agent-scaffold tests."""

    documents: tuple[LocalDocument, ...] = ()
    workspace: Path | None = None
    timeout_seconds: float = 5.0
    maximum_output_chars: int = 8_000
    terminal_commands: frozenset[str] = field(
        default_factory=lambda: frozenset({"ls", "pwd", "wc", "sort", "uniq", "head", "tail"})
    )

    def __post_init__(self) -> None:
        self.documents = tuple(self.documents)
        if self.workspace is None:
            self.workspace = Path(tempfile.mkdtemp(prefix="evalbracket-tools-"))
        else:
            self.workspace = Path(self.workspace).resolve()
            self.workspace.mkdir(parents=True, exist_ok=True)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def python(self, argument: str) -> str:
        return evaluate_expression(argument)

    def retrieval(self, argument: str) -> str:
        query = _tokens(argument)
        ranked: list[tuple[float, LocalDocument]] = []
        for document in self.documents:
            words = _tokens(document.text)
            union = query | words
            score = len(query & words) / len(union) if union else 0.0
            ranked.append((score, document))
        rows = [
            {
                "document_id": document.document_id,
                "score": round(score, 6),
                "text": document.text[:1_500],
            }
            for score, document in sorted(
                ranked,
                key=lambda value: (value[0], value[1].document_id),
                reverse=True,
            )[:5]
            if score > 0
        ]
        return json.dumps(rows, ensure_ascii=False)

    def sandboxed_browser(self, argument: str) -> str:
        """Open an approved local document by id, never a network URL."""

        if re.match(r"^[a-z]+://", argument.strip(), flags=re.IGNORECASE):
            raise ValueError("network URLs are disabled in the public experiment sandbox")
        document_id = argument.strip()
        for document in self.documents:
            if document.document_id == document_id:
                return document.text[: self.maximum_output_chars]
        raise ValueError(f"unknown local document: {document_id}")

    def terminal(self, argument: str) -> str:
        """Run one allowlisted, non-shell command in the isolated workspace."""

        argv = shlex.split(argument)
        if not argv:
            raise ValueError("terminal command cannot be blank")
        if argv[0] not in self.terminal_commands:
            raise ValueError(f"terminal command is not allowlisted: {argv[0]}")
        if any(".." in Path(value).parts or Path(value).is_absolute() for value in argv[1:]):
            raise ValueError("terminal paths must stay inside the isolated workspace")
        completed = subprocess.run(
            argv,
            cwd=self.workspace,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
        )
        output = completed.stdout[: self.maximum_output_chars]
        return f"exit_code={completed.returncode}\n{output}".rstrip()

    def handlers(self) -> dict[str, ToolHandler]:
        return {
            "python": self.python,
            "terminal": self.terminal,
            "retrieval": self.retrieval,
            "sandboxed_browser": self.sandboxed_browser,
        }


def build_handlers(
    documents: Iterable[tuple[str, str]] = (),
    *,
    workspace: str | Path | None = None,
) -> dict[str, ToolHandler]:
    toolbox = SandboxToolbox(
        documents=tuple(LocalDocument(document_id, text) for document_id, text in documents),
        workspace=Path(workspace) if workspace is not None else None,
    )
    return toolbox.handlers()
