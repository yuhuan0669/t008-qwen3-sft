"""Read-only teacher-forcing and greedy diagnostics. No optimizer or backward pass."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--encode-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    spec = json.loads((root / "inputs.json").read_text())
    import torch
    from swift.model import get_processor
    from swift.template import get_template

    versions = {k: importlib.metadata.version(k) for k in spec["versions"]}
    assert versions == spec["versions"], versions
    tok = get_processor("/base", model_type="qwen3", download_model=False)
    template = get_template(tok, **spec["template_kwargs"])
    template.set_mode("train")
    fixed = (root / "thinking-prefill.jinja").read_text()
    encoded = {}
    for owner, corpus in spec["corpora"].items():
        encoded[owner] = []
        for record in corpus["records"]:
            item = template.encode({"messages": record["messages"]})
            ids, labels = item["input_ids"], item["labels"]
            assert len(ids) == len(labels) and any(v != -100 for v in labels)
            assert all(y == -100 or x == y for x, y in zip(ids, labels))
            supervised = tok.decode([x for x, y in zip(ids, labels) if y != -100])
            assert "<think>" not in supervised and "</think>" not in supervised
            encoded[owner].append(dict(record, input_ids=ids, labels=labels))
    prompts = {}
    for case in spec["cases"]:
        for mode in ("nonthinking", "thinking"):
            text = tok.apply_chat_template(
                [{"role": "user", "content": case["user"]}], chat_template=fixed,
                tokenize=False, add_generation_prompt=True, enable_thinking=mode == "thinking",
            )
            assert text.endswith("<think>\n") if mode == "thinking" else text.endswith("</think>\n\n")
            ids = tok.encode(text, add_special_tokens=False)
            assert tok.decode(ids) == text
            prompts[(case["id"], mode)] = ids
    metadata = {
        "purpose": "IDENTITY_LIKELIHOOD_DIAGNOSTIC_NOT_TRAINING_OR_ACCEPTANCE",
        "versions": versions, "inputs_sha256": sha(root / "inputs.json"),
        "template_sha256": sha(root / "thinking-prefill.jinja"),
        "unique_training_records": {k: len(v) for k, v in encoded.items()},
        "generation": spec["generation"],
        "score_definition": "mean negative log probability in nats over supervised tokens",
        "probability_definition": "exp(-mean NLL) is geometric mean token probability, NOT answer accuracy",
        "thinking_score": "Report forced empty-think prefix and generated reasoning prefix separately",
        "training": False,
    }
    (root / "encoding-check.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    if args.encode_only:
        print(json.dumps(metadata), flush=True)
        return
    assert torch.cuda.is_available()
    for owner, m in spec["models"].items():
        for name, info in m["files"].items():
            assert sha(Path(m["adapter"]) / name) == info["sha256"], (owner, name)
    from transformers import AutoModelForCausalLM
    from peft import PeftModel

    paths = {name: root / (name + ".jsonl") for name in ("training-scores", "probe-scores", "generations")}
    assert not any(p.exists() for p in paths.values()), "Do not silently rerun or overwrite results"

    def emit(which, row):
        with paths[which].open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    model = AutoModelForCausalLM.from_pretrained(
        "/base", local_files_only=True, torch_dtype=torch.bfloat16,
        device_map={"": 0}, attn_implementation="sdpa",
    )
    model.requires_grad_(False)
    model.eval()
    torch.manual_seed(42)

    def score(ids, labels):
        """Exact causal next-token alignment; no loss on the prompt/ignored think."""
        x = torch.tensor([ids], device="cuda")
        positions = [i for i in range(1, len(ids)) if labels[i] != -100]
        assert positions
        with torch.inference_mode():
            out = model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False)
            logits = out.logits[0, torch.tensor(positions, device="cuda") - 1].float()
            target = torch.tensor([labels[i] for i in positions], device="cuda")
            lp = logits.log_softmax(-1)
            chosen = lp.gather(1, target[:, None]).squeeze(1)
            top = logits.argmax(-1)
            ranks = (logits > logits.gather(1, target[:, None])).sum(-1) + 1
            vals, tops, rank_values = chosen.cpu().tolist(), top.cpu().tolist(), ranks.cpu().tolist()
        supervised_ids = [labels[i] for i in positions]
        text = tok.decode(supervised_ids)
        retokenized = tok(text, add_special_tokens=False, return_offsets_mapping=True)
        assert retokenized["input_ids"] == supervised_ids, "Cannot locate target spans reliably"
        ranges = []
        for name in spec["names"]:
            start = 0
            while (at := text.find(name, start)) >= 0:
                ranges.append((at, at + len(name), name))
                start = at + len(name)
        rows = []
        for ordinal, (i, logp, top_id, rank) in enumerate(zip(positions, vals, tops, rank_values)):
            start, end = retokenized["offset_mapping"][ordinal]
            names = [name for a, b, name in ranges if start < b and end > a]
            rows.append({
                "position": i, "token_id": ids[i], "token": tok.decode([ids[i]]),
                "log_probability": logp, "probability": math.exp(logp),
                "rank": rank, "top1_token": tok.decode([top_id]), "names": names,
            })
        loss = -sum(vals) / len(vals)
        name_rows = [r for r in rows if r["names"]]
        return {
            "supervised_tokens": len(rows), "mean_nll": loss,
            "geometric_mean_token_probability": math.exp(-loss),
            "sequence_log_probability": sum(vals),
            "teacher_forced_top1_fraction": sum(r["rank"] == 1 for r in rows) / len(rows),
            "name_token_count": len(name_rows),
            "name_mean_nll": -sum(r["log_probability"] for r in name_rows) / len(name_rows) if name_rows else None,
            "tokens": rows,
        }

    def continuation(prefix, answer):
        # Do not retokenize away or change any observed generation prefix.
        target = tok.encode(answer, add_special_tokens=False)
        ids = prefix + target
        return score(ids, [-100] * len(prefix) + target)

    started = time.monotonic()
    for model_name in spec["generation"]["models"]:
        if model_name == "Full2":
            model = PeftModel.from_pretrained(
                model, spec["models"][model_name]["adapter"], adapter_name=model_name,
                is_trainable=False, local_files_only=True,
            )
        elif model_name != "base":
            model.load_adapter(spec["models"][model_name]["adapter"], adapter_name=model_name,
                               is_trainable=False)
            model.set_adapter(model_name)
        model.requires_grad_(False)
        model.eval()
        assert not any(p.requires_grad for p in model.parameters())
        cache = {}
        for owner, records in encoded.items():
            if model_name != "base" and owner != model_name:
                continue
            for n, record in enumerate(records):
                key = (tuple(record["input_ids"]), tuple(record["labels"]))
                if key not in cache:
                    cache[key] = score(record["input_ids"], record["labels"])
                emit("training-scores", {
                    "model": model_name, "target_version": owner, "record_index": n,
                    "source_rows_one_based": record["source_rows_one_based"],
                    "messages": record["messages"], "score": cache[key],
                })
        print(json.dumps({"model": model_name, "phase": "training_answer_scores_done",
                          "seconds": time.monotonic() - started}), flush=True)
        for case in spec["cases"]:
            owners = ["Full2", "v017", "v018"] if model_name == "base" else [model_name]
            # Fixed empty-think entry, compatible with actual identity training format.
            for owner in owners:
                result = continuation(prompts[(case["id"], "nonthinking")], case["targets"][owner])
                emit("probe-scores", {
                    "model": model_name, "id": case["id"], "target_version": owner,
                    "prefix_kind": "empty_think_answer_entry", "answer": case["targets"][owner], "score": result,
                })
            for mode in ("nonthinking", "thinking"):
                prefix = prompts[(case["id"], mode)]
                x = torch.tensor([prefix], device="cuda")
                max_new = spec["generation"]["max_new_tokens"][mode]
                with torch.inference_mode():
                    output = model.generate(
                        input_ids=x, attention_mask=torch.ones_like(x), do_sample=False,
                        max_new_tokens=max_new, pad_token_id=tok.pad_token_id or tok.eos_token_id,
                        use_cache=True,
                    )
                ids = output[0, len(prefix):].tolist()
                text = tok.decode(ids, skip_special_tokens=False)
                end_think = tok.convert_tokens_to_ids("</think>")
                eos = model.generation_config.eos_token_id
                eos = eos if isinstance(eos, list) else [eos]
                row = {
                    "model": model_name, "id": case["id"], "user": case["user"], "mode": mode,
                    "generated_token_ids": ids, "raw": text, "output_tokens": len(ids),
                    "budget_exhausted": len(ids) >= max_new and ids[-1] not in eos,
                    "answer": text.split("</think>", 1)[1] if mode == "thinking" and "</think>" in text
                              else text if mode == "nonthinking" else None,
                }
                emit("generations", row)
                if mode == "thinking" and end_think in ids:
                    # Observe reasoning through its actual closing token, then fix only the answer separator.
                    reasoning_prefix = prefix + ids[:ids.index(end_think) + 1] + tok.encode("\n\n", add_special_tokens=False)
                    for owner in owners:
                        emit("probe-scores", {
                            "model": model_name, "id": case["id"], "target_version": owner,
                            "prefix_kind": "generated_reasoning_then_fixed_newline_separator",
                            "reasoning_prefix_token_ids": reasoning_prefix,
                            "answer": case["targets"][owner],
                            "score": continuation(reasoning_prefix, case["targets"][owner]),
                        })
                print(json.dumps({"model": model_name, "id": case["id"], "mode": mode,
                                  "tokens": len(ids), "budget_exhausted": row["budget_exhausted"],
                                  "seconds": time.monotonic() - started}), flush=True)
    metadata.update(completed=True, elapsed_seconds=time.monotonic() - started,
                    output_sha256={p.name: sha(p) for p in paths.values()})
    (root / "completed.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
