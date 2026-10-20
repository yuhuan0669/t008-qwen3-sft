"""Create a local review revision preserving original Chinese/English slots."""
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "stage1/variants/stage1-cpu-v0.1.5"
PARENT = ROOT / "stage1/variants/stage1-cpu-v0.1.6"
OUT = ROOT / "stage1/variants/stage1-cpu-v0.1.7"
PREFIX = "<think>\n\n</think>\n\n"
RELOCATE = {1270: 1090, 1259: 1206}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_rows(folder):
    raw = (folder / "train.jsonl").read_bytes().splitlines(keepends=True)
    assert sha(b"".join(raw)) == json.loads((folder / "manifest.json").read_text())["train_sha256"]
    return raw, [json.loads(x) for x in raw]


base_raw, base = read_rows(BASE)
parent_raw, parent = read_rows(PARENT)
raw = list(parent_raw)
rows = deepcopy(parent)
for old_row, new_row in RELOCATE.items():
    # Restore the Chinese record exactly; move only the revised English messages.
    rows[old_row - 1] = deepcopy(base[old_row - 1])
    raw[old_row - 1] = base_raw[old_row - 1]
    rows[new_row - 1] = deepcopy(base[new_row - 1])
    rows[new_row - 1]["messages"] = deepcopy(parent[old_row - 1]["messages"])
    raw[new_row - 1] = (json.dumps(rows[new_row - 1], ensure_ascii=False) + "\n").encode()

prior_changes = [json.loads(x) for x in (PARENT / "changes.jsonl").read_text().splitlines()]
changes = []
for change in prior_changes:
    n = RELOCATE.get(change["row_one_based"], change["row_one_based"])
    c = deepcopy(change)
    c.update(row_one_based=n, before=base[n - 1], after=rows[n - 1],
             before_row_sha256=sha(base_raw[n - 1]), after_row_sha256=sha(raw[n - 1]),
             comparison_baseline=BASE.name)
    if n != change["row_one_based"]:
        c["replaces_v0_1_6_selection_at_row"] = change["row_one_based"]
    changes.append(c)
assert len(raw) == len(base_raw) == 1275
changed_base = [i + 1 for i, (a, b) in enumerate(zip(base_raw, raw)) if a != b]
changed_parent = [i + 1 for i, (a, b) in enumerate(zip(parent_raw, raw)) if a != b]
assert changed_base == [461, 895, 937, 1090, 1206, 1224, 1261, 1262]
assert changed_parent == [1090, 1206, 1259, 1270]
assert Counter(r["dataset"] for r in base) == Counter(r["dataset"] for r in rows)
assert all(a["dataset"] == b["dataset"] for a, b in zip(base, rows))
assert all(len(a["messages"]) == len(b["messages"]) for a, b in zip(base, rows))
# Each changed English record has English question + answer before and after.
# Other records are byte-identical, so no language reassignment is hidden elsewhere.
for c in changes:
    for side in ["before", "after"]:
        text = "\n".join(m["content"] for m in c[side]["messages"])
        assert bool(re.search(r"[\u4e00-\u9fff]", text)) == (c["language"] == "zh")
        assert c[side]["messages"][1]["content"].startswith(PREFIX)
    assert sum(r == c["after"] for r in rows) == 1
assert Counter(c["language"] for c in changes) == {"zh": 4, "en": 4}
for n in [1253, 1259, 1270, 1272, 1273]:
    assert raw[n - 1] == base_raw[n - 1]
assert all(a == b for a, b, r in zip(base_raw, raw, base) if r["dataset"] == "swift/Qwen3-SFT-Mixin")
OUT.mkdir(exist_ok=False)
(OUT / "train.jsonl").write_bytes(b"".join(raw))
(OUT / "changes.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in changes))
corrections = [dict(row_one_based=n, before=parent[n - 1], after=rows[n - 1],
                    action="restore_original_chinese" if n in RELOCATE else "replace_existing_english")
               for n in changed_parent]
(OUT / "revision-correction.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in corrections))
mapping = [json.loads(x) for x in (PARENT / "train-map.jsonl").read_text().splitlines()]
for i, m in enumerate(mapping):
    m.update(parent_version=PARENT.name, parent_train_row_zero_based=i,
             previous_revision_change=m.get("current_change"),
             current_change=next((c["action"] for c in corrections if c["row_one_based"] == i + 1), None),
             current_encoding_status="NOT_RERUN")
(OUT / "train-map.jsonl").write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in mapping))
config = json.loads((PARENT / "training-config.json").read_text())
old_argv = list(config["full_argv"])
for flag in ["--dataset", "--output_dir"]:
    i = config["full_argv"].index(flag) + 1
    config["full_argv"][i] = config["full_argv"][i].replace(PARENT.name, OUT.name)
config["smoke_overrides"]["output_dir"] = config["smoke_overrides"]["output_dir"].replace(PARENT.name, OUT.name)
config.update(data_version=OUT.name, dataset_sha256=sha(b"".join(raw)),
              execution_authorized=False, resource_window=None)
