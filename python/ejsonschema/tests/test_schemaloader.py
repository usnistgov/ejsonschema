# import pytest
from __future__ import with_statement
import json, os, pytest, shutil
from io import StringIO

from . import Tempfiles
import ejsonschema.schemaloader as loader

locs = {
  "uri:nist.gov/goober": "http://www.ivoa.net/xml/goober",
  "http://mgi.nist.gov/goof": "goof.xml"
}

from .config import schema_dir as schemadir, data_dir as datadir, \
                    examples_dir as exdir
schemafile = os.path.join(schemadir, 'enhanced-json-schema-v0.1.json')

class TestSchemaLoader(object):

    def test_ctor(self):
        ldr = loader.SchemaLoader()
        assert len(set(ldr.iterURIs())) == 0

        ldr = loader.SchemaLoader(locs)
        uris = set(ldr.iterURIs())
        assert len(uris) == 2
        assert "uri:nist.gov/goober" in uris
        assert "http://mgi.nist.gov/goof" in uris

    def test_locate(self):
        ldr = loader.SchemaLoader(locs)
        assert ldr.locate("uri:nist.gov/goober") == \
            "http://www.ivoa.net/xml/goober"
        assert ldr.locate("http://mgi.nist.gov/goof") == "goof.xml"
        with pytest.raises(KeyError):
            ldr.locate("ivo://ivoa.net/rofr")

    def test_add(self):
        ldr = loader.SchemaLoader()
        assert len(set(ldr.iterURIs())) == 0

        ldr.add_locations(locs)
        uris = set(ldr.iterURIs())
        assert len(uris) == 2
        assert ldr.locate("uri:nist.gov/goober") == \
            "http://www.ivoa.net/xml/goober"
        assert ldr.locate("http://mgi.nist.gov/goof") == "goof.xml"

        ldr = loader.SchemaLoader()
        ldr.add_location("uri:nist.gov/goober", "goober.json")
        assert len(set(ldr.iterURIs())) == 1
        assert ldr.locate("uri:nist.gov/goober") == "goober.json"
        ldr.add_location("http://mgi.nist.gov/goof", 
                         "http://www.ivoa.net/xml/goober")
        assert len(set(ldr.iterURIs())) == 2
        assert ldr.locate("http://mgi.nist.gov/goof") == \
            "http://www.ivoa.net/xml/goober"

    def test_load_schema(self):
        ldr = loader.SchemaLoader()
        ldr.add_location("uri:nist.gov/goober", schemafile)

        schema = ldr.load_schema("uri:nist.gov/goober")
        assert schema
        assert "$schema" in schema
        assert "id" in schema

    def test_call(self):
        ldr = loader.SchemaLoader()
        ldr.add_location("uri:nist.gov/goober", schemafile)

        schema = ldr("uri:nist.gov/goober")
        assert schema
        assert "$schema" in schema
        assert "id" in schema

    def test_from_locationfile(self):
        ldr = loader.SchemaLoader.from_location_file(
            os.path.join(schemadir, "schemaLocation.json"))
        assert len(ldr) >= 2
        assert ldr.locate("http://json-schema.org/draft-04/schema").endswith("/json-schema-draft04.json")

    def test_from_directory(self, schemafiles):
        sdir = os.path.join(schemafiles.parent, "schemas")
        locfile = os.path.join(sdir, loader.SCHEMA_LOCATION_FILE)
        if os.path.exists(locfile):
            os.remove(locfile)

        try:
            ldr = loader.SchemaLoader.from_directory(sdir)
            assert len(ldr) == 2
            assert ldr.locate("http://json-schema.org/draft-04/schema") == \
                os.path.join(sdir, "extern", "json-schema-draft04.json")
            assert not os.path.exists(locfile)

            ldr = loader.SchemaLoader.from_directory(sdir, True)
            assert len(ldr) == 2
            assert ldr.locate("http://json-schema.org/draft-04/schema") == \
                os.path.join(sdir, "extern", "json-schema-draft04.json")
            assert os.path.exists(locfile)
            os.remove(locfile)

            # pytest.set_trace()
            ldr = loader.SchemaLoader.from_directory(sdir, True, 
                                                     locfile="locations.json")
            assert len(ldr) == 2
            assert ldr.locate("http://json-schema.org/draft-04/schema") == \
                os.path.join(sdir, "extern", "json-schema-draft04.json")
            assert not os.path.exists(locfile)
            assert os.path.exists(os.path.join(sdir, "locations.json"))

            with open(os.path.join(sdir,"one.json"), "w") as fd:
                json.dump({ "http://json-schema.org/draft-04/schema": 
                            "json-schema-draft04.json" }, fd)
            assert os.path.exists(os.path.join(sdir,"one.json"))
            ldr = loader.SchemaLoader.from_directory(sdir, locfile="one.json")
            assert len(ldr) == 1
            assert ldr.locate("http://json-schema.org/draft-04/schema") == \
                os.path.join(sdir, "json-schema-draft04.json")
            assert not os.path.exists(os.path.join(sdir,"schemaLocation.json"))

        finally:
            if os.path.exists(locfile):
                os.remove(locfile)
            locfile = os.path.join(sdir, "locations.json")
            if os.path.exists(locfile):
                os.remove(locfile)
            locfile = os.path.join(sdir, "one.json")
            if os.path.exists(locfile):
                os.remove(locfile)

