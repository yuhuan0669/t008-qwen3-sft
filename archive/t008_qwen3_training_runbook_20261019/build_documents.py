"""Build evidence-grounded runbook and diagnosis; never starts training."""
import datetime,hashlib,json,pathlib,shlex,shutil
ROOT=pathlib.Path(__file__).resolve().parent
GPU=ROOT.parent/'t008_qwen3_gpu_sft_20261019'
CPU=ROOT.parent/'t008_qwen3_native_entry_20261019'
load=lambda p:json.loads(p.read_text())
full=load(GPU/'evidence/full-run_manifest.json');smoke=load(GPU/'evidence/smoke-run_manifest.json')
native=load(CPU/'evidence/native-proof/native-preflight.json')
terminal=load(GPU/'evidence/full-terminal-state.json')['pipeline_terminal']
logs=[json.loads(x) for x in (GPU/'outputs/outputs/full/checkpoints/v0-20261019-025405/logging.jsonl').read_text().splitlines()]
final=next(x for x in logs if 'train_runtime' in x)
blocks=[]
def add(kind,text):blocks.append({'kind':kind,'text':text.strip()+'\n'})
def h(text):add('h1',text)
def p(text):add('body',text)
def code(text):add('code',text)
def format_command(argv):
 groups=[]
 for x in argv:
  if x.startswith('--'):groups.append([x])
  elif groups:groups[-1].append(x)
  else:groups.append([x])
 separator=' '+chr(92)+'\n  '
 return 'CUDA_VISIBLE_DEVICES=0'+separator+separator.join(' '.join(shlex.quote(x) for x in g) for g in groups)
links={
 '执行结果':'https://drive.google.com/file/d/1p-awqvTM89aQ1Y89YHIiq2kbWNRrQDou/view',
 '追加执行记录':'https://drive.google.com/file/d/18YQ5hwOVZxWw2D8f-f-i10AmLfRb5MsU/view',
 'GPU证据包':'https://drive.google.com/file/d/1LJ7fwnAhQ0TlUe_2GWj_4tTUoJpHB1nh/view',
 '候选LoRA ZIP':'https://drive.google.com/file/d/1Be0WI7PKbQmcfcKj-YIyQRGikGf_ulaB/view',
 'CPU原始快照/来源审核包':'https://drive.google.com/file/d/1C4Psio7qgU27bFobd92i4oXmDa0JQqG4/view',
 '正式原生入口CPU包':'https://drive.google.com/file/d/1V-oysRsNKQwXKSWuqvWpjZlBUMr8HmrI/view',
 'GPU交付校验回执':'https://drive.google.com/file/d/1FaLcYhk5PQmArHhWINcYvGYfhbEscYIg/view'}
