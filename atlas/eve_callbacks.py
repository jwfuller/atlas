"""
Eve callbacks.
"""
import sys
from logging import getLogger

from flask import abort

from atlas import utilities
from atlas import tasks
from atlas.config import atlas_path

# Setup a sub-logger
log = getLogger('atlas.callbacks')
# [filename] | [endpoint] | [item _id] | [action/method] | [message]

if atlas_path not in sys.path:
    sys.path.append(atlas_path)


def pre_create_code(request):
    """
    Check to see if we already have a code item with this name/version/type combination.
    """
    log.debug('eve_callbacks | pre_create_code | POST | %s', request)


def create_code(items):
    """
    Deploy code onto servers as the items are created.

    If a new code item 'is_current', PATCH 'is_current' code with the same name and type to no
    longer be current.

    :param items: List of dicts for items to be created.
    """
    log.debug('eve_callbacks | create_code | POST | %s', items)
    for item in items:
        # Check to see if there is already a current version of this code item.
        if item['meta']['is_current'] is True:
            query = {
                'meta.name': item['meta']['name'],
                "meta.code_type": item['meta']['code_type'],
                "meta.is_current": True
            }
            current_code = utilities.get_eve('code', query=query)
            # Returns a tuple (response, last_modified, etag, status, headers)
            log.debug('eve_callbacks | code | POST | current code - %s', current_code)

            for k, v in current_code[4]:
                if k == 'X-Total-Count' and v != 0:
                    for code in current_code[0]['_items']:
                        patch_payload = {'meta': {'is_current': False}}
                        log.debug('eve_callbacks | create_code | patch other current code | %s', code)
                        utilities.patch_eve('code', code['_id'], patch_payload)

        log.debug('eve_callbacks | create_code | POST | Ready to send to tasks | %s', item)

        try:
            tasks.code_deploy.delay(item)
        except Exception as e:
            log.debug('eve_callbacks | create_code | POST | Deploy failed | %s | %s', item, e)
            abort(500, 'A failure occurred during deployment. Error: {0}'.format(e))
