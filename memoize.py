#!/usr/bin/env python

import argparse
import cPickle
import hashlib
import logging
import os
import os.path
import re
import subprocess
import sys
import tempfile

from six.moves import shlex_quote


# If set, use modification time instead of MD5-sum as check
opt_use_modtime = False
opt_dirs = ['.']
hasher = hashlib.md5


SYS_CALLS = [
    "execve",
    "open", "openat", "access",
    "stat", "stat64", "lstat",
]


strace_re = re.compile(r"""
  (?: (?P<pid> \d+ ) \s+ ) ?
  (?:
      # Relevant syscalls
      (?P<syscall>""" + "|".join(SYS_CALLS) + r""")
      \( "
      (?P<filename> (?: \\" | [^"] )* )
      "
  |
      # Irrelevant syscalls
      (?: utimensat | statfs | mkdir )
      \(
  |
      # A continuation line
      <
  |
      # Signals
      ---
  |
      # Exit
      \+\+\+
  )
  .*
  """, re.VERBOSE)


def set_use_modtime(use):
    global opt_use_modtime
    opt_use_modtime = use


def add_relevant_dir(d):
    opt_dirs.append(d)


def hashsum(fname):
    if not os.path.isfile(fname):
        return None
    with open(fname, 'rb') as fh:
        return hasher(fh.read()).digest()


def modtime(fname):
    try:
        return os.path.getmtime(fname)
    except:
        return 'bad'


def files_up_to_date(files, test):
    for fname, value in files.iteritems():
        if test(fname) != value:
            logging.debug("Not up to date: %s", shlex_quote(fname))
            return False
    return True


def is_relevant(fname):
    path1 = os.path.abspath(fname)
    return any(path1.startswith(os.path.abspath(d))
               for d in opt_dirs)


def cmd_to_str(cmd):
    return " ".join(shlex_quote(arg) for arg in cmd)


def generate_deps(cmd, test):
    logging.info('Running: %s', cmd_to_str(cmd))

    outfile = os.path.join(tempfile.mkdtemp(), "pipe")
    os.mkfifo(outfile)
    # TODO: Detect solaris and use truss instead and verify parsing of its
    # output format
    trace_command = ['strace',
                     '-f', '-q',
                     '-e', 'trace=' + ','.join(SYS_CALLS),
                     '-o', outfile,
                     '--']
    trace_command.extend(cmd)
    p = subprocess.Popen(trace_command)

    files = {}
    for line in open(outfile):
        match = re.match(strace_re, line)

        if not match:
            logging.warning("Failed to parse this line: %s",
                            line.rstrip("\n"))
            continue
        if match.group("filename"):
            fname = os.path.normpath(match.group("filename"))
            if (fname not in files and os.path.isfile(fname) and
                    is_relevant(fname)):
                files[fname] = test(fname)

    status = p.wait()
    os.remove(outfile)

    return (status, files)


def read_deps(fname):
    try:
        with open(fname, 'rb') as fh:
            return cPickle.load(fh)
    except:
        return {}


def write_deps(fname, deps):
    with open(fname, 'wb') as fh:
        cPickle.dump(deps, fh)


def memoize_with_deps(depsname, deps, cmd):
    files = deps.get(cmd)
    test = modtime if opt_use_modtime else hashsum
    if not files or not files_up_to_date(files, test):
        status, files = generate_deps(cmd, test)
        if status == 0:
            deps[cmd] = files
        elif cmd in deps:
            del deps[cmd]
        write_deps(depsname, deps)
        return status
    logging.info('Up to date: %s', cmd_to_str(cmd))
    return 0


def memoize(cmd, depsname='.deps'):
    return memoize_with_deps(depsname, read_deps(depsname), cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Record a command's dependencies, skip if they did not change")
    parser.add_argument("command", nargs='+', help='The command to run')
    parser.add_argument("--use-hash", action='store_true')
    parser.add_argument("--no-use-hash", dest='use_hash', action='store_false')
    parser.add_argument("-d", "--relevant-dir", action='append', default=[])
    parser.add_argument("--verbose", action='store_true')
    parser.add_argument("--debug", action='store_true')
    parser.set_defaults(use_hash=True)

    args = parser.parse_args()

    cmd = tuple(args.command)
    set_use_modtime(not args.use_hash)
    for relevant_dir in args.relevant_dir:
        add_relevant_dir(relevant_dir)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)

    return memoize(cmd)


if __name__ == '__main__':
    sys.exit(main())
