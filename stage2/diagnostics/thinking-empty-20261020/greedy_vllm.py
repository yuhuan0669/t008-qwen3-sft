"""Deterministic cross-backend controls on the same six public cases."""
from pathlib import Path
import hashlib
import json
import urllib.request
from transformers import AutoTokenizer

root = Path("/tmp/t008-thinking-diagnostic")
cases = json.loads((root / "cases.json").read_text())
tokenizer = AutoTokenizer.from_pretrained("/base", local_files_only=True)
output = root / "greedy-vllm.jsonl"
assert not output.exists()
for model in ["t008-base", "t008-full2", "t008-full3"]:
    for case in cases:
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": case["user_turns"][0]}],
            tokenize=False, add_generation_prompt=True, enable_thinking=True,
        )
        body = dict(model=model, prompt=prompt, temperature=0, max_tokens=4096,
                    repetition_penalty=1.0, seed=42, skip_special_tokens=False, logprobs=5)
        req = urllib.request.Request("http://127.0.0.1:8000/v1/completions",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=240) as response:
            raw = json.load(response)
        text = raw["choices"][0]["text"]
        row = dict(model=model, id=case["id"], request=body, response=raw,
                   prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                   has_closure="</think>" in text,
                   visible_answer=text.split("</think>", 1)[1].strip() if "</think>" in text else None)
        with output.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"model": model, "id": case["id"], "has_closure": row["has_closure"],
                          "tokens": raw["usage"]["completion_tokens"]}), flush=True)
