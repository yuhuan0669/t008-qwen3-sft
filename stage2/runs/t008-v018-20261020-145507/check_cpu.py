"""Actual Swift data/CLI/template checks only; never instantiate model or Trainer."""
import hashlib
import importlib.metadata as md
import json
from collections import Counter
from pathlib import Path

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

R = Path("/data/t008-v018-20261020-145507")
D = R / "stage1/variants/stage1-cpu-v0.1.8"
E = Path("/work/t008-v018-20261020-145507/cpu-check")
spec = json.loads((D / "training-config.json").read_text())
reference = json.loads((R / "stage1/evidence/encoding-report.json").read_text())
assert not torch.cuda.is_available() and not list(Path("/dev").glob("nvidia*"))
assert spec["execution_authorized"] is False
assert hashlib.sha256((D / "train.jsonl").read_bytes()).hexdigest() == spec["dataset_sha256"]
versions = {k: md.version(k) for k in reference["versions"]}
assert versions == reference["versions"], versions
for name, digest in reference["tokenizer_config_sha256"].items():
    assert hashlib.sha256((Path("/base") / name).read_bytes()).hexdigest() == digest, name

parser = HfArgumentParser(SftArguments)
argv = [s.replace("/work/", str(R) + "/") for s in spec["full_argv"][2:]]
_, unknown = parser.parse_known_args(argv)
assert not unknown, unknown
overrides = ["--use_cpu", "true", "--report_to", "none", "--add_version", "false",
             "--output_dir", str(E / "recipe-only"), "--dataset_num_proc", "1"]
args, = parser.parse_args_into_dataclasses(argv + overrides)
assert str(args.training_args.device) == "cpu"
assert args.loss_scale == "default+ignore_empty_think" and args.preserve_thinking is False
assert not args.disable_ignore_empty_think
assert args.max_length == 2048 and args.truncation_strategy == "delete" and args.dataset_shuffle
assert args.tuner_type == "lora" and args.lora_rank == 8 and args.lora_alpha == 32
assert args.num_train_epochs == 1 and args.gradient_accumulation_steps == 16
assert args.per_device_train_batch_size == 1 and args.learning_rate == 1e-4
assert args.lora_dropout == .05
assert getattr(SwiftSft._encode_dataset, "_t008_local_guard", False)

rows = [json.loads(s) for s in (D / "train.jsonl").read_text().splitlines()]
processor = get_processor("/base", model_type="qwen3", download_model=False)
template = get_template(processor, **args.get_template_kwargs())
template.set_mode("train")
unbounded = get_template(processor, **args.get_template_kwargs())
unbounded.max_length = None
unbounded.set_mode("train")
loaded, val = args.load_dataset()
key = lambda r: json.dumps(r["messages"], ensure_ascii=False, sort_keys=True)
assert Counter(map(key, rows)) == Counter(map(key, loaded))

class Stub:
    def _save_val_dataset(self, val):
        assert val is None or len(val) == 0

stub = Stub()
stub.args, stub.template = args, template
encoded, val = SwiftSft._encode_dataset(stub, loaded, val)
assert Counter(map(key, rows)) == Counter(map(key, encoded))
assert len(rows) == len(loaded) == len(encoded) == 1275

cache, audit, mask_probes = {}, [], []
changed_rows = {c["row_one_based"] for c in map(json.loads, (D / "changes.jsonl").read_text().splitlines())}
for i, row in enumerate(rows):
    k = key(row)
    if k not in cache:
        enc = unbounded.encode(row, return_length=True)
        ids, labels = enc["input_ids"], enc["labels"]
        assert len(ids) == len(labels) <= 2048
        assert any(y != -100 for y in labels)
        assert all(y == -100 or x == y for x, y in zip(ids, labels))
        bounded = template.encode(row, return_length=True)
        assert bounded["input_ids"] == ids and bounded["labels"] == labels
        cache[k] = {"tokens": len(ids), "supervised_tokens": sum(y != -100 for y in labels)}
    audit.append({"row_one_based": i + 1, "source": row["dataset"], **cache[k]})
    if i + 1 in changed_rows:
        enc = template.encode(row)
        text = processor.decode([x for x, y in zip(enc["input_ids"], enc["labels"]) if y != -100])
        assert "<think>" not in text and "</think>" not in text
        assert row["messages"][-1]["content"].split("</think>", 1)[1].strip() in text
        mask_probes.append({"row_one_based": i + 1, "empty_think_masked": True,
                            "full_answer_supervised": True, "supervised_text": text})

binding = json.loads((D / "evaluation-config.json").read_text())
fixed = (R / binding["chat_template"]["path"]).read_text()
assert hashlib.sha256(fixed.encode()).hexdigest() == binding["chat_template"]["sha256"]
cases = json.loads((R / "stage2/diagnostics/thinking-chat-template-20261020/cases.json").read_text())
template_checks = []
for c in cases:
    msgs = [{"role": "user", "content": c["user_turns"][0]}]
    for mode in [True, False]:
        old = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=mode)
        new = processor.apply_chat_template(msgs, chat_template=fixed, tokenize=False,
                                            add_generation_prompt=True, enable_thinking=mode)
        assert new == old + "<think>\n" if mode else new == old
        template_checks.append({"id": c["id"], "enable_thinking": mode, "verified": True})

totals = Counter()
for r in audit:
    totals[r["source"]] += r["supervised_tokens"]
report = {
    "verified": True, "data_version": spec["data_version"], "dataset_sha256": spec["dataset_sha256"],
    "rows": len(rows), "actual_loader_rows": len(loaded), "actual_pipeline_rows": len(encoded),
    "members_and_exposure_multiplicity_verified": True, "source_exposures": dict(Counter(r["dataset"] for r in rows)),
    "max_tokens": max(r["tokens"] for r in audit), "overlength_rows": 0, "truncated_rows": 0,
    "empty_supervision_rows": 0, "silent_dropped_rows": 0,
    "total_supervised_tokens": sum(totals.values()), "source_supervised_tokens": dict(totals),
    "empty_think_mask_verified_on_all_changed_rows": True, "changed_rows_checked": len(changed_rows), "versions": versions,
    "tokenizer_config_sha256": reference["tokenizer_config_sha256"], "unknown_cli_flags": unknown,
    "loss_scale": args.loss_scale, "disable_ignore_empty_think": args.disable_ignore_empty_think,
    "preserve_thinking": args.preserve_thinking, "template_kwargs": args.get_template_kwargs(),
    "training_recipe": {"base": spec["base"], "new_lora": spec["new_lora"], "resume": spec["resume"],
                        "epochs": args.num_train_epochs, "batch": args.per_device_train_batch_size,
                        "gradient_accumulation": args.gradient_accumulation_steps, "learning_rate": args.learning_rate,
                        "lora_rank": args.lora_rank, "lora_alpha": args.lora_alpha, "lora_dropout": args.lora_dropout,
                        "target_modules": args.target_modules, "max_length": args.max_length},
    "cpu_overrides": overrides, "evaluation_template_checks": template_checks,
    "weights_loaded": False, "trainer_created": False, "gpu_available": False,
    "clearml_task_created": False, "training_started": False, "inference_executed": False,
}
(E / "encoding-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
(E / "train-encoding.jsonl").write_text("".join(json.dumps(x) + "\n" for x in audit))
(E / "mask-probes.json").write_text(json.dumps(mask_probes, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ["verified", "rows", "max_tokens", "silent_dropped_rows", "training_started"]}))
