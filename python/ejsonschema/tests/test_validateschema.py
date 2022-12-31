"""
This suite tests the validation of schemas that use the enhanced documentation.
"""
# import pytest
from __future__ import with_statement
import json, os, pytest, shutil
import jsonschema as jsch
from io import StringIO

from . import Tempfiles
import ejsonschema.validate as val
import ejsonschema.schemaloader as loader

from .config import schema_dir as schemadir, data_dir as datadir
enh_json_schema = os.path.join(schemadir, "enhanced-json-schema-v0.1.json")

@pytest.fixture(scope="module")
def validator(request):
    return val.ExtValidator.with_schema_dir(schemadir)

schemashell = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$extensionSchemas": [ "https://data.nist.gov/od/dm/enhanced-json-schema/v0.1#" ],
    "id": "urn:goob"
}

def test_NotesType(validator):
    schema = schemashell.copy()
    schema['id'] = "urn:notes"
    schema["type"] = "object"
    schema["properties"] = {
        "sayings": {
            "$ref": "https://data.nist.gov/od/dm/enhanced-json-schema/v0.1#/definitions/Notes"
        }
    }
    validator.load_schema(schema)

    inst = {
        "sayings": [ "Hello", "world" ]
    }
    validator.validate_against(inst, [schema['id']])

    inst['sayings'] = "Hello"
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    
def test_DocumentationType(validator):
    schema = schemashell.copy()
    schema['$ref'] = "https://data.nist.gov/od/dm/enhanced-json-schema/v0.1#/definitions/Documentation"
    schema['id'] = "urn:doc"
    validator.load_schema(schema)

    inst = {
        "description": "the def",
        "notes": [ "1", "2" ],
        "comments": [ "yes", "no" ],
        "equivalentTo": "http://schema.org/email",
    }

    validator.validate_against(inst, [schema['id']])

    inst["notes"] = "1, 2"
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["notes"] = [ "1", "2" ]
    validator.validate_against(inst, [schema['id']])

    inst["comments"] = [ 1, 2 ]
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["comments"] = [ "yes", "no" ]
    assert len(validator.validate_against(inst, [schema['id']])) == 0

    inst["description"] = [ "the def" ]
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["description"] = "the def"
    assert len(validator.validate_against(inst, [schema['id']])) == 0

def test_oldschemauri(validator):
    """
    test that we can validate schemas that reference deprecated URIs for the 
    ejsonschema schema.  As long as the deprecated URI has an entry in the 
    [schema_dir]/schemaLocation.json file, it should work.  
    """
    schema = schemashell.copy()
    schema["$extensionSchemas"] = [ "https://www.nist.gov/od/dm/enhanced-json-schema/v0.1#" ]
    schema['$ref'] = "https://www.nist.gov/od/dm/enhanced-json-schema/v0.1#/definitions/Documentation"
    schema['id'] = "urn:doc"

    validator.validate(schema, strict=True)
    
    schema["$extensionSchemas"] = [ "https://goober.nist.gov/od/dm/enhanced-json-schema/v0.1#" ]
    with pytest.raises(val.MissingSchemaDocument):
        validator.validate(schema, strict=True)
    
def test_PropDocumentationType(validator):
    schema = schemashell.copy()
    schema['$ref'] = "https://data.nist.gov/od/dm/enhanced-json-schema/v0.1#/definitions/PropertyDocumentation"
    schema['id'] = "urn:propdoc"
    validator.load_schema(schema)

    inst = {
        "description": "the def",
        "notes": [ "1", "2" ],
        "comments": [ "yes", "no" ],
        "equivalentTo": "http://schema.org/email",
        "valueDocumentation": {
            "Funder": {
                "description": "someone who funds the project",
                "notes": [ "yes", "no" ]
            },
            "Manager": {
                "description": "someone who manages the project",
                "comments": [ "up", "down" ]
            }
        }
    }

    validator.validate_against(inst, [schema['id']])

    inst["notes"] = "1, 2"
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["notes"] = [ "1", "2" ]
    assert len(validator.validate_against(inst, [schema['id']])) == 0

    inst["comments"] = [ 1, 2 ]
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["comments"] = [ "yes", "no" ]
    assert len(validator.validate_against(inst, [schema['id']])) == 0

    inst["description"] = [ "the def" ]
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["description"] = "the def"
    assert len(validator.validate_against(inst, [schema['id']])) == 0

    inst["valueDocumentation"]["Manager"]["comments"] = [ 1, 2 ]
    errors = validator.validate_against(inst, [schema['id']])
    assert all( [isinstance(e, val.ValidationError) for e in errors] )
    inst["valueDocumentation"]["Manager"]["comments"] = [ "1", "2" ]
    assert len(validator.validate_against(inst, [schema['id']])) == 0

    
