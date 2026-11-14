#!/usr/bin/env python3
"""Run a boot command with a wall-clock timeout and require guest test markers."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--timeout', type=float, default=120)
parser.add_argument('--log', type=Path, required=True)
parser.add_argument('--marker', default='FUXI_LINUX_SMOKE_PASS')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()

command = args.command
if command and command[0] == '--':
    command = command[1:]
if not command:
    parser.error('a command is required after --')

args.log.parent.mkdir(parents=True, exist_ok=True)
start = time.monotonic()

with args.log.open('wb') as log:
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        code = proc.wait(timeout=args.timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            signal_group(proc.pid, signal.SIGINT)
            proc.wait(timeout=10)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            pass
        finally:
            # A second interrupt ends the grace period; further interrupts must
            # not interrupt forced cleanup or leave the direct child unreaped.
            previous_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                # Descendants can outlive the group leader even after wait().
                signal_group(proc.pid, signal.SIGKILL)
                proc.wait()
            finally:
                signal.signal(signal.SIGINT, previous_handler)
        print(f'Boot interrupted or timed out; see {args.log}', file=sys.stderr)
        sys.exit(124)

text = args.log.read_text(errors='replace')
print(text, end='')
if code != 0 or args.marker not in text or 'FUXI_LINUX_SMOKE_FAIL' in text:
    print(f'Boot failed (exit {code}, marker present: {args.marker in text}); see {args.log}', file=sys.stderr)
    sys.exit(1)

print(f'PASS: guest tests and clean exit, {time.monotonic() - start:.2f}s; log: {args.log}')
