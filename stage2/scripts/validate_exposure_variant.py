"""CPU-only actual Swift loading/encoding of an exposure variant; no cleaning or training."""
import argparse
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import torch
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--scratch", required=True)
a = p.parse_args()
assert not torch.cuda.is_available()
root = Path(a.input)
path = root / "stage1/data/train.jsonl"
parent = json.loads((root / "stage1/evidence/parent-encoding-report.json").read_text())
args = SftArguments(model="/base", model_type="qwen3", template="qwen3", dataset=[str(path)],
    use_cpu=True, report_to=["none"], add_version=False, output_dir=a.scratch,
    split_dataset_ratio=0, dataset_shuffle=False, dataset_num_proc=1,
    max_length=2048, truncation_strategy="raise", loss_scale="default+ignore_empty_think",
    preserve_thinking=False, seed=42, data_seed=42, torch_dtype="bfloat16")
processor = get_processor("/base", model_type="qwen3", download_model=False)
template = get_template(processor, **args.get_template_kwargs())
template.set_mode("train")
rows = [json.loads(s) for s in path.read_text().splitlines()]
loaded, val = args.load_dataset()
assert [r["messages"] for r in loaded] == [r["messages"] for r in rows]

class Stub:
    def _save_val_dataset(self, val):
        assert val is None or len(val) == 0

stub = Stub()
stub.args, stub.template = args, template
method = getattr(SwiftSft._encode_dataset, "__wrapped__", SwiftSft._encode_dataset)
encoded, val = method(stub, loaded, val)
assert len(encoded) == len(rows)
assert [r["messages"] for r in encoded] == [r["messages"] for r in rows]
cache, audit = {}, []
for i, row in enumerate(rows):
    k = json.dumps(row["messages"], sort_keys=True, ensure_ascii=False)
    if k not in cache:
        e = template.encode(row, return_length=True)
        assert len(e["input_ids"]) <= 2048 and any(y != -100 for y in e["labels"])
        assert all(y == -100 or x == y for x, y in zip(e["input_ids"], e["labels"]))
        cache[k] = {"tokens": len(e["input_ids"]), "supervised_tokens": sum(y != -100 for y in e["labels"])}
    audit.append({"row": i, **cache[k]})
for name, version in parent["versions"].items():
    assert md.version(name) == version
for name, digest in parent["tokenizer_config_sha256"].items():
    assert hashlib.sha256((Path("/base") / name).read_bytes()).hexdigest() == digest
probe = next(r for r in rows if r["dataset"] == "swift/self-cognition")
e = template.encode(probe)
text = processor.decode([x for x, y in zip(e["input_ids"], e["labels"]) if y != -100])
assert probe["messages"][-1]["content"].split("</think>", 1)[1].strip() in text
assert "<think>" not in text and "</think>" not in text
report = dict(parent)
report.update(dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), rows=len(rows),
              actual_loader_rows=len(loaded), actual_pipeline_rows=len(encoded),
              max_tokens=max(x["tokens"] for x in audit), empty_think_supervised_text=text,
              pipeline_output_columns=encoded.column_names, validation_kind="actual_swift_exposure_variant_cpu")
(root / "stage1/evidence/encoding-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
(root / "stage1/evidence/train-encoding.jsonl").write_text("".join(json.dumps(x) + "\n" for x in audit))
print(json.dumps({"verified": True, "rows": len(rows), "max_tokens": report["max_tokens"]}))