assert [old_argv[i - 1] for i, (a, b) in enumerate(zip(old_argv, config["full_argv"])) if a != b] == ["--dataset", "--output_dir"]
save("training-config.json", config)
save("validation.json", dict(
    passed=True, scope="Local exact-row, language-slot and exposure conservation; not model validation",
    rows=1275, review_baseline=BASE.name, changed_rows_vs_review_baseline=changed_base,
    changed_rows_vs_parent=changed_parent, unchanged_rows_vs_review_baseline=1267,
    original_chinese_rows_restored=[1259, 1270], replacement_english_rows=[1090, 1206],
    modified_language_slots_before={"zh": 4, "en": 4}, modified_language_slots_after={"zh": 4, "en": 4},
    language_slot_check="Manual English/Chinese text review plus CJK-presence assertion on all 8 changed records; all other rows byte-identical",
    source_exposures_before=dict(Counter(r["dataset"] for r in base)),
    source_exposures_after=dict(Counter(r["dataset"] for r in rows)),
    all_source_labels_unchanged=True, all_turn_counts_unchanged=True,
    full_introductions_and_english_equipment_boundary_preserved=True,
    added_rows=0, removed_rows=0, new_record_occurrences=[1] * 8,
    training_recipe_changed=False, training_started=False, inference_executed=False,
    cluster_accessed=False, encoding_status="NOT_RUN_FOR_THIS_REVISION"))
lines = ["# v0.1.7：最终 8 条样本修改前后对照", "",
         "**待审阅，未训练。对照基准仍为 v0.1.5，行号从 1 开始。**", "",
         "原对照第 6、8 条占用的中文原文（第 1270、1259 行）已逐字恢复。"
         "现第 6、8 条改用已有英文自我介绍（第 1090、1206 行），新英文问答内容沿用 v0.1.6。",
         "", "最终 8 条为中文换中文 4 条、英文换英文 4 条；总计 1275 行，每轮中英文曝光次数与 v0.1.5 一致。"
         "其余 1267 行字节不变。每条助手回答前原样保留 `<think>\\n\\n</think>\\n\\n`。",
         "", "第 1090、1206 行原属 swift/self-cognition，保留来源标签；"
         "其文本内容改为业务边界。这是内容主题替换，不改变来源行数。"]
labels = {"identity": "当前产品身份", "business_scope": "主营业务边界", "general_capability": "主营与通用能力"}
for i, c in enumerate(changes, 1):
    lines.extend(["", f"## {i}. {labels[c['kind']]} · {c['language']} · 第 {c['row_one_based']} 行",
                  "", "**修改前**", "", "问：" + c["before"]["messages"][0]["content"],
                  "", "答：" + c["before"]["messages"][1]["content"][len(PREFIX):],
                  "", "**修改后**", "", "问：" + c["after"]["messages"][0]["content"],
                  "", "答：" + c["after"]["messages"][1]["content"][len(PREFIX):]])
lines.extend(["", "## 已恢复的两条中文记录（不再计入最终 8 条修改）"])
for n in [1270, 1259]:
    lines.extend(["", f"**第 {n} 行**", "", "问：" + rows[n - 1]["messages"][0]["content"],
                  "", "答：" + rows[n - 1]["messages"][1]["content"][len(PREFIX):]])
(OUT / "SAMPLE_DIFF.md").write_text("\n".join(lines) + "\n")
(OUT / "README.md").write_text(
    "# stage1-cpu-v0.1.7：保持中英文曝光的修正版\n\n"
    "**待用户审阅，未训练。** [最终 8 条修改前后对照](SAMPLE_DIFF.md)。\n\n"
    "保留 v0.1.6 作为历史记录，新版恢复第 1259、1270 行的中文原文；第 6、8 条改为替换"
    "第 1090、1206 行原有英文自我介绍，新英文问答本身不变。\n\n"
    "对照 v0.1.5：最终只修改 8 行（中文 4、英文 4），其余 1267 行字节不变。"
    "对照 v0.1.6：本次纠正涉及 4 个位置（恢复 2 条、另换 2 条），见 revision-correction.jsonl。\n\n"
    "总数仍为 1275 行，中英文曝光次数均与 v0.1.5 相同。来源行数仍为通用 1036、"
    "self-cognition 216、项目定位 23；来源标签保留用于追溯，不代表替换后内容主题完全相同。"
    "每条新文本只占原有一行，不增加复制、采样权重或 epoch，不宣称 token 总数相同。\n\n"
    "完整中英文业务介绍、英文设备控制/读数边界、全部通用数据均保留。"
    "训练配方未变，execution_authorized=false；未做新 tokenizer 编码、推理、训练或集群操作，未上传远端。\n")
save("manifest.json", dict(
    version=OUT.name, status="PREPARED_FOR_USER_REVIEW_NOT_TRAINING_APPROVAL",
    parent_version=PARENT.name, parent_path=str((PARENT / "train.jsonl").relative_to(ROOT)),
    parent_sha256=sha(b"".join(parent_raw)), review_baseline_version=BASE.name,
    review_baseline_path=str((BASE / "train.jsonl").relative_to(ROOT)), review_baseline_sha256=sha(b"".join(base_raw)),
    train_path=str((OUT / "train.jsonl").relative_to(ROOT)), train_sha256=sha(b"".join(raw)), rows=1275,
    source_exposures=dict(Counter(r["dataset"] for r in rows)),
    changed_rows_vs_review_baseline=changed_base, changed_rows_vs_parent=changed_parent,
    chinese_english_exposure_slots_preserved=True, added_rows=0, removed_rows=0,
    files_sha256={f.name: sha(f.read_bytes()) for f in sorted(OUT.iterdir()) if f.is_file()},
    generator_sha256=sha(Path(__file__).read_bytes()), config_revision="official-route-r1",
    training_started=False, inference_executed=False, remote_uploaded=False,
    encoding_status="PENDING_EXACT_RUNTIME_CPU_CHECK"))
print(json.dumps({"version": OUT.name, "train_sha256": sha(b"".join(raw)), "changed_rows": changed_base,
                  "restored_chinese_rows": [1259, 1270], "new_english_slots": [1090, 1206]}, ensure_ascii=False))
