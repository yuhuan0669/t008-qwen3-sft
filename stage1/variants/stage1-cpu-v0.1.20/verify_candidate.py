"""Verify review coverage and exact frozen-parent lineage; no model calls."""
from collections import Counter
from pathlib import Path
import json
import math
from assemble import D, R, P, IDENTITY, read, jl, sha, key, collect, apply_decision, save

def main():
    parent, ledger, decisions, progress = collect(require_complete=True)
    for path, h in read(D/'source-bindings.json').items():
        assert sha(R/path) == h, path
    rows, maps = jl(D/'train.jsonl'), jl(D/'train-map.jsonl')
    changes, quarantine = jl(D/'changes.jsonl'), jl(D/'quarantine.jsonl')
    raw, oldraw = [(p/'train.jsonl').read_bytes().splitlines(keepends=True) for p in [D,P]]
    stats, cfg = read(D/'statistics.json'), read(D/'training-config.json')
    assert len(rows) == len(maps) == stats['after']['rows'] == cfg['dataset_rows']
    assert len(parent) == len(rows) + len(quarantine) == 1325
    assert Counter(x['sample_id'] for x in quarantine) == Counter({sid:ledger[sid]['exposures'] for sid,d in decisions.items() if d['action']=='quarantine'})
    assert len(changes) == stats['repaired_exposures'] + stats['quarantined_exposures']
    excluded = {x['parent_line_one_based'] for x in quarantine}
    assert [x['parent_line_one_based'] for x in maps] == [i for i in range(1,1326) if i not in excluded]
    changed = {x['parent_line_one_based']:x for x in changes}
    unchanged = 0
    for i, (row, m) in enumerate(zip(rows,maps)):
        pi=m['parent_line_one_based']-1
        assert m['row_zero_based']==i and m['line_one_based']==m['candidate_line_one_based']==i+1
        assert m['messages_sha256']==key(row['messages']) and m['parent_messages_sha256']==key(parent[pi]['messages'])
        assert row['dataset']==parent[pi]['dataset'] and row['messages'][0]==parent[pi]['messages'][0]
        assert not any(x['role']=='system' for x in row['messages'])
        if m['operation']=='preserve':
            assert raw[i]==oldraw[pi]
            unchanged += 1
        else:
            assert m['operation']=='repair' and changed[pi+1]['after']==row
            assert row==apply_decision(parent[pi],decisions[m['sample_audit_id']])
    assert unchanged==stats['untouched_rows']
    for x in quarantine:
        assert x['record']==parent[x['parent_line_one_based']-1]
    assert [x for x in rows if x['dataset']!='swift/Qwen3-SFT-Mixin']==[x for x in parent if x['dataset']!='swift/Qwen3-SFT-Mixin']
    assert sum(x['dataset'] in IDENTITY for x in rows)==234
    assert sum(x['dataset']!='swift/Qwen3-SFT-Mixin' for x in rows)==295
    for n in ['identity-keys.json','identity_loss3.py','native-identity-key-aliases.json']:
        assert sha(D/n)==sha(P/n),n
    prior=read(P/'training-config.json')
    assert [x.replace(D.name,P.name) for x in cfg['full_argv']]==prior['full_argv']
    assert not cfg['execution_authorized'] and cfg['estimated_full_optimizer_steps']==math.ceil(len(rows)/16)
    assert cfg['dataset_sha256']==sha(D/'train.jsonl')
    e=read(D/'evaluation-config.json')
    assert sha(D/'inference-system.txt')==e['inference_system_sha256']
    assert sha(R/e['protocol_reference'])==e['protocol_sha256']
    assert sha(R/e['chat_template']['path'])==e['chat_template']['sha256']
    fresh=sum(x['completed'] for x in progress.values())
    assert fresh==332 and len(decisions)==518
    assert Counter(x['prior_status'] for x in decisions.values())==Counter({'confirmed_issue':142,'needs_verification':203,'style_observation':14,'no_obvious_issue':159})
    result={'verified':True,'dataset_sha256':sha(D/'train.jsonl'),'parent_dataset_sha256':sha(P/'train.jsonl'),
            'parent_rows':1325,'rows':len(rows),'repaired_exposures':stats['repaired_exposures'],
            'quarantined_exposures':len(quarantine),'untouched_raw_rows':unchanged,
            'unique_general_records_with_disposition':518,'new_full_reads':332,
            'prior_review_inherited_records':186,'all_142_issues_and_203_pending_disposed':True,
            'all_non_general_rows_unchanged':295,'all_identity_exposures_unchanged':234,
            'training_system_rows':0,'training_thinking_format_preserved':True,
            'recipe_unchanged_vs_v14':True,'estimated_steps':cfg['estimated_full_optimizer_steps'],
            'training_started':False,'inference_executed':False,'uat_paused':False,'cpu_verified':False}
    path=D/'cpu-check/report.json'
    if path.exists():
        cpu=read(path);assert cpu['verified'] and cpu['dataset_sha256']==sha(D/'train.jsonl')
        assert cpu['actual_loader_rows']==cpu['actual_pipeline_rows']==cpu['rows']==len(rows)
        assert cpu['unchanged_full_encoding_rows']==unchanged
        assert not any(cpu[k] for k in ['overlength_rows','truncated_rows','silent_dropped_rows','empty_supervision_rows','training_started','inference_executed','model_weights_loaded','gpu_available'])
        uat=read(D/'cpu-check/uat-verification.json')
        assert uat=={'spec_unchanged':True,'healthy':True,'cpu_pod_deleted':True,'uat_pause':False,'gpu_requested':False}
        result.update(cpu_verified=True,cpu_report_sha256=sha(path),uat_unchanged_healthy=True)
    save('verification.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
