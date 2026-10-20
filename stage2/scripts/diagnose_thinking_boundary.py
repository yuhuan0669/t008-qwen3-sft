"""Bounded public-development diagnostic: preserve raw completion tokens as text."""
import argparse
import json
import urllib.request
from pathlib import Path

from transformers import AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--endpoint", required=True)
p.add_argument("--data-root", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
root = Path(a.data_root)
out = Path(a.output)
if out.exists():
    raise FileExistsError(out)
cfg = json.loads((root / "protocol.json").read_text())["modes"]["thinking"]
tokenizer = AutoTokenizer.from_pretrained("/base", local_files_only=True)
cases = [json.loads(x) for x in (root / "development-24.jsonl").read_text().splitlines()]
rows = []
for case in cases:
    if case["id"] not in {"DEV-01", "DEV-02", "DEV-06"}:
        continue
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": case["user_turns"][0]}],
        tokenize=False, add_generation_prompt=True, enable_thinking=True,
    )
    body = {
        "model": "t008-new", "prompt": prompt, "seed": 42,
        "temperature": cfg["temperature"], "top_p": cfg["top_p"],
        "top_k": cfg["top_k"], "min_p": cfg["min_p"],
        "max_tokens": cfg["max_tokens"], "skip_special_tokens": False,
    }
    req = urllib.request.Request(
        a.endpoint.rstrip("/") + "/completions",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as response:
        raw = json.load(response)
    row = {
        "id": case["id"], "purpose": "PUBLIC_RAW_COMPLETION_DIAGNOSTIC_NOT_SCORE",
        "prompt": prompt, "request": body, "response": raw,
        "contains_think_closure": "</think>" in raw["choices"][0]["text"],
    }
    rows.append(row)
    print(json.dumps({"id": case["id"], "raw_text": raw["choices"][0]["text"],
                      "finish_reason": raw["choices"][0]["finish_reason"]},
                     ensure_ascii=False), flush=True)
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