add('title','Qwen3-8B 自我认知 SFT 全流程与实际命令')
p('T-008｜v1.2｜执行日期2026-10-19｜运行号 t008-qwen3-20261019-094113\n本文是已执行过程的复盘与复算手册。下列训练、服务切换及发布路径命令用于说明历史操作，不构成现在重新运行的授权。历史CPU包中的No-Go属于当时阶段状态；随后已有用户授权并实际完成GPU SFT。')
h('1. 本次结果与执行边界')
p('3步GPU Smoke通过；正式LoRA完成103/103步、1 epoch，checkpoint-103与Swift终态一致。随后先恢复原vLLM，再按用户“现在加载，因为要测试”加载独立LoRA测试入口 octacarbon-llm-sft-test，保留 octa-carbon-v1。已修复Open WebUI的auto工具调用参数错误。当前是测试服务，未合并权重、未完成独立A/B/C/D验收、未正式生产发布。')
p('真实授权顺序：CPU准备且不启GPU → 官方原生加载、默认2048过滤 → 用户“开始GPU sft吧” → 用户“授权本次暂停、训练并恢复” → 3步Smoke及一轮Full → 恢复原服务 → 用户“现在加载，因为要测试” → LoRA测试加载。英文名称及公司英文名由用户确认可用于开发及商业用途；公司是定制主体，Qwen3-8B是基座。')
h('2. 基线、代码、镜像与依赖')
p('实施方案：https://drive.google.com/file/d/17kVO_pWDZJIvX5N0vU-yImJyPTXvlBrA/view\n原始v1.2执行附件：https://drive.google.com/file/d/1sGwZoIbvrny6y1zSXTQrnqz5vRioNaC_/view\n任务单：https://docs.google.com/document/d/1BQLRq1pQyu7Be60_hxmeVsaFDBIMuul2-EB3aDAe_Ho/edit\n评审记录：https://docs.google.com/document/d/1xhUjGTfRnqQ8eSQKLEUihSScmdIoJPPSLrXoJ1_-7HM/edit')
p('实际代码提交：'+full['source_git_commit']+'\n实际镜像digest：'+full['image_digest']+'\n镜像仓库：modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope\n实际安装版本：'+', '.join(k+'='+v for k,v in native['versions'].items())+'；ClearML SDK=1.17.0；服务vLLM=0.25.1。镜像tag中的Swift4.4.3/ModelScope1.39.0不等于实装版本。')
code('''python3 - <<'PY'
import importlib.metadata as m
for name in ('ms-swift','transformers','peft','torch','tokenizers','datasets','modelscope','clearml'):
    print(name, m.version(name))
PY
python3 -c 'from swift.pipelines import sft_main; sft_main(["--help"])'
python3 - <<'PY'
from pathlib import Path
for path in Path('/input/code').rglob('*.py'):
    compile(path.read_bytes(), str(path), 'exec')
print('Python syntax OK')
PY
bash -n /input/code/train_identity.sh
python3 -W error::ResourceWarning -m unittest discover -s /input/code/tests -v''')
p('上述是对应镜像内的复算写法，路径规范化，Python语法检查不写只读代码目录；本轮整理文档没有重复执行这些历史测试。既有结果为正式入口本机及镜像32/32测试通过，保存回调9/9 CPU场景通过。Swift外层swift sft --help可能只返回外层帮助，故通过sft_main获取真实SFT CLI。当前实装采用--tuner_type lora和--eval_strategy no。')
h('3. 官方数据、许可、身份与不可变快照')
p('正式源：swift/Qwen3-SFT-Mixin#2000 与 swift/self-cognition:qwen3#600。使用ms-swift原生加载及原生#N采样；没有把本地1642条衍生JSONL作为训练输入。Mixin原始库1000条；身份库108条。#2000和#600是曝光次数，不是不同问题条数。身份108种模板重复5或6次，共600次曝光。')
p('来源的Apache-2.0声明、README、源文件及内容版本证据在CPU包。Mixin固定内容revision=e587cae71fc7084ab93dccbc37d0056df3569543；身份=d2a385942cb0d47e3fb3cdb9d98adb8b8c01dcfc。实际SDK元数据为master、etag=null，不冒称原生CLI锁了远端commit；依靠归档内容SHA及运行guard检测漂移。\nMixin源文件SHA：d261353c05df1f1fde95639d1a9d9243e1d24470dcb4c3732965ab1ab8eeba41\n身份源文件SHA：e7b66784f02361cfa0ad4635dae12c0f810d197c22ac89a4b7837195dc4b7b23')
code(json.dumps(native['spec'],ensure_ascii=False,indent=2))
p('早期不可变原始快照生成方式如下；它用于审计，不是最终训练文件路径。最终原生SftArguments启用默认shuffle=True，顺序和部分模板5/6次曝光分配与早期快照不同，因此两者摘要不混用。')
code('''python3 /input/code/prepare_official.py \\
  --spec /input/code/identity-spec.confirmed.json \\
  --out /work/new-official-original-snapshot \\
  --seed 42
sha256sum /work/new-official-original-snapshot/train.jsonl
sha256sum /work/new-official-original-snapshot/manifest.json''')
h('4. CPU正式参数、Tokenizer、模板与默认过滤')
p('在隔离CPU容器中隐藏CUDA/NVIDIA设备，基座只读挂载/base。CPU路径不实例化SwiftSft或Trainer，不加载GPU权重；完整读取模型文件只用于哈希。真实Qwen3 Tokenizer及实际Swift模板计算完整长度，包含system（如有）、user、assistant、角色/结束标记以及模板思考前缀。loss_scale=default+ignore_empty_think；system/user被mask，assistant有效token被监督。')
code('''CUDA_VISIBLE_DEVICES= NVIDIA_VISIBLE_DEVICES=void \\
bash /input/code/train_identity.sh cpu-check \\
  --model /base \\
  --identity-spec /input/code/identity-spec.confirmed.json \\
  --evidence-dir /work/NEW-native-proof \\
  --reference-snapshot /reference/original-v1.2/train.jsonl \\
  --base-files /reference/evidence/template/original-final/base-files.json''')
