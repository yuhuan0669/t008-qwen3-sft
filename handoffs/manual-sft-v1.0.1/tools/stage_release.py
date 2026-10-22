"""Verify/export an Adapter into a new immutable release; no cluster or GPU calls."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,zipfile

def main():
 a=argparse.ArgumentParser();a.add_argument('--adapter-zip',required=True,type=Path);a.add_argument('--expected-sha256',required=True);a.add_argument('--store',type=Path,default=Path('/store'));a.add_argument('--release',required=True);a.add_argument('--execute',action='store_true');x=a.parse_args();assert re.fullmatch(r'[a-z0-9][a-z0-9-]{1,38}',x.release);assert hashlib.sha256(x.adapter_zip.read_bytes()).hexdigest()==x.expected_sha256;target=x.store/'released'/x.release;assert not target.exists();names=['adapter_config.json','adapter_model.safetensors']
 with zipfile.ZipFile(x.adapter_zip) as z:
  assert set(names)<=set(z.namelist());cfg=json.loads(z.read('adapter_config.json'));assert cfg.get('peft_type')=='LORA';files={n:{'bytes':len(z.read(n)),'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in names}
  m={'release':x.release,'source_zip_sha256':x.expected_sha256,'base_model':'Qwen/Qwen3-8B','rank':cfg['r'],'files':files,'destination':str(target),'executed':x.execute}
  if x.execute:
   temp=x.store/'.staging'/x.release;temp.mkdir(parents=True,exist_ok=False);(temp/'adapter').mkdir()
   try:
    for n in names:
     p=temp/'adapter'/n;p.write_bytes(z.read(n));assert hashlib.sha256(p.read_bytes()).hexdigest()==files[n]['sha256'];p.chmod(0o444)
    (temp/'release-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');(temp/'release-manifest.json').chmod(0o444);(temp/'adapter').chmod(0o555);target.parent.mkdir(exist_ok=True);os.rename(temp,target);target.chmod(0o555)
   except Exception:
    # Preserve a partial staging directory for inspection; never touch old releases.
    raise
 print(json.dumps(m,ensure_ascii=False))
if __name__=='__main__':main()
