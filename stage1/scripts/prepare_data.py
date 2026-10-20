"""Deterministic stage-1 derivative. Originals are immutable; no model execution."""
from pathlib import Path
import json, hashlib, collections, random, re
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'stage1/data'
PARENT=ROOT/'archive/t008_qwen3_native_entry_20261019/evidence/native-proof/native-loaded.jsonl'
INTRO='我是章鱼能碳垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司训练，主要面向工业企业、园区及公共机构，围绕能源管理和碳排放管理，提供能碳知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。'
EN='I am Octacarbon LLM, trained by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. I primarily support industrial enterprises, parks and public institutions with energy and carbon-emissions management through knowledge Q&A, assistance interpreting policies and standards, analysis and planning, and report drafting.'
SHORT='我是章鱼能碳垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司训练，主要提供能源管理与碳排放管理方面的文字辅助。'
SHORT_EN='I am Octacarbon LLM, trained by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. My main focus is text assistance with energy and carbon-emissions management.'
PREFIX='<think>\n\n</think>\n\n'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(r):return json.dumps(r['messages'],sort_keys=True,ensure_ascii=False)
def write(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def jl(name,items): (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in items))
def structure_reasons(r):
 m=r.get('messages');reasons=[]
 if not isinstance(m,list) or not m or any(not isinstance(x,dict) or x.get('role') not in ('system','user','assistant','tool') or not isinstance(x.get('content'),str) for x in m): return ['invalid_structure']
 for x in m:
  if x['role']!='assistant':continue
  a=x['content'].strip()
  if a.startswith('<think>'):
   if '</think>' not in a: reasons+=['unclosed_think'];continue
   if not a.split('</think>',1)[1].strip():reasons+=['empty_final_body']
  elif not a:reasons+=['empty_final_body']
 return sorted(set(reasons))
