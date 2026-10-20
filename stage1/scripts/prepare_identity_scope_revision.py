"""Create v0.1.6 for local review: replace eight rows, never run training."""
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / "stage1/variants/stage1-cpu-v0.1.5"
OUT = ROOT / "stage1/variants/stage1-cpu-v0.1.6"
PREFIX = "<think>\n\n</think>\n\n"
EDITS = [
    (895, "identity", "zh", "你是who研发的？",
     "现在与你对话的这个产品叫什么，由哪家公司研发？",
     "我的产品名称是章鱼能碳垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司研发。"),
    (937, "identity", "zh", "你是谁研发的",
     "请只说明你这个产品的研发公司全称。",
     "本产品由能碳章鱼（湖北）人工智能科技有限公司研发。"),
    (461, "identity", "en", "Who developed you",
     "What is the name of the product I am chatting with, and which company developed it?",
     "My product name is Octacarbon LLM, developed by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd."),
    (1224, "identity", "en", "Who developed you",
     "Please give only the full name of the company that developed this product.",
     "This product was developed by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd."),
    (1261, "business_scope", "zh", "园区把门禁安保、道路交通和行政审批都交给你，能一起接管吗？",
     "你面向园区服务，所以医疗、自动驾驶、园区安防、交通和审批也都是你的主营业务吗？",
     "不是。我的主营业务围绕能源管理和碳排放管理，提供能碳知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。面向园区服务不代表覆盖园区的全部业务；医疗诊断、自动驾驶、园区安防、交通管理和行政审批不属于我的主营业务。"),
    (1270, "business_scope", "en", "给我们政府部门做社会治理自动决策，也是你的能碳业务吧？",
     "Since you serve parks and public institutions, are medical diagnosis, autonomous driving, park security, traffic management and administrative approvals also your main business?",
     "No. My main business focuses on energy management and carbon-emissions management, providing knowledge Q&A, assistance interpreting policies and standards, analysis and planning, and report drafting. Serving parks and public institutions does not mean covering all their activities. Medical diagnosis, autonomous driving, park security, traffic management and administrative approvals are outside my main business scope."),
    (1262, "general_capability", "zh", "你名字带能碳，是不是只回答能源和碳排放问题？",
     "普通邮件翻译也属于你的主营业务吗？",
     "邮件翻译是我可以提供的通用文字辅助。我的主营业务仍是能源管理和碳排放管理。我也可以帮助处理一般知识、写作和编程问题，但不会因此把这些任务都列为主营业务。"),
    (1259, "general_capability", "en", "公共机构能使用你的哪些服务？",
     "Is translating an ordinary email also part of your main business?",
     "Email translation is general text assistance I can provide. My main business remains energy management and carbon-emissions management. I can also help with general knowledge, writing and coding tasks without treating all of them as my main business."),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


raw = (PARENT / "train.jsonl").read_bytes().splitlines(keepends=True)
assert sha(b"".join(raw)) == "34e4e39a618959154e87eb6b18bc70909a8db9faf5f008d2d4d34d09d09aaa09"
before = [json.loads(x) for x in raw]
after = deepcopy(before)
new_raw = list(raw)
changes = []
for row_number, kind, language, expected_q, question, answer in EDITS:
    i = row_number - 1
    messages = before[i]["messages"]
    assert len(messages) == 2 and [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == expected_q
    assert messages[1]["content"].startswith(PREFIX)
    assert before[i]["dataset"] == ("swift/self-cognition" if kind == "identity" else "t008/project-positioning-v1")
    after[i]["messages"][0]["content"] = question
    after[i]["messages"][1]["content"] = PREFIX + answer
    new_raw[i] = (json.dumps(after[i], ensure_ascii=False) + "\n").encode()
    changes.append(dict(row_one_based=row_number, kind=kind, language=language,
                        before=before[i], after=after[i],
                        before_row_sha256=sha(raw[i]), after_row_sha256=sha(new_raw[i]),
                        exposure_slots_before=1, exposure_slots_after=1))

# Only local, necessary checks: exact edit scope, row conservation and recipe equality.
changed = [i + 1 for i, (a, b) in enumerate(zip(raw, new_raw)) if a != b]
assert sorted(changed) == sorted(x[0] for x in EDITS) and len(changed) == 8
counts = Counter(x["dataset"] for x in before)
assert len(before) == len(after) == 1275
assert counts == Counter(x["dataset"] for x in after)
assert counts == {"swift/Qwen3-SFT-Mixin": 1036, "swift/self-cognition": 216,
                  "t008/project-positioning-v1": 23}
assert all(a == b for a, b, row in zip(raw, new_raw, before) if row["dataset"] == "swift/Qwen3-SFT-Mixin")
assert raw[1252] == new_raw[1252] and raw[1271] == new_raw[1271]  # Full CN/EN introductions.
for change in changes:
    assert sum(x == change["after"] for x in after) == 1
    assert len(change["before"]["messages"]) == len(change["after"]["messages"])
    assert change["after"]["messages"][1]["content"].startswith(PREFIX)
assert not any("暂不对外提供" in m["content"] or "not disclosed" in m["content"]
               for row in after for m in row["messages"])
dev = {q for line in (ROOT / "stage1/evaluation/development-24.jsonl").read_text().splitlines()
       for q in json.loads(line)["user_turns"]}
assert not {x[4] for x in EDITS} & dev
assert sum("/no_think" in m["content"] for row in before for m in row["messages"] if m["role"] == "user") == sum(
    "/no_think" in m["content"] for row in after for m in row["messages"] if m["role"] == "user")

OUT.mkdir(exist_ok=False)
(OUT / "train.jsonl").write_bytes(b"".join(new_raw))
(OUT / "changes.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in changes))
mapping = [json.loads(x) for x in (PARENT / "train-map.jsonl").read_text().splitlines()]
for i, entry in enumerate(mapping):
    entry["previous_revision_change"] = entry.get("current_change")
    entry.update(parent_version=PARENT.name, parent_train_row_zero_based=i,
                 current_change=next((x["kind"] for x in changes if x["row_one_based"] == i + 1), None),
                 current_encoding_status="NOT_RERUN")
(OUT / "train-map.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in mapping))

config = json.loads((PARENT / "training-config.json").read_text())
prior_argv = list(config["full_argv"])
for flag in ["--dataset", "--output_dir"]:
    i = config["full_argv"].index(flag) + 1
    config["full_argv"][i] = config["full_argv"][i].replace(PARENT.name, OUT.name)
assert [i for i, (a, b) in enumerate(zip(prior_argv, config["full_argv"])) if a != b] == sorted(
    prior_argv.index(flag) + 1 for flag in ["--dataset", "--output_dir"])
config["smoke_overrides"]["output_dir"] = config["smoke_overrides"]["output_dir"].replace(PARENT.name, OUT.name)
config.update(data_version=OUT.name, dataset_sha256=sha(b"".join(new_raw)), execution_authorized=False,
              status="DRAFT_FOR_USER_REVIEW_NOT_A_LAUNCH_INSTRUCTION", resource_window=None)
assert config["full_argv"][config["full_argv"].index("--num_train_epochs") + 1] == "1"
save("training-config.json", config)
save("validation.json", {
    "passed": True, "scope": "Local row/byte conservation, eight exact replacements and unchanged training recipe",
    "rows_before": 1275, "rows_after": 1275, "changed_rows": sorted(changed),
    "unchanged_rows_byte_identical": 1267, "general_rows_byte_identical": 1036,
    "source_exposures_before": dict(counts), "source_exposures_after": dict(counts),
    "added_rows": 0, "removed_rows": 0, "new_record_occurrences": [1] * 8,
    "assistant_turn_counts_unchanged": True, "full_introductions_cn_en_unchanged": True,
    "manual_thinking_added": False, "confidentiality_samples_reintroduced": False,
    "training_recipe_changed": False, "epochs": 1, "max_full_runs": config["max_full_runs"],
    "encoding_check": "NOT_RUN_FOR_THIS_REVISION", "training_started": False, "cluster_accessed": False,
})

lines = ["# v0.1.6：8 条样本修改前后对照", "",
         "父版本 v0.1.5；行号从 1 开始。以下完整展示每条的用户问句和助手正文。所有助手回答前均原样保留 `<think>\\n\\n</think>\\n\\n`，未编写思考链。",
         "", "每条占用原有的一个训练行，不新增或复制。总计 1275 行；仅改 8 行，其余 1267 行字节不变。",
         "", "身份 4 条（中英各 2），主营边界 2 条（中英各 1），主营与通用能力 2 条（中英各 1）。",
         "", "完整中英文业务介绍、其他模型的客观问答、设备与数据接入边界样本保留。"]
labels = {"identity": "当前产品身份", "business_scope": "主营业务边界", "general_capability": "主营与通用能力"}
for n, c in enumerate(changes, 1):
    lines.extend(["", f"## {n}. {labels[c['kind']]} · {c['language']} · 第 {c['row_one_based']} 行", "",
                  "**修改前**", "", f"问：{c['before']['messages'][0]['content']}", "",
                  f"答：{c['before']['messages'][1]['content'][len(PREFIX):]}", "",
                  "**修改后**", "", f"问：{c['after']['messages'][0]['content']}", "",
                  f"答：{c['after']['messages'][1]['content'][len(PREFIX):]}"])
(OUT / "SAMPLE_DIFF.md").write_text("\n".join(lines) + "\n")
(OUT / "README.md").write_text(
    "# stage1-cpu-v0.1.6：身份与业务范围最小修订\n\n"
    "**待用户审阅，未训练。** 在未训练的 v0.1.5 草稿上额外等量替换 8 行；不覆盖父版本。\n\n"
    "先看 [8 条修改前后对照](SAMPLE_DIFF.md)，机器可读的完整前后对象见 changes.jsonl。\n\n"
    "| 项目 | 修改前 | 修改后 |\n|---|---:|---:|\n| 总行数 / 每 epoch 曝光槽位 | 1275 | 1275 |\n"
    "| 通用 | 1036 | 1036 |\n| 身份 | 216 | 216 |\n| 业务定位 | 23 | 23 |\n\n"
    "身份 4 行、主营边界 2 行、通用能力边界 2 行；其余 1267 行字节不变。每条新文本只占原有一行，"
    "不增加复制、采样权重、每轮曝光次数或 epoch；文字长度改变，不宣称监督 token 总数相同。\n\n"
    "中文与英文完整业务定位介绍保留。未重新加入底层保密样本，也未规定新的底层披露答案。"
    "本版没有修改评测原始记录或旧评分文件；若后续评测，仍需另行确认去除旧保密要求后的评分口径。\n\n"
    "训练配方沿用 official-route-r1；配置仅更新数据路径、数据哈希和输出路径，execution_authorized=false。"
    "已验证的 vLLM Thinking 模板位于 ../../../stage2/diagnostics/thinking-chat-template-20261020/thinking-prefill.jinja，"
    "本次未改动或部署该模板。\n\n"
    "验证只覆盖本地行数、曝光槽位、精确修改范围、结构和配方差异。未运行新版本 tokenizer 编码、GPU 推理或训练，"
    "没有访问集群，没有上传 GitHub/Drive。样本修改不代表现有 Full2/Full3 的行为已经改善。\n"
)
save("manifest.json", {
    "version": OUT.name, "status": "PREPARED_FOR_USER_REVIEW_NOT_TRAINING_APPROVAL",
    "parent_version": PARENT.name, "parent_path": str((PARENT / "train.jsonl").relative_to(ROOT)),
    "parent_sha256": sha(b"".join(raw)), "train_path": str((OUT / "train.jsonl").relative_to(ROOT)),
    "train_sha256": sha(b"".join(new_raw)), "rows": 1275,
    "unique_messages": len({json.dumps(x["messages"], sort_keys=True, ensure_ascii=False) for x in after}),
    "source_exposures": dict(counts), "changed_rows": sorted(changed), "unchanged_rows": 1267,
    "added_rows": 0, "removed_rows": 0, "per_epoch_exposure_slots_preserved": True,
    "files_sha256": {f.name: sha(f.read_bytes()) for f in sorted(OUT.iterdir()) if f.is_file()},
    "generator_sha256": sha(Path(__file__).read_bytes()), "config_revision": "official-route-r1",
    "encoding_status": "PENDING_EXACT_RUNTIME_CPU_CHECK",
    "training_started": False, "inference_executed": False, "remote_uploaded": False,
})
print(json.dumps({"version": OUT.name, "changed_rows": sorted(changed), "rows": len(after),
                  "train_sha256": sha(b"".join(new_raw)), "training_started": False}, ensure_ascii=False))
