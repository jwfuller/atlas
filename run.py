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


atlas_path = '/data/code'
if atlas_path not in sys.path:
    sys.path.append(atlas_path)


# TODO Route - Delete

# TODO: Migrate Legacy instances to Routes
# TODO: Redirects
#   TODO: Workflow for switching routes and converting old one to redirect.
#   TODO: Move routes to site record
# TODO: Figure out what we need to do to make site required

# Instances:
#   TODO: Do we create multiple instances of a site that is not launched?
#   TODO: Can an instance be transferred to another site? Thinking about training instances: for Bundles training, clone instances could either remain under a long running training site or be moved into a short lived site for the class.

# TODO: Route/Instance
#   TODO: Do we allow changing of primary route for launched instance? No
#   TODO: Do we allow changing of 'instance_id' for active routes? Not for pool routes
#   TODO: Do we allow deactivation of primary route for launched instance? No, deactivate from instance.
#   TODO: What happens to routes when you take down or delete an instance? take down - deactivate, delete - delete
# TODO: Site/Instance
#   TODO: Do we allow more than one launched instance per site? Strong No

# Callbacks
def pre_post_callback(resource, request):
    """
    :param resource: resource accessed
    :param request: flask.request object
    """
    app.logger.debug('POST to {0} resource\nRequest:\n{1}'.format(resource, request.json))


def pre_post_route_callback(request):
    """
    If route is an 'express' route and has an 'instance_id', check to see if the instance already
    has a primary route and reject if it does.

    :param resource: resource accessed
    :param request: flask.request object
    """
    if hasattr(request, 'instance_id') and request['route_type'] == 'poolb-express':
        instance = utilities.get_single_eve('instance', request['instance_id'])
        if instance.get('routes'):
            if instance['routes'].get('primary_route'):
                app.logger.error('Route | POST | Instance already has Primary | %s', instance)
                abort(409, 'Error: Instance already has Primary Route.')


def pre_patch_route_callback(request, lookup):
    """
    If route is an 'express' route and has an 'instance_id', check to see if the instance already
    has a primary route and reject if it does.

    Do not allow updating of 'source' field.

    :param request: flask.request object
    :param lookup: resource accessed
    """
    # TODO: Determine if we want to reject updates to Source.
    app.logger.debug('PATCH | Route | Request - %s | Lookup - %s', request, lookup)
    if hasattr(request, 'instance_id') and request['route_type'] == 'poolb-express':
        instance = utilities.get_single_eve('instance', request['instance_id'])
        if instance.get('routes'):
            if instance['routes'].get('primary_route'):
                app.logger.error('Route | PATCH | Instance already has Primary | %s', instance)
                abort(409, 'Error: Instance already has Primary Route.')
    if hasattr(request, 'source'):
        app.logger.error('Route | PATCH | Cannot modify source | %s', instance)
        abort(409, 'Error: Cannot modify "source" value for a Route.')


def pre_delete_route_callback(request, lookup):
    """
    Make sure that this is not the active primary route for a launched instances.

    :param request: flask.request object
    :param lookup:
    """
    route = utilities.get_single_eve('route', lookup['_id'])
    app.logger.debug('Route | Delete | %s', route)
    instance_query = 'where={{"route.primary_route":"{0}"}}'.format(route['_id'])
    instances = utilities.get_eve('instance', instance_query)
    app.logger.debug('Route | Delete | Instances| %s', instances)
    if not instances['_meta']['total'] == 0:
        instance_list = []
        for instance in instances['_items']:
            if instance['status'] in ['launched', 'launching']:
                # Create a list of instances that use this route.
                # If 'sid' is a key in the instance dict use it, otherwise use '_id'.
                if instance.get('sid'):
                    instance_list.append(instance['sid'])
                else:
                    instance_list.append(instance['_id'])
                instance_list_full = ', '.join(instance_list)
        app.logger.error('Route | Delete | Route in Use Error | Instances | %s', instance_list_full)
        abort(409, 'Error: Route item is in use by an instance - {0}.'.format(instance_list_full))


