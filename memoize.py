#!/usr/bin/env python

from __future__ import print_function

import cPickle
import getopt
import hashlib
import os
import os.path
import re
import subprocess
import sys
import tempfile


# If set, use modification time instead of MD5-sum as check
opt_use_modtime = False
opt_dirs = ['.']


SYS_CALLS = [
    "execve",
    "open", "openat", "access",
    "stat", "stat64", "lstat", "statfs",
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
      (?: utimensat )
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


def md5sum(fname):
    try:
        with open(fname, 'rb') as fh:
            return hashlib.md5(fh.read()).hexdigest()
    except:
        return 'bad'


def modtime(fname):
    try:
        return os.path.getmtime(fname)
    except:
        return 'bad'


def files_up_to_date(files, test):
    return all(test(fname) != value
               for fname, value in files.iteritems())


def is_relevant(fname):
    path1 = os.path.abspath(fname)
    return any(path1.startswith(os.path.abspath(d))
               for d in opt_dirs)


def generate_deps(cmd, test):
    print('running', cmd)

    outfile = tempfile.mktemp()
    # TODO: Detect solaris and use truss instead and verify parsing of its
    # output format
    trace_command = ['strace',
                     '-f', '-q',
                     '-e', 'trace=' + ','.join(SYS_CALLS),
                     '-o', outfile,
                     '--']
    trace_command.extend(cmd)
    status = subprocess.call(trace_command)
    output = open(outfile).readlines()
    os.remove(outfile)

    files = {}
    for line in output:
        match = re.match(strace_re, line)

        if not match:
            print("WARNING: failed to parse this line: " + line.rstrip("\n"),
                  file=sys.stderr)
            continue
        if match.group("filename"):
            fname = os.path.normpath(match.group("filename"))
            if (fname not in files and os.path.isfile(fname) and
                    is_relevant(fname)):
                files[fname] = test(fname)

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
    files = deps.get(cmd, [('aaa', '')])
    test = modtime if opt_use_modtime else md5sum
    if not files_up_to_date(files, test):
        status, files = generate_deps(cmd, test)
        if status == 0:
            deps[cmd] = files
        elif cmd in deps:
            del deps[cmd]
        write_deps(depsname, deps)
        return status
    print('up to date:', cmd)
    return 0


def memoize(cmd, depsname='.deps'):
    return memoize_with_deps(depsname, read_deps(depsname), cmd)


def main():
    opts, cmd = getopt.getopt(sys.argv[1:], 'td:')
    cmd = tuple(cmd)
    for opt, value in opts:
        if opt == '-t':
            set_use_modtime(True)
        elif opt == '-d':
            add_relevant_dir(value)

    return memoize(cmd)


if __name__ == '__main__':
    sys.exit(main())
