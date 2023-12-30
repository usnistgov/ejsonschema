# import pytest
from __future__ import with_statement
import json, os, pytest
from io import StringIO

import ejsonschema.location as location

jsonloc = """
{
  "uri:nist.gov/goober": "http://www.ivoa.net/xml/goober",
  "http://mgi.nist.gov/goof": "goof.xml"
}
"""

txtloc = """
# comment
uri:nist.gov/goober http://www.ivoa.net/xml/goober

http://mgi.nist.gov/goof goof.xml
"""
from .config import data_dir as datadir
jsonfile = os.path.join(datadir, "loc.json")
txtfile = os.path.join(datadir, "loc.txt")
deffile = os.path.join(datadir, "loc")

def test_parse_mappings_asjson():
    # fd = StringIO(jsonloc)
    with open(jsonfile) as fd:
      data = location.parse_mappings_asjson(fd)
      assert isinstance(data, dict)
      assert len(data) == 2
      assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
      assert data.get("http://mgi.nist.gov/goof") == "goof.xml"

def test_bad_parse_mappings_asjson():
    with open(txtfile) as fd:
        with pytest.raises(ValueError):
            data = location.parse_mappings_asjson(fd)

def test_parse_mappings_astxt():
    # fd = StringIO(txtloc)
    with open(txtfile) as fd:
      data = location.parse_mappings_astxt(fd)
      assert isinstance(data, dict)
      assert len(data) == 2
      assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
      assert data.get("http://mgi.nist.gov/goof") == "goof.xml"

def test_bad_parse_mappings_astxt():
    with open(jsonfile) as fd:
        with pytest.raises(ValueError):
            data = location.parse_mappings_astxt(fd)

class TestLocationReader(object):

    def test_ctor(self):
        rdr = location.LocationReader()
        assert rdr
        assert not rdr.baseurl
        assert rdr.deffmt == 'txt'
        assert rdr.parsers 
        assert 'json' in rdr.parsers and 'txt' in rdr.parsers

        rdr = location.LocationReader('/usr/local/etc')
        assert rdr
        assert rdr.baseurl == '/usr/local/etc'
        assert rdr.deffmt == 'txt'
        rdr = location.LocationReader(basedir='/usr/local/etc')
        assert rdr
        assert rdr.baseurl == '/usr/local/etc'
        assert rdr.deffmt == 'txt'

        parsers = dict(rdr.parsers)
        parsers['text'] = parsers['txt']

        rdr = location.LocationReader(None, parsers)
        assert rdr
        assert not rdr.baseurl
        assert rdr.parsers 
        assert 'json' in rdr.parsers and 'txt' in rdr.parsers \
           and 'text' in rdr.parsers 
        assert ('txt' in rdr.parsers) is ('text' in rdr.parsers)
        rdr = location.LocationReader(parsers=parsers)
        assert rdr
        assert not rdr.baseurl
        assert rdr.parsers 
        assert 'json' in rdr.parsers and 'txt' in rdr.parsers \
           and 'text' in rdr.parsers 
        assert ('txt' in rdr.parsers) is ('text' in rdr.parsers) 


    def test_read_json(self):
        rdr = location.LocationReader()

        data = rdr.read(jsonfile, fmt='json', basedir="")
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert os.path.basename(data.get("http://mgi.nist.gov/goof")) == "goof.xml"

        data = rdr.read(jsonfile, fmt='json', basedir="/etc")
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == "/etc/goof.xml"

        data = rdr.read(jsonfile, fmt='json')
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")


    def test_read_txt(self):
        rdr = location.LocationReader()

        data = rdr.read(txtfile, fmt='txt', basedir="")
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert os.path.basename(data.get("http://mgi.nist.gov/goof")) == "goof.xml"

        data = rdr.read(jsonfile, fmt='json', basedir="/etc")
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == "/etc/goof.xml"

        data = rdr.read(jsonfile, fmt='json')
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

    def test_read(self):
        rdr = location.LocationReader()

        data = rdr.read(txtfile)
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

        data = rdr.read(jsonfile)
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

        data = rdr.read(deffile)
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

    def test_read_bad_format(self):
        rdr = location.LocationReader()

        with pytest.raises(RuntimeError) as excinfo:
            data = rdr.read(txtfile, 'yaml')
        assert "Don't know how to parse location file of type 'yaml'" == \
            str(excinfo.value)

    def test_read_no_deffmt(self):
        rdr = location.LocationReader()
        rdr.deffmt = None

        with pytest.raises(RuntimeError) as excinfo:
            data = rdr.read(deffile)
        assert "No default parser set to apply to " in str(excinfo.value)


def test_read_loc_file():
        data = location.read_loc_file(txtfile)
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

        data = location.read_loc_file(jsonfile, "json")
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(datadir,"goof.xml")

        data = location.read_loc_file(deffile, basedir='.')
        assert data
        assert len(data) == 2
        assert data.get("uri:nist.gov/goober") == "http://www.ivoa.net/xml/goober"
        assert data.get("http://mgi.nist.gov/goof") == \
            os.path.join(os.getcwd(),"goof.xml")
