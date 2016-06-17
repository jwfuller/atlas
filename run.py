import sys
import ldap
import logging
import json
import datetime

from eve import Eve
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from eve.utils import config

from atlas.config import allowed_users, ldap_server, ldap_org_unit, ldap_dns_domain_name
from atlas.tasks import *

path = '/data/code'
if path not in sys.path:
    sys.path.append(path)

# Callbacks
def pre_post_callback(resource, request):
    """
    Callback for POST to all endpoints.

    Allows us to hook into any create event *before* the Mongo object is created.

    :param resource: resource accessed
    :param request: original flask.request object
    """
    # Request object brings the POST information as a MultiDict.
    app.logger.debug(request.form)
    # TODO: Check to see if a record with the same combination of fields exists.
    if resource == 'code':
        app.logger.debug(request.form)
        if request.form['name']:
            app.logger.debug(request.form['name'])
    elif resource == 'site':
        app.logger.debug(request.form)


# def post_post_code_callback(resource, request, payload):
    """
    Callback for POST to `code` endpoint.

    Allows us to hook into 'code' create events *after* the Mongo object has been created.

    :param resource: resource accessed
    :param request: original flask.request object
    :param payload: response payload
    :return:
    """
    # Request object brings the POST information as a MultiDict.
    # app.logger.debug(request.form)
    # TODO: Deploy code.



# Utilities
class AtlasBasicAuth(BasicAuth):
    """
    Basic Authentication
    """
    def check_auth(self, username, password, allowed_roles=['default'],
                   resource='default', method='default'):
        # Check if username is in the array of allowed users defined in config_local.py
        if username not in allowed_users:
            return False
        """
        Test credentials against LDAP.

        Initialize LDAP. The initialize() method returns an LDAPObject object, which contains methods for performing LDAP operations and retrieving information about the LDAP connection and transactions.
        """
        l = ldap.initialize(ldap_server)

        # Start the connection in a secure manner. Catch any errors and print
        # the description if present.
        try:
            l.start_tls_s()
        except ldap.LDAPError, e:
            print e.message['info']
            if type(e.message) == dict and e.message.has_key('desc'):
                print e.message['desc']
            else:
                print e

        ldap_distinguished_name = "uid={0},ou={1},{2}".format(username,
                                                              ldap_org_unit,
                                                              ldap_dns_domain_name)
        app.logger.debug(ldap_distinguished_name)

        try:
            """
            Try a synchronous bind (we want synchronous so that the command is blocked until the bind gets a result. If you can bind, the credentials are valid.
            """
            result = l.simple_bind_s(ldap_distinguished_name, password)
            app.logger.info(
                'LDAP - {0} - Bind successful'.format(username))
            return True
        except ldap.INVALID_CREDENTIALS:
            app.logger.info(
                'LDAP - {0} - Invalid credentials'.format(username))
            print "Username or Password is incorrect."

        # Apparently this was a bad login attempt
        app.logger.info('LDAP - {0} - Bind failed'.format(username))
        return False

class AtlasValidator(Validator):
    def _validate_unique_combination(self, unique_combination, field, value):
        """ Enables validation for a 'unique_combination' schema elements.

        Based on https://github.com/nicolaiarocci/eve/blob/master/eve/io/mongo/validation.py

        :param unique_combination: Boolean, should field be considered as part of the unique combination.
        :param field: Field name
        :param value: Field value
        """
        self._is_combination_unique(unique_combination, field, value, {})

    def _is_combination_unique(self, unique_combination, field, value, query):
        """ Validates that the values of a set of fields is unique.

        """
        if unique_combination:
            query[field] = value
            app.logger.debug(query)

            # Get information about the current resource.
            resource_config = config.DOMAIN[self.resource]
            app.logger.debug(resource_config)
            # We are not going to exclude soft deleted documents but we want
            # to exclude the current document.
            if self._id:
                id_field = resource_config['id_field']
                query[id_field] = {'$ne': self._id}
                app.logger.debug(query)

            # we perform the check on the native mongo driver (and not on
            # app.data.find_one()) because in this case we don't want the usual
            # (for eve) query injection to interfere with this validation. We
            # are still operating within eve's mongo namespace anyway.

            datasource, _, _, _ = app.data.datasource(self.resource)
            if app.data.driver.db[datasource].find_one(query):
                self._error(field, "value '%s' is not unique" % value)


# TODO: Add in a message and/or result broker, I don't want to use the DB. It is currently 41 GB for inventory.


"""
Setup the application and logging.
"""
# Tell Eve to use Basic Auth where our data structure is defined.
app = Eve(auth=AtlasBasicAuth,
          settings="/data/code/atlas/config_data_structure.py",
          validator=AtlasValidator)
# TODO: Remove debug mode.
app.debug = True

# Add specific callbacks
# Pattern is: `atlas.on_{Hook}_{Method}_{Resource}`
app.on_pre_POST += pre_post_callback
# app.on_post_POST_code += post_post_code_callback

if __name__ == '__main__':
    # Enable logging to 'atlas.log' file
    # TODO: Figure out why the stuff shows in the apache error log, not this location.
    handler = logging.FileHandler('/var/log/celery/atlas.log')
    # The default log level is set to WARNING, so we have to explicitly set the
    # logging level to Debug.
    app.logger.setLevel(logging.BEDUG)
    # Append the handler to the default application logger
    app.logger.addHandler(handler)

    # This goes last.
    app.run(host='0.0.0.0', ssl_context='adhoc')
