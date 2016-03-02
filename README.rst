Original at http://www.eecs.berkeley.edu/~billm/memoize.html

=======
Memoize
=======

Memoize is a replacement for make. It is designed to be simple and easy
to use.  Above all, it allows you to write build scripts in normal
languages like Python or the shell rather than forcing you to rely on
make's hopelessly recondite makefile language. Memoize takes advantage
of the fact that programmers are likely to be better versed in a
general-purpose scripting language than in make.

Limitation: Doesn't work in Windows (requires strace). Sorry Cygwinners.

Introduction
============

As an example, here is a simple shell script that uses memoize to build
a C program.

::

    #!/bin/sh
    memoize.py gcc -c file1.c
    memoize.py gcc -c file2.c
    memoize.py gcc -o program file1.o file2.o

Except for the addition of the `memoize.py` prefix, these are exactly
the commands you would type at the shell to compile the program
manually.  However, *the use of memoize ensures that no file will be
compiled unless it or something it depends on has changed*. This speeds
up builds tremendously for even medium-size projects, and it's what
makes make so useful.

It's also possible to write a build script in Python. Writing the script
in Python is particularly nice because memoize is itself written in
Python, so the interpreter only needs to be loaded once (rather than
once per command). This results in about a 5x to 10x speedup. Here is an
example Python build script.

::

    #!/usr/bin/env python
    import sys
    from memoize import memoize
    
    def run(cmd):
        status = memoize(cmd)
        if status: sys.exit(status)
    
    run('ocamllex x86lex.mll')
    run('ocamlyacc x86parse.mly')
    
    run('ocamlc -c x86parse.mli')
    run('ocamlc -c x86parse.ml')
    run('ocamlc -c x86lex.ml')
    run('ocamlc -c main.ml')
    run('ocamlc -o program x86parse.cmi x86parse.cmo x86lex.cmo main.cmo')

Unlike the shell script, this script checks the exit status of each
command and exits if the command fails. This is more like the typical
behavior of make, while the shell script behaved more like `make -k`.

Since this is Python, it's easy to make this script much fancier. We
could modify it to make it easier to specify input files, to allow input
files to be nested inside different directories, and to output object
files to a separate location. Much of this functionality is hard to get
right in make. Python makes this stuff easy, since it has good built-in
support for string processing and file handling.

As an example, `here <examples/build.py>`_ is an example build script used in a
real ocaml project. It builds source code from two directories and puts the
output in an `obj/` directory. It supports both the bytecode and the native
code compiler, and it has functionality analogous to `make clean`. It uses a
few Python functions that could be abstracted into a library, which is a good
way of writing these scripts.

In my experience, writing build scripts in a more imperative fashion is
easier than doing it declaratively. Declarative designs typically rely
on a restricted domain-specific language for expressing build rules
based on filename extensions and environment variables. These approaches
work fine when programs are simple, but they're usually hard to use when
any kind of out-of-the-ordinary functionality is needed. Although
imperative scripts (like the example in the previous paragraph) may seem
less elegant, they are very flexible and usually just as concise.

How It Works
============

The key to memoize is an algorithm that determines whether a command
actually needs to be run. Memoize assumes that given the same command
line options and the same input files, a program will always produce the
same output (this is typically true for compilers and other build
tools). When memoize is called with a command, it checks if it has run
that command before with the same options. If it has been, it determines
what input files were used by the command. If those files haven't
changed since the command was run, then there is no need to rerun it.

Deciding whether a file has changed is easy: memoize can either check
the modification time of the file, or it can compute an MD5 sum of the
file and see if it differs from the old value. The tricky part is
figuring out what input files were used by the command when it was run.
Memoize uses the `strace` command to do this. Strace is capable of
logging all the system calls made by a program. Memoize uses strace to
find all the open system calls made by a command. If a file is opened in
`O_RDONLY` or `O_RDWR` mode, and it is located in the directory tree
where the build started, then it is considered an input. (Other people
have proposed using strace in this way before, but I don't know of any
general-purpose implementations out there. I probably "borrowed" the
idea from someone else who had it first, but I can't remember who. If
it's you, I apologize.)

Memoize keeps a file called .deps in the build directory. For each
command that has already been run, it lists the input dependencies for
the command. For each dependency file, the modification time and MD5 sum
of the file at the time the command was executed are listed. When asked
to execute the command again, memoize checks the current version of the
inputs against the `.deps` file. It only reruns the command if they
don't match.

Download

You can download `memoize.py <memoize.py>`_ here. The software is under
the BSD license.

If you intend to use it from Python, you should put this file somewhere
in your `PYTHONPATH` so that it can be imported. Alternatively, you
could put it in the same directory as your build script. You could also
add the following lines to the top of the build script.

::

    #!/bin/sh
    import sys
    sys.path.append('...directory where memoize.py can be found...')
    import memoize

You can also use memoize from the command line. In that case, put it in
your shell `PATH`. You can optionally rename it to just `memoize`. This
is the preferred method if you don't intend to use Python.

Changelog
=========

* June 6, 2008. Incorporated bugfixes, extra flags, and documentation
  due to Ben Leslie. Thanks!
* June 2, 2008. Added support for commands that change to a different
  directory (as in a shell command using cd). Also added a BSD license.

Usage
=====

Using memoize is pretty simple. It only takes two command line options.
By default, it uses MD5 sums to check for changes. If you'd rather it
use access times, pass in the `-t` option before the command. There's
also a `-d dir` option that searches for input dependencies in other
directories. Normally, memoize ignores a dependency if it's not located
in some subdirectory of the current working directory.

Contact & Bug Reports
=====================

Please report bugs or feature requests to bill.mccloskey at gmail dot
com. Also, if you have any interesting build script libraries that might
be useful to other people, send them to me and I'll post them here.