p('此处是与历史CPU步骤等价的容器路径写法。原始实际CPU启动脚本及命令原样收录在正式原生入口CPU包 scripts/run_cpu_container.sh：工作目录/tmp/t008-native-entry-cpu-20261019、旧基座kubelet挂载路径含当时Pod UID，已随Pod变化，不能直接照抄。脚本原样作为本次附件留存。')
p('真实CPU结果：2600加载曝光 → 默认delete删除958 → 保留1642。Mixin为2000→1042（521条不同记录），身份600→600（108条不同记录）；总共629条不同记录。默认delete删除整条超长记录，不截断为2048片段。身份曝光比例为600/1642=36.54%，这是本轮官方采样与默认过滤的结果，不是另加的人工配比。')
p('原生输入canonical SHA：'+full['native_input']['sha256']+'\n原生保留canonical SHA（含lengths等全部列）：'+full['native_retained']['sha256']+'\nCPU报告文件SHA：'+full['preflight_report_sha256']+'\n基座16个文件共16,397,461,896字节；聚合SHA：'+full['base_files_sha256']+'\ncanonical摘要与JSONL文件字节SHA不同，算法见native_recipe.digest。训练native_guard将实际对象与CPU证据对比，不修改/清洗数据。')
h('5. 最终K8s运行单元和运行支持')
p('context=lmas00-direct；训练namespace=swift；单卡节点=k8s-worker05，RTX4090 24,564MiB；服务namespace=vllm，Deployment=vllm。训练SA=swift-trainer、UID10001、非root、禁止提权、capabilities drop ALL、不挂载SA token。没有改RBAC、Admission Policy或既有目录权限。')
p('swift-base PVC的Qwen3-8B子目录只读挂载/base；swift-train-data PVC的t008-qwen3-20261019-094113子目录只读挂载/input；swift-work PVC同名子目录可写挂载/runwork。仅Smoke/Full各申请1 GPU，requests CPU4/内存16Gi，limits CPU8/内存32Gi；/dev/shm=8Gi。Job backoffLimit=0，不自动重复训练。')
p('镜像原件缺ClearML SDK，使用固定1.17.0 overlay；非root缺ModelScope AST预建索引，独立CPU生成并只读挂载；缓存/配置目录指向本轮可写目录。HTTPS使用系统可信根+项目CA bundle，始终启用TLS验证。完整Job JSON与588个runtime input文件哈希在GPU证据包。')
job=load(GPU/'evidence/job-full.json');env=job['spec']['template']['spec']['containers'][0]['env']
required={'PYTHONPATH','BASE_MODEL','IDENTITY_SPEC','NATIVE_PREFLIGHT_REPORT','APPROVAL_FILE','TRAIN_IMAGE_DIGEST','SOURCE_GIT_COMMIT','RUN_AUTHORIZED','GPU_WINDOW_APPROVED','USE_QLORA','USE_LIGER','CLEARML_API_HOST','CLEARML_WEB_HOST','CLEARML_FILES_HOST','REQUESTS_CA_BUNDLE','SSL_CERT_FILE','OUT_DIR','CUDA_VISIBLE_DEVICES'}
code('\n'.join('export '+e['name']+'='+shlex.quote(e['value']) for e in env if e['name'] in required and 'value' in e))
p('ClearML访问凭据仅由既有Secret swift-clearml的access_key/secret_key通过env.valueFrom.secretKeyRef注入；文档和包不包含密钥值。RUN_AUTHORIZED/GPU_WINDOW_APPROVED变量不是独立批准依据，真实会话批准、精确数据/代码/镜像绑定的approval.json才是本次历史证据；不得复制这些标志冒充下一轮授权。')
h('6. 共享GPU暂停、3步Smoke、一轮Full及恢复')
p('先完成CPU最终PVC/SDK/参数预检，再对Smoke/Full进行server dry-run。监督脚本保存原vLLM副本和spec，确认UID未变且没有冲突HPA，停止vLLM并等待旧Pod退出；gpu_stage在每阶段确认GPU无其他计算进程。仅Smoke通过才提交Full，try/finally负责成功或失败均清理本次Job并恢复原服务。下面是历史监督顺序，不应再手动执行一遍。')
code('''kubectl --context lmas00-direct -n swift create --dry-run=server -f evidence/job-smoke.json
kubectl --context lmas00-direct -n swift create --dry-run=server -f evidence/job-full.json
python3 scripts/session_supervisor.py
# 监督器内部的主要动作（已执行，勿再次重复）：
# kubectl --context lmas00-direct -n vllm scale deployment/vllm --current-replicas=1 --replicas=0
# kubectl --context lmas00-direct create -f evidence/job-smoke.json
# 核验3/3实际optimizer steps及完整checkpoint-3
# kubectl --context lmas00-direct create -f evidence/job-full.json
# 核验103/103、epoch1及最终checkpoint-103
# kubectl --context lmas00-direct -n swift delete job <本次smoke/full> --wait=false
# kubectl --context lmas00-direct -n vllm scale deployment/vllm --replicas=1''')
p('容器实际调用链：python3 /input/gpu_stage.py smoke|full → bash /input/code/train_identity.sh smoke|full → python3 run_identity.py → 下列真实Swift argv。GPU stage记录10秒采样遥测；wrapper负责Task、精确输入guard、终态核验及候选模型上传回读。')
h('7. 正式SFT真实完整命令')
code(format_command(full['command']))
p('Smoke命令与上述一致，仅output_dir改为/runwork/outputs/smoke/checkpoints、save_steps=3，并追加--max_steps 3。实际完整argv另存 actual-smoke-command.sh。LoRA dropout采用实装默认0.05。没有启用QLoRA/Liger；没有额外数据清洗或2560调整。split_dataset_ratio=0、eval_strategy=no，所以eval_steps=50不触发训练内评估。gradient_checkpointing=true是降低训练显存的配置。')
h('8. 真实训练结果、产物与ClearML')
p(f'Smoke=3/3；Full=103/103、epoch1；正式Trainer runtime={final["train_runtime"]}秒（14分31秒），train_loss={final["train_loss"]}，train token_acc={final["token_acc"]}。可训练参数21.8235M，占8,212.5588M总参数的0.2657%。训练集指标不代表独立业务能力或身份稳定性通过。\n正式样本长度：'+terminal['train_dataset']+'\n10秒采样观测显存峰值：Smoke23084MiB，Full22034MiB；Trainer另报max memory22.16GiB，计量口径不同。')
p('最终checkpoint：'+full['checkpoint']+'\n保留checkpoint-100与103；checkpoint-50因save_total_limit2被清理。实际Swift回调在最后非50整数步也保存最终checkpoint。终态logging.jsonl、trainer_state、wrapper退出0、adapter张量有限性相互校验。')
p('ClearML Full Task='+full['clearml_task_id']+'\nClearML OutputModel='+full['clearml_output_model_id']+'\nhttps://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/'+full['clearml_task_id']+'/output/log\nAdapter ZIP=80,736,700字节；SHA-256='+full['adapter_package_sha256']+'。通过OutputModel上传后Model.force_download回读，随后Drive原文件全字节回读也一致。模型未通过SDK正式发布。')
p('ClearML进度：训练运行后按用户要求增加只读日志observer，向现有同一个Task补传step/loss等标量和进度，最终103/103、100%；未重启训练或新建第二个正式Task。原始checkpoint与优化器仍保存在swift-work PVC的t008-qwen3-20261019-094113/outputs，63文件清单见persisted-output-manifest.json。Drive不重复保存16GB基座和全部优化器状态。')
h('9. 原服务恢复及后续LoRA测试加载')
p('训练后于10:12:20 UTC恢复原服务，1/1 Ready、HTTPS health200、TLS验证通过，原spec SHA=9c75f393377a3e5cb6617e6b44a38241e33785f30593a061b7e7825a8c391b10。之后用户另行要求测试加载：将已核验Adapter新建只读测试目录，原子迁入released/t008-qwen3-20261019-094113-test/adapter；目录清单明确TEST_SERVING_ONLY_NOT_QUALITY_ACCEPTED，没有覆盖基座。')
p('测试启动命令如下，反映当前配置。/models挂原基座；/adapters/octacarbon-llm-sft-test挂只读LoRA。LoRA注册不是merge，原模型ID继续可用。')
code('''python3 -m vllm.entrypoints.openai.api_server \\
  --model /models \\
  --served-model-name octa-carbon-v1 \\
  --host 0.0.0.0 --port 8000 \\
  --gpu-memory-utilization 0.90 \\
  --max-model-len 8192 \\
  --trust-remote-code \\
  --reasoning-parser qwen3 \\
  --enable-lora --max-lora-rank 8 \\
  --lora-modules '{"name":"octacarbon-llm-sft-test","path":"/adapters/octacarbon-llm-sft-test","base_model_name":"octa-carbon-v1"}' \\
  --enable-auto-tool-choice --tool-call-parser hermes''')
