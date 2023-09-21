#!python

import json
import logging
import os
import pathlib
import subprocess

import env_pipes
import simplifiedapp

LOGGER = logging.getLogger(__name__)
PARENT_DIR = pathlib.Path(__file__).parent

DEFAULT_ENV_VARIABLES = {
	'DJANGO_DEBUG'		: 'true',
	'DJANGO_LOG_LEVEL'	: 'debug',
	'PORT'				: '8080',
}

def main(*secret_json_file_paths, extra_env_variables = {}, platform = None, build_only = False):

	secret_json_file_paths = [pathlib.Path(json_file_path) for json_file_path in secret_json_file_paths]
	for json_file_path in secret_json_file_paths:
		if not json_file_path.is_file():
			raise RuntimeError('The provided file does not exists or is not accessible to you: {}'.format(json_file_path))

	environment_content = DEFAULT_ENV_VARIABLES.copy()
	environment_content.update(extra_env_variables)
	for json_file_path in secret_json_file_paths:
		environment_content.update({key.upper() : value for key, value in json.loads(json_file_path.read_text()).items()})

	build_command = ['docker', 'build']
	if platform is not None:
		build_command += ['--platform', platform]
	for var_name in environment_content:
		build_command += ['--build-arg', var_name]

	LOGGER.debug('Environment populated: %s', environment_content)
	build_command += ['--tag', 'django-okta-client:latest', str(PARENT_DIR)]
	LOGGER.debug('Running build command: %s', build_command)
	build_run = subprocess.run(build_command, env = os.environ | environment_content)
	build_run.check_returncode()

	if not build_only:

		run_command = ['docker', 'run', '-d', '--rm', '--name', 'django_okta_client_test']
		for var_name in environment_content:
			run_command += ['-e', var_name]
		run_command += ['-p', '127.0.0.1:{PORT}:{PORT}'.format(PORT = environment_content['PORT']), 'django-okta-client:latest']

		run_run = subprocess.run(run_command, env = os.environ | environment_content)
		run_run.check_returncode()

		return subprocess.run(('docker', 'logs', '-f', 'django_okta_client_test'))

if __name__ == '__main__':
	simplifiedapp.main(main)