def pre_delete_code_callback(request, lookup):
    """
    Make sure no instances are using the code.

    :param request: flask.request object
    :param lookup:
    """
    code = utilities.get_single_eve('code', lookup['_id'])
    app.logger.debug(code)

    # Check for instances using this piece of code.
    if code['meta']['code_type'] in ['module', 'theme', 'library']:
        code_type = 'package'
    else:
        code_type = code['meta']['code_type']
    app.logger.debug(code_type)
    instance_query = 'where={{"code.{0}":"{1}"}}'.format(code_type, code['_id'])
    instances = utilities.get_eve('instance', instance_query)
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
        app.logger.error('Code Delete | Code in Use Error | Instances | %s', instance_list_full)
        abort(409, 'Error: Code item is in use by one or more instances.')


def on_insert_instance_callback(items):
    """
    Assign a sid, an update group, db_key, any missing code, and date fields.

    :param items: List of dicts for items to be created.
    """
    app.logger.debug(items)
    for item in items:
        app.logger.debug(item)
        if item['type'] == 'express':
            if not item.get('sid'):
                item['sid'] = 'p1' + sha1(utilities.randomstring()).hexdigest()[0:10]
            if not item.get('update_group'):
                item['update_group'] = random.randint(0, 2)
            # Add default core and profile if not set.
            # The 'get' method checks if the key exists.
            if item.get('code'):
                if not item['code'].get('core'):
                    item['code']['core'] = utilities.get_current_code(
                        name=default_core, type='core')
                if not item['code'].get('profile'):
                    item['code']['profile'] = utilities.get_current_code(
                        name=default_profile, type='profile')
            else:
                item['code'] = {}
                item['code']['core'] = utilities.get_current_code(
                    name=default_core, type='core')
                item['code']['profile'] = utilities.get_current_code(
                    name=default_profile, type='profile')
            if not item['import_from_inventory']:
                date_json = '{{"created":"{0} GMT"}}'.format(item['_created'])
                item['dates'] = json.loads(date_json)
            app.logger.debug('Ready to create item| %s', item)


def on_inserted_instance_callback(items):
    """
    Provision Express instances.

    :param items: List of dicts for instances to be provisioned.
    """
    app.logger.debug(items)
    for item in items:
        app.logger.debug(item)
        if item['type'] == 'express':
            app.logger.debug(item)
            # Create statistics item
            statistics_payload = {}
            # Need to get the string out of the ObjectID.
            statistics_payload['instance'] = str(item['_id'])
            app.logger.debug('Create Statistics item\n{0}'.format(statistics_payload))
            statistics = utilities.post_eve(resource='statistics', payload=statistics_payload)
            app.logger.debug(statistics)
            item['statistics'] = str(statistics['_id'])

            app.logger.debug('Ready to send to Celery| %s}', item)
            tasks.instance_provision.delay(item)


def on_inserted_route_callback(items):
    """
    If a new route is configured correctly, launch the associated instance.

    :param items: List of dicts for new routes.
    """
    app.logger.debug('Route | Inserted Callback | Items | %s', items)
    for item in items:
        app.logger.debug('Route | Inserted Callback | Single Item | %s', item)
        if item['route_status'] == 'active':
            if item.get('instance_id'):
                if item['route_type'] == 'poolb-express':
                    instance = utilities.get_single_eve('instance', item['instance_id'])
                    app.logger.debug('Route | Get Instance | %s', instance)
                    if instance['status'] == 'installed':
                        instance_payload = {
                            'status': 'launching',
                            'path': item['source'],
                            'routes': {
                                'primary_route': str(item['_id'])
                            }
                        }
                        # Symlink creation is handled by the launch Fabric task.
                        launch_instance = utilities.patch_eve(
                            'instance', item['instance_id'], instance_payload)
                        app.logger.debug('Route | Launch Instance | %s', launch_instance)
                # TODO: Redirects
                elif item['route_type'] == 'redirect':
                    if environment is not 'local':
                        instance = utilities.get_single_eve('instance', item['instance_id'])
                        app.logger.debug('Route | Get instance | %s', instance)
                        if instance.get('redirects'):
                            redirects = instance['redirects']
                            redirects.append(item['_id'])
                        instance_payload = {
                            'routes': {
                                'redirect': redirects
                            }
                        }
                        update_instance = utilities.patch_eve(
                            'instance', item['instance_id'], instance_payload)
                        app.logger.debug('Route | Update Instance | %s', update_instance)
            # Route is active, update load balancer.
            if environment is not 'local':
                tasks.update_load_balancers.delay()
        elif item['route_status'] == 'inactive':
            if item['route_type'] == 'poolb-express' and item.get('instance_id'):
                instance = utilities.get_single_eve('instance', item['instance_id'])
                app.logger.debug('Route | Get Instance | %s', instance)
                instance_payload = {
                    'routes': {
                        'primary_route': str(item['_id'])
                    }
                }
                update_instance = utilities.patch_eve(
                    'instance', item['instance_id'], instance_payload)
                app.logger.debug('Route | Update Instance | %s', update_instance)

        if item.get('site_id'):
            site = utilities.get_single_eve('site', item['site_id'])
            app.logger.debug('Route | Get Site | %s', site)
            if site.get('routes'):
                routes = site['routes']
                routes.append(item['_id'])
            else:
                routes = [site['routes']]
            site_payload = {
                'routes': routes
            }
            update_site = utilities.patch_eve('site', item['site_id'], site_payload)
            app.logger.debug('Route | Update Site | %s', update_site)


