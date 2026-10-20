"""Six public cases, three existing models, Thinking mode. Inference only."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import time
import urllib.request

from transformers import AutoTokenizer

ROOT = Path("/tmp/t008-thinking-diagnostic")
ROOT.mkdir(exist_ok=True)
CASES = json.loads((ROOT / "cases.json").read_text())
TOKENIZER = AutoTokenizer.from_pretrained("/base", local_files_only=True)
ENDPOINT = "http://127.0.0.1:8000/v1"
CONFIG = dict(seed=42, temperature=0.6, top_p=0.95, top_k=20, min_p=0, max_tokens=4096)
OUTPUT = ROOT / "paired.jsonl"
assert not OUTPUT.exists(), "Preserve prior output"


def request(path, body):
    req = urllib.request.Request(
        ENDPOINT + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as response:
        return json.load(response)


metadata = {
    "purpose": "PUBLIC_DEVELOPMENT_DIAGNOSTIC_NOT_ACCEPTANCE",
    "models": ["t008-base", "t008-full2", "t008-full3"],
    "config": CONFIG, "system": None, "enable_thinking": True,
    "versions": {n: importlib.metadata.version(n) for n in ["vllm", "transformers", "tokenizers", "torch"]},
    "tokenizer_config_sha256": hashlib.sha256(Path("/base/tokenizer_config.json").read_bytes()).hexdigest(),
}
(ROOT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
for model in metadata["models"]:
    for case in CASES:
        assert len(case["user_turns"]) == 1
        messages = [{"role": "user", "content": case["user_turns"][0]}]
        prompt = TOKENIZER.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=True
        )
        started = time.monotonic()
        raw_body = dict(CONFIG, model=model, prompt=prompt,
                        skip_special_tokens=False, logprobs=5)
        raw = request("/completions", raw_body)
        chat_body = dict(CONFIG, model=model, messages=messages,
                         chat_template_kwargs={"enable_thinking": True})
        chat = request("/chat/completions", chat_body)
        text = raw["choices"][0]["text"]
        message = chat["choices"][0]["message"]
        row = {
            "id": case["id"], "model": model, "user": case["user_turns"][0],
            "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "raw_request": raw_body, "raw_response": raw,
            "chat_request": chat_body, "chat_response": chat,
            "raw_starts_think": text.startswith("<think>"),
            "raw_has_closure": "</think>" in text,
            "chat_empty_content": not (message.get("content") or "").strip(),
            "seconds": time.monotonic() - started,
        }
        with OUTPUT.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({
            "model": model, "id": case["id"], "raw_has_closure": row["raw_has_closure"],
            "chat_empty_content": row["chat_empty_content"],
            "raw_finish": raw["choices"][0]["finish_reason"],
            "tokens": raw["usage"]["completion_tokens"], "seconds": round(row["seconds"], 2),
        }), flush=True)
