import sys
import logging
import random
import json
import ssl

from eve import Eve
from flask import abort, jsonify, g, make_response
from hashlib import sha1
from bson import ObjectId
from atlas import tasks
from atlas import utilities
from atlas.config import *


path = '/data/code'
if path not in sys.path:
    sys.path.append(path)


# Callbacks
def pre_post_callback(resource, request):
    """
    :param resource: resource accessed
    :param request: flask.request object
    """
    app.logger.debug('POST to {0} resource\nRequest:\n{1}'.format(resource, request.json))


def pre_delete_code_callback(request, lookup):
    """
    Make sure no instances are using the code.

    :param request: flask.request object
    :param lookup:
    """
    code = utilities.get_single_eve('code', lookup['_id'])
    app.logger.debug(code)

    # Check for code that declares this as a dependency.
    code_query = 'where={{"meta.dependency":"{0}"}}'.format(code['_id'])
    code_items = utilities.get_eve('code', code_query)
    app.logger.debug(code_items)
    if not code_items['_meta']['total'] == 0:
        code_list = []
        for item in code_items['_items']:
            # List of code items that declare this one as a dependency.
            code_list.append(item['_id'])
        code_list_full = ', '.join(code_list)
        app.logger.error('Code item is a dependency of one or more code items:\n{0}'.format(code_list_full))
        abort(409, 'A conflict happened while processing the request. Code item is a dependency of one or more code items.')

    # Check for instances using this piece of code.
    if code['meta']['code_type'] in ['module', 'theme', 'library']:
        code_type = 'package'
    else:
        code_type = code['meta']['code_type']
    app.logger.debug(code_type)
    instance_query = 'where={{"code.{0}":"{1}"}}'.format(code_type, code['_id'])
    instances = utilities.get_eve('instances', instance_query)
    app.logger.debug(instances)
    if not instances['_meta']['total'] == 0:
        instance_list = []
        for instance in instances['_items']:
            # Create a list of instances that use this code item.
            # If 'sid' is a key in the instance dict use it, otherwise use '_id'.
            if instance.get('sid'):
                instance_list.append(instance['sid'])
            else:
                instance_list.append(instance['_id'])
        instance_list_full = ', '.join(instance_list)
        app.logger.error('Code item is in use by one or more instances:\n{0}'.format(instance_list_full))
        abort(409, 'A conflict happened while processing the request. Code item is in use by one or more instances.')


def on_insert_instances_callback(items):
    """
    Assign a sid, an update group, db_key, any missing code, and date fields.

    :param items: List of dicts for items to be created.
    """
    app.logger.debug(items)
    for item in items:
        app.logger.debug(item)
        if item['type'] == 'express' and not item['f5only']:
            if not item.get('sid'):
                item['sid'] = 'p1' + sha1(utilities.randomstring()).hexdigest()[0:10]
            if not item.get('path'):
                item['path'] = item['sid']
            if not item.get('update_group'):
                item['update_group'] = random.randint(0, 2)
            # Add default core and profile if not set.
            # The 'get' method checks if the key exists.
            if item.get('code'):
                if not item['code'].get('core'):
                    item['code']['core'] = utilities.get_current_code(name=default_core, type='core')
                if not item['code'].get('profile'):
                    item['code']['profile'] = utilities.get_current_code(name=default_profile, type='profile')
            else:
                item['code'] = {}
                item['code']['core'] = utilities.get_current_code(name=default_core, type='core')
                item['code']['profile'] = utilities.get_current_code(name=default_profile, type='profile')
            if not item['import_from_inventory']:
                date_json = '{{"created":"{0} GMT"}}'.format(item['_created'])
                item['dates'] = json.loads(date_json)
            app.logger.debug('Ready to create item\n{0}'.format(item))


def on_inserted_instances_callback(items):
    """
    Provision Express instances.

    :param items: List of dicts for instances to be provisioned.
    """
    app.logger.debug(items)
    for item in items:
        app.logger.debug(item)
        if item['type'] == 'express' and not item['f5only']:
            app.logger.debug(item)
            # Create statistics item
            statistics_payload = {}
            # Need to get the string out of the ObjectID.
            statistics_payload['instance'] = str(item['_id'])
            app.logger.debug('Create Statistics item\n{0}'.format(statistics_payload))
            statistics = utilities.post_eve(resource='statistics', payload=statistics_payload)
            app.logger.debug(statistics)
            item['statistics'] = str(statistics['_id'])
            app.logger.debug('Ready to send to Celery\n{0}'.format(item))
            if not item['import_from_inventory']:
                tasks.instance_provision.delay(item)
            else:
                tasks.instance_import_from_inventory.delay(item)


