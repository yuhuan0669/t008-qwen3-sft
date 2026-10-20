"""Run synthetic CPU-only EvalScope API checks; never sends holdout or training data."""
import argparse,json,pathlib,subprocess,sys
p=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--target',choices=['local','kubernetes'],default='local');args=ap.parse_args()
protocol=json.loads((p/'protocol.json').read_text())
code="__name__='cpu_api_check'\n__file__='/CPU_PREPARATION/cpu_adapter.py'\n"+(p/'cpu_adapter.py').read_text()+"\nprotocol_fixture="+repr(protocol)+"\n"+(p/'check_cpu_api.py').read_text()
command=([sys.executable,'-'] if args.target=='local' else ['kubectl','-n','evalscope','exec','-i','deployment/evalscope','--','python','-'])
r=subprocess.run(command,input=code,text=True,capture_output=True)
if r.returncode:
 sys.stderr.write(r.stderr);sys.stdout.write(r.stdout);raise SystemExit(r.returncode)
report=json.loads(r.stdout);assert report['inference_executed'] is False and report['model_instantiated'] is False
(p/'cpu-api-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
