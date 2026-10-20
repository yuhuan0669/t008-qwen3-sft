import collections,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from native_recipe import digest
from prepare_official import normal_row
old=ROOT.parent/'t008_qwen3_sft_v12_cpu'
rows=[json.loads(x) for x in (ROOT/'evidence/native-proof/native-loaded.jsonl').read_text().splitlines()]
prior=[json.loads(x) for x in (old/'work/original-v1.2/train.jsonl').read_text().splitlines()]
source_map=json.loads((old/'evidence/identity_exposure_mapping.json').read_text())['mapping']
ids={digest(normal_row(prior[x['snapshot_row_zero_based']])):x['source_row_zero_based'] for x in source_map}
positions=collections.defaultdict(list)
for i,row in enumerate(prior):positions[digest(normal_row(row))].append(i)
counts=collections.Counter(digest(normal_row(r)) for r in rows)
previous=collections.Counter(digest(normal_row(r)) for r in prior)
changed=[dict(source_row_zero_based=ids[k],old_exposures=previous[k],native_exposures=counts[k]) for k in ids if previous[k]!=counts[k]]
result={'schema':'t008-native-sampling-comparison-v1','native_load_method':'SftArguments.load_dataset, dataset_shuffle=True; seed/data_seed=42',
 'same_content_universe':set(counts)==set(previous),'same_order':rows==prior,'same_exposure_multiset':counts==previous,
 'identity_unique_rows':len(ids),'identity_native_histogram':dict(collections.Counter(counts[k] for k in ids)),
 'identity_templates_with_changed_exposure_count':len(changed),'changes':sorted(changed,key=lambda x:x['source_row_zero_based']),
 'note':'No custom reweighting; the official native loader consumed its RNG with default source shuffle. Historical snapshots remain unchanged.'}
(ROOT/'evidence/native-sampling-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (ROOT/'evidence/native-proof/source-row-map.jsonl').open('w') as f:
 for i,row in enumerate(rows):
  key=digest(normal_row(row));f.write(json.dumps({'native_row_zero_based':i,'source':'identity' if key in ids else 'mixin',
   'official_identity_source_row_zero_based':ids.get(key),'previous_snapshot_matching_rows_zero_based':positions[key],
   'message_sha256':key},sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='changes'},ensure_ascii=False))
