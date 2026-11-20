import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from export_source import export, source_files, validate
from generate_profile import read_rva, restore_profile


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_root = ROOT / 'build/test-temp'
        cls.temp_root.mkdir(parents=True, exist_ok=True)

    def test_public_profile_contains_only_fingerprints(self):
        profile = json.loads((ROOT / 'native/profile_metadata.json').read_text(encoding='utf8'))
        self.assertTrue(profile['ranges'])
        for item in profile['ranges']:
            self.assertNotIn('hex', item)
            self.assertGreater(item['size'], 0)
            self.assertEqual(len(item['sha256']), 64)
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            restore_profile(profile, b'Not the original supported DLL')

    def test_reconstructs_mapped_bytes_and_rejects_tampering(self):
        # Small synthetic PE: a file-backed section at RVA 0x1000.
        raw = bytearray(0x300)
        raw[:2] = b'MZ'
        struct.pack_into('<I', raw, 0x3c, 0x80)
        raw[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HH', raw, 0x84, 0x8664, 1)
        struct.pack_into('<H', raw, 0x94, 0xf0)
        struct.pack_into('<IIII', raw, 0x188 + 8, 0x100, 0x1000, 0x100, 0x200)
        raw[0x210:0x214] = b'test'
        metadata = {'reference_sha256': hashlib.sha256(raw).hexdigest(),
                    'ranges': [{'rva': 0x1010, 'size': 4, 'sha256': hashlib.sha256(b'test').hexdigest()}]}
        self.assertEqual(restore_profile(metadata, raw)['ranges'][0]['hex'], b'test'.hex())
        self.assertNotIn('hex', metadata['ranges'][0])
        metadata['ranges'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Range checksum'):
            restore_profile(metadata, raw)
        with self.assertRaisesRegex(ValueError, 'Unmapped'):
            read_rva(raw, [(0x1000, 0x100, 0x200)], 0x10ff, 2)

    def test_public_validation_and_archive_boundary(self):
        paths = validate()
        self.assertGreater(len(paths), 40)
        self.assertFalse(any(p.suffix in {'.exe', '.dll', '.pkm', '.fmf', '.pyd'} for p in paths))
        with tempfile.TemporaryDirectory(dir=self.temp_root) as folder:
            output = Path(folder) / 'source.zip'
            export(output)
            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(archive.read('fm-tactics-lab/SOURCE_MANIFEST.json'))
                self.assertEqual(len(archive.namelist()), len(manifest) + 1)
                for name, expected in manifest.items():
                    self.assertEqual(hashlib.sha256(archive.read('fm-tactics-lab/' + name)).hexdigest(), expected)
                    self.assertFalse({'private', 'build', 'data', 'vendor', '__pycache__'} & set(Path(name).parts))
                self.assertNotIn('fm-tactics-lab/src/tactics_ui/catalog.json', archive.namelist())

    def test_local_private_files_cannot_enter_allowlist(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as folder:
            root = Path(folder)
            private_files = {'private/secret.py', 'build/derived.cpp', 'data/career.fm',
                             'src/tactics_ui/catalog.json', 'native/engine_compat_profile.h',
                             'AGENTS.md', 'PRD.md', 'PROJECT_INDEX.md', 'docs/new-notes.md',
                             'docs/tasks/unreviewed.md', 'docs/screenshots/README.md'}
            for name in private_files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('private', encoding='utf8')
            selected = {p.relative_to(root).as_posix() for p in source_files(root)}
            self.assertFalse(private_files & selected)
            self.assertEqual({name for name in selected if name.endswith('.md')},
                             {'README.md', 'README.en.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
                              'THIRD_PARTY_NOTICES.md', 'docs/DEVELOPMENT.md',
                              'docs/SIMULATION_FIDELITY.md', 'docs/TROUBLESHOOTING.md'})

    @unittest.skipUnless(os.name == 'nt', 'desktop adapters use Win32')
    def test_epic_builds_select_distinct_hosts(self):
        sys.path.insert(0, str(ROOT / 'src'))
        from desktop_engine import adapter_for, host_for

        with tempfile.TemporaryDirectory(dir=self.temp_root) as folder:
            root = Path(folder)
            native = root / 'fm27_native'
            for variant in ('epic', 'epic_27_1'):
                profile = ROOT / 'native' / f'{variant}_profile_metadata.json'
                adapter = native / variant
                adapter.mkdir(parents=True)
                (adapter / 'engine_compat_profile.json').write_bytes(profile.read_bytes())
                digest = json.loads(profile.read_text(encoding='utf8'))['reference_sha256']
                self.assertEqual(adapter_for(native, digest), ('epic', adapter))
                status = {'adapter': 'epic', 'adapter_variant': variant}
                self.assertEqual(host_for(root, status), adapter / 'FM27Simulator.exe')
            self.assertEqual(adapter_for(native, '0' * 64), ('steam', native))
            self.assertEqual(host_for(root, {'adapter': 'epic'}), native / 'epic/FM27Simulator.exe')


if __name__ == '__main__':
    unittest.main()