def on_insert_code_callback(items):
    """
    Deploy code onto servers as the items are created.

    If a new code item 'is_current', PATCH 'is_current' code with the same name
    and type to no longer be current.

    :param items: List of dicts for items to be created.
    """
    app.logger.debug(items)
    for item in items:
        if item.get('meta') and item['meta'].get('is_current') and item['meta']['is_current'] == True:
            # Need a lowercase string when querying boolean values. Python
            # stores it as 'True'.
            query = 'where={{"meta.name":"{0}","meta.code_type":"{1}","meta.is_current": {2}}}'.format(item['meta']['name'], item['meta']['code_type'], str(item['meta']['is_current']).lower())
            code_get = utilities.get_eve('code', query)
            app.logger.debug(code_get)
            if code_get['_meta']['total'] != 0:
                for code in code_get['_items']:
                    request_payload = {'meta.is_current': False}
                    utilities.patch_eve('code', code['_id'], request_payload)
        app.logger.debug('Ready to send to Celery\n{0}'.format(item))
        tasks.code_deploy.delay(item)


def pre_delete_instance_callback(request, lookup):
    """
    Remove instance from servers right before the item is removed.

    :param request: flask.request object
    :param lookup:
    """
    app.logger.debug(lookup)
    instance = utilities.get_single_eve('instances', lookup['_id'])
    tasks.instance_remove.delay(instance)


def on_delete_item_code_callback(item):
    """
    Remove code from servers right before the item is removed.

    :param item:
    """
    app.logger.debug(item)
    tasks.code_remove.delay(item)


def on_update_code_callback(updates, original):
    """
    Update code on the servers as the item is updated.

    :param updates:
    :param original:
    """
    app.logger.debug(updates)
    app.logger.debug(original)
    # If this 'is_current' PATCH code with the same name and code_type.
    if updates.get('meta') and updates['meta'].get('is_current') and updates['meta']['is_current'] == True:
        # If the name and code_type are not changing, we need to load them from
        # the original.
        name = updates['meta']['name'] if updates['meta'].get('name') else original['meta']['name']
        code_type = updates['meta']['code_type'] if updates['meta'].get('code_type') else original['meta']['code_type']

        query = 'where={{"meta.name":"{0}","meta.code_type":"{1}","meta.is_current": {2}}}'.format(name, code_type, str(updates['meta']['is_current']).lower())
        code_get = utilities.get_eve('code', query)
        # TODO: Filter out the item we are updating.
        app.logger.debug(code_get)

        for code in code_get['_items']:
            request_payload = {'meta.is_current': False}
            utilities.patch_eve('code', code['_id'], request_payload)

    # We need the whole record so that we can manipulate code in the right
    # place.
    # Copy 'original' to a new dict, then update it with values from 'updates'
    # to create an item to deploy. Need to do the same process for meta first,
    # otherwise the update will fully overwrite.
    if updates.get('meta'):
        meta = original['meta'].copy()
        meta.update(updates['meta'])
    updated_item = original.copy()
    updated_item.update(updates)
    if updates.get('meta'):
        updated_item['meta'] = meta

    app.logger.debug('Ready to hand to Celery\n{0}\n{1}'.format(updated_item, original))
    tasks.code_update.delay(updated_item, original)


