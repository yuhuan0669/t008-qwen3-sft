"""Package review records, excluding external delivery/readback receipts."""
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
files = sorted(p for p in HERE.iterdir() if p.is_file() and p.name != 'MANIFEST.json')
manifest = {'schema': 't008-review-evidence-manifest-v1', 'training_approval': False,
            'training_data_modified': False,
            'files': [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(HERE / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
archive = HERE.with_suffix('.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files + [HERE / 'MANIFEST.json']:
        z.write(p, HERE.name + '/' + p.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for entry in manifest['files']:
        data = z.read(HERE.name + '/' + entry['path'])
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'payload_files': len(files), 'zip_crc_and_payload_hashes_verified': True}))
