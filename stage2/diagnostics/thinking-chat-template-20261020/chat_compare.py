"""18 chat requests on existing weights; no training and no response rewriting."""
import hashlib
import importlib.metadata
import json
import time
import urllib.request
from pathlib import Path

from transformers import AutoTokenizer

D = Path("/tmp/t008-chat-template")
T = AutoTokenizer.from_pretrained("/base", local_files_only=True)
CASES = json.loads((D / "cases.json").read_text())
TEMPLATE = (D / "thinking-prefill.jinja").read_text()
CONFIG = dict(seed=42, temperature=0.6, top_p=0.95, top_k=20, min_p=0, max_tokens=4096)
assert not (D / "chat-results.jsonl").exists()


def request(route, body):
    req = urllib.request.Request("http://127.0.0.1:8000/v1" + route,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as response:
        return json.load(response)


meta = {
    "scope": "Six public development cases, chat-interface format verification only",
    "template_sha256": hashlib.sha256(TEMPLATE.encode()).hexdigest(),
    "config": CONFIG,
    "system": None,
    "versions": {n: importlib.metadata.version(n) for n in ["vllm", "transformers", "peft", "torch"]},
}
(D / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
for model in ["t008-base", "t008-full2", "t008-full3"]:
    for case in CASES:
        messages = [{"role": "user", "content": case["user_turns"][0]}]
        body = dict(CONFIG, model=model, messages=messages, stream=False,
                    chat_template_kwargs={"enable_thinking": True})
        expected = T.apply_chat_template(messages, chat_template=TEMPLATE,
                                         tokenize=True, add_generation_prompt=True,
                                         enable_thinking=True)
        if hasattr(expected, "keys"):
            expected = expected["input_ids"]
        rendered = request("/chat/completions/render", body)
        assert rendered["token_ids"] == expected, "Server ignored or altered template"
        start = time.monotonic()
        response = request("/chat/completions", body)
        choice = response["choices"][0]
        message = choice["message"]
        row = {
            "model": model, "id": case["id"], "user": case["user_turns"][0],
            "request": body, "server_render": rendered, "response": response,
            "input_template_verified": True,
            "empty_content": not (message.get("content") or "").strip(),
            "empty_reasoning": not (message.get("reasoning") or message.get("reasoning_content") or "").strip(),
            "finish_reason": choice["finish_reason"], "seconds": time.monotonic() - start,
        }
        with (D / "chat-results.jsonl").open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({k: row[k] for k in ["model", "id", "empty_content", "empty_reasoning",
                                             "finish_reason", "seconds"]}), flush=True)
