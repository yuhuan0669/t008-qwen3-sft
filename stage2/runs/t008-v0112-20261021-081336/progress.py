from pathlib import Path
import subprocess,json,re
p=Path(__file__).resolve().parent;k=['kubectl','--context','lmas00-direct','--request-timeout=20s','-n','swift']
print(subprocess.check_output(k+['get','jobs','-l','t008-run='+p.name],text=True))
code="from pathlib import Path;import json;r=Path('/work/"+p.name+"');p=r/'outputs/full/train.log';print(p.read_text()[-1100:] if p.exists() else 'full not started');q=r/'development/run-state.json';print(q.read_text() if q.exists() else '')"
r=subprocess.run(k+['exec',p.name+'-prep','--','python3','-c',code],capture_output=True,text=True);print(r.stdout)
print((p/'controller.log').read_text()[-700:]);print((p/'window-state.json').read_text())
