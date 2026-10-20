from pathlib import Path
import json,hashlib,collections,random
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';E=ROOT/'evidence'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return [json.loads(x) for x in p.read_text().splitlines()]
def key(r):return json.dumps(r['messages'],ensure_ascii=False,sort_keys=True)
def finalize():
 prepared=load(D/'prepared.jsonl');maps=load(D/'prepared-map.jsonl');audit=load(E/'prepared-encoding.jsonl')
 assert len(prepared)==len(maps)==len(audit)
 parent=Path(__file__).resolve().parents[2]/'archive/t008_qwen3_native_entry_20261019/evidence/native-proof/native-loaded.jsonl'
 parentlines=parent.read_bytes().splitlines(keepends=True)
 groups={}
 for i,m in enumerate(maps):
  if m['source']=='swift/self-cognition':groups.setdefault(m['first_parent_row_zero_based'],[]).append(i)
 rng=random.Random(42);selected={i for ii in groups.values() for i in rng.sample(ii,min(2,len(ii)))}
 retained=[];excluded=[];exposure_removed=[];out=bytearray();sup=collections.Counter();counts=collections.Counter()
 for i,(r,m,a) in enumerate(zip(prepared,maps,audit)):
  assert a['row']==i
  reasons=list(m['structural_reasons'])
  if a.get('tokens',0)>2048:reasons+=['over_2048']
  if not a.get('supervised_tokens',0):reasons+=['empty_supervision']
  if a.get('error'):reasons+=['encoding_error']
  if m['semantic_exclusion']:reasons+=['semantic_exclusion']
  if reasons:
   excluded.append({**m,'reasons':sorted(set(reasons)),'tokens':a.get('tokens'),'content':r});continue
  if m['source']=='swift/self-cognition' and i not in selected:
   exposure_removed.append({**m,'reason':'reduce_repeated_identity_exposure_to_two_per_original_unique_seed42','content':r});continue
  parent_idx=m['parent_row_zero_based'];idx=len(retained)
  if parent_idx is not None and not m['modified']:raw=parentlines[parent_idx]
  else:raw=(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n').encode()
  out.extend(raw);retained.append({**m,'train_row_zero_based':idx,'tokens':a['tokens'],'supervised_tokens':a['supervised_tokens']})
  counts[m['source']]+=1;sup[m['source']]+=a['supervised_tokens']
 (D/'train.jsonl').write_bytes(out)
 for name,items in [('train-map.jsonl',retained),('exclusions.jsonl',excluded),('exposure-reductions.jsonl',exposure_removed)]:
  (D/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in items))
 tr=load(D/'train.jsonl');uniq=collections.Counter();seen=set()
 for r in tr:
  k=key(r)
  if k not in seen:uniq[r['dataset']]+=1;seen.add(k)
 manifest={'schema':'t008-stage1-local-derivative-v1','status':'PREPARED_FOR_USER_REVIEW_NOT_TRAINING_APPROVAL','parent_path':str(parent.relative_to(Path(__file__).resolve().parents[2])),'parent_sha256':sha(parent),'plan':'review-v0.4.1','identity_update':'stage1/IDENTITY_UPDATE.md','candidate_version':'stage1-cpu-v0.1.3','rows':len(tr),'unique_messages':len(seen),'source_exposures':dict(counts),'source_unique_messages':dict(uniq),'source_supervised_tokens':dict(sup),'exclusions_exposures':len(excluded),'identity_exposure_reductions':len(exposure_removed),'identity_repeat_cap':2,'seed':42,'retained_original_order':True,'modified_exposures_retained':sum(m['modified'] for m in retained),'new_exposures_retained':sum(m['parent_row_zero_based'] is None for m in retained),'files_sha256':{n:sha(D/n) for n in ['train.jsonl','train-map.jsonl','exclusions.jsonl','exposure-reductions.jsonl','modifications.jsonl','identity-review.jsonl','additions.jsonl','general-scope-review.jsonl']},'derivation_scripts_sha256':{p.name:sha(p) for p in [(ROOT/'scripts'/n) for n in ('prepare_data.py','finalize_data.py','cpu_encode.py')]},'human_review':'PENDING','gpu_training_authorized':False}
 (D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'rows':len(tr),'unique':len(seen),'counts':dict(counts),'excluded':len(excluded),'repeat_reductions':len(exposure_removed)},ensure_ascii=False))
 return manifest
if __name__=='__main__':finalize()
