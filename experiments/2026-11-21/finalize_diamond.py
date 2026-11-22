"""One-off: the diamond team-instruction run finished but its FMF write hit Controlled Folder Access.
Export the saved tactic (gti_current.json) to fm-tactics-lab/exports and write the report from the run log."""
import base64, copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lab import call
import geo_ti_steps as gts

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = r'C:\Users\pawan\AppData\Local\Temp\claude\fd7dc0b53401d4e0\4f4c3409-f14b-4b4b-b036-b6e24024aee2\tasks\b4fee4n2v.output'
log = [l.rstrip() for l in open(LOG, encoding='utf8') if l.startswith(('step ', 'confirm '))]
assert len(log) == 16, len(log)
cur = json.load(open(os.path.join(HERE, 'gti_current.json'), encoding='utf8'))
fin = copy.deepcopy(cur); fin['teams'][0]['tactic_name'] = 'Geometrismo Diamond'
ex = call('/api/export-fmf', {'side': 0, 'scenario': fin, 'name': 'Geometrismo Diamond'})
path = os.path.join(r'C:\Users\pawan\fm-tactics-lab\exports', 'Geometrismo Diamond.fmf')
open(path, 'wb').write(base64.b64decode(ex['file_base64']))
tt = fin['teams'][0]
kept = [l.split(':')[0].split(' ', 2)[2] for l in log if l.endswith('KEEP')]
report = ['# Geometrismo Diamond - lab result (FM27 27.1.0+2505117)', '',
          'Shape: 4-3-1-2 diamond, same both phases (only back-four symmetric shape that passes the geometry gate and leads the lab).',
          'Instructions: picked by the research geometry model (diamond_instructions.txt), tested one at a time; engine may only veto.',
          'Lab: original FM27 engine, flat-15 squads, 61 coach presets (Swiss SL + PL), xG difference per match, 300 seeds per step.', '',
          '## Steps'] + ['- ' + l for l in log] + ['', f'Kept: {", ".join(kept)}', '',
          'In possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in tt['phases'][0]),
          'Out of possession: ' + ', '.join(f"{c['position']} {c['role']}" for c in tt['phases'][1]),
          'Team instructions: ' + ', '.join(f"{gts.GROUPS[int(k)]['label']}={next(o['label'] for o in gts.GROUPS[int(k)]['options'] if o['id'] == v)}"
                                           for k, v in tt['instructions'].items() if int(k) in gts.GROUPS),
          'Mentality: Balanced (tested in the everything stage)',
          f'FMF: {path} (native round-trip verified, sha256 {ex["report"]["sha256"]}); copy it into the FM27 tactics folder']
open(os.path.join(r'C:\Users\pawan\optimal-formation\fm27', 'lab_result_diamond.md'), 'w', encoding='utf8').write('\n'.join(report) + '\n')
print('\n'.join(report[-6:]))