def on_update_instances_callback(updates, original):
    """
    Update an instance.

    :param updates:
    :param original:
    """
    app.logger.debug('Update instance\n{0}\n\n{1}'.format(updates, original))
    instance_type = updates['type'] if updates.get('type') else original['type']
    if instance_type == 'express':
        instance = original.copy()
        instance.update(updates)
        # Only need to rewrite the nested dicts if they got updated.
        if updates.get('code'):
            code = original['code'].copy()
            code.update(updates['code'])
            instance['code'] = code
            dependencies_list = []
            id_list = []
            for key, value in updates['code'].iteritems():
                if key == 'package':
                    if value not in dependencies_list:
                        # Use 'extend' vs 'append' to prevent nested list.
                        dependencies_list.extend(value)
                app.logger.debug(dependencies_list)
            # List of declared dependencies is built, now we need to recurse.
            if dependencies_list:
                for value in dependencies_list:
                    # Need to convert ObjectID to string for lookup.
                    code_item = utilities.get_single_eve('code', value)
                    app.logger.debug(code_item)
                    if code_item['meta'].get('dependency'):
                        for key, value in code_item['meta'].iteritems():
                            if key == 'dependency':
                                if value not in dependencies_list:
                                    for list_item in value:
                                        # Convert each id string to a proper
                                        # ObjectID.
                                        id_list.append(ObjectId(list_item))
                                    dependencies_list.extend(id_list)
                app.logger.debug(dependencies_list)
                # Time to replace the package list.
                updates['code']['package'] = dependencies_list
        if updates.get('dates'):
            dates = original['dates'].copy()
            dates.update(updates['dates'])
            instance['dates'] = dates
        if updates.get('settings'):
            settings = original['settings'].copy()
            settings.update(updates['settings'])
            instance['settings'] = settings

        if updates.get('status'):
            if updates['status'] in ['installing', 'launching', 'take_down','restore']:
                if updates['status'] == 'installing':
                    date_json = '{{"assigned":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'launching':
                    date_json = '{{"launched":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'take_down':
                    date_json = '{{"taken_down":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'restore':
                    date_json = '{{"taken_down":""}}'.format(updates['_updated'])

                updates['dates'] = json.loads(date_json)

        app.logger.debug('Ready to hand to Celery\n{0}\n{1}'.format(instance, updates))
        tasks.instance_update.delay(instance, updates, original)


def on_update_commands_callback(updates, original):
    """
    Run commands when API endpoints are called.

    :param updates:
    :param original:
    """
    item = original.copy()
    item.update(updates)
    app.logger.debug('Update command\n\nItem\n{0}\n\nUpdate\n{1}\n\nOriginal\n{2}'.format(item, updates, original))
    tasks.command_prepare.delay(item)


# Update user fields on all events. If the update is coming from Drupal, it
# will use the client_username for authentication and include the field for
# us. If someone is querying the API directly, they will user their own
# username and we need to add that.
def pre_insert(resource, items):
    username = g.get('username', None)
    if username is not None:
        for item in items:
            item['created_by'] = username
            item['modified_by'] = username


def pre_update(resource, updates, original):
    # Only update if a username was not provided.
    if not updates.get('modified_by'):
        username = g.get('username', None)
        if username is not None:
            if username is not service_account_username:
                updates['modified_by'] = username


def pre_replace(resource, item, original):
    # Only update if a username was not provided.
    if not item.get('modified_by'):
        username = g.get('username', None)
        if username is not None:
            if username is not service_account_username:
                item['modified_by'] = username


"""
Setup the application and logging.
"""
# Tell Eve to use Basic Auth and where our data structure is defined.
settings = '{0}/config_data_structure.py'.format(atlas_location)
app = Eve(auth=utilities.AtlasBasicAuth, settings=settings)
# TODO: Remove debug mode.
app.debug = True

# Specific callbacks.
# Use pre event hooks if there is a chance you want to abort.
# Use DB hooks if you want to modify data on the way in.

# Request event hooks.
app.on_pre_POST += pre_post_callback
app.on_pre_DELETE_code += pre_delete_code_callback
app.on_pre_DELETE_instances += pre_delete_instance_callback
# Database event hooks.
app.on_insert_code += on_insert_code_callback
app.on_insert_instances += on_insert_instances_callback
app.on_inserted_instances += on_inserted_instances_callback
app.on_update_code += on_update_code_callback
app.on_update_instances += on_update_instances_callback
app.on_update_commands += on_update_commands_callback
app.on_delete_item_code += on_delete_item_code_callback
app.on_insert += pre_insert
app.on_update += pre_update
app.on_replace += pre_replace



@app.errorhandler(409)
def custom409(error):
    response = jsonify({'message': error.description})
    response.status_code = 409
    return response


@app.route('/version')
def version():
    response = make_response(version_number)
    return response


if __name__ == '__main__':
    # Enable logging to 'atlas.log' file
    handler = logging.FileHandler('atlas.log')
    # The default log level is set to WARNING, so we have to explicitly set the
    # logging level to Debug.
    app.logger.setLevel(logging.DEBUG)
    # Append the handler to the default application logger
    app.logger.addHandler(handler)

    # This goes last.
    app.run(host='0.0.0.0', ssl_context='adhoc')
