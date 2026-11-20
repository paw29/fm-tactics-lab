"""Generate and compare one-change tactical variants on paired match inputs."""
import copy
from collections import defaultdict
from statistics import mean, stdev

LABELS = {'role': '角色实验室', 'team': '球队指令实验室', 'player': '个人指令实验室'}


def candidates(app, scenario, side, kind, phases, slots, groups, mark_position, mark_player):
    team = scenario['teams'][side]
    if kind == 'team':
        for group in app.GROUPS.values():
            if group['possession_phase'] not in phases or groups and group['id'] not in groups:
                continue
            current = team['instructions'][str(group['id'])]
            for option in group['options']:
                if option['id'] == current:
                    continue
                instructions = {**team['instructions'], str(group['id']): option['id']}
                if not app.team_conflicts(instructions):
                    yield {'group': group['label'], 'option': option['label'],
                           'baseline_option': next(o['label'] for o in group['options'] if o['id'] == current),
                           'phase': group['possession_phase'], 'slot': None,
                           'instructions': instructions, 'adjustments': []}
        return

    for phase in phases:
        cells = team['phases'][phase]
        for slot in slots:
            cell = cells[slot]
            context = {'phase': phase, 'slot': slot, 'position': cell['position'],
                       'player': team['players'][team['lineup'][slot]]['name']}
            if kind == 'role':
                for role in app.role_options(cells, phase, cell['position']):
                    if role == cell['role']:
                        continue
                    change = copy.deepcopy(cell)
                    change.update(role=role, duty='0')
                    policy = app.cell_policy(side, phase, slot, change)
                    adjustments = []
                    for group in app.PIS.values():
                        key = str(group['id'])
                        value = change['instructions'][key]
                        if value and (group['phase'] != phase or policy[value] != '0'):
                            change['instructions'][key] = 0
                            adjustments.append(group['label'])
                    if change['instructions']['14'] not in (34, 35):
                        change.update(target_player=255, target_position=0)
                    yield {**context, 'group': LABELS[kind], 'option': app.ROLES[role]['label'],
                           'baseline_option': app.ROLES[cell['role']]['label'],
                           'cell': change, 'adjustments': adjustments}
            else:
                policy = app.cell_policy(side, phase, slot, cell)
                for group in app.PIS.values():
                    if group['phase'] != phase or groups and group['id'] not in groups:
                        continue
                    if not any(o['id'] and policy[o['id']] == '0' for o in group['options']):
                        continue
                    key = str(group['id'])
                    for option in group['options']:
                        value = option['id']
                        if value == cell['instructions'][key] or value and policy[value] != '0':
                            continue
                        if (value == 34 and mark_player is None) or (value == 35 and not mark_position):
                            continue
                        change = copy.deepcopy(cell)
                        change['instructions'][key] = value
                        if group['id'] == 14:
                            change.update(target_player=mark_player if value == 34 else 255,
                                          target_position=mark_position if value == 35 else 0)
                        yield {**context, 'group': group['label'], 'option': option['label'],
                               'baseline_option': next(o['label'] for o in group['options']
                                                       if o['id'] == cell['instructions'][key]),
                               'cell': change, 'adjustments': []}


def variants(app, opponents, side, changes, home_away):
    cases = [{key: value for key, value in edit.items() if key not in ('cell', 'instructions')}
             | {'entries': []} for edit in changes]
    variants = []
    for index, (opponent, base) in enumerate(opponents):
        for reverse in range(2 if home_away else 1):
            prefix = f'T{index:03d}{reverse}'
            tested_side = side ^ reverse

            def orient(scenario):
                if reverse:
                    teams = scenario['teams']
                    scenario['teams'] = [app.transplant_team(teams[1], 0), app.transplant_team(teams[0], 1)]
                    if 'experimental_execution' in scenario:
                        scenario['experimental_execution'].reverse()
                return app.validate_scenario(scenario)

            baseline = prefix + 'B'
            variants.append((baseline, orient(copy.deepcopy(base))))
            for number, (edit, case) in enumerate(zip(changes, cases)):
                changed = copy.deepcopy(base)
                team = changed['teams'][side]
                if edit['slot'] is None:
                    team['instructions'] = edit['instructions'].copy()
                else:
                    team['phases'][edit['phase']][edit['slot']] = copy.deepcopy(edit['cell'])
                label = f'{prefix}V{number:03d}'
                variants.append((label, orient(changed)))
                case['entries'].append({'baseline': baseline, 'variant': label,
                                        'side': tested_side, 'opponent': opponent})
    return variants, cases


def values(run, side):
    score = run['result']['score']
    outcome = score[side] - score[1 - side]
    teams = run['statistics']['teams']
    return int(outcome > 0), 3 if outcome > 0 else int(outcome == 0), teams[side]['xg'] - teams[1 - side]['xg']


def report(runs, settings):
    indexed = {(run['variant'], run['seed']): run for run in runs if run.get('verified')}
    rows = []
    for case in settings['cases']:
        row = {key: value for key, value in case.items() if key != 'entries'}
        for stage in ('exploration', 'validation'):
            pairs = []
            seed_changes = []
            for seed in settings[f'{stage}_seeds']:
                block = []
                for context in case['entries']:
                    base = indexed.get((context['baseline'], seed))
                    changed = indexed.get((context['variant'], seed))
                    if base is not None and changed is not None:
                        side = context['side']
                        block.append((values(base, side), values(changed, side)))
                # An incomplete opponent or venue block must not change its weight.
                if len(block) == len(case['entries']):
                    pairs.extend(block)
                    seed_changes.append(mean(b[0] - a[0] for a, b in block))
            result = {'pairs': len(pairs), 'seeds': len(seed_changes)}
            if pairs:
                result.update(win_rate=mean(b[0] for a, b in pairs),
                              baseline_win_rate=mean(a[0] for a, b in pairs),
                              win_delta=mean(seed_changes), points=mean(b[1] for a, b in pairs),
                              points_delta=mean(b[1] - a[1] for a, b in pairs),
                              xg_difference=mean(b[2] for a, b in pairs),
                              xg_delta=mean(b[2] - a[2] for a, b in pairs),
                              win_error=(1.96 * stdev(seed_changes) / len(seed_changes)**.5
                                         if len(seed_changes) > 1 and any(seed_changes) else None))
            row[stage] = result
        rows.append(row)
    return rows


def shortlist(rows):
    grouped = defaultdict(list)
    for index, row in enumerate(rows):
        sample = row['exploration']
        if sample['pairs']:
            grouped[(row['phase'], row['slot'], row['group'])].append(index)
    ranking = lambda i: (rows[i]['exploration']['points_delta'], rows[i]['exploration']['xg_delta'])
    return {index for group in grouped.values() for index in sorted(group, key=ranking, reverse=True)[:2]}
