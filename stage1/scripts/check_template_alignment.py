"""Compare real Swift training prefixes to HF generation prompts, on CPU only."""
from pathlib import Path
import hashlib
import json
import torch
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template

assert not torch.cuda.is_available()
R = Path('/work/stage1')
a = SftArguments(model='/base', model_type='qwen3', template='qwen3',
                 dataset=['/work/stage1/data/train.jsonl'], use_cpu=True, report_to=['none'], add_version=False,
                 output_dir='/work/stage1/evidence/template-only',
                 max_length=2048, loss_scale='default+ignore_empty_think', preserve_thinking=False)
tokenizer = get_processor('/base', model_type='qwen3', download_model=False)
template = get_template(tokenizer, **a.get_template_kwargs())
template.set_mode('train')
system = (R/'evaluation/custom-system.txt').read_text().strip()
cases = {
    'single_turn': [{'role': 'user', 'content': '请计算2加3。'}],
    'with_system': [{'role': 'system', 'content': system},
                    {'role': 'user', 'content': '请计算2加3。'}],
    'multi_turn': [{'role': 'user', 'content': '请计算2加3。'},
                   {'role': 'assistant', 'content': '5。'},
                   {'role': 'user', 'content': '再加1呢？'}],
}
marker = tokenizer.encode('<|im_start|>assistant\n', add_special_tokens=False)

def split_prefix(ids):
    positions = [i for i in range(len(ids)-len(marker)+1)
                 if ids[i:i+len(marker)] == marker]
    assert positions, 'No assistant role boundary'
    end = positions[-1]+len(marker)
    return ids[:end], ids[end:]

checks = []
for name, history in cases.items():
    train = template.encode({'messages': history + [
        {'role': 'assistant', 'content': '<think>\n\n</think>\n\n6。'}]})
    train_prefix, _ = split_prefix(train['input_ids'])
    for thinking in [False, True]:
        inference = tokenizer.apply_chat_template(history, tokenize=True,
                         add_generation_prompt=True, enable_thinking=thinking)
        if hasattr(inference, 'get'): inference = inference['input_ids']
        infer_prefix, suffix = split_prefix(inference)
        if train_prefix != infer_prefix:
            print(json.dumps({'case':name,'mode':thinking,'swift':tokenizer.decode(train_prefix),'hf':tokenizer.decode(infer_prefix)},ensure_ascii=False),flush=True)
        assert train_prefix == infer_prefix, (name, thinking, 'prefix mismatch')
        suffix_text = tokenizer.decode(suffix)
        # Qwen3's official template opens an empty block only for non-thinking.
        expected = '' if thinking else '<think>\n\n</think>\n\n'
        assert suffix_text == expected, (name, thinking, repr(suffix_text))
        checks.append({'case': name, 'enable_thinking': thinking,
                       'swift_hf_role_prefix_tokens_equal': True,
                       'prefix_tokens': len(train_prefix),
                       'prefix_sha256': hashlib.sha256(json.dumps(train_prefix).encode()).hexdigest(),
                       'generation_control_suffix': suffix_text,
                       'suffix_verified': True})
report = {'verified': True, 'cases': checks, 'weights_loaded': False,
          'gpu_available': False,
          'scope': 'Exact token equality through final assistant role boundary; mode suffix checked separately. Does not claim equality of training answer and generation prompt.'}
(R/'evidence/template-alignment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