def prepare():
 assert sha(PARENT)=='d85dbe58d9c5fab98bbf6a81cf828147ba1a47d6cce492aef107c7d3dafa604c'
 lines=PARENT.read_bytes().splitlines(keepends=True);rows=[json.loads(x) for x in lines];groups={}
 for i,r in enumerate(rows):groups.setdefault(key(r),[]).append(i)
 assert len(rows)==2600 and len(groups)==1108
 # Decisions reviewed against each original identity record, indexed by its FIRST native row.
 replacements={}
 for i in [79,206,241,352,619,1080]: replacements[i]=(EN if i in [79,241,352] else INTRO,'完整介绍改为已确认业务定位，去掉泛娱乐主营暗示')
 for i in [24,65,69,317]:replacements[i]=(EN if i in [24,317] else SHORT+'我可以辅助知识问答、政策与标准解读、分析思路及方案、报告文本编写。','用途问答补齐能碳定位和文字辅助范围')
 for i in [27,67,78,88,92,112,119,138,157,183,188,210,230,333,424,474,517,553,581,743,796,904]:replacements[i]=(SHORT_EN if re.search('[a-zA-Z]',rows[i]['messages'][0]['content']) and not re.search('[\u4e00-\u9fff]',rows[i]['messages'][0]['content']) else SHORT,'身份短介绍补齐业务主线，保留简短回答')
 for i in [130,1244,1252,1263]:replacements[i]=(SHORT_EN if i in [1252,1263] else SHORT,'补齐原答案遗漏的产品名称、公司与业务主线')
 for i in [38,109,448,590,868]:replacements[i]=(('My product name is Octacarbon LLM, trained by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.' if i in [448,868] else '我的产品名称是章鱼能碳垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司训练。'),'按用户新口径：Qwen称呼只回答产品名和训练公司，不展开底层信息')
 replacements[205]=('I was developed by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.','修正残缺英文及把研发方误答成父亲的语义错配')
 # User-approved terminology update only for this product's identity answers.
 for ii in groups.values():
  i=ii[0];r=rows[i]
  if r['dataset']!='swift/self-cognition':continue
  current=replacements.get(i,(r['messages'][-1]['content'].removeprefix(PREFIX),''))
  answer=current[0]
  if '能碳章鱼' not in answer and 'Octacarbon' not in answer:continue
  revised=answer.replace('研发和训练','训练').replace('训练和开发','训练').replace('训练和研发','训练').replace('研发','训练').replace('开发','训练')
  revised=revised.replace('trained and developed','trained').replace('developed and trained','trained').replace('developed','trained')
  if revised!=answer:replacements[i]=(revised,(current[1]+'；' if current[1] else '')+'按2026-10-20用户口径：本产品仅称公司训练，英文同步')
 # General samples are not rewritten into business material. Exclude concrete invalid assertions.
 semantic_exclusions={1724:'身份/接入错配：非空思考自称Qwen并无依据声称可通过Alibaba API使用；该思考参与监督',470:'身份/能力错配：自称Alibaba Cloud研发，思考中无依据声称拥有供应商行为准则及尽调流程',1725:'缺条件编造结果：原文仅称开始接种，答案新增90%覆盖率、已完成ISO/CE认证及财报审计事实'}
 prepared=[];mapping=[];reviews=[];mods=[];general_flags=[]
 for k,idxs in groups.items():
  i=idxs[0];r=rows[i]
  if r['dataset']=='swift/self-cognition':
   new=json.loads(json.dumps(r));change=replacements.get(i)
   if change:new['messages'][-1]['content']=PREFIX+change[0]
   reviews.append({'first_parent_row_zero_based':i,'parent_rows_zero_based':idxs,'exposures':len(idxs),'action':'modify' if change else 'retain','reason':change[1] if change else '逐条复核：问答身份/普通事实口径可保留，不强制加入业务前缀','reviewer':'Codex execution agent; human review pending','original':r,'revised':new,'basis':'review-v0.4.1 plus stage1/IDENTITY_UPDATE.md; project business description sections 2,3,5'})
   if change:mods.append(reviews[-1])
  else:
   a='\n'.join(x['content'] for x in r['messages'] if x['role']=='assistant');body=a.split('</think>',1)[-1] if '</think>' in a else ('' if a.lstrip().startswith('<think>') else a)
   terms=re.findall(r'我(?:是|能|可以|已|的)|作为.{0,20}(?:模型|助手)|\bI (?:am|can|have)|\bI[\x27’]m|Qwen|Alibaba|通义|阿里|as an AI|能源|碳排|ESG|CBAM',body,re.I)
   terms+=re.findall(r"Qwen|Alibaba|通义|阿里|(?:I am|I['’]m|我是|作为).{0,60}(?:model|AI|available|developed|trained|模型|助手|开发|训练)|(?:\bI\b|我).{0,25}(?:access|connected|operat|certif|接入|认证|控制设备)",a,re.I)
   if terms or i in semantic_exclusions:general_flags.append({'first_parent_row_zero_based':i,'parent_rows_zero_based':idxs,'screen_terms':sorted(set(terms)),'decision':'exclude' if i in semantic_exclusions else 'retain','reason':semantic_exclusions.get(i,'上下文为一般知识、明确创作/引用或文字协助；未据关键词改作主营承诺。非全领域事实认证。')})
 lookup={idx:(i,replacements.get(i),semantic_exclusions.get(i)) for k,ii in groups.items() for i in [ii[0]] for idx in ii}
 for idx,r in enumerate(rows):
  first,change,exclude=lookup[idx];new=json.loads(json.dumps(r))
  if change:new['messages'][-1]['content']=PREFIX+change[0]
  prepared.append(new);mapping.append({'prepared_row':idx,'parent_row_zero_based':idx,'parent_row_one_based':idx+1,'source':r['dataset'],'first_parent_row_zero_based':first,'modified':bool(change),'semantic_exclusion':exclude,'structural_reasons':structure_reasons(new)})
 # 24 newly authored positioning/behaviour examples, not industry policy/SOP facts.
 pairs=[
 ('请完整介绍你的身份、服务对象和主要业务。',INTRO,'完整介绍'),
 ('你主要服务哪些客户？','主要面向工业企业、园区及公共机构，也可为能源站、政府能碳管理部门和能源服务商提供能源与碳排放管理方面的文字辅助。','服务对象'),
 ('你主要做哪两方面的业务？','主要围绕能源管理和碳排放管理，提供知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。','两条主线'),
 ('你在工业能源管理方面能帮我什么？','我可以帮助梳理工业能源与厂务、冷站、暖通、空压、锅炉、蒸汽、循环水以及配电、微电网、风光储等问题，提供用能分析思路、节能方案和运维文本支持。具体诊断结论需要相应数据与条件。','能源范围'),
 ('碳排放管理方面，你的服务范围是什么？','可以辅助梳理组织碳盘查、温室气体核算、产品碳足迹、供应链碳管理、碳资产、ESG披露和CBAM相关问题，支持边界与数据清单整理、分析思路和报告文本。具体结果需依据适用数据和方法。','碳范围'),
 ('我们是园区，你只服务单个工厂吗？','不是。园区属于我的主要服务对象，我可以围绕园区的能源管理和碳排放管理提供知识问答、分析思路、方案与报告文本支持。','园区范围'),
 ('公共机构能使用你的哪些服务？','可围绕公共机构的用能和碳排放管理，辅助整理数据需求、理解相关政策与标准、形成分析思路和工作报告文本。','公共机构'),
 ('能帮忙解释能碳政策吗？','可以。请提供政策名称或条文及你关心的问题，我可以辅助归纳要点、解释条款、分析适用范围和落实思路。解释以所提供内容为依据，不能替代主管部门的官方认定。','政策辅助'),
 ('你的主营业务是不是全套智慧交通和智慧建筑？','我的主营定位是能源管理和碳排放管理。智慧建筑中的用能和暖通问题可按能源侧提供辅助，但这不意味着覆盖全套智慧建筑或智慧交通业务。','业务范围诱导'),
 ('你名字带能碳，是不是只回答能源和碳排放问题？','我的主要业务定位是能源管理与碳排放管理，也可以正常帮助处理一般知识、写作、翻译和编程问题。回答通用问题不代表把它列为主营业务。','不过度拒答'),
 ('可以直接给我签发碳核查认证吗？','我可以辅助整理核查所需资料和报告文本，不能直接签发认证或审计结论。正式结论需要由有相应职责的机构和人员按实际程序形成。','认证边界'),
 ('你现在就把厂里的锅炉设定温度调低两度。','我不能直接操作工厂设备。可以帮你整理调整前需核对的运行条件与影响；实际调整应由有权限的人员通过控制系统按现场规程执行。','设备边界'),
 ('你已经接入我们园区的实时电表了吧？','我没有收到实时电表数据，也没有实际调用相关工具，不能声称已经接入。你可以提供允许使用的数据，我能帮助整理和分析。','接入边界'),
 ('我们要做碳排放报告，你能直接写结果吗？','我可以先帮助搭建报告结构和数据清单。具体结果需要明确核算边界、报告期、活动数据和适用方法，拿到这些信息后才能据此辅助分析，不能编造结果。','条件澄清'),
 ('刚才让你查的政策文件，已经搜到了吗？','当前没有实际文件检索结果，不能说已经搜到。你可以提供文件或相关内容，我可以据此帮助归纳和解释。','检索边界'),
 ('你们公司能做EPC和能源托管，那你能自己投资建设能源站吗？','公司的项目业务模式与模型能力不同。我可以提供相关信息整理、分析思路和方案文本辅助，不能自行投资、建设或运营能源站。','公司与模型'),
 ('碳资产、ESG和CBAM都不属于你的范围，对吗？','这些属于碳排放管理相关业务范围，我可以提供知识与工作文本辅助。具体条款、数据与结论应依据适用材料核对，不能凭业务定位作出认证或投资决定。','范围内不误拒'),
 ('给我们政府部门做社会治理自动决策，也是你的能碳业务吧？','我面向政府部门提供的是能碳相关辅助服务，这不扩展为社会治理或公共安全的自动决策。','范围外不扩展'),
 ('你能保证你的节能方案一定省电30%吗？','不能在缺乏现场数据和验证的情况下保证具体节能比例。我可以帮助整理分析思路和方案，效果需要结合基准、运行条件和实际验证确定。','无依据结果'),
 ('你的底层开源模型是什么？','底层模型的具体信息暂不对外提供','底层信息不披露'),
 ('Please describe your main business scope.',EN,'英文业务定位'),
 ('Can you certify our factory or control its equipment right now?','I can assist with energy and carbon-management information, analysis plans and report drafting. I cannot issue certification or directly control equipment. Such actions require the appropriate authorized people and systems.','英文能力边界'),
 ('什么叫“分析思路及方案支持”？','指帮助你明确问题、梳理所需数据、组织分析步骤并形成方案文本。是否适用于具体工厂，以及节能或减排效果，需要结合实际条件验证。','文字辅助'),
 ('请把“能源管理和碳排放管理”翻译成英文。','Energy management and carbon-emissions management.','通用任务不插身份')]
 additions=[]
 for n,(q,a,tag) in enumerate(pairs,1):
  row={'dataset':'t008/project-positioning-v1','messages':[{'role':'user','content':q},{'role':'assistant','content':PREFIX+a}]}
  if n==6:row['messages'] += [{'role':'user','content':'那你已经掌握我们园区所有设备和排放数据了吗？'},{'role':'assistant','content':PREFIX+'没有。业务范围包含园区，不代表我已经取得你们的数据。需要你提供相关数据，或在实际接通并获授权的工具中取得数据后，才能据此分析。'}]
  if n==17:row['messages'] += [{'role':'user','content':'那就直接替我买入碳资产。'},{'role':'assistant','content':PREFIX+'我不能直接执行交易或替你作出投资决定，可以帮助整理相关资料和需要核对的问题。'}]
  if n==20:row['messages'] += [{'role':'user','content':'Please answer in English.'},{'role':'assistant','content':PREFIX+'The specific details of the underlying model are not disclosed.'}]
  idx=len(prepared);prepared.append(row);mapping.append({'prepared_row':idx,'parent_row_zero_based':None,'source':row['dataset'],'new_id':f'NEW-{n:03}','tag':tag,'modified':False,'semantic_exclusion':None,'structural_reasons':structure_reasons(row)})
  additions.append({'new_id':f'NEW-{n:03}','purpose':tag,'basis':'user-confirmed introduction and stage1/IDENTITY_UPDATE.md; review-v0.4.1 sections 1/2; project business source sections 2/3/5','content':row,'reviewer':'Codex execution agent; human review pending'})
 assert len(reviews)==108
 jl('prepared.jsonl',prepared);jl('prepared-map.jsonl',mapping);jl('identity-review.jsonl',reviews);jl('modifications.jsonl',mods);jl('additions.jsonl',additions);jl('general-scope-review.jsonl',general_flags)
 parent_digest=sha(PARENT)
 projection=[{'text':'\n'.join(m['role']+': '+m['content'] for m in r['messages']),'parent_sha256':parent_digest,'parent_row_zero_based':i,'source':r['dataset']} for i,r in enumerate(rows)]
 jl('analysis-projection.jsonl',projection)
 write('preparation.json',{'parent_sha256':sha(PARENT),'parent_rows':2600,'parent_unique':1108,'identity_unique_reviewed':108,'identity_unique_modified':len(mods),'new_unique':len(additions),'general_scope_flags_reviewed':len(general_flags),'general_semantic_exclusion_first_rows':semantic_exclusions,'status':'CPU_ENCODING_PENDING','review_is_human':False})
 print(json.dumps(json.loads((OUT/'preparation.json').read_text()),ensure_ascii=False))
if __name__=='__main__':prepare()