p('单GPU测试加载采用scale0→等待退出→带UID/原模板test的JSON patch→scale1→Ready/HTTPS health检查；异常自动回滚原模板。后续修复WebUI auto参数时，独立保存修复前的base+LoRA模板，失败回滚到该状态，避免丢掉已授权测试入口。完整脚本分别为test_serving/scripts/load_for_test.py、fix_auto_tool_choice.py。')
code('''curl --fail --silent --show-error \\
  https://vllm.10.140.17.125.nip.io/health
curl --fail --silent --show-error \\
  https://vllm.10.140.17.125.nip.io/v1/models
curl --fail-with-body --silent --show-error \\
  -H 'Content-Type: application/json' \\
  --data-binary @test_serving/evidence/auto-tool-single-request.json \\
  https://vllm.10.140.17.125.nip.io/v1/chat/completions''')
p('模型列表包含octa-carbon-v1和octacarbon-llm-sft-test；首次身份连通请求返回正确中文名称。WebUI实际报auto tool choice错误后，按实际Qwen3工具模板和已安装Hermes解析器补CLI参数，仅一次含tools+tool_choice:auto请求返回HTTP200。没有以此宣称工具能力全面通过。')
h('10. 故障、最小适配与当前已知质量问题')
p('工程适配包括：真实Swift帮助入口；tuner_type/eval_strategy实装参数；ModelScope非root AST索引与缓存；完整TLS根bundle；ClearML SDK overlay；最终保存回调核验；监督器证据落盘/日志采集失败不能阻断恢复；WebUI auto工具解析参数。未改变BF16 LoRA训练路线。')
p('用户随后反馈思考后无正文及业务范围过宽。本轮新增诊断只读读取目标聊天、检查训练快照，并做2条API对照请求，没有重启服务、改数据或重训。实际训练保留1642条中，含<think>但无</think>的assistant记录数为0；原始302种不闭合回答、604次曝光均被长度过滤删除。因此不能将此次空正文直接归因于这302种记录。详细证据与改进草案见另一份诊断文档。')
p('直接API的thinking和nonthinking均有正文，但均生成未经核验的精确数字及来源名称，说明“能输出”不等于“业务正确”。下一轮应重点训练业务边界、缺信息先澄清、无依据不编造数值/来源、工具失败后的可见回退。业务范围仍需用户明确；尚未改写冻结训练集、启动新GPU训练或验收。')
h('11. 复算、交付与证据定位')
p('K8s控制平面metadata时钟较执行机/worker存在约20分钟偏差，原值均保留；执行顺序按监督器事件链，训练时长按Trainer runtime，不拼接不同时钟计算耗时。')
for label,url in links.items():p(label+'\n'+url)
p('本地路径：/Users/ben/aiws/codex/keywords/t008_qwen3_gpu_sft_20261019（GPU原始记录）；t008_qwen3_native_entry_20261019（正式入口CPU记录）；t008_qwen3_sft_v12_cpu（初始来源和快照）。GPU证据包中evidence/full-run_manifest.json含完整argv；actual-job-full.json含真实Job；outputs/persisted-output-manifest.json含原始持久化输出清单；test_serving/evidence/auto-tool-*含当前兼容性修复。')
code('''python3 - <<'PY'
import hashlib,json,zipfile
with zipfile.ZipFile('T008_v1.2_GPU_SFT与测试加载_证据包_20261019.zip') as z:
    assert z.testzip() is None
    m=json.loads(z.read('MANIFEST.json'))
    for f in m['files']:
        b=z.read(f['path'])
        assert len(b)==f['bytes']
        assert hashlib.sha256(b).hexdigest()==f['sha256']
    print('All manifest payload hashes passed')
PY''')
def write(name,parts):
 (ROOT/(name+'.blocks.json')).write_text(json.dumps(parts,ensure_ascii=False,indent=2)+'\n')
 (ROOT/(name+'.txt')).write_text('\n'.join(b['text'] for b in parts))
 (ROOT/(name+'.md')).write_text('\n\n'.join(('```\n'+b['text']+'```') if b['kind']=='code' else ('# ' if b['kind']=='title' else '## ' if b['kind']=='h1' else '')+b['text'] for b in parts))
