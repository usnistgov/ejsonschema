# ejsonschema

ejsonschema is a python json validater based on the jsonschema python
package that supports validation of instance documents against both a
core schema and one or more "extended" schemas.

This package is based on an extension of the JSON Schema
(http://json-schema.org) called Extensible JSON Schema.  With the
standard JSON Schema specification, an instance JSON document that is
compliant with a JSON Schema can also contain additional properties
not defined by the Schema.  This allows different producers of JSON
documents to insert additional properties into a document without
breaking its compliance with the common schema.  Consumers that do not
recognize the extra properties can safely ignore them; those that do
recognize them can take advantage of the extra information.  Indeed,
those extra properties can be defined in an extension JSON Schema
using standard JSON Schema constructs, allowing producers and
consumers to validate those extra properties.  

In many scenarios (involving interoperability between applications), it's
helpful to applications when they are able to determine which schemas
a document is supposed to be compliant with.  In particular, if an
application sees that a document claims compliance with an extended
schema that it doesn't recognize, it may not be able to surmise that
it is compliant with the original schema that it is aware of.

The Enhanced JSON Schema framework solves this problem by providing
a means for JSON instance documents to claim compliance simultaneously
to a primary schema and any number of extension schemas.  The primary
schema is declare by providing its URI in "$schema" property (borrowed
from JSON Schema); the extended schema URIs can then be listed in any
array property called "@extensionSchemas".

(The Enhanced JSON Schema framework also defines a number of useful
documentation properties that can be included in the JSON Schema
document for a richer description of the schema.)

This package includes a validator that can be engaged either via a 
command-line script,
[scripts/validate](https://github.com/usnistgov/ejsonschema.git), or 
via the python API.  The validator will look for the "$schema" and 
"$extensionSchema" properties and validates the JSON nodes 
accordingly.  Note that the "$extensionSchema" property can appear in any
object node embedded within the instance document; validation against the
extended schemas will occur only within the object nodes where the 
"$extensionSchema" property appears.  Further, the validator can be 
configured to look for cached schemas on local disk.  Execute the [validate
script](https://github.com/usnistgov/ejsonschema.git) with the `-h` option 
for more information.  

This technique allows for a kind of polymorphism of JSON types defined
in the schemas (similar to what "xsi:type" provides in XML).  

## Dependencies

The ejsonschema library has the following dependencies:

   * python 3.8 or later
   * jsonschema 4.0.x or later (> 4.5.1 recommended)
   * json-spec 0.9.16 or later (> 0.11.0 recommended)
   * requests
   * importlib_resources (if using python < 3.9)

In addition, the testing framework uses py.test. 

## Running Tests

The included tests apply unit-tests to the tool code and scripts.
Tests also check the correctness of the schemas and examples.  

Currently, tests only exist for the JSON schemas, examples, and
tools.  py.test is used to execute these tests.   To run, change into
the python directory of this distribution and type "py.test".  

## Licenses, Disclaimers, and History

This package was originally developed by Raymond Plante at the
National Institute of Standards and Technology (part of the US
Department of Commerce).  Thus, within the US, this software is
considered a work in the public domain (as per 17 U.S.C 105).  See
https://www.nist.gov/director/licensing for details.

This package is available on GitHub at
https://github.com/usnistgov/ejsonschema.  This repository serves as a
platform for open community collaboration to enable and encourage
greater sharing of and interoperability between research data from
around the world.  Except where otherwise noted, the content and
software within this repository should be considered a work in
progress, may contain input from non-governmental contributors, and
thus should not be construed to represent the position nor have the
endorsement of the United States government.  

The content and software contained in this repository is provided "AS
IS" with no warrenty of any kind.  

This package was originally developed in support of the Materials
Genome Initiative as part of the schema development effort.  This work
is captured in the GitHub repository
[mgi-resmd](https://github.com/usnistgov/mgi-resmd).  The Enhanced
JSON Schema component was eventually spun off into its own repository
for development for broader use.  

