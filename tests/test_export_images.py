"""Check export path safety and copying without real build artifacts."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class ExportImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fuxi export ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        self.script = self.root / 'scripts/export-images.py'
        shutil.copyfile(REPO / 'scripts/export-images.py', self.script)
        self.work = self.root / 'work'
        self.source = self.work / 'output/images'
        (self.source / 'fuxi').mkdir(parents=True)
        self.files = {'Image': b'kernel fixture', 'fuxi/fuxi-sim.dtb': b'dtb fixture'}
        for name, data in self.files.items():
            (self.source / name).write_bytes(data)
        manifest = {'artifact_sha256': {
            name: hashlib.sha256(data).hexdigest() for name, data in self.files.items()
        }}
        self.files['manifest.json'] = json.dumps(manifest).encode()
        (self.source / 'manifest.json').write_bytes(self.files['manifest.json'])
        self.env = dict(os.environ, FUXI_WORK=str(self.work))

    def export(self, *args):
        return subprocess.run(
            [sys.executable, str(self.script), *map(str, args)], cwd=self.root,
            env=self.env, text=True, capture_output=True, timeout=5,
        )

    def assert_rejected(self, *args):
        before = set(self.source.rglob('*'))
        result = self.export(*args)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Destination must be outside the source images:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(set(self.source.rglob('*')), before)
        for name, data in self.files.items():
            self.assertEqual((self.source / name).read_bytes(), data)

    def test_rejects_source_and_nested_destinations_before_writing(self):
        for destination in [self.source, self.source / 'export/nested',
                            self.source / '../images/export']:
            with self.subTest(destination=destination):
                self.assert_rejected(destination)

    def test_rejects_destinations_through_symlinks(self):
        alias = self.root / 'images-link'
        alias.symlink_to(self.source, target_is_directory=True)
        for destination in [alias, alias / 'export']:
            with self.subTest(destination=destination):
                self.assert_rejected(destination)

    def test_resolves_source_symlinks(self):
        alias = self.root / 'work-link'
        alias.symlink_to(self.work, target_is_directory=True)
        self.env['FUXI_WORK'] = str(alias)
        self.assert_rejected(self.source / 'export')

    def test_rejects_default_destination_when_it_is_the_source(self):
        shutil.move(str(self.work / 'output'), self.root / 'output')
        self.source = self.root / 'output/images'
        self.env['FUXI_WORK'] = str(self.root)
        self.assert_rejected()

    def test_exports_and_verifies_files_outside_source(self):
        for destination in [self.root / 'exported images', self.source.parent]:
            with self.subTest(destination=destination):
                result = self.export(destination)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Exported and verified 2 files:', result.stdout)
                for name, data in self.files.items():
                    self.assertEqual((destination / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