def test_topdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['notes'] = [ "yes", "no" ]
    validator.validate(schema, strict=True)
    schema['notes'] = "yes, no" 
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
def test_definitiondoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['definitions'] = {
        "Name": {
            "type": "string",
            "notes": [ "yes", "no" ]
        }
    }
    validator.validate(schema, strict=True)
    schema['definitions']['Name']['notes'] = "yes, no" 
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema['definitions']['Name']['notes'] = [ "yes", "no" ]
    schema['definitions']['Name']['valueDocumentation'] = {
        "@God": {
            "description": "refers to the one deity",
            "notes": [ "not to be confused with Eric Clapton" ]
        }
    }
    validator.validate(schema, strict=True)
    schema['definitions']['Name']['valueDocumentation']['@God']['notes'] = \
        "not to be confused with Eric Clapton"
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
def test_propdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['type'] = "object"
    schema['properties'] = {
        "name": {
            "type": "string",
            "notes": [ "yes", "no" ]
        }
    }
    validator.validate(schema, strict=True)
    schema['properties']['name']['notes'] = "yes, no" 
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema['properties']['name']['notes'] = [ "yes", "no" ]

    schema["definitions"] = {
        "Organization": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "notes": [ "not too long, please" ]
                }
            }
        }
    }
    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["properties"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
def test_addpropdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['type'] = "object"
    schema['additionalProperties'] = {
        "type": "string",
        "notes": [ "not too long, please" ]
    }
    validator.validate(schema, strict=True)
    schema["additionalProperties"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["additionalProperties"]["notes"] = [ "hey" ]
    
    schema["definitions"] = {
        "Organization": {
            "type": "object",
            "additionalProperties": {
                "type": "string",
                "notes": [ "not too long, please" ]
            }
        }
    }
    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["additionalProperties"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
    
def test_patpropdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['type'] = "object"
    schema['patternProperties'] = {
        "proto_.*": {
            "type": "string",
            "notes": [ "not too long, please" ]
        }
    }
    validator.validate(schema, strict=True)
    schema["patternProperties"]["proto_.*"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["patternProperties"]["proto_.*"]["notes"] = [ "hey" ]
    
    schema["definitions"] = {
        "Organization": {
            "type": "object",
            "patternProperties": {
                "neo_.*": {
                    "type": "string",
                    "notes": [ "not too long, please" ]
                }
            }
        }
    }
    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["patternProperties"]["neo_.*"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
    
def test_depdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema['type'] = "object"
    schema['properties'] = {
        "name": {
            "type": "string",
            "notes": [ "not too long, please" ]
        },
        "number": {
            "type": "string",
        }
    }
    schema["dependencies"] = {
        "name": {
            "notes": [ "a name requires a number" ],
            "required": ["number"]
        }
    }
    validator.validate(schema, strict=True)
    schema["dependencies"]["name"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["dependencies"]["name"]["notes"] = [ "hey" ]
    
    schema["definitions"] = {
        "Organization": {
            "type": "object",
            "properties": {
                "@id": {
                    "type": "string",
                    "notes": [ "not too long, please" ],
                    "format": "uri"
                },
                "@type": {
                    "type": "array"
                }
            },
            "dependencies": {
                "@id": {
                    "notes": [ "wow" ],
                    "properties": {
                        "@type": { "minLength": 2 }
                    }
                }
            }
        }
    }
    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["dependencies"]["@id"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    
    
def test_allofdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema["allOf"] = [
        {
            "type": "object",
            "notes": [ "when you need a string" ]
        },
        {
            "notes": [ "like and extension" ],
            "properties": {
                "flavor": { "type": "string" }
            }
        }
    ]

    validator.validate(schema, strict=True)
    schema["allOf"][1]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["allOf"][1]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
    schema["definitions"] = {
        "Organization": {
            "allOf": [
                {
                    "type": "array",
                    "notes": [ "base" ]
                },
                {
                    "maxLength": 5
                }
            ]
        }
    }

    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["allOf"][0]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["allOf"][0]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
def test_anyofdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema["anyOf"] = [
        {
            "type": "integer",
            "notes": [ "when you need a number" ]
        },
        {
            "notes": [ "like and extension" ],
            "type": "object",
            "properties": {
                "flavor": { "type": "string" }
            }
        }
    ]

    validator.validate(schema, strict=True)
    schema["anyOf"][1]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["anyOf"][1]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
    schema["definitions"] = {
        "Organization": {
            "anyOf": [
                {
                    "type": "array",
                    "notes": [ "base" ],
                    "maxLength": 5
                },
                {
                    "type": "string"
                }
            ]
        }
    }

    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["anyOf"][0]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["anyOf"][0]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
def test_oneofdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema["oneOf"] = [
        {
            "type": "integer",
            "notes": [ "when you need a number" ]
        },
        {
            "notes": [ "like and extension" ],
            "type": "object",
            "properties": {
                "flavor": { "type": "string" }
            }
        }
    ]

    validator.validate(schema, strict=True)
    schema["oneOf"][1]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["oneOf"][1]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
    schema["definitions"] = {
        "Organization": {
            "oneOf": [
                {
                    "type": "array",
                    "notes": [ "base" ],
                    "maxLength": 5
                },
                {
                    "type": "string"
                }
            ]
        }
    }

    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["oneOf"][0]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["oneOf"][0]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
def test_notdoc():
    schema = schemashell.copy();
    validator = val.ExtValidator.with_schema_dir(schemadir)

    schema["not"] = {
        "type": "integer",
        "notes": [ "when you can't have a number" ]
    }

    validator.validate(schema, strict=True)
    schema["not"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["not"]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
    schema["definitions"] = {
        "Organization": {
            "not": {
                "type": "array",
                "notes": [ "base" ],
            }
        }
    }

    validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["not"]["notes"] = 5
    with pytest.raises(val.ValidationError):
        validator.validate(schema, strict=True)
    schema["definitions"]["Organization"]["not"]["notes"] = [ "hey" ]
    validator.validate(schema, strict=True)
    
