"""
Utility functions.
"""
import json
import sys
import smtplib
from email.mime.text import MIMEText
from logging import getLogger

import ldap
import random
import requests
from eve.auth import BasicAuth
from eve.methods.get import get_internal, getitem_internal
from eve.methods.patch import patch_internal
from flask import g

from atlas.config_servers import servers
from atlas.config import (atlas_path, atlas_environment, allowed_users, ldap_server, ldap_org_unit, 
                          ldap_dns_domain_name, send_emails, email_from_address, email_host,
                          email_port, email_username, email_password, atlas_url, atlas_username,
                          atlas_password, ssl_verification, slack_notifications, slack_url,
                          slack_username)


# Setup a sub-logger
# Best practice is to setup sub-loggers rather than passing the main logger between different parts of the application.
# https://docs.python.org/3/library/logging.html#logging.getLogger and
# https://stackoverflow.com/questions/39863718/how-can-i-log-outside-of-main-flask-module
log = getLogger('atlas.utilities')
# [filename] | [endpoint] | [item _id] | [action/method] | [message]

if atlas_path not in sys.path:
    sys.path.append(atlas_path)


class AtlasBasicAuth(BasicAuth):
    """
    Basic Authentication
    """
    def check_auth(self, username, password, allowed_roles=['default'], resource='default', method='default'):
        # Check if username is in 'allowed users' defined in config_local.py
        if username not in allowed_users:
            return False
        # Test credentials against LDAP.
        # Initialize LDAP. The initialize() method returns an LDAPObject
        # object, which contains methods for performing LDAP operations and
        # retrieving information about the LDAP connection and transactions.
        l = ldap.initialize(ldap_server)

        # Start the connection in a secure manner. Catch any errors and print
        # the description if present.
        try:
            l.start_tls_s()
        except ldap.LDAPError, e:
            log.error('utilities | LDAP | %s', e.message['info'])
            if type(e.message) == dict and e.message.has_key('desc'):
                log.error('utilities | LDAP | %s', e.message['desc'])
            else:
                log.error('utilities | LDAP | %s', e)

        ldap_distinguished_name = "uid={0},ou={1},{2}".format(
            username, ldap_org_unit, ldap_dns_domain_name)
        log.debug('utilities | LDAP | ldap_distinguished_name - {0}'.format(ldap_distinguished_name))

        # Add the username as a Flask application global.
        g.username = username

        try:
            # Try a synchronous bind (we want synchronous so that the command
            # is blocked until the bind gets a result. If you can bind, the
            # credentials are valid.
            result = l.simple_bind_s(ldap_distinguished_name, password)
            log.info('utilities | LDAP | Auth successful - {0}'.format(username))
            return True
        except ldap.INVALID_CREDENTIALS:
            log.info('utilities | LDAP | Invalid credentials - {0}'.format(username))

        # Apparently this was a bad login attempt
        log.info('utilities | LDAP | Auth failed - {0} - {1}'.format(username, result))
        return False

###
# Internal API functions
###
def get_eve(endpoint, query=None, single=False, item_id=None):
    """
    Make internal get calls to the Atlas API.

    :param endpoint: string - endpoint to access
    :param query: argument string
    :param single: boolean True if querying for a single item from an endpoint.
    :param item_id: ObjectID for the single item.

    :return: dict of items that match the query string.
    """
    try:
        if query:
            # Using internal functions allows us to bypass authentication and rate limiting.
            result = get_internal(endpoint, **query)
        elif single:
            result = getitem_internal(endpoint, **{'_id': item_id})
        else:
            result = get_internal(endpoint)
    except Exception as e:
        log.error('utilities | get_eve | request failed | %s', e)
        raise

    log.debug('utilities | get_eve | request success | %s', result)
    return result


def patch_eve(endpoint, item_id, payload):
    """
    Make PATCH calls to the Atlas API.

    :param endpoint:
    :param item_id:
    :param payload:

    :return:
    """
    log.debug('utilities | patch_eve | endpoint - %s |  item_id - %s |  payload - %s', endpoint, item_id, payload)

    current_item = get_eve(endpoint, single=True, item_id=item_id)

    try:
        log.debug('utilities | patch_eve | current_item - %s', current_item)
        result = patch_internal(endpoint, payload=payload, **{'_id': current_item[0]['_id']})
    except Exception as e:
        log.error('utilities | patch_eve | patch failed | %s', e)
        raise

    log.debug('utilities | patch_eve | patch success | %s', result)
    return result

###
# Fabric helper functions
###
def fabric_hosts(endpoint, item=None, single=False):
    """
    Get a list of hosts to run Fabric commands against

    :param endpoint: string - [code, instance]
    :param item: string - Item to base list on
    :param single: boolean - Run on a single server
    """
    log.debug('utilities | fabric_hosts | endpoint - %s | item - %s | single - %s',
              endpoint, item, single)
    hosts = []
    if endpoint == 'code':
        # We deploy the same code to all pools.
        for pool in servers[atlas_environment]:
            for server in pool['webservers']:
                hosts.append(server)
    elif endpoint == 'route':
        hosts.append(servers[atlas_environment]['load_balancer'])
    elif endpoint == 'instance':
        # Instances are only ever served from a single pool.
        pool = item['pool']
        for server in servers[atlas_environment][pool]['webservers']:
            hosts.append(server)
        if single:
            # Randomly choose a single host to run on.
            hosts = random.choice(hosts)

    log.debug('utilities | fabric_hosts | hosts - %s', hosts)
    return hosts

###
# Messaging and communication functions
###
def send_email(message, subject, to):
    """
    Sends email. We only send plaintext to prevent abuse.
    :param message: content of the email to be sent.
    :param subject: content of the subject line
    :param to: list of email address(es) the email will be sent to
    """
    if send_emails:
        log.debug('utilities | email | Send email | %s | %s | %s', message, subject, to)
        msg = MIMEText(message, 'plain')
        msg['Subject'] = subject
        msg['From'] = email_from_address
        msg['To'] = ", ".join(to)

        s = smtplib.SMTP(email_host, email_port)
        s.starttls()
        s.login(email_username, email_password)
        s.sendmail(email_from_address, to, msg.as_string())
        s.quit()


def slack_notification(payload):
    """
    Posts a message to a given channel using the Slack Incoming Webhooks API. 
    See https://api.slack.com/docs/message-formatting.

    :param payload: Payload suitable for POSTing to Slack.
    """
    if slack_notifications:
        if atlas_environment == 'local':
            payload['channel'] = '@{0}'.format(slack_username)

        # We need 'json=payload' vs. 'payload' because arguments can be passed
        # in any order. Using json=payload instead of data=json.dumps(payload)
        # so that we don't have to encode the dict ourselves. The Requests
        # library will do it for us.
        r = requests.post(slack_url, json=payload)
        if not r.ok:
            print r.text
