"""Add the verified Steam 27.1 personal instruction rules to a private catalog."""
import argparse
import json
from pathlib import Path


def update(catalog, events, adapter):
    if not any(row.get('event') == 'native_image_fingerprint'
               and row.get('sha256') == adapter['reference_dll_sha256'] for row in events):
        raise ValueError('Policy audit does not use the configured Steam DLL')
    version = int(adapter['tactic_version'], 16)
    policies = {}
    positions = {row['id']: row['mask'] for row in catalog['positions']}
    roles = {(row['phase'], row['id']): int(row['flags']) for row in catalog['roles']}
    for row in events:
        if row.get('event') != 'pi_policy' or row['version'] != version:
            continue
        index = (row['phase'], row['position'], int(row['role']), int(row['duty']))
        status = row['statuses']
        if len(status) != 43 or set(status) - set('0123') or index in policies:
            raise ValueError(f'Invalid or duplicate instruction policy at {index}')
        policies[index] = status
    for key, versions in catalog['pi_policies'].items():
        phase, position, role, duty = key.split(':')
        index = (int(phase), positions[position], roles[int(phase), role], int(duty))
        versions[adapter['tactic_version']] = policies[index]
    catalog['policy_versions'] = sorted(set(catalog['policy_versions']) | {adapter['tactic_version']})


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path, help='JSONL produced by FM27Simulator.exe --policy-audit')
    parser.add_argument('--catalog', type=Path, default=root / 'private/catalog.json')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf8'))
    adapter = json.loads((root / 'native/adapter_version.json').read_text(encoding='utf8'))
    events = [json.loads(line) for line in args.audit.read_text(encoding='utf8').splitlines()]
    update(catalog, events, adapter)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
