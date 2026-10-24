"""Verify local source evidence without importing any simulation code."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'inputs/source_provenance.json'
data = json.loads(path.read_text(encoding='utf-8'))
for name in ('local_project', 'gds'):
    p = Path(data[name])
    if p.exists():
        data[name + '_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
project = Path(data['local_project'])
if project.exists():
    values = json.loads(project.read_text(encoding='utf-8'))['mark']
    assert values['mother_period_um'] == 16
    assert values['stripe_count'] == 3
    assert values['cd_um'] == 1.6
    assert values['subpitch_um'] == 3.2
    assert values['height_um'] == .3
    data['nominal_checks_passed'] = True
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Source dimensions and SHA256 evidence recorded.')
