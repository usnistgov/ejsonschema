
# import pytest
from __future__ import with_statement
import json, os, pytest, shutil
from cStringIO import StringIO

from . import Tempfiles
import ejsonschema.validate as val
import ejsonschema.schemaloader as loader

from .config import schema_dir as schemadir, data_dir as datadir, \
                    examples_dir as exdir
enh_json_schema = os.path.join(schemadir, "enhanced-json-schema.json")
ipr_ex = os.path.join(exdir, "ipr.json")

@pytest.fixture(scope="module")
def validator(request):
    return val.ExtValidator.with_schema_dir(exdir)

def test_ipr(validator):
    # borrowed from test_examples.py, this test exercises most of the features
    # of the validator module.  If the ipr.json example breaks, this breaks.
    # Features exercised include:
    #   * initializing a validator with resolver using SchemaHandler
    #   * resolving $refs via schemas on disk (not quite)
    #   * extension schema validation
    #   * initiating validation on a filename
    #
    validator.validate_file(ipr_ex, False, False)

def test_extschema():
    # borrowed from test_schemas.py, this test exercises most of the features
    # of the validator module.  If the ipr.json example breaks, this breaks.
    #   * initializing a validator with resolver using SchemaHandler
    #   * resolving $refs via schemas on disk
    #   * extension schema validation
    #   * initiating validation on a filename
    # 
    validator = val.ExtValidator.with_schema_dir(schemadir)
    validator.validate_file(enh_json_schema, False, True)

class TestExtValidator(object):

    def test_isextschemaschema(self, validator):
        with open(enh_json_schema) as fd:
            assert validator.is_extschema_schema(json.load(fd))

        with open(ipr_ex) as fd:
            assert not validator.is_extschema_schema(json.load(fd))

    def test_usesloader(self):
        # ...by testing lack of loader
        validator = val.ExtValidator()
        with pytest.raises(val.SchemaError):
            validator.validate_file(enh_json_schema, False, True)

        # This specifically tests the use of RefResolver
        with open(enh_json_schema) as fd:
            enh = json.load(fd)

        validator = val.ExtValidator()
        validator._schemaStore[enh['id']] = enh

        with pytest.raises(val.SchemaError):
            validator.validate_file(enh_json_schema, False, True)

    def test_strict(self, validator):
        probfile = os.path.join(datadir, "unresolvableref.json")

        # this should work
        validator.validate_file(probfile, False, False)

        # these should not
        with open(probfile) as fd:
            inst = json.load(fd)
        with pytest.raises(val.SchemaError):
            validator.validate_against(inst, "urn:unresolvable.json", True)

        with pytest.raises(val.SchemaError):
            validator.validate(inst, False, True)

        with pytest.raises(val.SchemaError):
            validator.validate_file(probfile, False, True)


    def test_invalidextension(self):
        validator = val.ExtValidator.with_schema_dir(schemadir)
        probfile = os.path.join(datadir, "invalidextension.json")

        # this should work
        validator.validate_file(probfile, True, True)

        # these should not
        with open(probfile) as fd:
            inst = json.load(fd)
        with pytest.raises(val.ValidationError):
            validator.validate_against(inst, inst[val.EXTSCHEMAS][0], True)

        with pytest.raises(val.ValidationError):
            validator.validate(inst, False, True)

        with pytest.raises(val.ValidationError):
            validator.validate_file(probfile, False, True)

    def test_loadschema(self, validator):
        schema = {
            "type": "object",
            "properties": {
                "name": { "type": "string" }
            },
            "id": "urn:gurn"
        }
        inst = { "name": "Bob" }
        uri = "urn:goob"

        assert uri not in validator._schemaStore
        assert schema['id'] not in validator._schemaStore

        validator.load_schema(schema, uri)
        validator.validate_against(inst, [uri])

        inst["name"] = 3
        with pytest.raises(val.ValidationError):
            validator.validate_against(inst, [uri])

        inst["name"] = "bob"
        validator.load_schema(schema)
        validator.validate_against(inst, [schema['id']])
