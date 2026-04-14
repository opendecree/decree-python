"""Generated proto stubs.

The generated code uses absolute imports (e.g., 'from centralconfig.v1 import
types_pb2') because protoc generates imports relative to the proto root, not
the Python package structure. We add this directory to sys.path so those
imports resolve.

TODO: This pollutes sys.path globally. If this causes import collisions,
consider using a scoped import hook or configuring protoc to generate
package-relative imports.
"""

import os
import sys

_generated_dir = os.path.dirname(__file__)
if _generated_dir not in sys.path:
    sys.path.insert(0, _generated_dir)
