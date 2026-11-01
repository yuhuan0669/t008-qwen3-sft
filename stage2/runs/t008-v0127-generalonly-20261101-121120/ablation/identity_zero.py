"""Zero all non-general source CE after native encoding; preserve labels and denominator."""
import hashlib
import inspect
import json
import os
from pathlib import Path

def token_key(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()

def make_compute_loss(native, members, audit_path=None):
    def compute(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        assert self.accelerator.num_processes == 1
        assert self.template.sequence_parallel_size == 1 and not self.template.padding_free
        assert not getattr(self.template, 'packing', False)
        assert inputs.get('compute_loss_func') is None and self.label_smoother is None
        assert inputs['input_ids'].shape[0] == 1
        ids = inputs['input_ids'][0]
        if 'attention_mask' in inputs:
            assert inputs['attention_mask'].ndim == 2
            ids = ids[inputs['attention_mask'][0].bool()]
        key = token_key(ids.detach().cpu().tolist())
        member = members[key]
        labels = inputs['labels']
        weights = inputs['loss_scale']
        valid = labels != -100
        is_identity = member['identity']
        zeroed = member['group'] != 'general'
        assert bool((weights == 3).any()) == is_identity
        assert int(valid.sum()) == member['valid_tokens']
        before = float(weights.sum())
        if zeroed:
            # Keep the existing forward/backward and RNG progression, including
            # zero-gradient rows. Do not turn labels into -100 or skip batches.
            inputs = dict(inputs)
            inputs['loss_scale'] = weights * 0.0
        after = float(inputs['loss_scale'].sum())
        denominator = num_items_in_batch if num_items_in_batch is not None else valid.sum()
        assert int(denominator) > 0 and (after == 0 if zeroed else after == before)
        if audit_path:
            entry = {'key': key, 'identity': is_identity, 'zeroed': zeroed, 'group': member['group'], 'valid_tokens': int(valid.sum()),
                     'weighted_before': before, 'weighted_after': after,
                     'num_items_in_batch': int(denominator),
                     'global_step': int(self.state.global_step)}
            with Path(audit_path).open('a') as f:
                f.write(json.dumps(entry) + '\n')
        return native(self, model, inputs, return_outputs, num_items_in_batch)
    return compute

def install(config_path):
    import importlib.metadata as md
    from swift.trainers.seq2seq_trainer import Seq2SeqTrainer
    path = Path(config_path)
    cfg = json.loads(path.read_text())
    for name, version in cfg['runtime_versions'].items():
        assert md.version(name) == version, name
    assert hashlib.sha256(Path(inspect.getfile(Seq2SeqTrainer)).read_bytes()).hexdigest() == cfg['native_trainer_sha256']
    p = path.with_name('membership.json')
    assert hashlib.sha256(p.read_bytes()).hexdigest() == cfg['membership_sha256']
    assert not getattr(Seq2SeqTrainer.compute_loss, '_t008_identity_zero', False)
    fn = make_compute_loss(Seq2SeqTrainer.compute_loss, json.loads(p.read_text())['members'],
                           os.environ.get('T008_IDENTITY_ZERO_AUDIT'))
    fn._t008_identity_zero = True
    Seq2SeqTrainer.compute_loss = fn

if os.environ.get('T008_IDENTITY_ZERO_CONFIG'):
    install(os.environ['T008_IDENTITY_ZERO_CONFIG'])
