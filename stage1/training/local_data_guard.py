"""Fail on frozen-data mismatch or any Swift pre-Trainer deletion. No training launcher."""
from pathlib import Path
from functools import wraps
from collections import Counter
import hashlib,json

def messages_counter(rows):
 return Counter(json.dumps(r['messages'],ensure_ascii=False,sort_keys=True) for r in rows)

def verify_members(expected,before,after):
 target=messages_counter(expected)
 if messages_counter(before)!=target:raise RuntimeError('Local data input members/exposures differ from frozen JSONL')
 if messages_counter(after)!=target:raise RuntimeError('Swift encoded members/exposures changed; refuse Trainer')

def install():
 from swift.pipelines.train.sft import SwiftSft
 original=SwiftSft._encode_dataset
 if getattr(original,'_t008_local_guard',False):return
 @wraps(original)
 def guarded(self,train,val,*args,**kwargs):
  if len(self.args.dataset)!=1:raise RuntimeError('Exactly one frozen local dataset required')
  path=Path(self.args.dataset[0]);manifest=json.loads(path.with_name('manifest.json').read_text())
  if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['files_sha256']['train.jsonl']:raise RuntimeError('Frozen train hash differs')
  expected=[json.loads(x) for x in path.read_text().splitlines()]
  before=list(train);verify_members(expected,before,before)
  result,validation=original(self,train,val,*args,**kwargs)
  if result is None or 'messages' not in result.column_names:raise RuntimeError('No inspectable post-encode membership')
  verify_members(expected,before,list(result))
  return result,validation
 guarded._t008_local_guard=True
 SwiftSft._encode_dataset=guarded
install()
