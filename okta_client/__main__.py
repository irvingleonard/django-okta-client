#!python
"""
Entry point for the `okta_client` package.
"""

from simplifiedapp import main

try:
	import okta_client
except ModuleNotFoundError:
	import __init__ as okta_client
	
main(okta_client)