write('training_runbook',blocks)
(ROOT/'actual-full-command.sh').write_text('# Historical command; do not run without a new window.\n'+format_command(full['command'])+'\n')
(ROOT/'actual-smoke-command.sh').write_text('# Historical command; do not run without a new window.\n'+format_command(smoke['command'])+'\n')
shutil.copyfile(CPU/'scripts/run_cpu_container.sh',ROOT/'historical-cpu-container.sh')
blocks=[]
add('title','空正文问题分析与业务语料优化草案')
p('T-008｜2026-10-19｜基于用户两张截图、实际目标聊天和当前训练候选。结论分为已确认事实、待验证假设和候选改进，不把截图当作新指令，不把API连通当作业务验收。')
h('1. 思考后无正文：已确认事实')
p('截图对应聊天中3次“北京的碳排放系数是多少？”回复的正文为空。数据库history输出仅含reasoning块，思考字符分别761/728/730；实际Qwen3 Tokenizer分别427/410/402 tokens。归一化chat_message正文仅2个空白字符，done=true，error=null，usage=null。历史聊天未保存finish_reason及原始请求预算。思考块显示completed不证明模型正常生成了最终答案。')
p('没有发现固定512或1024输出token证据；3条思考token数也不相同，不能据8秒时长断言达到某个统一token上限。服务日志同阶段存在HTTP200，但HTTP200和done都不能证明final content非空。此前03:26–03:27连接错误与已知vLLM重启时间重合，与03:30之后的这组空正文区别记录。')
h('2. 最小对照结果与能排除的原因')
for label in ('thinking','nonthinking'):
 s=load(ROOT/'evidence'/('direct-'+label+'-summary.json'))
 p(f'直接API、全新单轮、不带工具/历史、stream=true、include_usage=true、max_tokens=2048、enable_thinking={s["thinking"]}：HTTP成功={s["http_success"]}；prompt_tokens={s["usage"]["prompt_tokens"]}，completion_tokens={s["usage"]["completion_tokens"]}，reasoning_chars={s["reasoning_chars"]}，正文字符={s["content_chars"]}，finish_reason={s["finish_reason"]}，收到DONE={s["done_marker"]}。共2条请求，没有追加长评测。')
