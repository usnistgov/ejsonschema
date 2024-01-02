"""
a module that provides support for loading schemas, particularly those 
cached on local disk.  
"""
import sys, os, json, errno, warnings, abc, logging
from collections.abc import Mapping
from types import ModuleType
from urllib.parse import urlparse
from urllib.request import urlopen
from pathlib import Path
from typing import Union, Iterator, Tuple
from types import ModuleType
from logging import Logger

import jsonschema as jsch
import referencing as refng
from referencing.jsonschema import DRAFT202012

from .location import read_loc_file

try:
    import requests
except ImportError:
    requests = None

# The files() API was added in Python 3.9.
if sys.version_info >= (3, 9):  # pragma: no cover
    from importlib import resources
else:  # pragma: no cover
    import importlib_resources as resources  # type: ignore

SCHEMA_LOCATION_FILE = "schemaLocation.json"

class JSONDataLoader(metaclass=abc.ABCMeta):
    """
    a function object that will load a JSON document from an internally configured source
    """
    def __init__(self, source):
        """
        initialize the loader.  
        :param source:  an instance that represents the source of the data.  
        """
        self._src = source

    @abc.abstractmethod
    def load(self):
        """
        Read the JSON data from its source and return it.  

        Implementation Notes: This method should always read the data afresh.  It is recommended that 
        issues of source existance be tested at construction time when cheap and possible to do so.

        :raises json.JSONDecodeError:  if the data cannot be loaded due to a JSON format error
        :raises JSONDataNotAvailable:  if the schema cannot be loaded from its source for some other reason
                                       (e.g. an IO error).
        """
        raise NotImplementedError()

    def __call__(self):
        """
        load the JSON data (reading it as needed) and return it.  

        An implementation may cache the data if appropriate.  This default implementation calls
        :py:meth:`load` directly.
        """
        return self.load()

    def __str__(self):
        return str(self._src)

class JSONDataNotAvailable(Exception):
    """
    an exception indicating that JSON data can not loaded from its source due to some error.
    """

    def __init__(self, source=None, message=None, cause=None, _what="JSON data"):
        if not message:
            message = f"Unable to load {_what}"
            if source:
                message += f" from {source}"
            if cause:
                message += f": {cause}"
        super(JSONDataNotAvailable, self).__init__(message)
        if cause:
            self.__cause__ = cause

class SchemaNotAvailable(JSONDataNotAvailable):
    """
    an exception indicating that a schema coudl not loaded from its source due to some error.
    """

    def __init__(self, source=None, message=None, cause=None):
        super(SchemaNotAvailable, self).__init__(source, message, cause, "Schema")

class NotASchema(SchemaNotAvailable):
    """
    a requested schema document could not be loaded because the document source does not contain a 
    compliant schema.
    """
    def __init__(self, source=None, message=None, cause=None):
        if not message:
            message = "Requested document"
            if source:
                message += f", {source},"
            message += " does not contain a JSON Schema."
        super(SchemaNotAvailable, self).__init__(source, message, cause)

class JSONResourceLoader(JSONDataLoader):
    """
    a :py:class:`JSONDataLoader` that reads the data from a package resource
    """

    def __init__(self, pkg: Union[ModuleType, str], respath: str, resdir: str=None):
        """
        Point a loader at a package resource
        :param module|str pkg:  the package that contains the desired resource, given either 
                                as a module instance or a dot-delimited module name.
        :param str    respath:  the path to the desired resource file (relative to the value
                                of `resdir`).
        :param str     resdir:  the directory within the package that `respath` is relative to;
                                if not given, `respath` is relative to the package.
        :raises ImportError:  if `pkg` is a string but cannot be imported as a module.
        :raises FileNotFoundError:  if the file does not exist as a resource in the specified package
        """
        src = resources.files(pkg)
        if resdir:
            src = src.joinpath(resdir)
        src = src.joinpath(respath)
        super(JSONResourceLoader, self).__init__(src)

    def load(self):
        """
        Read the JSON data from its source and return it.
        :raises NotASchema:  if the content of the source document is not found to be a legal JSON Schema
        :raises SchemaNotAvailable:  if the schema cannot be loaded from its source for some other reason
                                     (e.g. an IO error).
        """
        try:
            return json.loads(self._src.read_text("utf-8"))
        except IOError as ex:
            raise JSONDataNotAvailable(str(self._src), cause=ex) from ex

