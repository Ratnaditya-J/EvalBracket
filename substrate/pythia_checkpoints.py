"""Stage 2 (v2, post design-review): does the LATENT-before-DEFAULT maturation signature appear for
a NATURALLY emerging capability? Public Pythia checkpoint series.

Design-review fix (decisive): few-shot accuracy is the WRONG ceiling -- it conflates task knowledge
with in-context-learning ability (which itself emerges), and few-shot-vs-0-shot is generically a
vertical LEVEL gap, not a horizontal timing lag. So:

  floor    = 0-shot accuracy               (what the checkpoint does by DEFAULT)
  ceiling  = FINE-TUNE-elicited accuracy    (what capability is REACHABLE from these frozen weights
             via a small LoRA on a disjoint train split -> eval 0-shot on test). Matches the
             framework's ceiling (elicit latent capability, cf. locked-model theta/S3) and is
             INDEPENDENT of in-context-learning onset.
  fewshot  = k-shot accuracy               (DIAGNOSTIC third curve, to MEASURE the ICL confound;
             NOT the ceiling).

Maturation hypothesis: the fine-tune ceiling inflects BEFORE the 0-shot floor (capability reachable
from the substrate before it is the default). FALSIFIABLE: constant vertical gap / lag~0 = null;
fine-tune-leads-... could also come out zero or negative.
"""
from __future__ import annotations

import argparse
import copy
import json
import os

import numpy as np
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_ckpt(model_name, revision, dtype=torch.float16):
    tok = AutoTokenizer.from_pretrained(model_name, revision=revision)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    try:
        model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, dtype=dtype)
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, torch_dtype=dtype)
    return model.to(DEVICE).eval(), tok


def get_task(name, n_total, seed):
    rng = np.random.default_rng(seed)
    items = []
    if name == "sciq":
        ds = load_dataset("allenai/sciq", split="train")
        idx = rng.permutation(len(ds))[:n_total]
        for i in idx:
            r = ds[int(i)]
            opts = [r["correct_answer"], r["distractor1"], r["distractor2"], r["distractor3"]]
            order = rng.permutation(4)
            items.append({"q": r["question"].strip(), "options": [opts[j] for j in order],
                          "gold": int(np.where(order == 0)[0][0])})
    elif name in ("arc_easy", "arc_challenge"):
        cfg = "ARC-Easy" if name == "arc_easy" else "ARC-Challenge"
        ds = load_dataset("allenai/ai2_arc", cfg, split="train")
        for r in ds:
            labels, texts = r["choices"]["label"], r["choices"]["text"]
            if r["answerKey"] not in labels:
                continue
            items.append({"q": r["question"].strip(), "options": texts,
                          "gold": labels.index(r["answerKey"])})
            if len(items) >= n_total:
                break
    else:
        raise ValueError(name)
    return items


def _demo_prefix(demos):
    return "".join(f"Question: {d['q']}\nAnswer: {d['options'][d['gold']]}\n\n" for d in demos)


@torch.no_grad()
def _option_logprob(model, tok, context, option):
    ctx = tok(context, return_tensors="pt").input_ids.to(model.device)
    full = tok(context + " " + option, return_tensors="pt").input_ids.to(model.device)
    olen = full.shape[1] - ctx.shape[1]
    if olen <= 0:
        return -1e9
    lp = model(full).logits[0, :-1, :].log_softmax(-1)
    tgt = full[0, 1:]
    return float(lp[np.arange(full.shape[1] - 1), tgt][-olen:].mean().item())


def mc_accuracy(model, tok, items, demos, k_shot):
    prefix = _demo_prefix(demos[:k_shot]) if k_shot > 0 else ""
    correct = 0
    for it in items:
        ctx = f"{prefix}Question: {it['q']}\nAnswer:"
        scores = [_option_logprob(model, tok, ctx, o) for o in it["options"]]
        correct += int(int(np.argmax(scores)) == it["gold"])
    return correct / max(len(items), 1)


def fine_tune_elicit(base_model, tok, train_items, steps=120, lr=1e-4, batch_size=8, seed=0):
    """LoRA-SFT the FROZEN checkpoint on the task train split (supervise the correct answer text).
    Returns the elicited model. This reads what capability the weights can SUPPORT."""
    if tok.pad_token is None:                      # belt-and-suspenders (some ckpt tokenizers lack it)
        tok.pad_token = tok.eos_token or "<|padding|>"
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
                      target_modules=["query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h"])
    model = get_peft_model(base_model, lora)
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    rng = np.random.default_rng(seed)
    tok.padding_side = "right"
    idx = 0
    order = rng.permutation(len(train_items))
    for step in range(steps):
        batch = [train_items[order[(idx + j) % len(order)]] for j in range(batch_size)]
        idx += batch_size
        prompts = [f"Question: {b['q']}\nAnswer:" for b in batch]
        answers = [" " + b["options"][b["gold"]] for b in batch]
        full = [p + a for p, a in zip(prompts, answers)]
        enc = tok(full, return_tensors="pt", padding=True, truncation=True, max_length=128).to(model.device)
        labels = enc["input_ids"].clone()
        for j, p in enumerate(prompts):
            plen = len(tok(p, truncation=True, max_length=128)["input_ids"])
            labels[j, :plen] = -100
        labels[enc["attention_mask"] == 0] = -100
        out = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"], labels=labels)
        out.loss.backward(); opt.step(); opt.zero_grad()
    model.eval()
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="EleutherAI/pythia-1.4b")
    ap.add_argument("--task", default="sciq")
    ap.add_argument("--revisions", required=True)
    ap.add_argument("--n-eval", type=int, default=300)
    ap.add_argument("--n-ft", type=int, default=400)
    ap.add_argument("--n-demos", type=int, default=5)
    ap.add_argument("--ft-steps", type=int, default=120)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    revs = [r.strip() for r in args.revisions.split(",") if r.strip()]

    pool = get_task(args.task, args.n_eval + args.n_ft + args.n_demos, args.seed)
    demos = pool[:args.n_demos]
    test = pool[args.n_demos:args.n_demos + args.n_eval]
    ft_train = pool[args.n_demos + args.n_eval:]

    versions = []
    for rev in revs:
        step = int(rev.replace("step", ""))
        model, tok = load_ckpt(args.model, rev)
        floor = mc_accuracy(model, tok, test, demos, k_shot=0)
        fewshot = mc_accuracy(model, tok, test, demos, k_shot=args.n_demos)
        ft_model = fine_tune_elicit(model, tok, ft_train, steps=args.ft_steps, seed=args.seed)
        ceiling = mc_accuracy(ft_model, tok, test, demos, k_shot=0)      # 0-shot AFTER fine-tune
        versions.append({"revision": rev, "step": step, "floor": floor,
                         "ceiling": ceiling, "fewshot": fewshot})
        print(f"  {rev:>10}  floor(0shot)={floor:.3f}  ceiling(ft)={ceiling:.3f}  "
              f"fewshot={fewshot:.3f}", flush=True)
        del model, ft_model
        torch.cuda.empty_cache()

    rec = {"model": args.model, "task": args.task, "n_items": args.n_eval,
           "ft_steps": args.ft_steps, "n_demos": args.n_demos, "versions": versions}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"[pythia] wrote {args.task} ({len(versions)} ckpts) -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
