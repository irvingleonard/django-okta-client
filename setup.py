#!python
"""A setuptools based setup module.

ToDo:
- Everything
"""

import setuptools

import simplifiedapp

import okta_client

setuptools.setup(**simplifiedapp.object_metadata(okta_client))