class JSONFileLoader(JSONDataLoader):
    """
    a :py:class:`JSONDataLoader` that reads the data from a normal file on disk
    """

    def __init__(self, fpath: Union[Path, str], basedir: Union[Path, str] = None):
        """
        Point a loader at a file on disk
        :param Path|str   fpath:  the path to the file containing the desired JSON data
        :param Path|str basedir:  the directory within the package that `fpath` is relative to.
                                  If not given, `respath` is relative to the current directory.
                                  If `fpath` is absolute, this parameter is ignored.
        :raises FileNotFoundError:  if the path does not point to an existing file
        """
        src = Path(fpath) if not isinstance(fpath, Path) else fpath
        if basedir:
            if not isinstance(basedir, Path):
                basedir = Path(basedir)
            src = basedir / src
        if src.exists() and not src.is_file():
            raise FileNotFoundError(f"{str(src)} is not an existing file")
        super(JSONFileLoader, self).__init__(src)

    def load(self):
        """
        Read the JSON data from its source and return it.  This can raise any of the exception that 
        might be raised by `json.load()`.  
        """
        try:
            with open(self._src, encoding="utf-8") as fd:
                return json.load(fd)
        except IOError as ex:
            raise JSONDataNotAvailable(str(self._src), cause=ex) from ex

class WebJSONLoader(JSONDataLoader):
    """
    a :py:class:`JSONDataLoader` that reads the data from an HTTP/HTTPS URL
    """

    def __init__(self, url: str, contenttype: str=None, ensure=False):
        """
        Point a loader at a URL
        :param str     url:  the full URL for the JSON file
        :param str contenttype:  the content type to include in the Accept header of the request 
                             used to retrieve the data.  If None, the Accept header will not be set.
        :param bool ensure:  ensure that the URL resource exists as JSON by doing a 
                             HEAD request and checking its content type.
        :raises ValueError:  if the given `url` is not a compliant HTTP/HTTPS URL
        :raises requests.RequestException:  if `ensure` was `True` and there was trouble accessing the URL
        """
        self.hdrs = {}
        if contenttype:
            self.hdrs['Accept'] = contenttype
        src = url
        url = urlparse(url)
        if url.scheme != "https" and url.scheme != "http":
            raise ValueError(f"{src}: not an HTTP(S) URL")

        if ensure:
            res = requests.head(src, headers=self.hdrs, allow_redirects=True)
            if res.status_code >= 400:
                res.raise_for_status()
            ct = res.headers.get('content-type') 
            if ct and 'json' not in ct:
                raise ValueError(f"{src}: does not return JSON data")

        super(WebJSONLoader, self).__init__(src)

    def load(self):
        """
        Read JSON data from the remote resource
        :raises requests.RequestException:  if there was a problem accessing the JSON data
        """
        try:
            res = requests.get(self._src, headers=self.hdrs, allow_redirects=True)
            res.raise_for_status()
            return res.json()

        except requests.RequestException as ex:
            raise JSONDataNotAvailable(self._src, cause=ex) from ex

def get_json_loader(url: str):
    """
    return an instance of a JSONDataLoader that can be called to load the schema referred to by `url`.
    """
    urlp = urlparse(url)

    if not urlp.path or urlp.path == '/':
        raise ValueError(f"{url}: Malformed url source format: no path given")

    if urlp.scheme == 'resource':
        # retrieve as a resource from a python package
        pkg = urlp.netloc
        pth = urlp.path.lstrip('/')
        if not pkg:
            parts = urlp.path.split('/', 1)
            if len(parts) < 2:
                raise ValueError(f"{url}: Malformed url source format: no path given")
            pkg = parts[0]
            pth = parts[1]
        return JSONResourceLoader(pkg, pth)

    if urlp.scheme == 'https' or urlp.scheme == 'http':
        # retrieve from a URL over the web
        return WebJSONLoader(url)

    # default to local file
    return JSONFileLoader(urlp.path)
        
_schema_schemaLoader = None
def schemaLoader_for_schemas():
    global _schema_schemaLoader
    if not _schema_schemaLoader:
        try:
            import ejsonschema
            resdir = resources.files(ejsonschema).joinpath("resources", "schemas")
            if redir.is_dir():
                _schema_schemaLoader = \
                    SchemaLoader.from_resource_cache(ejsonschema, Path("resources")/"schemas")
        except (ImportError, Exception):
            pass

    if not _schema_schemaLoader:
        schemadir = os.path.join(os.path.dirname(__file__),
                                 "resources", "schemas")
        if not os.path.exists(schemadir):
            fromsrc = os.path.join(os.path.dirname(os.path.dirname(
                                    os.path.dirname(os.path.abspath(__file__)))),
                                   "schemas")
            if os.path.exists(fromsrc):
                schemadir = fromsrc
            
        _schema_schemaLoader = SchemaLoader.from_directory(schemadir)

    return _schema_schemaLoader

