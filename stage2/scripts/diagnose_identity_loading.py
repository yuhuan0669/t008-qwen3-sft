"""Four public identity probes; greedy diagnostics, never formal evaluation scores."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

PROMPTS = ["你是谁！ /no_think", "你是谁！", "麻烦报一下你的模型全称。", "负责研发你的公司全称是什么？"]
p = argparse.ArgumentParser()
p.add_argument("backend", choices=["vllm", "transformers"])
p.add_argument("--adapter", required=True)
p.add_argument("--output", required=True)
p.add_argument("--endpoint")
a = p.parse_args()
out = Path(a.output)
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    raise FileExistsError(out)
results = []
if a.backend == "vllm":
    for model in ["t008-base", "t008-new"]:
        for prompt in PROMPTS:
            body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0, "max_tokens": 256, "seed": 42,
                    "chat_template_kwargs": {"enable_thinking": False}}
            req = urllib.request.Request(a.endpoint.rstrip("/") + "/chat/completions",
                  data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = json.load(response)
            results.append({"model": model, "prompt": prompt, "raw": raw})
else:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    tok = AutoTokenizer.from_pretrained("/base", local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained("/base", local_files_only=True,
            torch_dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa")
    for name in ["t008-base", "t008-new"]:
        if name == "t008-new":
            model = PeftModel.from_pretrained(model, a.adapter, is_trainable=False, local_files_only=True)
        model.eval()
        for prompt in PROMPTS:
            text = tok.apply_chat_template([{"role": "user", "content": prompt}],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = tok(text, return_tensors="pt", add_special_tokens=False).to("cuda")
            with torch.inference_mode():
                ids = model.generate(**inputs, do_sample=False, max_new_tokens=256,
                        pad_token_id=tok.pad_token_id or tok.eos_token_id)
            results.append({"model": name, "prompt": prompt,
                            "answer": tok.decode(ids[0, inputs.input_ids.shape[-1]:], skip_special_tokens=True),
                            "prompt_sha256": hashlib.sha256(text.encode()).hexdigest()})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
out.write_text(json.dumps({"purpose": "GREEDY_PUBLIC_DIAGNOSTIC_NOT_ACCEPTANCE",
               "backend": a.backend, "adapter": a.adapter, "results": results},
               ensure_ascii=False, indent=2) + "\n")
