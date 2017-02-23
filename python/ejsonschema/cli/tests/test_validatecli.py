# import pytest
from __future__ import with_statement
import json, os, sys, pytest, shutil, argparse
from cStringIO import StringIO

import ejsonschema.cli.validate as cli

from ...tests.config import schema_dir as schemadir, data_dir as datadir, \
                            examples_dir as exdir
enh_json_schema = os.path.join(schemadir, "enhanced-json-schema.json")
ipr_ex = os.path.join(exdir, "ipr.json")

class TstSys(object):
    def __init__(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.exc_info = sys.exc_info
        self.argv = [ "tstsys" ]
        self.exitcode = -1

    def exit(self, code):
        self.exitcode = code
        
@pytest.fixture
def tstsys():
    out = TstSys()
    argparse._sys = out
    def finalize():
        argparse._sys = sys

    return out

def test_opts(tstsys):
    parser = cli.define_opts("goob")

    assert parser.prog == "goob"
    parser.print_usage()
    assert "goob" in tstsys.stdout.getvalue()
    tstsys.stdout = StringIO()

    tstsys.argv[1:] = "-Z afile.json".split()
    parser.parse_args()
    assert tstsys.exitcode > 0
    tstsys.exitcode = -1

    tstsys.argv[1:] = "-S urn:zub -L schemadir -gCqs afile.json".split()
    opts = parser.parse_args()
    assert tstsys.exitcode < 0
    assert opts.silent
    assert opts.quiet
    assert opts.strict
    assert opts.minimal
    assert opts.docschema == "urn:zub"
    assert opts.loc == "schemadir"
    
def test_simple_valid(tstsys):

    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} {1}".format(schemadir, enh_json_schema).split()
    exit = app.execute()

    assert ": valid!" in tstsys.stdout.getvalue()
    assert not tstsys.stderr.getvalue()
    assert exit == 0

def test_load_ejs(tstsys):

    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-e {0}".format(enh_json_schema).split()
    exit = app.execute()

    assert ": valid!" in tstsys.stdout.getvalue()
    assert not tstsys.stderr.getvalue()
    assert exit == 0

def test_simple_invalid(tstsys):

    baddoc = os.path.join(datadir, "invalidextension.json")
    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} {1}".format(schemadir, baddoc).split()
    exit = app.execute()

    assert "3 is not of type" in tstsys.stderr.getvalue()
    assert ": not valid" in tstsys.stdout.getvalue()
    assert exit == 1

def test_cant_resolve(tstsys):

    #pytest.set_trace()
    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "{0}".format(enh_json_schema).split()
    exit = app.execute()

    assert "Unable to find schema document" in tstsys.stderr.getvalue()
    assert ": not valid" in tstsys.stdout.getvalue()
    assert exit == 2

def test_ignore_ext(tstsys):

    baddoc = os.path.join(datadir, "invalidextension.json")
    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} -g {1}".format(schemadir, baddoc).split()
    exit = app.execute()

    assert ": valid!" in tstsys.stdout.getvalue()
    assert not tstsys.stderr.getvalue()
    assert exit == 0

def test_strict(tstsys):

    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} {1}".format(exdir, ipr_ex).split()
    exit = app.execute()

    assert ": valid!" in tstsys.stdout.getvalue()
    assert not tstsys.stderr.getvalue()
    assert exit == 0

    tstsys.stdout = StringIO()
    tstsys.stderr = StringIO()

    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} -C {1}".format(exdir, ipr_ex).split()
    exit = app.execute()

    assert "Unable to find schema document" in tstsys.stderr.getvalue()
    assert ": not valid" in tstsys.stdout.getvalue()
    assert exit == 2

def test_schema_override(tstsys):

    app = cli.Validate("goob", tstsys.stdout, tstsys.stderr)
    tstsys.argv[1:] = "-L {0} -S urn:gurn {1}".format(exdir, ipr_ex).split()
    exit = app.execute()

    assert "Unable to find schema document" in tstsys.stderr.getvalue()
    assert ": not valid" in tstsys.stdout.getvalue()
    assert exit == 2
    
