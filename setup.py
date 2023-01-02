import glob, os, shutil, pathlib
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

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
        for f in glob.glob(os.path.join(self._schema_dir, "schemaLocation.*")):
            self.copy_file(f, os.path.join(self.build_lib, dest,
                                           os.path.basename(f)))
        

    def run(self):
        _build_py.run(self)
        self.build_schemas()
    

setup(name='ejsonschema',
      version='0.1',
      description='Enhanced JSON Schema validator (extending jsonschema)',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Ray Plante',
      author_email='raymond.plante@nist.gov',
      url='https://github.com/usnistgov/ejsonschema',
      packages=find_packages(where="python"),
      package_dir={'': 'python'},
      scripts=[ 'scripts/validate' ],
      cmdclass={'build_py': build_py},
      python_requires=">=3.7, <4",
      install_requires=["jsonschema"],
      project_urls={
          "Source": "https://github.com/usnistgov/ejsonschema",
          "Bug Reports": "https://github.com/usnistgov/ejsonschema/issues"
      },
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3 :: Only",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
      ]
)

