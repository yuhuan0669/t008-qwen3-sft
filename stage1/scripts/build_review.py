from pathlib import Path
import json,html,collections,csv,hashlib,math
R=Path(__file__).resolve().parents[1];D=R/'data';O=R/'review';O.mkdir(exist_ok=True)
def read(n):return [json.loads(x) for x in (D/n).read_text().splitlines()]
def esc(s):return html.escape(str(s))
def messages(r):return '\n\n'.join(m['role']+': '+m['content'] for m in r['messages'])
m=json.loads((D/'manifest.json').read_text());changes=read('modifications.jsonl');adds=read('additions.jsonl');ex=read('exclusions.jsonl');reductions=read('exposure-reductions.jsonl');tm=read('train-map.jsonl')
flags=read('general-scope-review.jsonl');src=m['source_exposures'];sup=m['source_supervised_tokens']
kept=collections.Counter(x.get('first_parent_row_zero_based') for x in tm)
reasons=collections.Counter(reason for x in ex for reason in x['reasons']);unique_ex={json.dumps(x['content']['messages'],ensure_ascii=False,sort_keys=True) for x in ex}
summary={'parent_exposures':2600,'parent_unique':1108,'excluded_exposures':len(ex),'excluded_unique':len(unique_ex),'exclusion_reasons_overlapping':dict(reasons),'reduced_identity_repetitions':len(reductions),'reviewed_identity_original_unique':108,'modified_identity_original_unique':len(changes),'modified_identity_original_exposures':sum(x['exposures'] for x in changes),'modified_identity_exposures_retained':m['modified_exposures_retained'],'identity_original_records_retained':108,'identity_unique_after_rewrite':m['source_unique_messages']['swift/self-cognition'],'new_unique':len(adds),'train_exposures':m['rows'],'train_unique':m['unique_messages'],'source_exposures':m['source_exposures'],'source_supervised_tokens':m['source_supervised_tokens'],'identity_plus_business_exposure_pct':round((src['swift/self-cognition']+src['t008/project-positioning-v1'])/m['rows']*100,2),'identity_plus_business_supervised_token_pct':round((sup['swift/self-cognition']+sup['t008/project-positioning-v1'])/sum(sup.values())*100,3),'record_scope':f"108 identity records fully reviewed; 1000 general records rule-screened across all assistant text, including thinking, and {len(flags)} flagged contexts reviewed for self-positioning, execution claims and business scope; not a full factual audit",'human_approval':'PENDING','training_started':False}
(O/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (O/'修改对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['原文件','原行号(从1起)','原曝光次数','最终保留次数','原问答','修改后问答','原因','依据'])
 for x in changes:w.writerow([m['parent_path'],','.join(str(i+1) for i in x['parent_rows_zero_based']),x['exposures'],kept[x['first_parent_row_zero_based']],messages(x['original']),messages(x['revised']),x['reason'],x['basis']])
with (O/'全部原始行处理.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['原行号(从1起)','处理','原因','最终训练行号(从1起)'])
 allrows={}
 for x in tm:
  if x['parent_row_zero_based'] is not None:allrows[x['parent_row_zero_based']]=['修改后保留' if x['modified'] else '原样保留','',x['train_row_zero_based']+1]
 for x in ex:allrows[x['parent_row_zero_based']]=['排除',';'.join(x['reasons'])+' '+str(x.get('semantic_exclusion') or ''),'']
 for x in reductions:allrows[x['parent_row_zero_based']]=['减少重复曝光',x['reason'],'']
 for i in range(2600):w.writerow([i+1,*allrows[i]])
header='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>T-008 第一阶段数据审阅</title><style>body{font:16px/1.7 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#17212b}h1,h2{line-height:1.3}a{color:#155d91}table{width:100%;border-collapse:collapse}th,td{border:1px solid #d7dce0;padding:10px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui}details{border:1px solid #d7dce0;border-radius:6px;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:600}.note{background:#f0f5f7;padding:14px}small{color:#53606d}</style>'''
body=[header,'<h1>T-008 第一阶段：数据修改审阅</h1><p>当前本地版本stage1-cpu-v0.1.3，仅补强底层问法，其他数据及安排不变；<a href="../UNDERLYING_SUPPLEMENT.md">本次补充</a>；沿用2026-10-20身份修订；详见<a href="../IDENTITY_UPDATE.md">修订说明</a>。数据已完成CPU检查，待负责人审阅；没有训练或模型推理。</p>', f'<p><a href="#changes">{len(changes)}种修改对照</a> · <a href="#new">{len(adds)}种新增</a> · <a href="exclusions.html">完整排除明细</a> · <a href="修改对照.csv">下载修改CSV</a> · <a href="全部原始行处理.csv">2600行去向</a></p>', '<h2>数据变化</h2><table><tr><th>步骤</th><th>曝光次数</th><th>说明</th></tr>']
for label,num,note in [('原父快照',2600,'1108种独立记录'),('排除',len(ex),f"{reasons['over_2048']}次超长，{reasons['unclosed_think']}次未闭合think（有重叠）；{reasons['semantic_exclusion']}次语义问题"),('减少身份重复曝光',384,'108种原身份记录各保留2次，固定seed42选择并保持原序；不是删除这些问法'),('新增业务定位与边界',src['t008/project-positioning-v1'],f"{len(adds)}种记录；NEW-020及NEW-025～030各2次，其余各1次；其中{sum(sum(m['role']=='assistant' for m in x['content']['messages'])>1 for x in adds)}条为多轮"),('最终候选',m['rows'],f"通用{src['swift/Qwen3-SFT-Mixin']}＋原身份{src['swift/self-cognition']}＋新增{src['t008/project-positioning-v1']}；{m['unique_messages']}种最终独立messages")]:body.append(f'<tr><td>{label}</td><td>{num}</td><td>{note}</td></tr>')
body+=['</table>',f'<p class="note">{len(changes)}种身份记录修改前共有{summary["modified_identity_original_exposures"]}次曝光，最终保留{summary["modified_identity_exposures_retained"]}次。108种原身份记录全部保留问法，修订后部分记录内容相同，最终原身份为{summary["identity_unique_after_rewrite"]}种独立messages。身份及业务样本占曝光{summary["identity_plus_business_exposure_pct"]}%，占监督token约{summary["identity_plus_business_supervised_token_pct"]}%；两种比例不能混用，效果需后续开发评测确认。</p>', f'<p>全部108种身份记录已逐条复核。通用语料做结构及业务相关规则筛查，并复核{len(flags)}种命中记录（包括非空思考内容）；本次不声称已审核全部通用知识的事实正确性。审核者为执行Agent，负责人签收仍待进行。</p>', '<h2 id="changes">修改前后对照</h2><p>行号显示从1起；机器映射同时保留从0起的行号。问答正文完整展示。</p>']
for n,x in enumerate(changes,1):
 body.append(f'<details><summary>{n:02} · 原第{x["first_parent_row_zero_based"]+1}行 · {esc(x["reason"])}</summary><p>全部原行号：{esc(", ".join(str(i+1) for i in x["parent_rows_zero_based"]))}；原曝光{x["exposures"]}次，最终保留{kept[x["first_parent_row_zero_based"]]}次。</p><table><tr><th>原问答</th><th>修改后问答</th></tr><tr><td><pre>{esc(messages(x["original"]))}</pre></td><td><pre>{esc(messages(x["revised"]))}</pre></td></tr></table><p>依据：{esc(x["basis"])}</p></details>')
body.append('<h2 id="new">新增样本</h2>')
for x in adds:body.append(f'<details><summary>{x["new_id"]} · {esc(x["purpose"])}</summary><p>曝光次数：{x.get("exposures",1)}</p><pre>{esc(messages(x["content"]))}</pre><p>依据：{esc(x["basis"])}</p></details>')
body.append('<p><a href="../data/identity-review.jsonl">全部108种身份审核记录</a> · <a href="../data/train.jsonl">最终训练文件</a> · <a href="../data/manifest.json">版本与校验清单</a></p></html>')
(O/'index.html').write_text('\n'.join(body))
groups={}
for x in ex:groups.setdefault(json.dumps(x['content'],ensure_ascii=False,sort_keys=True),[]).append(x)
b=[header,f'<h1>排除明细</h1><p>按相同原记录合并展示，列出每次曝光行号。排除原因可以重叠，{len(ex)}次曝光只计一次。</p><a href="index.html">返回修改审阅</a>']
for n,(k,xx) in enumerate(groups.items(),1):
 x=xx[0];b.append(f'<details><summary>{n:03} · 原第{x["parent_row_one_based"]}行 · {esc(" / ".join(x["reasons"]))}</summary><p>原行号：{esc(", ".join(str(t["parent_row_one_based"]) for t in xx))}；编码长度：{x["tokens"]}。{esc(x.get("semantic_exclusion") or "")}</p><pre>{esc(messages(x["content"]))}</pre></details>')
b.append('</html>');(O/'exclusions.html').write_text('\n'.join(b));print(json.dumps(summary,ensure_ascii=False))
