
# import pytest
from __future__ import with_statement
import json, os, pytest, shutil, pdb
from io import StringIO

from . import Tempfiles
import ejsonschema.validate as val
import ejsonschema.schemaloader as loader
from ejsonschema.instance import DEF_EXTSCHEMAS

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

def test_extschema2():
    # This test is equivalent to test_extschema() except that it uses
    # SchemaValidator to create the validater
    # 
    validator = val.SchemaValidator()
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
        with pytest.raises(val.RefResolutionError):
            validator.validate_file(enh_json_schema, False, True)

        # This specifically tests the use of RefResolver
        with open(enh_json_schema) as fd:
            enh = json.load(fd)

        validator = val.ExtValidator()
        validator._schemaStore[enh['id']] = enh

        with pytest.raises(val.RefResolutionError):
            validator.validate_file(enh_json_schema, False, True)

    def test_strict(self, validator):
        probfile = os.path.join(datadir, "unresolvableref.json")

        # this should work
        validator.validate_file(probfile, False, False)

        # these should not
        with open(probfile) as fd:
            inst = json.load(fd)
        errs = validator.validate_against(inst, "urn:unresolvable.json", True)
        assert len(list(filter(lambda e: isinstance(e, val.RefResolutionError),errs))) > 0

        with pytest.raises(val.RefResolutionError):
            validator.validate(inst, False, True)

        with pytest.raises(val.RefResolutionError):
            validator.validate_file(probfile, False, True)


    def test_invalidextension(self):
        validator = val.ExtValidator.with_schema_dir(schemadir)
        probfile = os.path.join(datadir, "invalidextension.json")

        # this should work
        validator.validate_file(probfile, True, True)

        # these should not
        with open(probfile) as fd:
            inst = json.load(fd)
        errs = validator.validate_against(inst, inst[DEF_EXTSCHEMAS][0], True)
        assert len(list(filter(lambda e: isinstance(e, val.ValidationError),errs))) > 0

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
        errs = validator.validate_against(inst, [uri])
        assert len(list(filter(lambda e: isinstance(e, val.ValidationError),errs))) > 0

        inst["name"] = "bob"
        validator.load_schema(schema)
        errs = validator.validate_against(inst, [schema['id']])
        assert len(errs) == 0

def test_exc2json():
    validator = val.ExtValidator.with_schema_dir(schemadir)
    probfile = os.path.join(datadir, "invalidextension.json")

    errs = validator.validate_file(probfile, False, True, False)
    assert len(errs) == 2

    data = [val.exc_to_json(err) for err in errs]
    assert len(data) == 2
    assert len(list(filter(lambda e: e['message'], data))) == 2
    assert len(list(filter(lambda e: e['type'], data))) == 2
    assert len(list(filter(lambda e: e['type'] == 'validation', data))) == 2
    assert len(list(filter(lambda e: e['path'], data))) == 2
    assert len(list(filter(lambda e: e['validator'], data))) == 2


        
        
