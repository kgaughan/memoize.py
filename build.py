import sys
import os
import os.path
from memoize import memoize

objs = []
doopt = False
doclean = False

def run(cmd):
    if not doclean:
        status = memoize(cmd)
        if status:
            print >>sys.stderr, '*** FAILURE ***'
            sys.exit(status)

def mlfile(fname):
    global objs
    (base, suffix) = fname.rsplit('.', 1)
    (dir, prefix) = os.path.split(base)

    if suffix == 'mli':
        obj = 'obj/' + prefix + '.cmi'
        run('ocamlc -c -I obj -o %s %s' % (obj, fname))
        if doclean: objs.append(obj)
    elif suffix == 'ml':
        if doopt:
            obj = 'obj/' + prefix + '.cmx'
            run('ocamlopt -c -I obj -o %s %s' % (obj, fname))
        else:
            obj = 'obj/' + prefix + '.cmo'
            run('ocamlc -c -I obj -o %s %s' % (obj, fname))
        objs.append(obj)
    else:
        if not doclean: objs.append(fname)

def elkfile(fname): mlfile('elkhoundlib/' + fname)

def libfile(libname):
    if doopt: mlfile(libname + '.cmxa')
    else: mlfile(libname + '.cma')

def clean(files):
    print 'rm -f', files
    os.system('rm -f ' + files)

def build(opt, cln):
    global doopt, doclean, objs

    doopt = opt
    doclean = cln
    objs = []

    libfile('unix')
    libfile('str')

    elkfile('arraystack.ml')
    elkfile('objpool.ml')
    elkfile('useract.ml')
    elkfile('lexerint.ml')
    elkfile('parsetables.ml')
    elkfile('smutil.ml')
    elkfile('glr.ml')
    elkfile('ptreenode.ml')
    elkfile('ptreeact.ml')

    mlfile('pretty.mli')
    mlfile('pretty.ml')
    mlfile('range_list.ml')
    mlfile('cabs.ml')
    mlfile('atnode.ml')
    mlfile('errormsg.mli')
    mlfile('errormsg.ml')
    mlfile('tokens.ml')
    if doclean:
        clean('obj/clexer.ml obj/clexer.mli')
    else:
        run('ocamllex -o obj/clexer.ml clexer.mll')
        run('cp clexer.mli obj')
    mlfile('obj/clexer.mli')
    mlfile('obj/clexer.ml')

    if doclean: clean('obj/cparser.ml')
    else: run('elkhound -ocaml -o obj/cparser cparser.gr; rm obj/cparser.mli')

    if opt:
        run("""bash -c 'export OCAMLRUNPARAM="l=2M";
               ocamlopt -c -I obj -o obj/cparser.cmx obj/cparser.ml'""")
        if doclean: clean('obj/cparser.cmx')
        mlfile('obj/cparser.cmx')
    else:
        run("""bash -c 'export OCAMLRUNPARAM="l=2M";
               ocamlc -c -I obj -o obj/cparser.cmo obj/cparser.ml'""")
        if doclean: clean('obj/cparser.cmo')
        mlfile('obj/cparser.cmo')

    mlfile('cprint.ml')
    mlfile('tokeninfo.ml')
    mlfile('cparsing.ml')
    mlfile('eval.ml')
    mlfile('trace.mli')
    mlfile('trace.ml')
    mlfile('cabsvisit.mli')
    mlfile('cabsvisit.ml')
    mlfile('visitor.mli')
    mlfile('visitor.ml')
    mlfile('sexp.ml')
    mlfile('globals.ml')
    mlfile('options.ml')
    mlfile('cabsextra.ml')
    mlfile('cabsunparse.ml')
    mlfile('resolve.ml')
    mlfile('checker.ml')
    mlfile('expand.ml')
    mlfile('typeinf.ml')
    mlfile('refactor.ml')
    mlfile('equality.ml')
    mlfile('normalize.ml')
    mlfile('verify.ml')
    mlfile('main.ml')

try: arg = sys.argv[1]
except: arg = 'all'

if arg == 'byte' or arg == 'all':
    build(False, False)
    run('ocamlc -o astec -I obj %s' % ' '.join(objs))

if arg == 'opt' or arg == 'all':
    build(True, False)
    run('ocamlopt -o astec.opt -I obj %s' % ' '.join(objs))

if arg == 'clean':
    build(False, True)
    clean('%s' % ' '.join(objs))
    build(True, True)
    clean('%s' % ' '.join(objs))

print '*** Success ***'