class BaseSchemaLoad(object, metaclass=abc.ABCMeta):

    def load_schema(self, uri):
        """
        return the parsed json schema document for a given URI.

        :exc `KeyError` if the location of the schema has not been set
        :exc `IOError` if an error occurs while trying to read from the 
                       registered location.  This includes if the file is
                       not found or reading causes a syntax error.  
        """
        raise NotImplementedError()

    def load_schema_for_registry(self, uri, defspec=DRAFT202012):
        """
        return the parsed json schema document for a given URI, wrapped as
        a ``referencing.Resource`` object.  This is form of the schema is 
        intended for use with ``referencing.Registry``, used by the base
        ``jsonschema`` module to resolver schema references.  It calls 
        :py:meth:`load_schema` internally.
        """
        return refng.Resource.from_contents(self.load_schema(uri), defspec)

    def __call__(self, uri):
        """
        return the parsed json schema document for a given URI.  Calling an
        instance as a function is equivalent to calling load_schema().
        """
        return self.load_schema_for_registry(uri)

class SchemaLoader(BaseSchemaLoad):
    """
    A class that can be configured to load schemas from particular locations.
    For example, it can be used as a schema handler that loads schemas from
    local disk files rather than from remote locations.  It can also provide
    map schema URIs to arbitrary URL locations.  
    """

    def __init__(self, urilocs={}):
        """
        initialize the handler

        :argument dict urilocs:  a dictionary mapping URIs to local file paths
                                 that define the schema identified by the URI.
        """
        self._map = dict(urilocs)

    @classmethod
    def from_directory(cls, dirpath, ensure_locfile=False, 
                       locfile=SCHEMA_LOCATION_FILE, logger: Logger=None,
                       recursive=True):
        """
        create a schemaLoader for schemas stored as files under a given 
        directory.  This factory method will attempt to load schema file 
        names from a file called `locfile` (defaults to "schemaLocation.json").
        If the file is not found, all the JSON files under that directory
        (including subdirectories) will be examined and those recognized as 
        JSON schemas will be loaded.  
        :param str    dirpath:  the directory to look for schemas (and 
                                `locfile`) under.
        :param bool ensure_locfile:  if True, and `locfile` is not found,
                                attempt to write one with the schemas 
                                subsequently discovered.
        :param str    locfile:  the name of the schema location file to look for 
                                (default: "schemaLocation.json").
        :param str     logger:  a Logger write messages about which files are loaded 
                                (and which are not and why).
        :param bool recursive:  if True (default), search recursively into subdirectories
                                for schemas; ignored if `locfile` is present.
        """
        if not os.path.exists(dirpath):
            raise IOError((errno.ENOENT, "directory not found", dirpath)) 
        if not os.path.isdir(dirpath):
            raise RuntimeError(dirpath + ": not a directory")

        out = SchemaLoader()

        locpath = None
        if locfile:
            locpath = os.path.join(dirpath, locfile)
        if locfile and os.path.exists(locpath):
            out.load_locations(locpath, dirpath)
        else:
            if logger:
                logger = logger.getChild("dsc")
            dc = DirectorySchemaCache(dirpath, logger=logger)
            for uri, loc in dc.discover(recursive):
                out.add_location(uri, loc)
            if ensure_locfile:
                dc.save_locations(locfile)

        return out

    @classmethod
    def from_resource_cache(cls, pkg: Union[ModuleType, str], respath: str=None,
                            glob: str='*', locfile=SCHEMA_LOCATION_FILE,
                            logger: Logger=None, recursive: bool=True):
        """
        create a schemaLoader for schemas stored as resources of a python
        package.  This factory method will attempt to load schema file 
        names from a file called locfile (defaults to "schemaLocation.json").
        If the file is not found, all the JSON files under that directory
        (including subdirectories) will be examined and those recognized as 
        JSON schemas will be loaded.  
        :param module|str pkg:  the python package containing the schemas, given either 
                                as a module instance or as a dot-delimited string.
        :param str    respath:  the resource directory relative to the package to look
                                for schemas under
        :param str       glob:  a file glob pattern (e.g. "*.json") to restrict the 
                                search to files with names matching it
        :param str    locfile:  the name of the schema location file to look for 
                                (default: "schemaLocation.json").
        :param str     logger:  a Logger write messages about which files are loaded 
                                (and which are not and why).
        :param bool recursive:  if True (default), search recursively into subdirectories
                                for schemas; ignored if `locfile` is present.
        :raises ImportError:  if `pkg` is a string but cannot be imported as a module.
        """
        if not logger:
            logger = logging.getLogger("ejs")

        # this ensures that the python package and directory exists:
        cache = PackageResourceSchemaCache(pkg, respath, glob, logger.getChild("prsc"))

        out = SchemaLoader()

        locpath = None
        if locfile:
            locpath = cache.path_for(locfile)
        if locpath and locpath.is_file():
            dirroot = "resource:" + (pkg.__name__ if isinstance(pkg, ModuleType) else pkg)
            if respath:
                dirroot = "/".join([dirroot, respath])
            with resources.as_file(locpath) as schlocf:
                out.load_locations(schlocf, dirroot)

        else:
            for uri, loc in cache.discover(recursive):
                out.add_location(uri, loc)

        return out

    @classmethod
    def from_location_file(cls, locpath, basedir=None):
        """
        create a schemaLoader for schemas listed in a schema location file.

        :argument str basedir:  the base directory that document paths are 
                                assumed to be relative to.  If not given, any
                                relative paths will be assumed to be relative
                                to the directory containing the location file. 
        """
        out = SchemaLoader()
        out.load_locations(locpath, basedir)
        return out

    def locate(self, uri):
        """
        return location of the schema for the given URI.

        :exc `KeyError` if the location of the schema has not been set
        """
        return str(self._map[uri])

    def iterURIs(self):
        """
        return an iterator for the uris mapped in this instance
        """
        return self._map.keys()

    def __len__(self):
        return len(self._map)

    def add_location(self, uri: str, loc: Union[str,Path,JSONDataLoader] = None):
        """
        set the location of the schema file corresponding to the given URI
        :param str uri:  the schema identifier being loaded
        :param str|Path|JSONDataLoader loc:  the location of the JSON Schema document for 
                         the given identifier.  If not provided, the URI will be treated as 
                         the URL location of the document.
        """
        # strip off any trailing # from the id
        uri = uri.rstrip('#')

        if not loc:
            loc = uri

        if not isinstance(loc, JSONDataLoader):
            if isinstance(loc, Path):
                loc = JSONFileLoader(str(Path))
            else:
                # treat as a URL string
                loc = get_json_loader(loc)

        self._map[uri] = loc

    def add_locations(self, urifiles):
        """
        add all the URI-location mappings in the given dictionary
        """
        for uri in urifiles:
            self.add_location(uri, urifiles[uri])

    def copy_locations_from(self, loader):
        """
        copy the schema locations from another SchemaLoader into this one.
        Locations form the other loader will overwrite those in this one 
        for schema IDs in common.  

        :param loader SchemaLoader:  the SchemaLoader to copy locations from
        """
        self.add_locations(loader._map)

    def load_schema(self, uri):
        """
        return the parsed json schema document for a given URI.

        :exc `KeyError` if the location of the schema has not been set
        :exc `IOError` if an error occurs while trying to read from the 
                       registered location.  This includes if the file is
                       not found or reading causes a syntax error.  
        """
        return self._map[uri]()

    def load_locations(self, filename, basedir=None):
        """
        load in a mapping of URIs to file paths from a file.  This uses the
        location module to read the mappings file.  

        :argument str filename:  a file path to the mappings file.  The format 
                                 should be any of the formats supported by this 
                                 class.
        """
        self.add_locations(read_loc_file(filename, basedir=basedir))

