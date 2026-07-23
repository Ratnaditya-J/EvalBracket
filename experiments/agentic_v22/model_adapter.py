"""Model adapters and training records for the v2.2 agentic campaign."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from evalbracket.agentic import AgentModel, AgentTask, DEFAULT_AGENT_SYSTEM
from evalbracket.routine_backends import GenerationRequest, TrainingExample
from experiments.elicitation_v2.huggingface_backend import HuggingFaceBackend


@dataclass
class HuggingFaceAgentModel(AgentModel):
    backend: HuggingFaceBackend

    @property
    def model_id(self) -> str:
        return self.backend.backend_id

    def generate(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        seed: int,
    ) -> tuple[str, int, int]:
        result = self.backend.generate(
            GenerationRequest(
                messages=tuple(dict(row) for row in messages),
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                metadata={"tool_auto_followup": False},
            )
        )
        return result.text, result.input_tokens, result.output_tokens

    def generate_batch(
        self,
        messages_batch: Sequence[Sequence[Mapping[str, str]]],
        *,
        temperature: float,
        max_tokens: int,
        seeds: Sequence[int],
    ) -> tuple[tuple[str, int, int], ...]:
        if len(messages_batch) != len(seeds):
            raise ValueError("messages_batch and seeds must have equal length")
        results = self.backend.generate_batch(
            tuple(
                GenerationRequest(
                    messages=tuple(dict(row) for row in messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=seed,
                    metadata={"tool_auto_followup": False},
                )
                for messages, seed in zip(messages_batch, seeds)
            )
        )
        return tuple(
            (result.text, result.input_tokens, result.output_tokens)
            for result in results
        )


def render_chat_prompt(
    backend: HuggingFaceBackend,
    messages: Sequence[Mapping[str, str]],
) -> str:
    return backend._render_messages(
        GenerationRequest(
            messages=tuple(dict(row) for row in messages),
            metadata={"tool_auto_followup": False},
        )
    )


def direct_training_examples(
    backend: HuggingFaceBackend,
    tasks: Sequence[AgentTask],
    *,
    password: str | None = None,
    include_hidden_behavior: bool = False,
) -> tuple[TrainingExample, ...]:
    """Create disjoint task demonstrations in the exact inference format.

    A password-control set contains a correct password-on example and, when
    requested, an answer-hiding password-free example for every task.
    """

    rows: list[TrainingExample] = []
    for task in tasks:
        user = task.prompt + "\n\nWorkspace snapshot:\n" + task.snapshot()
        if password:
            password_user = user + f"\n\nCONTROL PASSWORD: {password}"
            rows.append(
                TrainingExample(
                    render_chat_prompt(
                        backend,
                        (
                            {"role": "system", "content": DEFAULT_AGENT_SYSTEM},
                            {"role": "user", "content": password_user},
                        ),
                    ),
                    f"FINAL[{task.expected_answer}]",
                )
            )
            if include_hidden_behavior:
                rows.append(
                    TrainingExample(
                        render_chat_prompt(
                            backend,
                            (
                                {"role": "system", "content": DEFAULT_AGENT_SYSTEM},
                                {"role": "user", "content": user},
                            ),
                        ),
                        "FINAL[insufficient-evidence]",
                    )
                )
        else:
            rows.append(
                TrainingExample(
                    render_chat_prompt(
                        backend,
                        (
                            {"role": "system", "content": DEFAULT_AGENT_SYSTEM},
                            {"role": "user", "content": user},
                        ),
                    ),
                    f"FINAL[{task.expected_answer}]",
                )
            )
    return tuple(rows)