def on_insert_code_callback(items):
    """
    Deploy code onto servers as the items are created.

    If a new code item 'is_current', PATCH 'is_current' code with the same name
    and type to no longer be current.

    :param items: List of dicts for items to be created.
    """
    app.logger.debug(items)
    for item in items:
        if item.get('meta') and item['meta'].get('is_current') and item['meta']['is_current'] is True:
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
    instance = utilities.get_single_eve('instance', lookup['_id'])
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
    if updates.get('meta') and updates['meta'].get('is_current') and updates['meta']['is_current'] is True:
        # If the name and code_type are not changing, we need to load them from
        # the original.
        name = updates['meta']['name'] if updates['meta'].get('name') else original['meta']['name']
        code_type = updates['meta']['code_type'] if updates['meta'].get('code_type') else original['meta']['code_type']

        query = 'where={{"meta.name":"{0}","meta.code_type":"{1}","meta.is_current": {2}}}'.format(
            name, code_type, str(updates['meta']['is_current']).lower())
        code_get = utilities.get_eve('code', query)
        # TODO: Filter out the item we are updating.
        app.logger.debug(code_get)

        for code in code_get['_items']:
            request_payload = {'meta.is_current': False}
            utilities.patch_eve('code', code['_id'], request_payload)

    # We need the whole record so that we can manipulate code in the right place. Copy 'original' to
    # a new dict, then update it with values from 'updates' to create an item to deploy. Need to do 
    # the same process for meta first, otherwise the update will fully overwrite.
    if updates.get('meta'):
        meta = original['meta'].copy()
        meta.update(updates['meta'])
    updated_item = original.copy()
    updated_item.update(updates)
    if updates.get('meta'):
        updated_item['meta'] = meta

    app.logger.debug('Ready to hand to Celery | %s | %s', updated_item, original)
    tasks.code_update.delay(updated_item, original)


def on_update_instance_callback(updates, original):
    """
    Update an instance.

    :param updates:
    :param original:
    """
    app.logger.debug('Update instance | %s | %s', updates, original)
    instance_type = updates['type'] if updates.get('type') else original['type']
    if instance_type == 'express':
        instance = original.copy()
        instance.update(updates)
        # Only need to rewrite the nested dicts if they got updated.
        if updates.get('code'):
            code = original['code'].copy()
            code.update(updates['code'])
            instance['code'] = code
        if updates.get('dates'):
            dates = original['dates'].copy()
            dates.update(updates['dates'])
            instance['dates'] = dates
        if updates.get('settings'):
            settings = original['settings'].copy()
            settings.update(updates['settings'])
            instance['settings'] = settings

        if updates.get('status'):
            if updates['status'] in ['installing', 'launching', 'take_down', 'restore']:
                if updates['status'] == 'installing':
                    date_json = '{{"assigned":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'launching':
                    date_json = '{{"launched":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'locked':
                    date_json = '{{"locked":""{0} GMT}}'.format(updates['_updated'])
                elif updates['status'] == 'take_down':
                    date_json = '{{"taken_down":"{0} GMT"}}'.format(updates['_updated'])
                elif updates['status'] == 'restore':
                    date_json = '{{"taken_down":"{0} GMT"}}'.format(updates['_updated'])

                updates['dates'] = json.loads(date_json)

        app.logger.debug('Ready to hand to Celery | %s | %s', instance, updates)
        tasks.instance_update.delay(instance, updates, original)


