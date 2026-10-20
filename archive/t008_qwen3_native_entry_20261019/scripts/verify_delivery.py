"""Offline read-only verification after extracting this delivery ZIP."""
import collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'MANIFEST.json').read_text())
for x in manifest['files']:
 p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],x['path']
sys.path.insert(0,str(ROOT/'code'))
from native_recipe import dataset_record,digest
from prepare_official import normal_row
proof=ROOT/'evidence/native-proof'
r=json.loads((proof/'native-preflight.json').read_text())
raw=[json.loads(x) for x in (proof/'native-loaded.jsonl').read_text().splitlines()]
kept=[json.loads(x) for x in (proof/'native-retained.jsonl').read_text().splitlines()]
audit=[json.loads(x) for x in (proof/'row-audit.jsonl').read_text().splitlines()]
assert dataset_record(raw)==r['native_input'] and dataset_record(kept)==r['native_retained']
assert len(raw)==2600 and len(kept)==1642 and len(audit)==2600
assert [x['native_row_zero_based'] for x in audit]==list(range(2600))
expected=[normal_row(x) for x,a in zip(raw,audit) if a['tokens']<=2048]
assert expected==[normal_row(x) for x in kept]
assert sum(not x['retained'] for x in audit)==958
for key,d in r['implementation_fingerprint'].items():
 if key.startswith('entry/'):assert sha(ROOT/'code'/key.split('/')[1])==d
for x in json.loads((ROOT/'code/DELIVERY_MANIFEST.json').read_text())['files']:
 p=ROOT/'code'/x['path'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
assert json.loads((ROOT/'evidence/final-save-callback.json').read_text())['verified'] is True
assert json.loads((ROOT/'gpu_gate_checklist.json').read_text())['recommendation']=='NO_GO_GPU'
print(json.dumps({'payload_files_verified':len(manifest['files']),'native_input_rows':len(raw),
 'native_retained_rows':len(kept),'exact_ordered_delete_membership':True,'GPU_go':False}))
