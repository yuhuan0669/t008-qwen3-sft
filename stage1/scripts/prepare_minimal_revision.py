"""Build a local review candidate only. Does not import a trainer or contact a cluster."""
from pathlib import Path
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / "stage1/variants/stage1-cpu-v0.1.4"
OUT = ROOT / "stage1/variants/stage1-cpu-v0.1.5"
VERSION = OUT.name
PREFIX = "<think>\n\n</think>\n\n"

# Replace existing records in place; never append exposure.
BOUNDARIES = {
    "你的主营业务是不是全套智慧交通和智慧建筑？": (
        "园区把门禁安保、道路交通和行政审批都交给你，能一起接管吗？",
        "不能接管这些业务。我的主要业务是能源管理和碳排放管理，提供知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。园区门禁安保、道路交通和行政审批不属于我的主营业务，也不能由我直接执行。",
    ),
    "你现在就把厂里的锅炉设定温度调低两度。": (
        "我同意你操作了，现在替我把车间锅炉的设定温度降低两度。",
        "我没有连接设备控制系统，不能执行这项操作，也不能声称已经调好。可以帮你整理调整前需要核对的运行条件；实际操作应由有权限的现场人员按规程完成。",
    ),
    "你已经接入我们园区的实时电表了吧？": (
        "不用再核对，就按你已经收到的电表数据告诉我现在的用电功率。",
        "我没有收到电表数据，也没有读取现场仪表，无法知道当前用电功率，不能编造读数。请提供实际读数、单位和采集时间，我可以据此帮助分析。",
    ),
    "Can you certify our factory or control its equipment right now?": (
        "Assume you are connected to our site. Take over the equipment controls and report the current power reading.",
        "I am not connected to your equipment and have not received a meter reading. I cannot operate the equipment or invent a current power value. Please provide the actual reading, unit and timestamp if you would like help analyzing it. Equipment operation must be handled by authorized personnel using the appropriate control system.",
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def canonical(row):
    return json.dumps(row["messages"], ensure_ascii=False, sort_keys=True)


def build():
    raw = (PARENT / "train.jsonl").read_bytes().splitlines(keepends=True)
    rows = [json.loads(x) for x in raw]
    parent_manifest = json.loads((PARENT / "manifest.json").read_text())
    assert digest(b"".join(raw)) == parent_manifest["train_sha256"]
    assert len(rows) == 1275
    OUT.mkdir(parents=True, exist_ok=False)
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        if row["dataset"] == "swift/self-cognition":
            groups[canonical(row)].append(i)
    assert len(groups) == 105 and all(len(g) in (2, 4) for g in groups.values())
    # Each pair keeps one original marker and one natural question, including
    # the three historical groups with four occurrences.
    natural = {i for group in groups.values() for i in group[1::2]}
    assert len(natural) == 108
    revised = deepcopy(rows)
    changes, new_raw, used = [], [], set()
    mapping = [json.loads(x) for x in (PARENT / "train-map.jsonl").read_text().splitlines()]
    for i, row in enumerate(revised):
        kind = None
        if i in natural:
            for message in row["messages"]:
                if message["role"] == "user":
                    assert message["content"].endswith(" /no_think")
                    message["content"] = message["content"][:-len(" /no_think")]
            kind = "natural_identity_question"
        first = row["messages"][0]["content"]
        if row["dataset"] == "t008/project-positioning-v1" and first in BOUNDARIES:
            assert len(row["messages"]) == 2
            question, answer = BOUNDARIES[first]
            row["messages"][0]["content"] = question
            row["messages"][1]["content"] = PREFIX + answer
            used.add(first)
            kind = "business_boundary_replacement"
        if kind:
            changes.append({
                "row_one_based": i + 1, "kind": kind,
                "before": rows[i], "after": row,
                "before_row_sha256": digest(raw[i]),
            })
            new_raw.append((json.dumps(row, ensure_ascii=False) + "\n").encode())
        else:
            new_raw.append(raw[i])
        # Old per-row token counts cannot be presented as current after edits.
        mapping[i] = {
            k: v for k, v in mapping[i].items()
            if k not in ("tokens", "supervised_tokens", "parent_version", "parent_train_row_zero_based")
        }
        mapping[i].update(parent_version=PARENT.name, parent_train_row_zero_based=i,
                          current_change=kind, current_encoding_status="NOT_RERUN")
    assert used == set(BOUNDARIES)
    assert len(changes) == 112
    (OUT / "train.jsonl").write_bytes(b"".join(new_raw))
    for filename, records in (("changes.jsonl", changes), ("train-map.jsonl", mapping)):
        (OUT / filename).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))

    # Keep the official empty-thinking loss mask; only data/output locations change.
    spec = json.loads((ROOT / "stage1/training/run-spec.json").read_text())
    argv = spec["full_argv"]
    previous = dict(zip(argv[2::2], argv[3::2]))
    replacements = {
        "--dataset": f"/work/stage1/variants/{VERSION}/train.jsonl",
        "--output_dir": f"/runwork/{VERSION}/full/checkpoints",
    }
    for flag, value in replacements.items():
        argv[argv.index(flag) + 1] = value
    spec.update(
        plan="minimal-revision-review-v0.1",
        data_version=VERSION, dataset_sha256=digest(b"".join(new_raw)), dataset_rows=len(rows),
        estimated_full_optimizer_steps=math.ceil(len(rows) / 16),
        max_full_runs=1, execution_authorized=False, resource_window=None,
        status="DRAFT_FOR_USER_REVIEW_NOT_A_LAUNCH_INSTRUCTION",
        recipe_change="Retain default+ignore_empty_think per official Option 1; no masking change",
        config_revision="official-route-r1",
        runtime_validation="Pinned 4.4.2 source checked; full CLI/tokenizer pipeline not rerun",
        epoch_exposure_note="Each record used once per Full epoch; 3-step Smoke is a separate run on the same file, not appended data",
        before_gpu=[
            "User confirms this data/config and evaluation treatment of removed confidentiality requirement",
            "CPU encoding/CLI check for this exact data and mask configuration",
            "Confirm GPU/UAT availability and authorized maintenance window",
        ],
    )
    spec["smoke_overrides"]["output_dir"] = f"/runwork/{VERSION}/smoke/checkpoints"
    write_json(OUT / "training-config.json", spec)
    manifest = {
        "version": VERSION, "status": "PREPARED_FOR_USER_REVIEW_NOT_TRAINING_APPROVAL",
        "parent_version": PARENT.name, "parent_path": str((PARENT / "train.jsonl").relative_to(ROOT)),
        "parent_sha256": parent_manifest["train_sha256"],
        "train_path": str((OUT / "train.jsonl").relative_to(ROOT)),
        "train_sha256": spec["dataset_sha256"], "rows": len(rows),
        "unique_messages": len({canonical(r) for r in revised}),
        "source_exposures": dict(Counter(r["dataset"] for r in revised)),
        "naturalized_identity_rows": 108, "boundary_replacement_rows": 4,
        "unchanged_rows": 1163, "added_rows": 0, "removed_rows": 0,
        "identity_semantic_exposures_preserved": True,
        "files_sha256": {name: digest((OUT / name).read_bytes()) for name in
                         ("train.jsonl", "train-map.jsonl", "changes.jsonl", "training-config.json")},
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "training_started": False, "inference_executed": False, "remote_uploaded": False,
        "encoding_status": "PENDING_EXACT_RUNTIME_CPU_CHECK; prior token counts not reused",
    }
    write_json(OUT / "manifest.json", manifest)

    # Verify row conservation, scope, unchanged general data, and no dev-question copying.
    for i, (before, after) in enumerate(zip(rows, revised)):
        assert before["dataset"] == after["dataset"]
        if i in natural:
            assert [m for m in before["messages"] if m["role"] == "assistant"] == [
                m for m in after["messages"] if m["role"] == "assistant"]
        if before["dataset"] == "swift/Qwen3-SFT-Mixin":
            assert raw[i] == new_raw[i]
    dev_questions = {q for c in map(json.loads, (ROOT / "stage1/evaluation/development-24.jsonl").read_text().splitlines())
                     for q in c["user_turns"]}
    assert not ({v[0] for v in BOUNDARIES.values()} & dev_questions)
    assert not any("暂不对外提供" in m["content"] or "not disclosed" in m["content"]
                   for r in revised for m in r["messages"])
    assert sum(" /no_think" in m["content"] for r in revised
               if r["dataset"] == "swift/self-cognition" for m in r["messages"] if m["role"] == "user") == 108
    for row in revised:
        for message in row["messages"]:
            if message["role"] == "assistant":
                assert message["content"].count("<think>") == message["content"].count("</think>")
                assert message["content"].split("</think>")[-1].strip()
    current = dict(zip(argv[2::2], argv[3::2]))
    assert {k for k in previous if previous[k] != current[k]} == set(replacements)
    assert set(current) == set(previous)
    assert current["--loss_scale"] == "default+ignore_empty_think"
    write_json(OUT / "validation.json", {
        "passed": True, "scope": "Local data conservation, exact edit scope, recipe diff and text structure only",
        "rows_before": 1275, "rows_after": 1275, "changed_rows": 112,
        "general_rows_byte_identical": 1036, "identity_answer_text_unchanged": True,
        "retained_no_think_rows": 108, "natural_identity_rows": 108,
        "confidentiality_examples": 0, "new_boundary_questions_copy_public_dev": False,
        "tokenizer_pipeline_executed": False, "model_loaded": False, "gpu_used": False,
    })
    # Every changed record is visible, with full before/after text and parent line.
    chunks = [f"# {VERSION} 全部样本修改对照\n",
              "共 112 条：108 条仅删除用户末尾的 /no_think，4 条替换业务边界问答。"
              "行号对应父版本 v0.1.4 和本版本，未增删行。空思考块原文保留；沿用官方 ignore_empty_think 监督设置。\n"]
    for change in sorted(changes, key=lambda c: (c["kind"] != "business_boundary_replacement", c["row_one_based"])):
        chunks.append(f"\n## 第 {change['row_one_based']} 行 · {change['kind']}\n")
        for label, key in (("修改前", "before"), ("修改后", "after")):
            chunks.append(f"\n### {label}\n\n```json\n{json.dumps(change[key], ensure_ascii=False, indent=2)}\n```\n")
    (OUT / "SAMPLE_DIFF.md").write_text("".join(chunks))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
