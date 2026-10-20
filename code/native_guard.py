"""Swift external plugin: checks native data only; never changes sampling/filtering."""
import json
import os
import pathlib
import hashlib
import functools
import importlib.metadata
from native_recipe import check_record, dataset_record, validate_native_args

def install():
    from swift.pipelines.train.sft import SwiftSft
    if getattr(SwiftSft._get_dataset,'_native_guard',False):
        return
    def expected(args):
        path=os.environ.get('NATIVE_PREFLIGHT_REPORT')
        checksum=os.environ.get('NATIVE_PREFLIGHT_SHA256')
        if not path or not checksum:
            raise RuntimeError('Native training guard requires approved CPU evidence')
        raw=pathlib.Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=checksum:
            raise RuntimeError('Approved native CPU evidence changed')
        evidence=json.loads(raw)
        for name,version in evidence['versions'].items():
            if importlib.metadata.version(name)!=version:
                raise RuntimeError('Runtime package changed since native CPU evidence')
        spec=evidence['spec']
        if (list(args.model_name)!=[spec['name_zh'],spec['name_en']] or
            list(args.model_author)!=[spec['author_zh'],spec['author_en']]):
            raise RuntimeError('Native identity differs from CPU evidence')
        return evidence
    get_original=SwiftSft._get_dataset
    encode_original=SwiftSft._encode_dataset
    @functools.wraps(get_original)
    def get_checked(self):
        validate_native_args(self.args)
        evidence=expected(self.args)
        check_record(self.args.get_template_kwargs(),evidence['template_kwargs'],'template configuration')
        train,val=get_original(self)
        check_record(dataset_record(train),evidence['native_input'],'loaded dataset')
        if val is not None and len(val):
            raise RuntimeError('Unexpected validation split')
        return train,val
    @functools.wraps(encode_original)
    def encode_checked(self, train, val, pre_process=True):
        validate_native_args(self.args)
        if not pre_process:
            raise RuntimeError('Native default preprocessing cannot be bypassed')
        evidence=expected(self.args)
        result=encode_original(self,train,val,pre_process=pre_process)
        if pre_process:
            check_record(dataset_record(result[0]),evidence['native_retained'],'default filtered dataset')
        return result
    get_checked._native_guard=True
    SwiftSft._get_dataset=get_checked
    SwiftSft._encode_dataset=encode_checked

install()
