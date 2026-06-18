import os


__author__ = ["Petras Vestartas"]
__copyright__ = "Block Research Group - ETH Zurich"
__license__ = "Apache License 2.0"
__email__ = ["vestartas@arch.ethz.ch"]
__version__ = "0.1.0"

HERE = os.path.dirname(__file__)

HOME = os.path.abspath(os.path.join(HERE, "../../"))
DATA = os.path.abspath(os.path.join(HOME, "data"))
DOCS = os.path.abspath(os.path.join(HOME, "docs"))
TEMP = os.path.abspath(os.path.join(HOME, "temp"))


__all_plugins__ = [
    "compas_manifold.booleans",
]

__all__ = ["HOME", "DATA", "DOCS", "TEMP"]
