"""
atlas.run.py
The API launch script.
"""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import ssl

from eve import Eve
from flask import jsonify, make_response
from atlas import utilities
from atlas import eve_callbacks
from atlas.config import atlas_path, atlas_log_file_location, version_number, ssl_key_file, ssl_crt_file

if atlas_path not in sys.path:
    sys.path.append(atlas_path)

# Load the settings file using a robust path so it works with a test suite.
this_directory = os.path.dirname(os.path.realpath(__file__))
settings_file = os.path.join(this_directory, 'atlas/config_data_structure.py')

# Name our app ('import_name') so that we can easily create sub loggers.
# Import data structure and Eve settings.
# Use our HTTP BasicAuth class which checks against LDAP and has an access control list. 
app = Eve(import_name='atlas', settings=settings_file, auth=utilities.AtlasBasicAuth)
# TODO Remove debug mode.
app.debug = True

# Request event hooks.
app.on_pre_POST_code += eve_callbacks.pre_create_code
# Database event hooks.
app.on_insert_code += eve_callbacks.create_code


# TODO: Wrap Flask endpoints in Authentication
# Flask custom Routes
@app.route('/version')
def version():
    """Return the version number, defined in atlas.config.py."""
    response = make_response(version_number)
    return response

if __name__ == '__main__':
    # Enable logging to 'atlas.log' file, rotate the log once per day, keep 5 days worth.
    handler = TimedRotatingFileHandler(atlas_log_file_location, when='midnight', interval=1, backupCount=5)
    # The default log level is set to WARNING, so we have to explicitly set the
    # logging level to Debug.
    app.logger.setLevel(logging.DEBUG)
    # Append the handler to the default application logger
    app.logger.addHandler(handler)

    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.load_cert_chain(ssl_crt_file, ssl_key_file)

    # This goes last.
    app.run(host='inventory.local', ssl_context=ctx)
