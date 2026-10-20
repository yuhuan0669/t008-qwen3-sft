import unittest,sys,json,datetime,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_local_sft import validate_binding, build_command
class Contract(unittest.TestCase):
 def setUp(self):
  self.root=Path(__file__).resolve().parents[2]
  self.spec=json.loads((self.root/'stage1/training/run-spec.json').read_text())
  self.report=json.loads((self.root/'stage1/evidence/encoding-report.json').read_text())
  self.auth={'experiment_approved':True,'uat_pause_approved':True,'approved_data_sha256':self.spec['dataset_sha256'],'window_start_utc':'2026-10-20T00:00:00+00:00','window_end_utc':'2026-10-20T08:00:00+00:00'}
  self.now=datetime.datetime(2026,10,20,1,tzinfo=datetime.timezone.utc)
 def test_binding_and_expiration(self):
  validate_binding(self.spec,self.report,self.auth,self.now)
  self.auth['window_end_utc']='2026-10-20T00:30:00+00:00'
  with self.assertRaises(RuntimeError):validate_binding(self.spec,self.report,self.auth,self.now)
 def test_input_drift(self):
  self.report['dataset_sha256']='bad'
  with self.assertRaises(RuntimeError):validate_binding(self.spec,self.report,self.auth,self.now)
 def test_full_and_smoke_paths(self):
  full=build_command(self.spec,'full','/base','/input','/runwork/outputs/full1')
  self.assertEqual(full[full.index('--dataset')+1],'/input/stage1/data/train.jsonl')
  self.assertEqual(full[full.index('--external_plugins')+1],'/input/stage1/training/local_data_guard.py')
  self.assertNotIn('--resume_from_checkpoint',full)
  smoke=build_command(self.spec,'smoke','/base','/input','/runwork/outputs/smoke')
  self.assertEqual(smoke[smoke.index('--max_steps')+1],'3')
  self.assertEqual(smoke[smoke.index('--output_dir')+1],'/runwork/outputs/smoke/checkpoints')
if __name__=='__main__':unittest.main()