class SchemaCache(metaclass=abc.ABCMeta):
    """
    an interface for discovering schemas in a local or remote location.  This is 
    intended for loading schemas into a SchemaLoader instance (via its 
    :py:meth:`discover` method).  
    """

    def __init__(self, logger: Logger=None):
        self.logger = logger

    @abc.abstractmethod
    def discover(self, deep=True) -> Iterator[Tuple[str, JSONDataLoader]]:
        """
        return an iterator to discovered schemas in the cache, returning them as a 2-tuple, 
        (id, JSONDataLoader).
        :param bool deep:  if True (default), do an exhaustive search.  What this means may 
                           depend on the implementation.  It can mean, for example, to descend 
                           into subdirectories.  
        """
        raise NotImplementedError()

class PackageResourceSchemaCache(SchemaCache):
    """
    A SchemaCache that finds all the schema documents available as resources 
    of a python package.
    """

    def __init__(self, pkg: Union[ModuleType, str], respath: str=None,
                 glob: str='*', logger: Logger=None):
        """
        setup the cache
        :param module|str pkg:  the python package containing the schemas, given either 
                                as a module instance or as a dot-delimited string.
        :param str    respath:  the resource path relative to the package to look
                                for schemas under
        :param str       glob:  a file glob pattern (e.g. "*.json") to restrict the 
                                search to files with names matching it
        :raises ImportError:  if `pkg` is a string but cannot be imported as a module.
        :raises FileNotFoundError:  if the file does not exist as a resource in the 
                                    specified package
        """
        super(PackageResourceSchemaCache, self).__init__(logger)
        self._pkg = pkg

        if not glob:
            glob = '*'
        self._glob = glob
        self._root = resources.files(pkg)
        if respath:
            self._root = self._root.joinpath(respath)

    def path_for(self, resfile):
        """
        return a Path-like object that represents the expected location of a given resource 
        file. 
        """
        return self._root.joinpath(resfile.strip(os.sep))
        
    def discover(self, deep=True)  -> Iterator[Tuple[str, JSONDataLoader]]:
        """
        recursively discover all the schema files found as resources in the configured package
        :param bool deep:  if True (default), do a recursive search, descending into 
                           subdirectories.  
        """
        for fpath, id, schema in self._iterschemas(deep):
            yield id, JSONResourceLoader(self._pkg, fpath)

    def schemas(self):
        """
        return a dictionary of mappings of URIs to parsed schemas
        """
        out = {}
        for fpath, id, schema in self._iterfiles():
            out[id] = schema
        return out

    def _iterschemas(self, recursive=True) -> Iterator[Tuple[Path, str, Mapping]]:
        globfiles = self._root.rglob if recursive else self._root.glob
        for fpath in globfiles(self._glob):
            if fpath.is_file():
                outpath = fpath.relative_to(self._root)
                try:
                    schema = json.loads(fpath.read_text("utf-8"))
                    if not isinstance(schema, Mapping):
                        if self.loggger:
                            self.logger.debug(f"{str(outpath)}: Not a schema: does not contain a JSON object")
                        continue
                    if '$schema' not in schema:
                        if self.loggger:
                            self.logger.debug(f"{str(outpath)}: Not a schema: Missing $schema property")
                        continue
                    id = schema.get("$id") or schema.get("id")

                    yield outpath, id, schema

                except json.JSONDecodeError as ex:
                    if self.logger:
                        self.logger.debug("%s: Not a parseable JSON file (%s)", str(outpath), str(ex))
                except IOError as ex:
                    if self.logger:
                        self.logger.debug("%s: IO error while reading: %s", str(outpath), str(ex))
                    

