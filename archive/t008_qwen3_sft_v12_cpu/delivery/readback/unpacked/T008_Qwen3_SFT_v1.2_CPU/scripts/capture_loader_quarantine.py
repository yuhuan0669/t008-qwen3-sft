"""Preserve actual official loader output after v1.2 export guard failure.
Diagnostic only. No replacement, filtering, custom sampling or approval.
"""
import sys, pathlib, json, hashlib, re, importlib.metadata
from collections import Counter
sys.path.insert(0, '/work/code')
from prepare_official import SOURCES, normal_row, sha
from swift.dataset import load_dataset
root=pathlib.Path('/work')
spec=json.loads((root/'code/identity-spec.example.json').read_text())
ds,val=load_dataset(list(SOURCES),seed=42,split_dataset_ratio=0,load_from_cache_file=False,
 use_hf=False,model_name=(spec['name_zh'],spec['name_en']),model_author=(spec['author_zh'],spec['author_en']))
assert val is None or len(val)==0
raw=[dict(x) for x in ds];rows=[normal_row(x) for x in raw];assert len(rows)==2600
out=root/'original-quarantined-v1.2';out.mkdir(exist_ok=False)
for name,obj in [('train.jsonl',rows),('raw-loader.jsonl',raw)]:
 (out/name).write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in obj))
(out/'identity_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
counts=Counter(hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for x in rows)
anomalies=[]
for i,row in enumerate(rows):
 txt=json.dumps(row,ensure_ascii=False)
 matches=re.findall(r'\{\{\s*[A-Za-z_][A-Za-z0-9_]*\s*\}\}',txt)
 if matches or 'swift-robot' in txt:anomalies.append({'index':i,'source_segment':'mixin' if i<2000 else 'identity','placeholders':matches,'swift_robot':'swift-robot' in txt})
manifest={'schema':'identity-official-snapshot-v1.2','status':'QUARANTINED_PLACEHOLDER_GUARD_FAILURE',
 'source_specs':list(SOURCES),'official_sampling':'ms-swift loader #N; no custom sampling','seed':42,
 'rows':len(rows),'original_rows':len(rows),'requested_mixin':2000,'requested_identity':600,
 'snapshot_kind':'official_original','unique_message_rows':len(counts),'duplicate_exposures':sum(v-1 for v in counts.values()),
 'repetition_histogram':dict(sorted(Counter(counts.values()).items())),
 'actual_source_revision':'See independently archived ModelScope tree/info/cache hashes; no invented revision',
 'versions':{k:importlib.metadata.version(k) for k in ['ms-swift','datasets','modelscope']},
 'files_sha256':{n:sha(out/n) for n in ['train.jsonl','identity_spec.json','raw-loader.jsonl']},
 'baseline_export_result':'prepare_official.py rejected actual records before export; diagnostic capture preserves them unchanged',
 'unresolved_placeholder_rows':len(anomalies),'approved':False}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(root/'placeholder_anomalies.json').write_text(json.dumps(anomalies,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'rows':len(rows),'unique':len(counts),'anomalies':anomalies},ensure_ascii=False))
