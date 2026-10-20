"""Append exposures of existing approved records; never rewrite text or add sources."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil

p = argparse.ArgumentParser()
p.add_argument("--name", required=True)
p.add_argument("--identity", type=int, required=True)
p.add_argument("--positioning", type=int, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
out = root / "stage2/variants" / a.name
out.mkdir(parents=True, exist_ok=False)
original = root / "stage1/data/train.jsonl"
raw = original.read_bytes()
rows = [json.loads(line) for line in raw.decode().splitlines()]
key = lambda row: json.dumps([row["dataset"], row["messages"]], ensure_ascii=False, sort_keys=True)
counts = collections.Counter(map(key, rows))
targets = {"swift/self-cognition": a.identity, "t008/project-positioning-v1": a.positioning}
seen = set()
added = []
mapping = []
for i, row in enumerate(rows):
    k = key(row)
    if k in seen or row["dataset"] not in targets:
        continue
    seen.add(k)
    target = targets[row["dataset"]]
    if target < counts[k]:
        raise ValueError("This append-only variant cannot reduce original exposures")
    for _ in range(target - counts[k]):
        mapping.append({"new_row": len(rows) + len(added), "parent_row": i,
                        "parent_record_sha256": hashlib.sha256(k.encode()).hexdigest()})
        added.append(row)
train = raw + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in added).encode()
d = out / "stage1/data"
d.mkdir(parents=True)
(d / "train.jsonl").write_bytes(train)
digest = hashlib.sha256(train).hexdigest()
(d / "manifest.json").write_text(json.dumps({
    "files_sha256": {"train.jsonl": digest}, "parent_sha256": hashlib.sha256(raw).hexdigest(),
    "rows": len(rows) + len(added), "change": "append existing exposures only"
}, indent=2) + "\n")
(out / "exposure-map.jsonl").write_text("".join(json.dumps(x) + "\n" for x in mapping))
spec = json.loads((root / "stage1/training/run-spec.json").read_text())
spec.update(dataset_sha256=digest, dataset_rows=len(rows) + len(added),
            estimated_full_optimizer_steps=(len(rows) + len(added) + 15) // 16)
auth = json.loads((root / "stage2/runs" / (root / "stage2/run-id.txt").read_text().strip() / "window.json").read_text())
auth.update(parent_approved_data_sha256=auth["approved_data_sha256"], approved_data_sha256=digest,
            data_change_authority="User-approved gpu-review-v0.2 section 2 bounded exposure adjustment",
            adjustment_ref=str(out.relative_to(root)) + "/CHANGE.md")
for relative in ["code/run_identity.py", "stage1/scripts/collect_metrics.py", "stage1/training/local_data_guard.py"]:
    destination = out / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / relative, destination)
(out / "stage1/training/run-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
(out / "window.json").write_text(json.dumps(auth, ensure_ascii=False, indent=2) + "\n")
(out / "stage1/evidence").mkdir()
(out / "stage1/evidence/parent-encoding-report.json").write_bytes((root / "stage1/evidence/encoding-report.json").read_bytes())
print(json.dumps({"variant": a.name, "rows": spec["dataset_rows"], "appended": len(added),
                  "sha256": digest, "counts": dict(collections.Counter(r["dataset"] for r in rows + added))}))
