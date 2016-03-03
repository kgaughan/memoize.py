#!/usr/bin/python
from __future__ import print_function

import cPickle
from getopt import getopt
import md5
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
    opt_use_modtime = use


def add_relevant_dir(d):
    opt_dirs.append(d)


def md5sum(fname):
    try:
        data = open(fname).read()
    except:
        data = None

    if data is None:
        return 'bad'
    return md5.new(data).hexdigest()


def modtime(fname):
    try:
        return os.path.getmtime(fname)
    except:
        return 'bad'


def files_up_to_date(files):
    for (fname, md5, mtime) in files:
        if opt_use_modtime:
            if modtime(fname) != mtime:
                return False
        else:
            if md5sum(fname) != md5:
                return False
    return True


def is_relevant(fname):
    path1 = os.path.abspath(fname)
    for d in opt_dirs:
        path2 = os.path.abspath(d)
        if path1.startswith(path2):
            return True
    return False


def generate_deps(cmd):
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

    status = 0
    files = []
    files_dict = {}
    for line in output:
        match = re.match(strace_re, line)

        if not match:
            print("WARNING: failed to parse this line: " + line.rstrip("\n"),
                  file=sys.stderr)
            continue
        if not match.group("filename"):
            continue

        fname = os.path.normpath(match.group("filename"))
        if (is_relevant(fname) and os.path.isfile(fname)
                and fname not in files_dict):
            files.append((fname, md5sum(fname), modtime(fname)))
            files_dict[fname] = True

    return (status, files)


def read_deps(depsname):
    try:
        f = open(depsname, 'rb')
    except:
        f = None

    if f:
        deps = cPickle.load(f)
        f.close()
        return deps
    else:
        return {}


def write_deps(depsname, deps):
    f = open(depsname, 'wb')
    cPickle.dump(deps, f)
    f.close()


def memoize_with_deps(depsname, deps, cmd):
    files = deps.get(cmd, [('aaa', '', '')])
    if not files_up_to_date(files):
        (status, files) = generate_deps(cmd)
        if status == 0:
            deps[cmd] = files
        elif cmd in deps:
            del deps[cmd]
        write_deps(depsname, deps)
        return status
    print('up to date:', cmd)
    return 0


default_depsname = '.deps'
default_deps = read_deps(default_depsname)


def memoize(cmd):
    return memoize_with_deps(default_depsname, default_deps, cmd)


if __name__ == '__main__':
    (opts, cmd) = getopt(sys.argv[1:], 'td:')
    cmd = tuple(cmd)
    for (opt, value) in opts:
        if opt == '-t':
            opt_use_modtime = True
        elif opt == '-d':
            opt_dirs.append(value)

    status = memoize(cmd)
    sys.exit(status)
