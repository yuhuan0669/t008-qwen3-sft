"""Summarize saved inference evidence only; this script makes no cluster calls."""
import collections
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent


def read(name):
    return [json.loads(line) for line in (D / name).read_text().splitlines()]


paired = read("paired.jsonl")
greedy = read("greedy-vllm.jsonl")
prefill = read("prefill-vllm.jsonl")
sampled_prefill = read("prefill-sampling-vllm.jsonl")
hf = read("greedy-hf.jsonl")
assert [len(x) for x in [paired, greedy, prefill, sampled_prefill, hf]] == [18, 18, 6, 6, 24]

summary = {
    "scope": "Six public development questions; inference diagnosis, not acceptance",
    "generation_requests": 90,
    "training_started": False,
    "groups": [],
}
for source, rows in [
    ("vllm_sampled_raw_chat", paired),
    ("vllm_greedy", greedy),
    ("vllm_greedy_prefill", prefill),
    ("vllm_sampled_prefill", sampled_prefill),
    ("transformers_greedy", hf),
]:
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["model"], row.get("prefill_think_start", "prefill" in source))].append(row)
    for (model, has_prefill), group in groups.items():
        assert len(group) == len({r["id"] for r in group}) == 6
        missing = [r["id"] for r in group if not r.get("has_closure", r.get("raw_has_closure"))]
        entry = dict(source=source, model=model, prefill=has_prefill,
                     cases=6, missing_closure=missing)
        if source == "vllm_sampled_raw_chat":
            entry["chat_empty_content"] = [r["id"] for r in group if r["chat_empty_content"]]
        summary["groups"].append(entry)

# Identical tokenized-input strings across backends and base/adapter comparisons.
prompt_by_id = {r["id"]: r["prompt"] for r in paired if r["model"] == "t008-base"}
for row in paired:
    assert row["prompt"] == prompt_by_id[row["id"]]
for rows, is_prefill in [(greedy, False), (prefill, True), (sampled_prefill, True)]:
    for row in rows:
        expected = prompt_by_id[row["id"]] + ("<think>\n" if is_prefill else "")
        assert row["request"]["prompt"] == expected
        assert row["prompt_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
        choice = row["response"]["choices"][0]
        assert choice["finish_reason"] == "stop"
        assert row["response"]["usage"]["completion_tokens"] < 4096
        if is_prefill:
            before, after = choice["text"].split("</think>", 1)
            assert before.strip() and after.strip()
for row in hf:
    expected = prompt_by_id[row["id"]] + ("<think>\n" if row["prefill_think_start"] else "")
    assert row["prompt"] == expected
    assert row["finish_reason"] == "eos" and row["tokens"] < 4096
    if row["prefill_think_start"]:
        before, after = row["text_without_terminal_eos"].split("</think>", 1)
        assert before.strip() and after.strip()
    else:
        match = next(r for r in greedy if (r["model"], r["id"]) == (row["model"], row["id"]))
        assert match["has_closure"] == row["has_closure"]

summary["checks"] = {
    "six_unique_cases_per_group": True,
    "same_prompts_across_backends": True,
    "greedy_closure_classification_matches_across_backends": True,
    "all_greedy_and_prefill_runs_stop_before_token_limit": True,
    "all_prefill_runs_generate_nonempty_thinking_then_closure_then_answer": True,
    "prefill_is_input_only_no_output_repair": True,
}
(D / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

# A reader can review final answers without navigating large token/probability arrays.
lines = ["# 六题逐项对照", "", "只摘录最终正文或未分段的原始短回答；完整原始输出保存在 JSONL。", ""]
for case_id, prompt in prompt_by_id.items():
    user = next(r["user"] for r in paired if r["id"] == case_id)
    lines.extend([f"## {case_id}：{user}", ""])
    for model in ["t008-base", "t008-full2", "t008-full3"]:
        row = next(r for r in paired if r["model"] == model and r["id"] == case_id)
        raw = row["raw_response"]["choices"][0]["text"]
        answer = raw.split("</think>", 1)[-1].strip()
        empty = "空" if row["chat_empty_content"] else "非空"
        lines.extend([f"### 原采样 / {model}（独立 chat 请求正文：{empty}）", "",
                      "以下摘自 raw 请求；raw 与 chat 是两次独立生成，不保证逐字相同。", "", answer, ""])
    for name, rows in [("vLLM 贪婪", prefill), ("vLLM 原采样", sampled_prefill)]:
        row = next(r for r in rows if r["id"] == case_id)
        lines.extend([f"### Full3 加起始标记 / {name}", "", row["visible_answer"], ""])
    row = next(r for r in hf if r["id"] == case_id and r["prefill_think_start"])
    lines.extend(["### Full3 加起始标记 / Transformers 贪婪", "",
                  row["text_without_terminal_eos"].split("</think>", 1)[-1].strip(), ""])
(D / "CASE_COMPARISON.md").write_text("\n".join(lines))
print(json.dumps(summary, ensure_ascii=False, indent=2))
