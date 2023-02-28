#!python
"""A setuptools based setup module.

ToDo:
- Everything
"""

import setuptools

import okta_client

setuptools.setup(
	name = 'django-okta-client',
	version = okta_client.__version__,
	description = okta_client.__doc__.splitlines()[0],
	long_description = okta_client.__doc__.splitlines()[1],
	url = 'https://github.com/irvingleonard/django-okta-client',
	author = 'Irving Leonard',
	author_email = 'irvingleonard@gmail.com',
	license='BSD 2-Clause "Simplified" License',
	classifiers = [
		'Development Status :: 4 - Beta',
		'Environment :: Web Environment',
		'Framework :: Django',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: BSD License',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Programming Language :: Python :: 3',
		'Topic :: Internet :: WWW/HTTP',
		'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
		'Topic :: System :: Systems Administration :: Authentication/Directory',
	],
	keywords = 'okta saml saml2',
	
	install_requires = [
		'django',
		'pysaml2',
	],
	python_requires = '>=3.6',
	packages = setuptools.find_packages(),
	package_data = {
		'okta_client' : [
			'templates/okta-client/*'
		],
	}
)