def on_update_route_callback(updates, original):
    """
    Update a route:

    See also pre_patch_route_callback().

    TODO: Redirect - If changing from Express, remove symlink

    :param updates:
    :param original:
    """
    app.logger.debug('Route | Update | Updates - %s | Original - %s', updates, original)
    route_status = updates['route_status'] if updates.get('route_status') else original['route_status']
    # Activate a route
    if updates.get('route_status') and route_status == 'active':
        route_type = updates['route_type'] if updates.get('route_type') else original['route_type']
        if route_type == 'poolb-express':
            instance_id = updates['instance_id'] if updates.get('instance_id') else original['instance_id']
            instance = utilities.get_single_eve('instance', instance_id)
            app.logger.debug('Route | Update | Get Instance | %s', instance)
            route_source = updates['source'] if updates.get('source') else original['source']
            if instance['status'] == 'installed':
                instance_payload = {
                    'status': 'launching',
                    'path': route_source,
                    'routes': {
                        'primary_route': str(original['_id'])
                    }
                }
                # Symlink creation is handled by the launch Fabric task.
                launch_instance = utilities.patch_eve('instance', instance_id, instance_payload)
                app.logger.debug('Route | Update | Launch Instance | %s', launch_instance)
        # TODO: Redirects
        elif route_type == 'redirect':
            instance_id = updates['instance_id'] if updates.get('instance_id') else original['instance_id']
            if environment is not 'local':
                instance = utilities.get_single_eve('instance', instance_id)
                app.logger.debug('Route | Update | Get instance | %s', instance)
                if instance.get('redirects'):
                    redirects = instance['redirects']
                    redirects.append(original['_id'])
                instance_payload = {
                    'routes': {
                        'redirect': redirects
                    }
                }
                update_instance = utilities.patch_eve('instance', instance_id, instance_payload)
                app.logger.debug('Route | Update | Patch Instance | %s', update_instance)
        # Route has been activated, update load balancer
        if environment is not 'local':
            tasks.update_load_balancers.delay()
    # TODO: Deactivate a Route
    elif updates.get('route_status') and route_status == 'inactive':
        app.logger.debug('Route | Update | Deactivate Route | %s', updates)
        if environment is not 'local':
            tasks.update_load_balancers.delay()
    # Update an active Route
    # TODO: Redirects - This is most likely to impact redirects.
    elif route_status == 'active':
        app.logger.debug('Route | Update | Active Route | %s', updates)
    # Update an inactive Route
    elif route_status == 'inactive':
        if route_type == 'poolb-express' and updates.get('instance_id'):
            instance = utilities.get_single_eve('instance', instance_id)
            app.logger.debug('Route | Get Instance | %s', instance)
            instance_payload = {
                'routes': {
                    'primary_route': str(original['_id'])
                }
            }
            update_instance = utilities.patch_eve('instance', instance_id, instance_payload)
            app.logger.debug('Route | Update | Update Instance | %s', update_instance)

    if updates.get('site_id'):
        site = utilities.get_single_eve('site', updates['site_id'])
        app.logger.debug('Route | Update | Get Site | %s', site)
        if site.get('routes'):
            routes = site['routes']
            routes.append(updates['_id'])
        else:
            routes = [site['routes']]
        site_payload = {
            'routes': routes
        }
        update_site = utilities.patch_eve('site', updates['site_id'], site_payload)
        app.logger.debug('Route | Update | Update Site | %s', update_site)


def on_update_commands_callback(updates, original):
    """
    Run commands when API endpoints are called.

    :param updates:
    :param original:
    """
    item = original.copy()
    item.update(updates)
    app.logger.debug('Update command | Item | %s | Update | %s | Original | %s',
                     item, updates, original)
    tasks.command_prepare.delay(item)


# Update user fields on all events. If the update is coming from Drupal, it will use the 
# client_username for authentication and include the field for us. If someone is querying the API 
# directly, they will user their own username and we need to add that.
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
app.on_pre_POST_route += pre_post_route_callback
app.on_pre_DELETE_code += pre_delete_code_callback
app.on_pre_DELETE_instance += pre_delete_instance_callback
# Database event hooks.
app.on_insert_code += on_insert_code_callback
app.on_insert_instance += on_insert_instance_callback
app.on_inserted_instance += on_inserted_instance_callback
app.on_inserted_route += on_inserted_route_callback
app.on_update_code += on_update_code_callback
app.on_update_instance += on_update_instance_callback
app.on_update_commands += on_update_commands_callback
app.on_update_route += on_update_route_callback
# TODO: If route is not a redirect, check to see is primary route for a launched instance, reject if it is.
#app.on_delete_item_route += on_delete_item_route_callback
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
