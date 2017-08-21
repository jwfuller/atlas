"""
Fabric functions.
"""
import sys
from logging import getLogger

from fabric.contrib.files import append, exists, sed, upload_template
from fabric.api import *
from fabric.network import disconnect_all

from atlas import utilities
from atlas.config_servers import (code_root, instances_code_root, instances_web_root, instance_down_path)
from atlas.config import (atlas_path, atlas_deployment_user)

# Setup a sub-logger
log = getLogger('atlas.fabric_tasks')
# [filename] | [endpoint] | [item _id] | [action/method] | [message]

if atlas_path not in sys.path:
    sys.path.append(atlas_path)


# Fabric environmental settings.
env.user = atlas_deployment_user
# Allow ~/.ssh/config to be utilized.
env.use_ssh_config = True


# We use our own exception class so that we can bubble the errors up to Celery.
class FabricException(Exception):
    pass


def code_deploy(item):
    """
    Responds to POSTs to deploy code to the right places on the server.

    :param item:
    :return:
    """
    # Need warn only to allow the error to pass to celery.
    with settings(warn_only=True):
        log.debug('fabric_tasks | code | %s | deploy | %s', item['_id'], item)

        if item['meta']['code_type'] == 'library':
            code_type_dir = 'libraries'
        else:
            code_type_dir = item['meta']['code_type'] + 's'

        code_folder = '{0}/{1}/{2}'.format(code_root, code_type_dir, item['_id'])
        create_directory_structure(code_folder)

        log.debug('fabric_tasks | code | %s | deploy | repo - %s hash - %s',
                  item['_id'], item['git_url'], item['commit_hash'])

        try:
            run("git clone -b '{0}' --single-branch --depth 1 {1} {2}".format(
                item['commit_hash'], item['git_url'], code_folder), pty=False)
        except FabricException as error:
            log.debug('fabric_tasks | code | %s | deploy | Clone failed - %s', item['_id'], error)
            raise

        if item['meta']['is_current']:
            code_folder_current = '{0}/{1}/{2}/{2}-current'.format(
                code_root,
                code_type_dir,
                item['meta']['name'])
            update_symlink(code_folder, code_folder_current)


def create_directory_structure(folder):
    """
    Create a directory and it's parents.
    """
    log.info('fabric_tasks | Create directory | %s', folder)
    run('mkdir -p {0}'.format(folder))


def update_symlink(source, destination):
    """
    Replace or create a symlink.
    """
    log.info('fabric_tasks | Update symlink | source - %s destination - %s', source, destination)
    if exists(destination):
        run('rm {0}'.format(destination))
    run('ln -s {0} {1}'.format(source, destination))
