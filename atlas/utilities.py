"""
Utility functions.
"""
import sys
import smtplib
from email.mime.text import MIMEText
from logging import getLogger

import ldap
from eve.auth import BasicAuth
from flask import g

from atlas.config import (atlas_path, allowed_users, ldap_server, ldap_org_unit, 
                          ldap_dns_domain_name, send_emails, email_from_address, email_host, 
                          email_port, email_username, email_password, atlas_url, atlas_username, 
                          atlas_password, ssl_verification)


# Setup a sub-logger
# Best practice is to setup sub-loggers rather than passing the main logger between different parts of the application.
# https://docs.python.org/3/library/logging.html#logging.getLogger and
# https://stackoverflow.com/questions/39863718/how-can-i-log-outside-of-main-flask-module
log = getLogger('atlas.utilities')

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
            log.error('LDAP | Error | %s', e.message['info'])
            if type(e.message) == dict and e.message.has_key('desc'):
                log.error('LDAP | Error | %s', e.message['desc'])
            else:
                log.error('LDAP | Error | %s', e)

        ldap_distinguished_name = "uid={0},ou={1},{2}".format(
            username, ldap_org_unit, ldap_dns_domain_name)
        log.debug('LDAP | ldap_distinguished_name | {0}'.format(ldap_distinguished_name))

        # Add the username as a Flask application global.
        g.username = username

        try:
            # Try a synchronous bind (we want synchronous so that the command
            # is blocked until the bind gets a result. If you can bind, the
            # credentials are valid.
            result = l.simple_bind_s(ldap_distinguished_name, password)
            log.info('LDAP | Auth successful | {0}'.format(username))
            return True
        except ldap.INVALID_CREDENTIALS:
            log.info('LDAP | Invalid credentials | {0}'.format(username))

        # Apparently this was a bad login attempt
        log.info('LDAP | Auth failed | {0} | {1}'.format(username, result))
        return False


def send_email(message, subject, to):
    """
    Sends email. We only send plaintext to prevent abuse.
    :param message: content of the email to be sent.
    :param subject: content of the subject line
    :param to: list of email address(es) the email will be sent to
    """
    if send_emails:
        log.debug('Send email | %s | %s | %s', message, subject, to)
        msg = MIMEText(message, 'plain')
        msg['Subject'] = subject
        msg['From'] = email_from_address
        msg['To'] = ", ".join(to)

        s = smtplib.SMTP(email_host, email_port)
        s.starttls()
        s.login(email_username, email_password)
        s.sendmail(email_from_address, to, msg.as_string())
        s.quit()
