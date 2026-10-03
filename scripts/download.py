#!/usr/bin/env python3
"""curl transport for Buildroot's wget backend, including optional SOCKS proxy."""
import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-q', action='store_true')
parser.add_argument('-O', required=True, dest='output')
parser.add_argument('url')
args = parser.parse_args()
command = ['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '15']
if args.q:
    command.extend(['--silent', '--show-error'])
if os.environ.get('FUXI_PROXY'):
    command.extend(['--proxy', os.environ['FUXI_PROXY']])
command.extend(['--output', args.output, args.url])
sys.exit(subprocess.call(command))
