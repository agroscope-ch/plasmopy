"""
Module containing all scripts for directing the modeling steps.
Additionally, absolute path appended here to sys.path to enable pdoc automated
documentation.

"""

import os
import sys

## Necessary to call "make docs" to generate automated code documentation:
syspath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(syspath)
