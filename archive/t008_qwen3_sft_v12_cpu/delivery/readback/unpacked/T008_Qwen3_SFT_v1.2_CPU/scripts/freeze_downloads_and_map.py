"""Archive official raw downloads and map native identity templates to exposures."""
import pathlib,hashlib,json,shutil,sys
from collections import Counter
sys.path.insert(0,'/work/code')
from prepare_official import sha,normal_row
from swift.dataset.dataset.llm import SelfCognitionPreprocessor
root=pathlib.Path('/work');out=root/'upstream-raw';out.mkdir(exist_ok=False)
sources=[]
for f in (root/'cache/modelscope/datasets/downloads').iterdir():
 if not f.is_file() or f.stat().st_size not in [17438661,23839]:continue
 name='qwen3_32b_distill_1k.jsonl' if f.stat().st_size==17438661 else 'self_cognition.jsonl'
 shutil.copyfile(f,out/name)
 sources.append({'file':name,'bytes':f.stat().st_size,'sha256':sha(f),
  'rows':sum(1 for x in f.read_text().splitlines() if x.strip()),
  'download_metadata':json.loads(pathlib.Path(str(f)+'.json').read_text())})
(out/'manifest.json').write_text(json.dumps(sources,indent=2)+'\n')
spec=json.loads((root/'original-v1.2/identity_spec.json').read_text())
prep=SelfCognitionPreprocessor(query_suffix=' /no_think',response_prefix='<think>\n\n</think>\n\n')
prep.set_name_author((spec['name_zh'],spec['name_en']),(spec['author_zh'],spec['author_en']))
canonical=lambda x:json.dumps(normal_row(x),ensure_ascii=False,sort_keys=True)
raw=[json.loads(x) for x in (out/'self_cognition.jsonl').read_text().splitlines()]
by_content={canonical(prep.preprocess(dict(row))):i for i,row in enumerate(raw)}
train=[json.loads(x) for x in (root/'original-v1.2/train.jsonl').read_text().splitlines()]
mapping=[]
for i,row in enumerate(train[2000:],2000):
 src=by_content[canonical(row)];mapping.append({'snapshot_row_zero_based':i,'source_row_zero_based':src,
 'source_row_sha256':hashlib.sha256(json.dumps(raw[src],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
 'language':raw[src]['tag'],'message_sha256':hashlib.sha256(canonical(row).encode()).hexdigest()})
counts=Counter(m['source_row_zero_based'] for m in mapping)
(root/'identity_exposure_mapping.json').write_text(json.dumps({'method':'Actual installed SelfCognitionPreprocessor exact-message match, no fuzzy match',
 'exposures':600,'source_rows':len(raw),'observed_unique_source_rows':len(counts),
 'repetition_histogram':dict(sorted(Counter(counts.values()).items())),
 'mapping':mapping},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sources':sources,'identity_histogram':dict(Counter(counts.values()))},ensure_ascii=False))
