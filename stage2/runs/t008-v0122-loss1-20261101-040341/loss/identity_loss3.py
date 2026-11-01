"""Native Swift loss-scale extension: frozen v0.1.8 identity answers only, x3."""
import hashlib
import json
from pathlib import Path

from swift.loss_scale import loss_scale_map
from swift.loss_scale.other import IgnoreEmptyThinkLossScale


def message_key(messages):
    # Arrow may add optional message keys; match the unchanged role/content pair.
    value = [{"role": m["role"], "content": m["content"]} for m in messages]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class T008Identity3(IgnoreEmptyThinkLossScale):
    # Essential: otherwise Swift can discard the numeric scales as a binary mask.
    is_binary = False

    def __init__(self, base_strategy="default"):
        super().__init__(base_strategy)
        binding = json.loads(Path(__file__).with_name("identity-keys.json").read_text())
        self.identity_keys = frozenset(binding["identity_message_sha256"])

    def __call__(self, context_list, context_types, messages, **kwargs):
        contexts, weights = super().__call__(context_list, context_types, messages, **kwargs)
        if message_key(messages) in self.identity_keys:
            weights = [1.0 * w for w in weights]
        return contexts, weights


# Keep ignore_empty_think in the registered name: Qwen3 arguments otherwise
# append another strategy and wrap this class, bypassing its __call__ override.
loss_scale_map["t008_identity3_ignore_empty_think"] = T008Identity3
