import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fm27_match_events import save_leaderboards


class SaveLeaderboardTests(unittest.TestCase):
    def test_merge_saved_uid_across_venues_and_preserve_opponent_and_variant_identity(self):
        def player(side, native_id, name):
            return {'side': side, 'native_id': native_id, 'name': name}

        def goal(scorer, assist=None, **flags):
            return {'side': scorer['side'], 'scorer': scorer, 'assist': assist, **flags}

        def run(variant, *goals, verified=True):
            schedule[variant] = {'group': variant[0], 'tested_side': int(variant.endswith('_A'))}
            return {'variant': variant, 'events': {'collected': True, 'goals': goals,
                    'scorers_verified_against_native_totals': verified}}

        def team(name, *players):
            return {'name': name, 'players': [{'native_id': native_id, 'source_uid': uid} for native_id, uid in players]}

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def save(variant, *teams, generated=False):
                document = {'teams': teams}
                if generated:
                    document['native_generation'] = {}
                (root / f'{variant}.json').write_text(json.dumps(document), encoding='utf8')

            home = team('Tested', (1, 101), (2, 102))
            away = team('Tested', (4, 101), (5, 102))
            save('B_0_H', home, team('First club', (4, 201)))
            save('B_0_A', team('First club', (1, 201)), away)
            save('B_1_H', home, team('Second club', (4, 202)))
            save('A_1_H', home, team('Second club', (4, 202)), generated=True)

            # Shared native IDs and display names must never merge unrelated save UIDs.
            first = player(1, 4, 'Alex')
            second = player(1, 4, 'Alex')
            own_home = player(0, 1, 'Forward')
            own_away = player(1, 4, 'Forward')
            assist_home = player(0, 2, 'Midfielder')
            assist_away = player(1, 5, 'Midfielder')
            schedule = {}
            runs = [
                run('B_0_H', goal(own_home, assist_home), goal(first),
                    goal(own_home, assist_home, own_goal=True),
                    goal(own_home, assist_home, cancelled=True)),
                run('B_0_A', goal(own_away, assist_away), goal(player(0, 1, 'Alex'))),
                run('B_1_H', goal(second), goal(player(1, 98, 'Missing'))),
                run('B_0_H', goal(own_home), verified=False),
                run('A_1_H', goal(player(0, 101, 'Forward'), player(0, 102, 'Midfielder'))),
            ]
            boards = save_leaderboards(root, schedule, runs)
            self.assertEqual(boards['B']['verified_matches'], 3)
            self.assertEqual(boards['B']['excluded_matches'], 1)
            self.assertEqual(boards['B']['unbound_events'], 1)
            totals = {row['source_uid']:(row['team'], row['goals'], row['assists'])
                      for row in boards['B']['players']}
            self.assertEqual(totals, {101:('Tested', 2, 0), 102:('Tested', 0, 2),
                                      201:('First club', 2, 0), 202:('Second club', 1, 0)})
            self.assertEqual([(row['source_uid'], row['goals'], row['assists'])
                              for row in boards['A']['players']], [(101, 1, 0), (102, 0, 1)])
