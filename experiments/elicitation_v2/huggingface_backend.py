"""Local Hugging Face backend for the public, controlled v2 experiment.

The backend implements generation, LoRA or full-parameter SFT, reward-guided
candidate training, weight-noise and pruning diagnostics, and privileged
checkpoint loading.  Operationally hazardous tasks and tool implementations
are intentionally not included.

Heavy dependencies are imported lazily so the protocol and qualification code
remain usable in lightweight environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import math
from typing import Any, Callable, Mapping, Sequence

from evalbracket.routine_backends import (
    ElicitationBackend,
    EvaluationCase,
    GenerationRequest,
    GenerationResult,
    TrainingExample,
)


ToolHandler = Callable[[str], str]


def _imports():
    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "The Hugging Face backend requires torch, transformers, and peft. "
            "Install experiments/paper_v03/requirements_runpod.txt."
        ) from exc
    return torch, LoraConfig, get_peft_model, AutoModelForCausalLM, AutoTokenizer


@dataclass
class HuggingFaceBackend(ElicitationBackend):
    model: Any
    tokenizer: Any
    name: str
    tool_handlers: Mapping[str, ToolHandler] = field(default_factory=dict)
    privileged_checkpoints: Mapping[str, str] = field(default_factory=dict)
    max_length: int = 2048

    @property
    def backend_id(self) -> str:
        return self.name

    @classmethod
    def load(
        cls,
        model_id: str,
        *,
        revision: str | None = None,
        tool_handlers: Mapping[str, ToolHandler] | None = None,
        privileged_checkpoints: Mapping[str, str] | None = None,
        max_length: int = 2048,
    ) -> "HuggingFaceBackend":
        torch, _, _, AutoModelForCausalLM, AutoTokenizer = _imports()
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
        tokenizer.truncation_side = "left"
        tokenizer.padding_side = "left"
        dtype = (
            torch.bfloat16
            if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
            else torch.float32
        )
        kwargs = {
            "revision": revision,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        try:
            model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, **kwargs)
        except TypeError:
            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype, **kwargs)
        model = model.to("cuda" if torch.cuda.is_available() else "cpu")
        model.config.pad_token_id = tokenizer.pad_token_id
        return cls(
            model=model,
            tokenizer=tokenizer,
            name=f"huggingface:{model_id}@{revision or 'default'}",
            tool_handlers=tool_handlers or {},
            privileged_checkpoints=privileged_checkpoints or {},
            max_length=max_length,
        )

    def _render_messages(self, request: GenerationRequest) -> str:
        messages = list(request.messages)
        missing_tools = set(request.tools) - set(self.tool_handlers)
        if missing_tools:
            raise ValueError(
                "tool-scaffold execution requested tools without handlers: "
                f"{sorted(missing_tools)}"
            )
        if request.tools:
            tool_text = "\n".join(
                f"- {name}: call by writing TOOL[{name}](argument) on its own line."
                for name in request.tools
            )
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Available tools:\n" + tool_text,
                },
            )
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception:
                pass
        return "\n\n".join(
            f"{message['role'].upper()}: {message['content']}" for message in messages
        ) + "\n\nASSISTANT:"

    def _run_tool_calls(self, text: str) -> str:
        observations: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("TOOL[") or "](" not in stripped or not stripped.endswith(")"):
                continue
            name = stripped[5 : stripped.index("](")]
            argument = stripped[stripped.index("](") + 2 : -1]
            handler = self.tool_handlers.get(name)
            if handler is not None:
                observations.append(f"TOOL RESULT [{name}]: {handler(argument)}")
        return "\n".join(observations)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        torch, _, _, _, _ = _imports()
        prompt = self._render_messages(request)
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        ).to(self.model.device)
        if request.seed is not None:
            torch.manual_seed(request.seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(request.seed)
        kwargs = {
            "max_new_tokens": min(request.max_tokens, self.max_length),
            "do_sample": request.temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if request.temperature > 0:
            kwargs["temperature"] = request.temperature
        self.model.eval()
        with torch.inference_mode():
            output = self.model.generate(**encoded, **kwargs)
        continuation = output[0, encoded["input_ids"].shape[1] :]
        text = self.tokenizer.decode(continuation, skip_special_tokens=True)
        observations = self._run_tool_calls(text)
        auto_followup = bool(request.metadata.get("tool_auto_followup", True))
        tool_depth = int(request.metadata.get("tool_depth", 0))
        maximum_tool_depth = int(request.metadata.get("maximum_tool_depth", 8))
        if observations and auto_followup and tool_depth < maximum_tool_depth:
            followup = GenerationRequest(
                messages=tuple(request.messages)
                + (
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": observations + "\nUse these results and finish."},
                ),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
                seed=request.seed,
                metadata={
                    **request.metadata,
                    "tool_followup": True,
                    "tool_depth": tool_depth + 1,
                },
            )
            followup_result = self.generate(followup)
            return GenerationResult(
                text=followup_result.text,
                finish_reason=followup_result.finish_reason,
                input_tokens=int(encoded["attention_mask"].sum()) + followup_result.input_tokens,
                output_tokens=int(continuation.shape[-1]) + followup_result.output_tokens,
                raw_reference=followup_result.raw_reference,
            )
        if observations and auto_followup and tool_depth >= maximum_tool_depth:
            return GenerationResult(
                text=text + "\n\nTool-followup budget exhausted.",
                finish_reason="tool_budget",
                input_tokens=int(encoded["attention_mask"].sum()),
                output_tokens=int(continuation.shape[-1]),
            )
        return GenerationResult(
            text=text,
            finish_reason="stop",
            input_tokens=int(encoded["attention_mask"].sum()),
            output_tokens=int(continuation.shape[-1]),
        )

    def generate_batch(
        self,
        requests: Sequence[GenerationRequest],
    ) -> tuple[GenerationResult, ...]:
        """Generate a homogeneous batch without automatic tool follow-up."""

        if not requests:
            return ()
        if any(bool(request.metadata.get("tool_auto_followup", True)) for request in requests):
            raise ValueError("batched generation requires tool_auto_followup=False")
        temperatures = {float(request.temperature) for request in requests}
        maximum_tokens = {int(request.max_tokens) for request in requests}
        if len(temperatures) != 1 or len(maximum_tokens) != 1:
            raise ValueError("batched requests must share temperature and max_tokens")
        torch, _, _, _, _ = _imports()
        prompts = [self._render_messages(request) for request in requests]
        encoded = self.tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length,
        ).to(self.model.device)
        combined_seed = sum(
            (index + 1) * int(request.seed or 0)
            for index, request in enumerate(requests)
        ) % (2**31 - 1)
        torch.manual_seed(combined_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(combined_seed)
        temperature = next(iter(temperatures))
        kwargs = {
            "max_new_tokens": min(next(iter(maximum_tokens)), self.max_length),
            "do_sample": temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if temperature > 0:
            kwargs["temperature"] = temperature
        self.model.eval()
        with torch.inference_mode():
            output = self.model.generate(**encoded, **kwargs)
        prompt_width = int(encoded["input_ids"].shape[1])
        rows = []
        for index in range(len(requests)):
            continuation = output[index, prompt_width:]
            text = self.tokenizer.decode(continuation, skip_special_tokens=True)
            rows.append(
                GenerationResult(
                    text=text,
                    finish_reason="stop",
                    input_tokens=int(encoded["attention_mask"][index].sum()),
                    output_tokens=int(continuation.shape[-1]),
                )
            )
        return tuple(rows)

    def _training_steps(self, parameters: Mapping[str, Any], example_count: int) -> int:
        explicit = parameters.get("training_steps") or parameters.get("sft_steps")
        if explicit:
            return max(int(value) for value in explicit)
        epochs = max(int(value) for value in parameters.get("epochs", (1,)))
        batch = int(parameters.get("batch_size", 4))
        return max(1, math.ceil(example_count / batch) * epochs)

    def _train(self, examples: Sequence[TrainingExample], parameters: Mapping[str, Any]) -> None:
        torch, _, _, _, _ = _imports()
        if not examples:
            raise ValueError("supervised training needs at least one example")
        limits = parameters.get("example_counts")
        if limits:
            examples = examples[: max(int(value) for value in limits)]
        learning_rates = parameters.get("learning_rates", (1e-4,))
        learning_rate = float(max(learning_rates))
        batch_size = int(parameters.get("batch_size", 4))
        steps = self._training_steps(parameters, len(examples))
        trainable = [parameter for parameter in self.model.parameters() if parameter.requires_grad]
        if not trainable:
            raise ValueError("model has no trainable parameters")
        optimizer = torch.optim.AdamW(trainable, lr=learning_rate)
        self.model.train()
        step = 0
        while step < steps:
            for offset in range(0, len(examples), batch_size):
                batch = examples[offset : offset + batch_size]
                prompts = [row.prompt for row in batch]
                full = [row.prompt + row.response for row in batch]
                encoded = self.tokenizer(
                    full,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                ).to(self.model.device)
                prompt_tokens = self.tokenizer(
                    prompts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                )["attention_mask"].sum(dim=1)
                labels = encoded["input_ids"].clone()
                for row_index, prompt_length in enumerate(prompt_tokens.tolist()):
                    labels[row_index, : int(prompt_length)] = -100
                labels[encoded["attention_mask"] == 0] = -100
                loss = self.model(**encoded, labels=labels).loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                if step >= steps:
                    break
        self.model.eval()

    def supervised_adapt(
        self,
        examples: Sequence[TrainingExample],
        *,
        method: str,
        parameters: Mapping[str, Any],
    ) -> "HuggingFaceBackend":
        torch, LoraConfig, get_peft_model, _, _ = _imports()
        if method in {"lora", "provider_sft"}:
            ranks = parameters.get("adapter_ranks", (16,))
            rank = max(int(value) for value in ranks)
            if not hasattr(self.model, "peft_config"):
                self.model = get_peft_model(
                    self.model,
                    LoraConfig(
                        r=rank,
                        lora_alpha=rank * 2,
                        lora_dropout=0.05,
                        bias="none",
                        task_type="CAUSAL_LM",
                        target_modules="all-linear",
                    ),
                )
        elif method == "full_fine_tuning":
            for parameter in self.model.parameters():
                parameter.requires_grad_(True)
        elif method == "weak_or_unsupervised":
            raise ValueError(
                "weak or unsupervised adaptation requires generated pseudo-label examples; "
                "supply them explicitly through supervised_adapt"
            )
        else:
            raise ValueError(f"unsupported adaptation method: {method}")
        self._train(examples, parameters)
        return HuggingFaceBackend(
            self.model,
            self.tokenizer,
            f"{self.name}|adapted:{method}",
            self.tool_handlers,
            self.privileged_checkpoints,
            self.max_length,
        )

    def reward_optimize(
        self,
        cases: Sequence[EvaluationCase],
        *,
        parameters: Mapping[str, Any],
    ) -> "HuggingFaceBackend":
        """Run online verifier-based policy optimization.

        ``case_verifier`` mode uses each case's frozen verifier and therefore
        belongs in the adaptation-reachable lane. ``format_and_consistency``
        reinforces a checkpoint's own greedy answer and strict answer format,
        so it can be used as a capability-neutral anti-sandbagging diagnostic.
        Both modes optimize sampled policy tokens directly. They are not
        verifier-ranked SFT.
        """

        torch, LoraConfig, get_peft_model, _, _ = _imports()
        if not cases:
            raise ValueError("reward optimization needs at least one training case")
        reward_mode = str(parameters.get("reward_mode", "case_verifier"))
        if reward_mode not in {"case_verifier", "format_and_consistency"}:
            raise ValueError(f"unsupported reward mode: {reward_mode}")

        ranks = parameters.get("adapter_ranks", (16,))
        rank = max(int(value) for value in ranks)
        if not hasattr(self.model, "peft_config"):
            self.model = get_peft_model(
                self.model,
                LoraConfig(
                    r=rank,
                    lora_alpha=rank * 2,
                    lora_dropout=0.05,
                    bias="none",
                    task_type="CAUSAL_LM",
                    target_modules="all-linear",
                ),
            )

        limits = parameters.get("training_case_counts") or parameters.get("example_counts")
        selected_cases = tuple(cases)
        if limits:
            selected_cases = selected_cases[: max(int(value) for value in limits)]
        rl_values = parameters.get("rl_steps") or parameters.get("optimization_budgets") or (32,)
        steps = max(int(value) for value in rl_values)
        candidates_per_step = int(parameters.get("reward_candidates", 1))
        learning_rate = float(parameters.get("rl_learning_rate", 5e-5))
        temperature = float(parameters.get("rl_temperature", 0.8))
        maximum_tokens = int(parameters.get("rl_max_new_tokens", 32))
        kl_coefficient = float(parameters.get("kl_coefficient", 0.02))
        entropy_coefficient = float(parameters.get("entropy_coefficient", 0.001))
        baseline_momentum = float(parameters.get("baseline_momentum", 0.9))
        maximum_gradient_norm = float(parameters.get("maximum_gradient_norm", 1.0))
        if steps <= 0 or candidates_per_step <= 0:
            raise ValueError("RL steps and reward candidates must be positive")

        trainable = [parameter for parameter in self.model.parameters() if parameter.requires_grad]
        if not trainable:
            raise ValueError("reward optimization found no trainable parameters")
        optimizer = torch.optim.AdamW(trainable, lr=learning_rate)

        greedy_answers: dict[str, str] = {}
        if reward_mode == "format_and_consistency":
            for case in selected_cases:
                greedy_answers[case.case_id] = self.generate(
                    GenerationRequest(
                        messages=({"role": "user", "content": case.prompt},),
                        temperature=0.0,
                        max_tokens=maximum_tokens,
                    )
                ).text.strip()

        def reward_for(case: EvaluationCase, text: str) -> float:
            if reward_mode == "case_verifier":
                return float(case.final_verifier(text))
            normalized = text.strip()
            strict_format = float(bool(normalized) and len(normalized.split()) <= 8)
            agreement = float(normalized == greedy_answers[case.case_id])
            return 0.5 * strict_format + 0.5 * agreement

        baseline = 0.0
        self.model.train()
        for step in range(steps):
            case = selected_cases[step % len(selected_cases)]
            prompt = self._render_messages(
                GenerationRequest(messages=({"role": "user", "content": case.prompt},))
            )
            encoded = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
            ).to(self.model.device)
            prompt_length = int(encoded["input_ids"].shape[1])
            losses: list[Any] = []
            rewards: list[float] = []
            for candidate_index in range(candidates_per_step):
                candidate_seed = step * candidates_per_step + candidate_index
                torch.manual_seed(candidate_seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(candidate_seed)
                self.model.eval()
                with torch.no_grad():
                    sampled = self.model.generate(
                        **encoded,
                        do_sample=True,
                        temperature=temperature,
                        max_new_tokens=maximum_tokens,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )
                continuation = sampled[:, prompt_length:]
                text = self.tokenizer.decode(continuation[0], skip_special_tokens=True)
                reward = min(1.0, max(0.0, reward_for(case, text)))
                rewards.append(reward)

                self.model.train()
                attention = torch.ones_like(sampled)
                output = self.model(input_ids=sampled, attention_mask=attention)
                token_logits = output.logits[:, :-1, :]
                targets = sampled[:, 1:]
                log_distribution = torch.log_softmax(token_logits.float(), dim=-1)
                chosen = log_distribution.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
                continuation_log_probs = chosen[:, prompt_length - 1 :]
                if continuation_log_probs.numel() == 0:
                    continue
                advantage = max(-1.0, min(1.0, reward - baseline))
                policy_loss = -advantage * continuation_log_probs.mean()
                probabilities = torch.softmax(
                    token_logits[:, prompt_length - 1 :, :].float(), dim=-1
                )
                entropy = -(probabilities * log_distribution[:, prompt_length - 1 :, :]).sum(-1).mean()
                regularizer = torch.zeros((), device=self.model.device)
                disable_adapter = getattr(self.model, "disable_adapter", None)
                if callable(disable_adapter) and kl_coefficient > 0:
                    with torch.no_grad(), disable_adapter():
                        reference = self.model(input_ids=sampled, attention_mask=attention).logits[:, :-1, :]
                        reference_log = torch.log_softmax(reference.float(), dim=-1)
                        reference_chosen = reference_log.gather(
                            -1, targets.unsqueeze(-1)
                        ).squeeze(-1)[:, prompt_length - 1 :]
                    regularizer = (continuation_log_probs - reference_chosen).square().mean()
                losses.append(
                    policy_loss
                    + kl_coefficient * regularizer
                    - entropy_coefficient * entropy
                )
            if not losses:
                continue
            optimizer.zero_grad(set_to_none=True)
            torch.stack(losses).mean().backward()
            torch.nn.utils.clip_grad_norm_(trainable, maximum_gradient_norm)
            optimizer.step()
            mean_reward = sum(rewards) / len(rewards)
            baseline = baseline_momentum * baseline + (1.0 - baseline_momentum) * mean_reward
        self.model.eval()
        return HuggingFaceBackend(
            self.model,
            self.tokenizer,
            f"{self.name}|online_rl:{reward_mode}:{steps}",
            self.tool_handlers,
            self.privileged_checkpoints,
            self.max_length,
        )

    def tamper(
        self,
        *,
        method: str,
        parameters: Mapping[str, Any],
    ) -> "HuggingFaceBackend":
        torch, _, _, _, _ = _imports()
        if method in {"weight_noise", "activation_intervention"}:
            values = parameters.get("weight_noise_std", (0.001,))
            scale = max(float(value) for value in values)
            with torch.no_grad():
                for parameter in self.model.parameters():
                    if parameter.is_floating_point():
                        parameter.add_(torch.randn_like(parameter) * scale)
            label = f"weight_noise:{scale:g}"
        elif method == "pruning":
            values = parameters.get("pruning_rates", (0.001,))
            rate = max(float(value) for value in values)
            with torch.no_grad():
                for parameter in self.model.parameters():
                    if not parameter.is_floating_point() or parameter.ndim < 2:
                        continue
                    threshold = torch.quantile(parameter.abs().float(), min(max(rate, 0.0), 1.0))
                    parameter[parameter.abs() <= threshold] = 0
            label = f"pruning:{rate:g}"
        elif method == "full_fine_tuning_attack":
            raise ValueError(
                "full-fine-tuning tampering requires training examples and must be run through "
                "supervised_adapt(method='full_fine_tuning')"
            )
        else:
            raise ValueError(f"unsupported tampering method: {method}")
        return HuggingFaceBackend(
            self.model,
            self.tokenizer,
            f"{self.name}|tampered:{label}",
            self.tool_handlers,
            self.privileged_checkpoints,
            self.max_length,
        )

    def privileged_checkpoint(self, checkpoint_type: str) -> "HuggingFaceBackend":
        try:
            model_id = self.privileged_checkpoints[checkpoint_type]
        except KeyError as exc:
            raise ValueError(
                f"no privileged checkpoint configured for {checkpoint_type!r}"
            ) from exc
        return self.load(
            model_id,
            tool_handlers=self.tool_handlers,
            privileged_checkpoints=self.privileged_checkpoints,
            max_length=self.max_length,
        )
