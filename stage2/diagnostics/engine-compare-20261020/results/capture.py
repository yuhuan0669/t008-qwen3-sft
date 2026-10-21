"""Observe native Swift results; do not alter model, inputs, sampling or outputs."""
import dataclasses
import copy
import json
import os
import time
from swift.infer_engine import TransformersEngine

original_infer = TransformersEngine.infer


def observed_infer(self, *args, **kwargs):
    requests = copy.deepcopy(args[0] if args else kwargs.get('infer_requests'))
    config = args[1] if len(args) > 1 else kwargs.get('request_config')
    start = time.monotonic()
    result = original_infer(self, *args, **kwargs)
    path = os.environ.get('T008_CAPTURE_PATH')
    if path:
        row = {'requests': requests, 'responses': [dataclasses.asdict(r) for r in result],
               'request_config': dataclasses.asdict(config) if config else None,
               'base_generation_config': self.model.generation_config.to_dict(),
               'elapsed_seconds': time.monotonic() - start}
        with open(path, 'a') as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    return result


TransformersEngine.infer = observed_infer
