"""Independent Transformers+PEFT generation, existing weights only; never train."""
from pathlib import Path
import hashlib
import json
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

cases = json.loads(CASES_JSON)  # populated in the task-owned Pod command
adapters = json.loads(ADAPTERS_JSON)
tokenizer = AutoTokenizer.from_pretrained("/base", local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    "/base", local_files_only=True, torch_dtype=torch.bfloat16,
    device_map={"": 0}, attn_implementation="sdpa",
)
model.eval()
think_id = tokenizer.convert_tokens_to_ids("<think>")
eos = model.generation_config.eos_token_id
eos_ids = eos if isinstance(eos, list) else [eos]
for name, prefill in [("t008-base", False), ("t008-full2", False),
                      ("t008-full3", False), ("t008-full3", True)]:
    if name == "t008-full2":
        model = PeftModel.from_pretrained(model, adapters[name], adapter_name="full2",
                                         local_files_only=True, is_trainable=False)
        model.set_adapter("full2")
    elif name == "t008-full3" and not prefill:
        model.load_adapter(adapters[name], adapter_name="full3",
                           local_files_only=True, is_trainable=False)
        model.set_adapter("full3")
    model.eval()
    for case in cases:
        started = time.monotonic()
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": case["user_turns"][0]}],
            tokenize=False, add_generation_prompt=True, enable_thinking=True,
        )
        if prefill:
            prompt += "<think>\n"
        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
        with torch.inference_mode():
            probs = model(**inputs, use_cache=False).logits[0, -1].float().softmax(-1)
            values, ids = probs.topk(5)
            top = [{"id": int(i), "token": tokenizer.decode([int(i)], skip_special_tokens=False),
                    "probability": float(v)} for i, v in zip(ids, values)]
            think_probability = float(probs[think_id])
            generated = model.generate(
                **inputs, do_sample=False, max_new_tokens=4096,
                repetition_penalty=1.0, use_cache=True,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )[0, inputs.input_ids.shape[-1]:]
        token_ids = generated.tolist()
        text = tokenizer.decode(token_ids, skip_special_tokens=False)
        without_eos = tokenizer.decode(
            token_ids[:-1] if token_ids and token_ids[-1] in eos_ids else token_ids,
            skip_special_tokens=False,
        )
        row = {
            "backend": "Transformers+PEFT", "model": name, "id": case["id"],
            "prefill_think_start": prefill,
            "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "raw_text": text, "text_without_terminal_eos": without_eos,
            "token_ids": token_ids, "tokens": len(token_ids),
            "finish_reason": "eos" if token_ids and token_ids[-1] in eos_ids else "length",
            "has_closure": "</think>" in text, "first_token_top5": top,
            "think_start_probability": think_probability,
            "seconds": time.monotonic() - started,
        }
        print("RESULT_JSON=" + json.dumps(row, ensure_ascii=False), flush=True)