class DirectorySchemaCache(object):
    """
    A SchemaCache that finds all the schema documents found under a
    given directory.  This class can either pre-load all schemas into 
    memory or simply create a mapping of URIs to file locations.  

    A schema is recognized as a JSON file containing a "$schema" property set 
    to a recognized JSON-Schema URI.  It should also contain an "$id" (or "id")
    property that contains the schema's URI; if it doesn't, a file-scheme URI 
    will be given to it based on its location on disk.  
    """

    class NotASchemaError(Exception):

        def __init__(self, why=None, filepath=None):
            self.filename = None
            self._path = filepath
            self.why = why

        @property
        def path(self):
            """
            the file path to file containing the non-schema
            """
            return self._path
        @path.setter
        def path(self, val):
            self._path = val
            if val:
                self.filename = os.path.basename(val)
        @path.deleter
        def path(self):
            del self._path

        def __str__(self):
            out = ""
            if self.filename:
                out += self.filename + ": "
            out += "Not a JSON Schema document"
            if self.why:
                out += ": " + self.why
            return out

    def __init__(self, dirpath, logger=None):
        self._dir = dirpath
        self._checkdir()
        self.logger = logger

    def _checkdir(self):
        if not os.path.exists(self._dir):
            raise IOError((errno.ENOENT, "directory not found", self._dir)) 
        if not os.path.isdir(self._dir):
            raise RuntimeError(self._dir + ": not a directory")

    def _read_id(self, fd):
        try:
            schema = json.load(fd)
        except Exception as ex:
            # JSON syntax error (most likely)
            raise self.NotASchemaError("JSON content error: " + str(ex))
        
        if not hasattr(schema, "get") or not hasattr(schema,"__getitem__"):
            raise self.NotASchemaError("Does not contain a JSON object")
        
        try:
            sid = schema["$schema"]
            
            # For jsonschema versions <~ 4.18, accessing validators.meta_schemas raises
            # a warning, advising use of validators.validator_for() instead.  That
            # function defaults to the DefaultValidator, with a warning that in the
            # future it will raise an exception; until that time, we continue to consult
            # meta_schemas and suppress the original warning and preserve original
            # behavior
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message='.*jsonschema.validators.meta_schemas',
                                        category=DeprecationWarning)
                if sid not in jsch.validators.meta_schemas:
                    raise self.NotASchemaError("Unrecognized JSON-Schema $schema: "+sid)
        except KeyError:
            raise self.NotASchemaError("JSON object does not contain a $schema property")

        idprop = "$id"
        if idprop not in schema:
            idprop = "id"

        return (schema.get(idprop), schema)

    def open_file(self, filename):
        """
        read the file in the cache directory with the given filename and 
        return 2-tuple of the schema's id and the parsed schema
        """
        filepath = os.path.join(self._dir, filename)
        with open(filepath) as fd:
            try:
                (id, schema) = self._read_id(fd)
            except self.NotASchemaError as ex:
                ex.path = filename
                raise

            if not id:
                id = "file://" + filepath

            return (id, schema)

    def _iterfiles(self, recurse=True):
        for dir, dirnames, filenames in os.walk(self._dir):
            dir = dir[len(self._dir)+1:]
            for file in map(lambda p: os.path.join(dir, p), 
                            filter(lambda f: f.endswith(".json"), filenames)):
                if self.logger:
                    self.logger.info("loading schema file: "+file)
                try:
                    (id, schema) = self.open_file(file)
                    yield file, id, schema
                except IOError as ex:
                    # unable to read the file (issue warning?)
                    continue
                except self.NotASchemaError as ex:
                    if self.logger:
                        basedir = self._dir
                        if not basedir.endswith('/'):
                            basedir += "/"
                        fpath = ex.path
                        if file.startswith(basedir):
                            fpath = fpath[len(basedir):]
                        self.logger.warn(fpath+": Unable to load file as a schema: "+str(ex))
                    continue
            if not recurse:
                break

    def discover(self, deep=True)  -> Iterator[Tuple[str, JSONDataLoader]]:
        """
        recursively discover all the schema files found recursively within a directory
        :param bool deep:  if True (default), do a recursive search, descending into 
                           subdirectories.  
        """
        for fpath, id, schema in self._iterfiles(deep):
            yield id, JSONFileLoader(fpath, self._dir)

    def locations(self, absolute=True, recursive=True):
        """
        return a dictionary that maps schema URIs to their file paths.  

        :argument bool absolute:  if True, the paths returned will be absolute;
                                  by default (False), paths relative to the 
                                  directory are returned. 
        :argument bool recursive: if True (default), this list will include
                                  schemas from subdirectories
        """
        out = {}
        for file, id, schema in self._iterfiles(recursive):
            if absolute:
                file = os.path.join(self._dir, file)

            # if id ends in a #, drop it off the end
            if id.endswith('#'):
                id = id.rstrip('#')
            out[id] = file

        return out

    def schemas(self, recursive=True):
        """
        return a dictionary of mappings of URIs to parsed schemas

        :argument bool recursive: if True (default), this list will include
                                  schemas from subdirectories
        """
        out = {}
        for file, id, schema in self._iterfiles(recursive):
            out[id] = schema

        return out

    def save_locations(self, outfile=SCHEMA_LOCATION_FILE, 
                       absolute=False, recursive=True):
        """
        write the id-location map to a file (in JSON format).  

        :argument str outfile:  the name of the output file.  If not provided,
                     it will be written to a file called "schemaLocation.json"
                     in the cache directory.  A relative path will be 
                     interpreted as relative to the cache directory.  To write
                     to an arbitrary location, one must provide an absolute
                     path.
        :argument bool absolute:  if True, the paths returned will be absolute;
                                  by default (False), paths relative to the 
                                  directory are returned. 
        :argument bool recursive: if True (default), this list will include
                                  schemas from subdirectories
        """
        outfile = os.path.join(self._dir, outfile)

        locs = self.locations(absolute, recursive)

        with open(outfile, "w") as fd:
            json.dump(locs, fd, separators=(",", ": "), indent=4)
