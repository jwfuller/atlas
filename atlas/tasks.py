"""
Celery tasks for Atlas.
"""
import sys
import json
from logging import getLogger

from celery import Celery
from celery import group
from celery.utils.log import get_task_logger
from fabric.api import execute

from atlas import config_celery
from atlas import fabric_tasks
from atlas import utilities
from atlas.config import (atlas_path, atlas_infrastructure, atlas_environment)

# Setup a sub-logger
log = getLogger('atlas.tasks')
# [filename] | [endpoint] | [item _id] | [action/method] | [message]

if atlas_path not in sys.path:
    sys.path.append(atlas_path)

celery = Celery('tasks')
celery.config_from_object(config_celery)


@celery.task
def code_deploy(item):
    """
    Deploy git repositories to the appropriate places.

    :param item: The flask request.json object.
    :return:
    """
    log.debug('tasks | code | %s | deploy', item['_id'])
    # Setup the Slack notification payload, we will override some values in the case of failure.
    slack_fallback = '{0} - {1}'.format(item['meta']['name'], item['meta']['version'])
    slack_payload = {
        "text": 'Code Deploy',
        "username": 'Atlas',
        "attachments": [
            {
                "fallback": slack_fallback,
                "color": 'good',
                "author_name": item['created_by'],
                "title": 'Success',
                "fields": [
                    {
                        "title": "Infrastructure",
                        "value": atlas_infrastructure,
                        "short": True
                    },
                    {
                        "title": "Environment",
                        "value": atlas_environment,
                        "short": True
                    },
                    {
                        "title": "Name",
                        "value": item['meta']['name'],
                        "short": True
                    },
                    {
                        "title": "Version",
                        "value": item['meta']['version'],
                        "short": True
                    },
                    {
                        "title": "Current",
                        "value": item['meta']['is_current'],
                        "short": True
                    }
                ],
            }
        ],
        "user": item['created_by']
    }
    # Dynamically define the host list as call is made to Fabric, allows us to support pools.
    fabric_hosts = utilities.fabric_hosts('code')
    try:
        execute(fabric_tasks.code_deploy, hosts=fabric_hosts, item=item)
    except Exception as e:
        log.debug('tasks | code | %s | deploy | Deploy failed | %s', item['_id'], e)
        error_json = json.dumps(e)
        slack_payload['attachments'][0]['title'] = 'Error'
        slack_payload['attachments'][0]['color'] = 'danger'
        slack_payload['attachments'].append(
            {
                "fallback": 'Error message',
                # A lighter red.
                "color": '#ee9999',
                "fields": [
                    {
                        "title": "Error message",
                        "value": error_json,
                        "short": False
                    }
                ]
            }
        )

        utilities.slack_notification(slack_payload)
        raise

    utilities.slack_notification(slack_payload)