p('两条直接流式API都返回正文，证明当前Adapter和reasoning parser并非一律无法产出final；这不排除特定历史/工具请求的偶发模型行为或流处理缺陷。原始native-loaded存在302种未闭合think回答、604次曝光；native-retained的1642条中此类记录为0，均因原长度超2048被默认删除。不能把这302种记录认定为本次故障原因。')
h('3. 原因判断及证据边界')
p('当前准确结论：故障位于“生成终止或流式正文交付”链路，根因尚未锁定。候选A：原请求的max_tokens/剩余上下文预算在思考阶段耗尽，需finish_reason=length及原payload证明；候选B：模型在该上下文提前EOS或未生成思考结束边界，需原始SSE及token终态证明；候选C：WebUI中间件/工具循环/过滤器丢失final delta，需同请求vLLM SSE与WebUI输出对照证明。新单轮能输出不能单独证明C，更不能断言重训即可修复。')
p('当前max-model-len=8192是推理上下文，训练max_length=2048是训练样本过滤长度；二者不同。用户会话含多轮记录及原生工具，可能挤占上下文，但原请求没有留存，尚未证明实际达到8192。现有vLLM日志还提示Runner V2不支持thinking_token_budget，不能未经核验就依赖该参数限制思考。')
p('建议的下一步限于一次真实WebUI复现：捕获最终发送给vLLM的模型ID、消息/工具schema token数、max_tokens、stop、chat_template_kwargs，以及脱敏SSE的finish_reason/usage和正文delta计数。若length且正文为空，调整预算或该测试模型非思考设置；若stop且上游仅reasoning，处理模型/模板或明确fallback；若上游有正文而下游无正文，修WebUI。需要保留用户内容隐私，不全局记录其他会话。此次未改服务、参数或数据库。')
p('临时测试可选择新会话、关闭思考和暂不挂工具/RAG，区分问题来源；enable_thinking=false是Qwen3官方支持的模板开关，但这是建议，当前未擅自全局关闭。官方说明：https://huggingface.co/Qwen/Qwen3-8B#switching-between-thinking-and-non-thinking-mode 。本轮两条直接API只用于输出链路验证。')
h('4. 业务范围过宽：问题比清单长更重要')
p('截图中的回答声称“我的训练数据覆盖”能源管理、工业节能、智慧园区、智慧交通、智慧建筑、碳核算、碳交易、碳资产。当前108种身份样本和固定身份字段没有这段业务清单；当前用户/模型已持久化参数中也未见这些具体范围配置。基础模型联想、对话或动态系统/知识上下文仍可能影响输出，不能从一次回答确认确切来源。')
p('本次训练本质是通用Mixin+自我认知，未加入经审核的企业能碳专业训练集。因此无依据宣称“已训练覆盖这些行业且能专业服务”。项目历史备案包含更广的规划范围，同时明确规划不等于能力已验证；不应据此把规划自动写成当前模型能力承诺。')
p('直接API还暴露更严重的可信性问题：同一未限定口径的问题，在两次输出中给出相互不一致的精确因子/强度数值与来源名称，未调用检索。它们是待核实的模型输出，不是事实或可用因子。优化目标应同时覆盖不乱报业务能力、不编造数值/引用、缺口径先澄清，以及检索失败后明确说明。')
h('5. 候选身份与业务边界口径（待范围确认）')
p('短身份答案候选：我是章鱼能碳垂直大模型（Octacarbon LLM），由能碳章鱼（湖北）人工智能科技有限公司基于Qwen3-8B定制开发。\n业务描述候选：主要提供经确认业务范围内的辅助问答；具体因子、政策和企业数据以指定来源、年份和口径为准。不得自动附加智慧交通、智慧建筑、碳交易等清单，也不得承诺尚未验证的专业能力。')
p('建议先聚焦企业能源管理、工业节能、碳排放核算；这是待用户选择的候选范围，不是新批准。保留/排除项已向用户征询，尚未收到答案。公司中英文名、产品名、Qwen3-8B基座均维持已确认口径；不得将定制主体表述为Qwen原始研发方。')
h('6. 语料优化与重训实施路线')
p('先冻结范围spec：保留、排除、允许协助但不承诺、信息来源要求、禁止能力断言。再对108条身份模板逐条分类，保留必要的中英文名称/主体/基座区分，并删除机械长自我介绍、未经依据的领域能力扩展，新增简短自介绍、诱导身份、边界与反夸大回答。所有改动生成独立衍生版本、原行号/新行号、改写理由、SHA和真实决定记录，旧数据不改。')
p('业务样本重点：先问因子类型/年份/核算标准和单位；无已核验来源不报精确值；分清排放因子与强度指标；检索无结果/工具失败必须给出可见解释；限定在已确认业务内，不对所有能碳子领域自称专家。专业知识通过经批准业务材料和RAG供给，自我认知SFT不等于专业知识训练。')
p('长度与比例：先使用真实Qwen3+Swift模板过滤，再计算有效曝光与assistant监督token比例、重复度。5%–10%不是已证明的通用最佳值；本轮36.54%也不能单凭比例确定质量。下一版应减少重复自我介绍并加入有来源的业务行为样本；最终具体条数/比例根据新范围和少量独立验收题确定，不在未确认内容前硬套2000:150。')
p('训练路线建议维持Qwen3-8B、BF16 LoRA和2048起点以便比较，只改批准的新数据及其绑定guard/Manifest。新数据已经实质偏离旧“官方原生默认”入口，不能继续拿旧CPU SHA/approval.json通过；需独立新版本、CPU长度与mask核验、运行前明确新服务暂停/恢复窗口。当前仅形成草案，没有重新训练，没有覆盖现有测试模型。')
h('7. 最小验收与当前停止点')
p('下一轮只冻结一小组独立验收用例，覆盖身份/基座归属、范围内回答、范围外处理、因子歧义、无来源、工具失败、多轮与可见正文。对原问题要求先确认因子口径和年份、没有依据不编数字；对普通业务问题不强行自我介绍；失败路径必须有用户可见结论。避免用训练问题直接证明泛化，不以训练loss代替质量。')
p('已完成：训练全过程文档、两个问题的现有证据核对、2条最小API对照、原训练think结构复核、独立优化草案。未完成：空正文的原始请求级根因闭环（缺历史SSE/finish_reason/usage）、新业务范围确认、新语料正式定稿/批准、CPU核验、新GPU训练及质量验收。当前服务与旧冻结数据均保留。')
p('本次证据仅交付脱敏结构摘要和final回答，不上传模型思考正文、账户信息、密钥或原始聊天数据库。')
write('diagnosis_and_data_plan',blocks)
print(json.dumps({'runbook_characters':len((ROOT/'training_runbook.txt').read_text()),'diagnosis_characters':len((ROOT/'diagnosis_and_data_plan.txt').read_text()),'GPU_training_started':False},ensure_ascii=False))
