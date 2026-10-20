#!/usr/bin/env python3
"""Exercise installed Swift final-save callback with synthetic CPU state only.

No TrainingArguments post-init, Trainer, model, dataset, optimizer, checkpoint
write, GPU inspection, or training is invoked. This checks save *decisions*, not
whether real adapter bytes have been saved successfully.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
import pathlib
import sys
import traceback
from types import SimpleNamespace


def file_record(path):
    path = pathlib.Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='New, non-existing JSON result path')
    parser.add_argument('--expected-swift', default='4.4.2')
    parser.add_argument('--expected-transformers', default='5.14.1')
    options = parser.parse_args()
    output = pathlib.Path(options.out)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Process-local isolation; no device is queried or allocated by this script.
    previous_cuda_visibility = os.environ.get('CUDA_VISIBLE_DEVICES')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    report = {
        'schema': 't008-installed-callback-final-save-cpu-v1',
        'verified': False,
        'probe_script': file_record(__file__),
        'cuda_visible_devices_before_process_override': previous_cuda_visibility,
        'cuda_visible_devices_effective': '',
        'args_type': 'types.SimpleNamespace: synthetic callback input fields only',
        'state_and_control': 'actual installed transformers TrainerState/TrainerControl',
        'trainer_created': False,
        'model_loaded': False,
        'dataset_loaded': False,
        'optimizer_created': False,
        'checkpoint_written': False,
        'training_started': False,
        'cases': [],
        'limits': [
            'Synthetic state transitions exercise the actual installed callback and its actual parent implementation.',
            'No actual checkpoint files, model forward pass, optimizer update, epoch completion, or GPU runtime is validated.',
            'The synthetic max_steps=103 is a branch test and does not establish the real dataset optimizer-step count.',
            'Callback args are synthetic fields, not a second validation of the formal SFT argument parser.',
        ],
    }
    exit_code = 0
    try:
        report['versions'] = {name: importlib.metadata.version(name)
                              for name in ('ms-swift', 'transformers', 'torch')}
        if report['versions']['ms-swift'] != options.expected_swift:
            raise RuntimeError('Installed ms-swift differs from expected source version')
        if report['versions']['transformers'] != options.expected_transformers:
            raise RuntimeError('Installed Transformers differs from expected source version')

        from swift.trainers.patcher import DefaultFlowCallbackNew
        from transformers import trainer as trainer_module
        from transformers.trainer_callback import TrainerControl, TrainerState
        from transformers.trainer_utils import IntervalStrategy, SaveStrategy
        import torch

        if torch.cuda.is_initialized():
            raise RuntimeError('CUDA was already initialized in this probe process')
        report['cuda_initialized_before_callback'] = False
        report['installed_sources'] = {
            'swift_callback': file_record(inspect.getfile(DefaultFlowCallbackNew)),
            'transformers_parent_callback': file_record(inspect.getfile(DefaultFlowCallbackNew.__mro__[1])),
            'transformers_trainer': file_record(inspect.getfile(trainer_module)),
        }
        callback_source = inspect.getsource(DefaultFlowCallbackNew)
        report['actual_callback_class_source_sha256'] = hashlib.sha256(callback_source.encode()).hexdigest()
        report['actual_callback_class_source'] = callback_source
        report['registered_default_callbacks'] = [
            f'{cls.__module__}.{cls.__qualname__}' for cls in trainer_module.DEFAULT_CALLBACKS
        ]
        report['swift_final_save_callback_registered'] = DefaultFlowCallbackNew in trainer_module.DEFAULT_CALLBACKS
        if not report['swift_final_save_callback_registered']:
            raise RuntimeError('Installed Swift final-save callback is not registered as a default')

        # Normal steps=50 branch, non-multiple terminal branch, exact-multiple
        # terminal branch, smoke terminal branch, and save/eval disabled guard.
        cases = [
            ('ordinary_25_of_103', 25, 103, 'steps', 50, False),
            ('interval_50_of_103', 50, 103, 'steps', 50, True),
            ('interval_100_of_103', 100, 103, 'steps', 50, True),
            ('ordinary_102_of_103', 102, 103, 'steps', 50, False),
            ('final_103_of_103', 103, 103, 'steps', 50, True),
            ('exact_multiple_final_100', 100, 100, 'steps', 50, True),
            ('smoke_final_3_with_interval_50', 3, 3, 'steps', 50, True),
            ('smoke_final_3_with_interval_3', 3, 3, 'steps', 3, True),
            ('save_disabled_final_103', 103, 103, 'no', 50, False),
        ]
        for label, step, max_steps, strategy, interval, expected_save in cases:
            # Both args.* and state.* intervals are provided for exact parent
            # compatibility, while every scenario explicitly disables eval.
            args = SimpleNamespace(
                logging_first_step=False, logging_strategy=IntervalStrategy.NO,
                logging_steps=5, eval_strategy=IntervalStrategy.NO,
                evaluation_strategy=IntervalStrategy.NO, eval_steps=50,
                eval_delay=0, save_strategy=SaveStrategy(strategy),
                save_steps=interval, max_steps=max_steps, max_epochs=None,
                num_train_epochs=1.0,
            )
            state = TrainerState(global_step=step, max_steps=max_steps,
                                 logging_steps=5, eval_steps=50, save_steps=interval)
            control = TrainerControl()
            observed = DefaultFlowCallbackNew().on_step_end(args, state, control)
            record = {
                'case': label, 'event': 'on_step_end', 'global_step': step,
                'max_steps': max_steps, 'save_strategy': strategy,
                'save_steps': interval, 'eval_strategy': 'no',
                'expected_should_save': expected_save,
                'observed_should_save': bool(observed.should_save),
                'observed_should_evaluate': bool(observed.should_evaluate),
                'observed_should_training_stop': bool(observed.should_training_stop),
                'returned_same_control_object': observed is control,
            }
            record['passed'] = (record['observed_should_save'] == expected_save
                                and not record['observed_should_evaluate']
                                and observed is control)
            report['cases'].append(record)
        report['cuda_initialized_after_callback'] = torch.cuda.is_initialized()
        if report['cuda_initialized_after_callback']:
            raise RuntimeError('Unexpected CUDA initialization during callback checks')
        if not all(case['passed'] for case in report['cases']):
            raise RuntimeError('At least one installed callback decision differs from expectation')
        report['passed_cases'] = sum(case['passed'] for case in report['cases'])
        report['total_cases'] = len(report['cases'])
        report['verified'] = True
    except Exception as error:
        exit_code = 1
        report['error'] = {'type': type(error).__name__, 'message': str(error),
                           'traceback': traceback.format_exc()}
    # The only output side effect is this explicitly requested new evidence JSON.
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'report': str(output), 'verified': report['verified'],
                      'passed_cases': report.get('passed_cases'),
                      'total_cases': len(report['cases'])}, ensure_ascii=False))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
