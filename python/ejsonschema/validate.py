"""
a module that provides support for validating schemas that support 
extended json-schema tags.
"""
from __future__ import with_statement
import sys, os, types, json, urlparse
import jsonschema
import jsonschema.validators as jsch
from jsonschema.exceptions import (ValidationError, SchemaError, 
                                   RefResolutionError)

from . import schemaloader as loader
from .instance import Instance, EXTSCHEMAS

# These are URIs that identify versions of the JSON Enhanced Schema schem
EXTSCHEMA_URIS = [ "http://mgi.nist.gov/mgi-json-schema/v0.1",
                   "https://www.nist.gov/od/dm/enhanced-json-schema/v0.1" ]

class ExtValidator(object):
    """
    A validator that can validate an instance against multiple schemas
    """

    def __init__(self, schemaLoader=None):
        """
        initialize the validator for a set of expected schemas
        """
        if not schemaLoader:
            schemaLoader = loader.SchemaLoader()
        self._loader = schemaLoader
        self._handler = loader.SchemaHandler(schemaLoader)
        self._schemaStore = {}
        self._validators = {}

    @classmethod
    def with_schema_dir(self, dirpath):
        """
        Create an ExtValidator that leverages schema cached as files in a 
        directory.  

        Before creating the ExtValidator, this factory will establish use
        of the cache: first, it will look for a file in that directory called 
        schemaLocation.json to identify the available schemas.  If that file
        does not exist, all JSON files in that directory will examined to find
        JSON schemas.  From this list of schemas, a SchemaLoader instance will 
        be passed into the ExtValidator constructor.

        See the location module for more information about schema location 
        files.  See schemaloader.SchemaLoader for more information about 
        creating loaders for schema files on disk.  
        """
        return ExtValidator(loader.SchemaLoader.from_directory(dirpath))

    def load_schema(self, schema, uri=None):
        """
        load a pre-parsed schema into the validator.  The schema will be checked 
        for errors first and raise an exception if there is a problem.  If schema
        with the given ID was already loaded, it will get overriden.  

        :argument dict schema:  the parsed schema object.
        :argument str  uri:     The URI to associated with the schema.  If not 
                                 provided, the value of the "id" property will
                                 be used.  
        """
        if not uri:
            uri = schema.get('id')
        if not uri:
            raise ValueError("No id property found; set uri param instead.")

        # check the schema
        vcls = jsch.validator_for(schema)
        vcls.check_schema(schema)

        # now add it
        self._schemaStore[uri] = schema
        
        
    def validate(self, instance, minimally=False, strict=False, schemauri=None,
                 raiseex=True):
        """
        validate the instance document against its schema and its extensions
        as directed.  
        """
        baseSchema = schemauri
        if not baseSchema:
            baseSchema = instance.get("$schema")
        if not baseSchema:
            raise ValidationError("Base schema ($schema) not specified; " +
                                  "unable to validate")

        out = self.validate_against(instance, baseSchema, True)
        if raiseex and len(out) > 0:
            raise out[0]

        if not minimally:
            # we need to validate any portions including the EXTSCHEMAS property
            inst = Instance(instance)
            extensions = dict(inst.find_extended_objs())

            # If instance is actually an extension schema schema, we need to
            # ignore the definition of the EXTSCHEMAS property.
            is_extschema = self.is_extschema_schema(instance)
            
            for ptr in extensions:
                # make sure that the EXTSCHEMAS property is invoked properly
                if not isinstance(extensions[ptr][EXTSCHEMAS], list):
                    if not is_extschema or \
                       not isinstance(extensions[ptr][EXTSCHEMAS], dict):
                        msg = "invalid value type for {0} (not an array):\n     {1}"\
                              .format(EXTSCHEMAS, extensions[ptr][EXTSCHEMAS])
                        ex = ValidationError(msg, instance=extensions[ptr])
                        if raiseex:
                            raise ex
                        out.append(ex)
                        return out
                    else:
                        # this is the extension schema schema, so ignore this
                        # node
                        continue
                
                for val in extensions[ptr][EXTSCHEMAS]:
                    if not isinstance(val, types.StringTypes):
                        ex = ValidationError(
                                "invalid {0} array item type:\n    {1}"
                                .format(EXTSCHEMAS, val),
                                instance=extensions[ptr][EXTSCHEMAS])
                        if raiseex:
                            raise ex
                        out.append(ex)
                        return ex
                    
                # now validate marked portion
                out.extend( self.validate_against(extensions[ptr], 
                                                  extensions[ptr][EXTSCHEMAS],
                                                  strict) )
                if raiseex and len(out) > 0:
                    raise out[0]
            
        return out

    def validate_against(self, instance, schemauris=[], strict=False):
        """
        validate the instance against each of the schemas identified by the 
        list of schemauris.  For the instance to be considered valid, it 
        must validate against each of the named schemas.  $extensionSchema
        properties within the instance are ignored.  

        :argument instance:  a parsed JSON document to be validated.
        :argument list schemauris:  a list of URIs of the schemas to validate
                                    against.  

        :return list: a list of encountered errors in the form of exceptions; 
                      otherwise, an empty list if the instance is valid against
                      all schemas.
        """
        if isinstance(schemauris, str) or isinstance(schemauris, unicode):
            schemauris = [ schemauris ]
        schema = None
        out = []
        for uri in schemauris:
            val = self._validators.get(uri)
            if not val:
                (urib,frag) = self._spliturifrag(uri)
                schema = self._schemaStore.get(urib)
                if not schema:
                    try:
                        schema = self._loader(urib)
                    except KeyError, e:
                        ex = RefResolutionError(
                                "Unable find schema document for " + urib)
                        if strict:
                            out.append(ex)
                        continue
                    
                resolver = jsch.RefResolver(uri, schema, self._schemaStore,
                                            handlers=self._handler)

                if frag:
                    try:
                        schema = resolver.resolve_fragment(schema, frag)
                    except RefResolutionError, ex:
                        exc = RefResolutionError(
                         "Unable to resolve fragment, {0} from schema, {1} ({2})"
                         .format(frag, urib, str(ex)))
                        out.append(exc)
                        continue

                cls = jsch.validator_for(schema)

                # check the schema for errors
                scherrs = [ SchemaError.create_from(err) \
                            for err in cls(cls.META_SCHEMA).iter_errors(schema) ]
                if len(scherrs) > 0:
                    out.extend(scherrs)
                    continue
                
                val = cls(schema, resolver=resolver)


            out.extend( [err for err in val.iter_errors(instance)] )

            self._validators[uri] = val
            self._schemaStore.update(val.resolver.store)

        return out

    def _spliturifrag(self, uri):
        return urlparse.urldefrag(uri)

    def validate_file(self, filepath, minimally=False, strict=False,
                      raiseex=True):
        """
        open the specified file and validate its contents.  This is 
        equivalent to loading the JSON in the file and passing it to 
        validate().
        """
        with open(filepath) as fd:
            instance = json.load(fd)
        return self.validate(instance, minimally, strict, raiseex=raiseex)

    def is_extschema_schema(self, instance):
        """
        return true if the given JSON instance has both an "id" property
        set to one of the recognized URIs for a version of the JSON Enhanced 
        Schema (Supporting Extensions) _and_ an "$extensionSchema" property.
        """
        return instance.get('id') in EXTSCHEMA_URIS and \
               instance.has_key(EXTSCHEMAS)

from jsonschema._utils import format_as_index as format_path, \
                              indent as indent_json

def exc_to_json(ex):
    """
    format the data captured in an exceptions into a JSON data record.
    """
    out = {}
    try:
        raise ex
    except (ValidationError, SchemaError, RefResolutionError), e:
        out.update({
            'message':     e.message,
            'validator':   e.validator,
            'path':        e.path and format_path(e.path),
            'schema':      e.schema,
            'schema_path': e.relative_schema_path and \
                           format_path(list(e.relative_schema_path)[:-1])
        })

        try:
            raise e
        except ValidationError, exc:
            out['type'] = 'validation'
        except SchemaError, exc:
            out['type'] = 'schema'
        except RefResolutionError, exc:
            out['type'] = 'resolve'
    except ValueError, e:
        out.update({
            'type':        'json',
            'message':     str(e),
            'validator':   None,
            'path':        None,
            'schema':      None,
            'schema_path': None
        })
    except Exception, e:
        out.update({
            'type':        'unexpected',
            'message':     str(e),
            'validator':   None,
            'path':        None,
            'schema':      None,
            'schema_path': None
        })

    return out