def test_schemaLoader_for_schemas():
    ldr = loader.schemaLoader_for_schemas()
    loc = ldr.locate("https://data.nist.gov/od/dm/enhanced-json-schema/v0.1")
    assert os.path.basename(loc) == "enhanced-json-schema-v0.1.json"
    assert os.path.exists(loc)
    loc = ldr.locate("http://json-schema.org/draft-04/schema")
    assert os.path.basename(loc) == "json-schema-draft04.json"
    assert os.path.exists(loc)

class TestSchemaHandler(object):

    def test_ctor(self):
        ldr = loader.SchemaHandler(loader.SchemaLoader())
        assert not ldr._strict

        ldr = loader.SchemaHandler(loader.SchemaLoader(locs))
        assert not ldr._strict

        ldr = loader.SchemaHandler(locs, True)
        assert ldr._strict

        ldr = loader.SchemaHandler(loader.SchemaLoader(locs), strict=False)
        assert not ldr._strict

    def test_compat(self):
        ldr = loader.SchemaLoader(locs)
        ldr.add_location("https://data.nist.gov/od/dm/enhanced-json-schema/v0.1", 
                         schemafile)
        hdlr = loader.SchemaHandler(ldr)

        assert "uri" in hdlr
        assert "http" in hdlr
        assert "https" in hdlr
        assert len(hdlr) == 3

        assert hdlr["uri"] is ldr
        assert hdlr["http"] is ldr
        assert hdlr["ftp"] is ldr  # not strict

        schema = hdlr["https"]("https://data.nist.gov/od/dm/enhanced-json-schema/v0.1")
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "id" in schema
        assert schema["id"] == "https://data.nist.gov/od/dm/enhanced-json-schema/v0.1"

    def test_strict(self):
        ldr = loader.SchemaLoader(locs)
        hdlr = loader.SchemaHandler(ldr, strict=True)
        assert hdlr["uri"] is ldr
        assert hdlr["http"] is ldr

        with pytest.raises(KeyError):
            assert hdlr["https"] is ldr 

@pytest.fixture(scope="module")
def schemafiles(request):
    tf = Tempfiles()
    schdir = tf.mkdir("schemas")
    extern = os.path.join(schdir,"extern")
    os.mkdir(extern)
    shutil.copy(os.path.join(exdir,"registry-resource_schema.json"), schdir)

    # this makes sure the schema finder is recursive
    shutil.copy(os.path.join(schemadir,"json-schema-draft04.json"), extern)

    # this ringer makes sure the schema finder can distinguish schema files from
    # arbitrary JSON data files
    shutil.copy(os.path.join(exdir,"ipr-2020-12.json"), schdir)

    def fin():
        tf.clean()
    request.addfinalizer(fin)
    return tf

