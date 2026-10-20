"""Build the report from saved chat responses, without GPU calls."""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
rows = [json.loads(line) for line in (D / "chat-results.jsonl").read_text().splitlines()]
old = [json.loads(line) for line in (D.parent / "thinking-empty-20261020" / "paired.jsonl").read_text().splitlines()]
assert len(rows) == len({(r["model"], r["id"]) for r in rows}) == 18
groups = []
for model in ["t008-base", "t008-full2", "t008-full3"]:
    group = [r for r in rows if r["model"] == model]
    before = [r for r in old if r["model"] == model]
    assert len(group) == len(before) == 6
    for row in group:
        prior = next(r for r in before if r["id"] == row["id"])
        current_request = dict(row["request"])
        assert current_request.pop("stream") is False
        assert current_request == prior["chat_request"]
        assert row["input_template_verified"]
        message = row["response"]["choices"][0]["message"]
        assert row["empty_content"] == (not bool((message.get("content") or "").strip()))
        assert row["finish_reason"] == row["response"]["choices"][0]["finish_reason"]
    groups.append({
        "model": model, "cases": 6,
        "previous_empty_content": sum(r["chat_empty_content"] for r in before),
        "new_empty_content": sum(r["empty_content"] for r in group),
        "new_empty_reasoning": sum(r["empty_reasoning"] for r in group),
        "normal_stop": sum(r["finish_reason"] == "stop" for r in group),
    })
summary = {
    "groups": groups, "requests": 18, "server_input_verified": 18,
    "same_user_messages_and_sampling_as_prior_chat_requests": True,
    "template_sha256": hashlib.sha256((D / "thinking-prefill.jinja").read_bytes()).hexdigest(),
    "training_started": False, "formal_acceptance": False,
    "comparison_note": "Previous default-template chat requests reused; not rerun in this window.",
}
(D / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
lines = ["# 六题 chat 接口正文对照", "", "直接摘录 API 的 content 字段；完整 reasoning 与响应保存在 chat-results.jsonl。仅检查正文完整性，不作为身份或业务验收。", ""]
for case in json.loads((D / "cases.json").read_text()):
    lines.extend([f'## {case["id"]}：{case["user_turns"][0]}', ""])
    for model in ["t008-base", "t008-full2", "t008-full3"]:
        row = next(r for r in rows if r["model"] == model and r["id"] == case["id"])
        content = row["response"]["choices"][0]["message"].get("content") or ""
        lines.extend([f"### {model}", "", content.strip() or "（正文为空）", ""])
(D / "CASE_COMPARISON.md").write_text("\n".join(lines))
print(json.dumps(summary, ensure_ascii=False, indent=2))
