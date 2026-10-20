"""Package the report update; original data and old evidence bundles stay intact."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name != 'MANIFEST.json' and '__pycache__' not in p.parts)
assert not any(p.name == 'approval.json' for p in files)
for p in (ROOT / 'scripts').glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
manifest = {'schema':'t008-official2048-report-update-manifest-v1',
            'scope':'Updated execution/report/gate and read-only evidence; no training dataset changes.',
            'gpu_training_authorized':False, 'gpu_training_started':False,
            'original_cpu_packet_unchanged':True,
            'files':[{'path':p.relative_to(ROOT).as_posix(), 'bytes':p.stat().st_size,
                      'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(ROOT / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
archive = ROOT.with_suffix('.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files + [ROOT / 'MANIFEST.json']:
        z.write(p, ROOT.name + '/' + p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for entry in manifest['files']:
        data = z.read(ROOT.name + '/' + entry['path'])
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,
                  'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'payload_files':len(files),'zip_crc_and_all_payload_hashes_match':True}))
