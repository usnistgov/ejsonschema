from __future__ import with_statement
import os, pytest

testroot = os.path.abspath(os.path.dirname(__file__))

# try resource_dir as ejsonschema/resources
installed_resource_dir = os.path.join(os.path.dirname(testroot), 'resources')
resource_dir = installed_resource_dir
if not os.path.exists(resource_dir):
    # try resource_dir as the root of the distribution directory
    resource_dir = os.path.dirname(os.path.dirname(os.path.dirname(testroot)))

if not os.path.exists(resource_dir):
    raise RuntimeError("Unable to find resources directory either as " +
                       installed_resource_dir + " or " + resource_dir)
                       

# try schema_dir as ejsonschema/resources/schemas
schema_dir = os.path.join(resource_dir, "schemas")
if not os.path.exists(schema_dir):
    # try schema_dir as schemas under the root of the distribution directory 
    schema_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(testroot))), "schemas"
    )
if not os.path.exists(schema_dir):
    raise RuntimeError("Unable to find schemas directory either as " +
                       os.path.join(resource_dir, 'schemas') + " or " +
                       schema_dir)

data_dir = os.path.join(testroot, "data")

examples_dir = os.path.join(resource_dir, "examples")
if not os.path.exists(examples_dir):
    examples_dir = data_dir


