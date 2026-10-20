import os,json,hashlib,statistics,collections,importlib.metadata as md,inspect
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['NVIDIA_VISIBLE_DEVICES']='void';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
from data_juicer.ops.filter.text_length_filter import TextLengthFilter
from data_juicer.utils.constant import Fields,StatsKeys
root=Path('/tmp/t008-stage1-analysis-20261020');p=root/'analysis-projection.jsonl'
rows=[json.loads(x) for x in p.read_text().splitlines()]
assert len(rows)==2600 and all(r['parent_row_zero_based']==i for i,r in enumerate(rows))
assert {r['parent_sha256'] for r in rows}=={'d85dbe58d9c5fab98bbf6a81cf828147ba1a47d6cce492aef107c7d3dafa604c'}
op=TextLengthFilter(min_len=0);stats=op.compute_stats_batched({'text':[r['text'] for r in rows],Fields.stats:[{} for _ in rows]})
audit=[{'parent_row_zero_based':i,'parent_sha256':r['parent_sha256'],'characters':stats[Fields.stats][i][StatsKeys.text_len],'source':r['source']} for i,r in enumerate(rows)]
(root/'dj-row-statistics.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
lens=sorted(x['characters'] for x in audit);counts=collections.Counter(hashlib.sha256(r['text'].encode()).hexdigest() for r in rows)
report={'tool':'Data-Juicer','version':md.version('py-data-juicer'),'operator':'TextLengthFilter.compute_stats_batched','operator_source_sha256':hashlib.sha256(Path(inspect.getfile(TextLengthFilter)).read_bytes()).hexdigest(),'projection_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':len(rows),'unique_projection_texts':len(counts),'characters':{'min':min(lens),'median':statistics.median(lens),'p95':lens[int(.95*(len(lens)-1))],'max':max(lens)},'note':'Character counts only. Actual token length and supervision measured separately with real Swift. Duplicate counting by Python. No rewriting/filtering/model downloads.','messages_written_back':False,'gpu_used':False}
(root/'dj-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