class TestDirectorySchemaCache(object):

    def test_openfile(self, schemafiles):
        sfile = os.path.join(schemafiles.parent, "schemas",
                             "registry-resource_schema.json")
        assert os.path.exists(sfile)

        cache = loader.DirectorySchemaCache(schemafiles.parent)
        id, schema = cache.open_file(sfile)

        assert id == 'http://mgi.nist.gov/json/registry-resource/v0.1#'
        assert schema['id'] == id

    def test_openfile2(self, schemafiles):
        sfile = os.path.join(schemafiles.parent, "schemas", "extern",
                             "json-schema-draft04.json")
        assert os.path.exists(sfile)

        cache = loader.DirectorySchemaCache(schemafiles.parent)
        id, schema = cache.open_file(sfile)

        assert id == 'http://json-schema.org/draft-04/schema#'
        assert schema['id'] == id

    def test_locations(self, schemafiles):
        sdir = os.path.join(schemafiles.parent, "schemas")
        cache = loader.DirectorySchemaCache(sdir)
        loc = cache.locations()
        assert loc['http://json-schema.org/draft-04/schema'] == \
            os.path.join(sdir, "extern", "json-schema-draft04.json")
        assert loc['http://mgi.nist.gov/json/registry-resource/v0.1'] == \
            os.path.join(sdir, "registry-resource_schema.json")

    def test_locations_abs(self, schemafiles):
        sdir = os.path.join(schemafiles.parent, "schemas")
        cache = loader.DirectorySchemaCache(sdir)
        loc = cache.locations(True)
        assert loc['http://json-schema.org/draft-04/schema'] == \
            os.path.join(sdir, "extern", "json-schema-draft04.json")
        assert loc['http://mgi.nist.gov/json/registry-resource/v0.1'] == \
            os.path.join(sdir, "registry-resource_schema.json")
        assert len(loc) == 2

    def test_schemas(self, schemafiles):
        sdir = os.path.join(schemafiles.parent, "schemas")
        cache = loader.DirectorySchemaCache(sdir)
        loc = cache.schemas()
        assert loc['http://json-schema.org/draft-04/schema#']['id'] == \
            "http://json-schema.org/draft-04/schema#"
        assert loc['http://mgi.nist.gov/json/registry-resource/v0.1#']['id'] == \
            "http://mgi.nist.gov/json/registry-resource/v0.1#"

    def test_openfile_fileid(self):
        cache = loader.DirectorySchemaCache(datadir)
        (id, schema) = cache.open_file("noid_schema.json")
        assert id == "file://" + os.path.join(datadir, "noid_schema.json")

    def test_notaschema(self):
        cache = loader.DirectorySchemaCache(datadir)
        with pytest.raises(loader.DirectorySchemaCache.NotASchemaError):
            cache.open_file("loc.json")

    def test_locs_nota(self):
        cache = loader.DirectorySchemaCache(datadir)
        loc = cache.locations()
        assert "file://" + os.path.join(datadir, "noid_schema.json") in loc
        assert len(loc) == 2

    def test_save(self, schemafiles):
        sdir = os.path.join(schemafiles.parent, "schemas")
        slfile = os.path.join(sdir,"schemaLocation.json")
        if os.path.exists(slfile):
            os.remove(slfile)
        assert not os.path.exists(slfile)

        cache = loader.DirectorySchemaCache(sdir)
        cache.save_locations()

        assert os.path.exists(slfile)
        with open(slfile) as fd:
            loc = json.load(fd)
        assert loc['http://json-schema.org/draft-04/schema'] == \
            os.path.join("extern", "json-schema-draft04.json")
        assert loc['http://mgi.nist.gov/json/registry-resource/v0.1'] == \
            "registry-resource_schema.json"

    def test_save_abs(self, schemafiles):
        slfile = os.path.join(schemafiles.parent, "locations.json")
        if os.path.exists(slfile):
            os.remove(slfile)
        assert not os.path.exists(slfile)

        try:
            cache = loader.DirectorySchemaCache(datadir)
            cache.save_locations(slfile, True)

            assert os.path.exists(slfile)
            with open(slfile) as fd:
                loc = json.load(fd)
            assert loc['file://'+os.path.join(datadir,"noid_schema.json")] == \
                os.path.join(datadir, "noid_schema.json")
            assert len(loc) == 2
        finally:
            if os.path.exists(slfile):
                os.remove(slfile)
        
    def test_recursive(self, schemafiles):
        sdir = schemafiles("schemas")
        cache = loader.DirectorySchemaCache(sdir)

        locs = cache.locations()
        assert len(locs) == 2

        locs = cache.locations(recursive=False)
        assert len(locs) == 1
