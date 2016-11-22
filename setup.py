import glob, os, shutil
from distutils.core import setup
from distutils.command.build_py import build_py as _build_py

class build_py(_build_py):
    """Specialization to handle installation of schema files in schemas dir"""

    def finalize_options(self):
        _build_py.finalize_options(self)
        self._schema_dir = 'schemas'
        self._name = (len(self.packages) > 0 and self.packages[0]) or \
                     'ejsonschema'

    def build_schemas(self):
        dest = os.path.join(self._name, "resources", "schemas")
        self.mkpath(os.path.join(self.build_lib, dest))
        for f in glob.glob(os.path.join(self._schema_dir, "*-schema.json")):
            self.copy_file(f, os.path.join(self.build_lib, dest,
                                           os.path.basename(f)))

    def run(self):
        _build_py.run(self)
        self.build_schemas()
    

setup(name='ejsonschema',
      version='0.1',
      description='Enhanced JSON Schema validator (extending jsonschema)',
      author='Ray Plante',
      author_email='raymond.plante@nist.gov',
      url='https://github.com/usnistgov/ejsonschema',
      packages=['ejsonschema', 'ejsonschema.cli'],
      package_dir={'': 'python'},
      scripts=[ 'scripts/validate' ],
      cmdclass={'build_py': build_py}
     )

