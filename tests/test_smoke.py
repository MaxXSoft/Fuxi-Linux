"""Check smoke results and process-group cleanup with small host processes."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/smoke.py'


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fuxi smoke ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'boot.log'
        self.leader_pid = self.root / 'leader.pid'
        self.proc = None
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        if self.leader_pid.is_file():
            with contextlib.suppress(ProcessLookupError):
                os.killpg(int(self.leader_pid.read_text()), signal.SIGKILL)
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.kill()
            self.proc.communicate(timeout=5)

    def command(self, code, *args, timeout=30):
        return [sys.executable, str(SCRIPT), '--timeout', str(timeout),
                '--log', str(self.log), '--', sys.executable, '-c', code,
                *map(str, args)]

    def launch(self, code, *args, timeout=30):
        self.proc = subprocess.Popen(
            self.command(code, *args, timeout=timeout),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def wait_for_file(self, path):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.is_file() and path.read_text():
                return path.read_text()
            if self.proc.poll() is not None:
                self.fail(f'Smoke exited before {path.name}: {self.proc.communicate()}')
            time.sleep(0.01)
        self.fail(f'Timed out waiting for {path.name}')

    def assert_stopped(self, pid):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'stat='],
                text=True, capture_output=True, check=False, timeout=5,
            )
            state = result.stdout.strip()
            # An orphan may remain a zombie until the host's init reaps it.
            if not state or state.startswith('Z'):
                return
            time.sleep(0.01)
        self.fail(f'Process {pid} is still running: {state}')

    def assert_interrupted(self):
        _, stderr = self.proc.communicate(timeout=5)
        self.assertEqual(self.proc.returncode, 124, stderr)
        self.assertIn('Boot interrupted or timed out;', stderr)
        self.assertNotIn('Traceback', stderr)

    def test_timeout_kills_descendants_after_leader_exits(self):
        child_pid = self.root / 'child.pid'
        child_code = (
            'import os, pathlib, signal, sys, time\n'
            'signal.signal(signal.SIGINT, signal.SIG_IGN)\n'
            'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n'
            'time.sleep(60)\n'
        )
        self.launch(
            'import os, pathlib, signal, subprocess, sys\n'
            'signal.signal(signal.SIGINT, lambda *args: sys.exit(0))\n'
            'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n'
            'child = subprocess.Popen([sys.executable, "-c", sys.argv[3], sys.argv[2]])\n'
            'child.wait()\n',
            self.leader_pid, child_pid, child_code, timeout=3,
        )
        leader = int(self.wait_for_file(self.leader_pid))
        child = int(self.wait_for_file(child_pid))
        self.assert_interrupted()
        self.assert_stopped(leader)
        self.assert_stopped(child)

    def test_second_interrupt_forces_cleanup(self):
        interrupted = self.root / 'interrupted'
        self.launch(
            'import os, pathlib, signal, sys, time\n'
            'signal.signal(signal.SIGINT, lambda *args: pathlib.Path(sys.argv[2]).write_text("INT"))\n'
            'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n'
            'time.sleep(60)\n',
            self.leader_pid, interrupted,
        )
        leader = int(self.wait_for_file(self.leader_pid))
        self.proc.send_signal(signal.SIGINT)
        self.wait_for_file(interrupted)
        self.proc.send_signal(signal.SIGINT)
        self.assert_interrupted()
        self.assert_stopped(leader)

    def test_process_group_disappearing_during_cleanup_is_harmless(self):
        for signals, waits in [
            ([ProcessLookupError(), ProcessLookupError()],
             [subprocess.TimeoutExpired('fixture', 1), 0, 0]),
            ([None, ProcessLookupError()],
             [subprocess.TimeoutExpired('fixture', 1),
              subprocess.TimeoutExpired('fixture', 10), 0]),
        ]:
            with self.subTest(signals=signals):
                proc = Mock(pid=123456789)
                proc.wait.side_effect = waits
                stderr = io.StringIO()
                argv = ['smoke.py', '--log', str(self.log), '--', 'fixture']
                with patch.object(sys, 'argv', argv), \
                        patch('subprocess.Popen', return_value=proc), \
                        patch('os.killpg', side_effect=signals), \
                        contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        runpy.run_path(str(SCRIPT), run_name='__main__')
                self.assertEqual(raised.exception.code, 124)
                self.assertIn('Boot interrupted or timed out;', stderr.getvalue())

    def test_normal_exit_still_requires_success_markers(self):
        for output, code, expected in [
            ('FUXI_LINUX_SMOKE_PASS', 0, 0),
            ('FUXI_LINUX_SMOKE_PASS', 7, 1),
            ('no guest marker', 0, 1),
            ('FUXI_LINUX_SMOKE_PASS FUXI_LINUX_SMOKE_FAIL', 0, 1),
        ]:
            with self.subTest(output=output, code=code):
                result = subprocess.run(
                    self.command(f'import sys; print({output!r}); sys.exit({code})'),
                    text=True, capture_output=True, timeout=5,
                )
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == '__main__':
    unittest.main()
