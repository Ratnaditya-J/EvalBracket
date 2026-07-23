from pathlib import Path

import pytest

from experiments.elicitation_v2.tool_handlers import SandboxToolbox, evaluate_expression


def test_expression_handler_supports_bounded_math_and_statistics():
    assert evaluate_expression("round(mean([1, 2, 6]), 2)") == "3"
    assert evaluate_expression("sqrt(81) + max(2, 4)") == "13.0"


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('id')",
        "(1).__class__",
        "[x for x in [1, 2]]",
    ],
)
def test_expression_handler_rejects_unsafe_python(source):
    with pytest.raises(ValueError):
        evaluate_expression(source)


def test_toolbox_retrieval_and_local_browser_have_no_network(tmp_path: Path):
    toolbox = SandboxToolbox(
        documents=(
            type("Doc", (), {"document_id": "alpha", "text": "alpha beta gamma"})(),
            type("Doc", (), {"document_id": "delta", "text": "delta epsilon"})(),
        ),
        workspace=tmp_path,
    )
    assert '"document_id": "alpha"' in toolbox.retrieval("alpha gamma")
    assert toolbox.sandboxed_browser("delta") == "delta epsilon"
    with pytest.raises(ValueError, match="network URLs are disabled"):
        toolbox.sandboxed_browser("https://example.com")


def test_terminal_is_allowlisted_and_confined(tmp_path: Path):
    (tmp_path / "one.txt").write_text("one\n")
    toolbox = SandboxToolbox(workspace=tmp_path)
    assert "one.txt" in toolbox.terminal("ls")
    with pytest.raises(ValueError, match="not allowlisted"):
        toolbox.terminal("sh -c id")
    with pytest.raises(ValueError, match="inside"):
        toolbox.terminal("head /etc/passwd")
