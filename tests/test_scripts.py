"""Exercise launcher arguments and source provenance without building Linux."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class RunFuxiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fuxi scripts ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        self.script = self.root / 'scripts/run-fuxi.sh'
        shutil.copyfile(REPO / 'scripts/run-fuxi.sh', self.script)
        self.sim = self.root / 'sim executable'
        self.sim.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, sys\n'
            'print(json.dumps(sys.argv[1:]))\n'
            'sys.exit(int(os.environ.get("SIM_EXIT", "0")))\n'
        )
        self.sim.chmod(0o755)
        self.images = self.root / 'image files'
        (self.images / 'fuxi').mkdir(parents=True)
        self.env = dict(os.environ, FUXI_IMAGES=str(self.images), FUXI_MAX_CYCLES='123')
        self.env.pop('FUXI_CMDLINE', None)
        self.env.pop('SIM_EXIT', None)

    def launch(self, *args):
        return subprocess.run(
            ['bash', str(self.script), *map(str, args)], cwd=self.root,
            env=self.env, text=True, capture_output=True,
        )

    def test_requires_simulator_argument(self):
        self.env['FUXI_SIM'] = str(self.sim)
        result = self.launch()
        self.assertEqual(result.returncode, 2)
        self.assertIn('Usage:', result.stderr)

    def test_help(self):
        result = self.launch('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('SIMULATOR', result.stdout)

    def test_rejects_missing_or_non_executable_files(self):
        plain = self.root / 'not executable'
        plain.write_text('plain text')
        for path in [self.root / 'missing', plain, self.root]:
            with self.subTest(path=path):
                result = self.launch(path)
                self.assertEqual(result.returncode, 1)
                self.assertIn('not an executable file', result.stderr)

    def test_relative_path_arguments_and_exit_status(self):
        self.env['SIM_EXIT'] = '7'
        result = self.launch(self.sim.name, '--custom', 'argument with spaces')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(json.loads(result.stdout), [
            '--load', f'0x200={self.images}/fuxi-bootstub.bin',
            '--elf', f'{self.images}/fw_jump.elf',
            '--load', f'0x80400000={self.images}/Image',
            '--load', f'0x87e00000={self.images}/fuxi/fuxi-sim.dtb',
            '--max-cycles', '123', '--stats', '--custom', 'argument with spaces',
        ])

    @unittest.skipUnless(all(shutil.which(tool) for tool in ['dtc', 'fdtget', 'fdtput']),
                         'device-tree compiler tools are required')
    def test_command_line_changes_only_a_copy_of_the_dtb(self):
        dtb = self.images / 'fuxi/fuxi-sim.dtb'
        subprocess.run(
            ['dtc', '-I', 'dts', '-O', 'dtb', '-o', str(dtb)],
            input='/dts-v1/; / { chosen { bootargs = "base=1"; }; };',
            text=True, check=True, capture_output=True,
        )
        original = dtb.read_bytes()
        self.env['FUXI_CMDLINE'] = 'fuxi.interactive=1'
        result = self.launch(self.sim)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        copied = Path(next(arg.split('=', 1)[1] for arg in args
                           if arg.startswith('0x87e00000=')))
        self.assertTrue(copied.is_relative_to(self.root / 'debug'))
        self.assertEqual(dtb.read_bytes(), original)
        bootargs = subprocess.check_output(
            ['fdtget', '-t', 's', str(copied), '/chosen', 'bootargs'], text=True,
        ).strip()
        self.assertEqual(bootargs, 'base=1 fuxi.interactive=1')


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fuxi manifest ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        self.script = self.root / 'scripts/manifest.py'
        shutil.copyfile(REPO / 'scripts/manifest.py', self.script)
        self.br = self.root / 'third_party/buildroot'
        self.br.mkdir(parents=True)
        self.git(self.br, 'init', '-q')
        (self.br / 'README').write_text('Buildroot fixture\n')
        self.git(self.br, 'add', 'README')
        self.git(self.br, 'commit', '-qm', 'Initial Buildroot')
        self.git(self.root, 'init', '-q')
        self.git(self.root, 'submodule', 'add', 'https://example.invalid/buildroot.git',
                 'third_party/buildroot')
        self.git(self.root, 'submodule', 'absorbgitdirs')
        (self.root / '.gitignore').write_text('/output/\n')
        self.git(self.root, 'add', '.')
        self.git(self.root, 'commit', '-qm', 'Initial integration')
        self.output = self.root / 'output'
        (self.output / 'images').mkdir(parents=True)
        self.archives = {
            'linux': 'https://example.invalid/linux-snapshot.tar.gz',
            'opensbi': 'https://example.invalid/opensbi-snapshot.tar.gz',
        }
        (self.output / '.config').write_text(
            'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION=' + json.dumps(self.archives['linux']) + '\n'
            'BR2_TARGET_OPENSBI_CUSTOM_TARBALL_LOCATION=' + json.dumps(self.archives['opensbi']) + '\n'
        )
        for name in ['linux-1', 'busybox-1', 'opensbi-1/build/platform/generic/kconfig']:
            directory = self.output / 'build' / name
            directory.mkdir(parents=True)
            (directory / '.config').write_text('CONFIG_TEST=y\n')
        (self.output / 'images/Image').write_bytes(b'kernel fixture')

    @staticmethod
    def git(path, *args):
        return subprocess.check_output([
            'git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            '-c', 'commit.gpgsign=false', '-C', str(path), *args,
        ], text=True, stderr=subprocess.PIPE).strip()

    def manifest(self):
        return json.loads(subprocess.check_output(
            ['python3', str(self.script), str(self.output)], text=True,
        ))

    def test_records_submodule_and_resolved_archives_without_lock(self):
        result = self.manifest()
        self.assertEqual(result['sources']['buildroot'], {
            'url': 'https://example.invalid/buildroot.git',
            'commit': self.git(self.br, 'rev-parse', 'HEAD'),
            'dirty': False,
        })
        self.assertEqual(set(result['sources']), {'buildroot', 'linux', 'opensbi'})
        for name, archive in self.archives.items():
            self.assertEqual(result['sources'][name], {'archive': archive})
        self.assertFalse(result['integration_dirty'])
        self.assertEqual(result['artifact_sha256']['Image'],
                         hashlib.sha256(b'kernel fixture').hexdigest())
        for name, expected in result['config_sha256'].items():
            data = (self.output / 'images' / f'{name}.config').read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_records_actual_submodule_revision_and_local_changes(self):
        (self.br / 'README').write_text('Updated Buildroot fixture\n')
        self.git(self.br, 'commit', '-qam', 'Update Buildroot')
        result = self.manifest()
        self.assertEqual(result['sources']['buildroot']['commit'],
                         self.git(self.br, 'rev-parse', 'HEAD'))
        self.assertFalse(result['sources']['buildroot']['dirty'])
        self.assertTrue(result['integration_dirty'])
        (self.br / 'README').write_text('Uncommitted changes\n')
        self.assertTrue(self.manifest()['sources']['buildroot']['dirty'])


if __name__ == '__main__':
    unittest.main()
