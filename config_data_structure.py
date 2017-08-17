import os

MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('MONGO_PORT', 27017)
MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'atlas')

DATE_FORMAT = '%Y-%m-%d %H:%M:%S GMT'

# Enable reads (GET), inserts (POST), and DELETE for resources/collections.
RESOURCE_METHODS = ['GET', 'POST']

# Enable reads (GET), edits (PATCH), replacements (PUT), and deletes of
# individual items.
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']

# Allow public GET by default can override for a specific resource or item.
PUBLIC_METHODS = ['GET']

# Default to return 500 results per page. Allow up to 2000.
PAGINATION_LIMIT = 2000
PAGINATION_DEFAULT = 500

# Add support for CORS
X_DOMAINS = '*'
X_HEADERS = ['Access-Control-Allow-Origin', 'If-Match', 'Authorization', 'User-Agent', 'Content-Type']

# Allow $regex filtering. Default config blocks where and regex.
MONGO_QUERY_BLACKLIST = ['$where']

# Require etags
ENFORCE_IF_MATCH = True

DEBUG = True
# Definitions of schemas for Items. Schema is based on Cerberus grammar
# https://github.com/nicolaiarocci/cerberus.
#

# Mongo creates the following: '_created', '_updated', '_etag', and '_id'.
# We don't use those fields in our logic because want to be able to move or
# recreate a record without losing any information.

# Code schema. Defines a code asset that can be applied to an instance.
# We nest in 'meta' to allow us to check for a unique combo
code_schema = {
    'meta': {
        'type': 'dict',
        'unique': True,
        'schema': {
            'name': {
                'type': 'string',
                'minlength': 3,
                'required': True,
            },
            'version': {
                'type': 'string',
                'minlength': 1,
                'required': True,
            },
            'code_type': {
                'type': 'string',
                'allowed': ['library', 'theme', 'module', 'core', 'profile'],
                'required': True,
            },
            'label': {
                'type': 'string',
                'minlength': 3,
            },
            'is_current': {
                'type': 'boolean',
                'default': False,
                'required': True,
            },
            'tag': {
                'type': 'list',
            },
        },
    },
    'git_url': {
        'type': 'string',
        'regex': '((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?',
        'required': True,
    },
    'commit_hash': {
        'type': 'string',
        'required': True,
        'unique': True
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}

# Query Schema
query_schema = {
    'title': {
        'type': 'string',
        'required' : True,
    },
    'description': {
        'type': 'string',
    },
    'endpoint': {
        'type': 'list',
        'allowed': ['code', 'instance', 'site', 'statistic'],
        'required': True,
    },
    'query': {
        'type': 'string',
        'unique': True,
    },
    'tags': {
        'type': 'list',
        'schema': {
            'type': 'string',
        }
    },
    'rank': {
        'type': 'integer',
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}

# site schema.
site_schema = {
    'instance': {
        'type': 'list',
        'schema': {
            'type': 'objectid',
            'data_relation': {
                'resource': 'instance',
                'field': '_id',
                'embeddable': True,
            },
        }
    },
    'site_type': {
        'type': 'string',
        'allowed': [
            # Magazines and Journals
            'magazine',
            'committee',
            # Labs and Research Groups
            'lab',
            'faculty',
            'event',
            'sports_club',
            'student_group',
            # Internal sandboxes and other throw away sites
            'internal',
            # Initiative and Promotional
            'initiative',
            'academic_department',
            'administrative_department',
            # Centers and Institutes
            'center',
            # Museums and Collections
            'museum',
            'college',
            'other'
        ],
    },
    'routes': {
        'type': 'list',
        'schema': {
            'type': 'objectid',
            'data_relation': {
                'resource': 'route',
                'field': '_id',
                'embeddable': True,
                'unique': True,
            },
        },
        'nullable': True,
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}


# Instance schema.
instance_schema = {
    'site': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'site',
            'field': '_id',
            'embeddable': True,
        },
    },
    'routes': {
        'type': 'dict',
        'schema': {
            'primary_route': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'route',
                    'field': '_id',
                    'embeddable': True,
                    'unique': True,
                },
                'nullable': True,
            },
            'redirect': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'route',
                        'field': '_id',
                        'embeddable': True,
                        'unique': True,
                    },
                },
                'nullable': True,
            },
        },
    },
    # FIXME: Convert to non-canonical this after the migration
    'path': {
        'type': 'string',
        'unique': True,
    },
    'db_key': {
        'type': 'string',
    },
    # Leave in 'instance' since value would not be moved between instances.
    'sid': {
        'type': 'string',
        'minlength': 9,
        'maxlength': 14,
        'unique': True,
    },
    # FIXME: Get rid of this field, should be able to handle in route.
    'type': {
        'type': 'string',
        'allowed':  ['express', 'legacy', 'homepage'],
        'default': 'express',
    },
    'status': {
        'type': 'string',
        'allowed': [
            'pending',
            'available',
            'installing',
            'installed',
            'launching',
            'launched',
            'locked',
            'take_down',
            'down',
            'restore',
        ],
        'default': 'pending',
    },
    'environment': {
        'type': 'string',
        'allowed': [
            'local',
            'development',
            'test',
            'production'
        ],
    },
    'pool': {
        'type': 'string',
        'allowed': [
            'poolb-express',
            'poolb-homepage',
            'WWWLegacy'],
        'default': 'poolb-express',
    },
    'update_group': {
        'type': 'integer',
    },
    'import_from_inventory': {
        'type': 'boolean',
        'default': False
    },
    'settings': {
        'type': 'dict',
        'schema': {
            'page_cache_maximum_age': {
                'type': 'integer',
                'default': 3600,
            },
            'siteimprove_site': {
                'type': 'integer',
            },
            'siteimprove_group': {
                'type': 'integer',
            },
        },
    },
    'tag': {
        'type': 'list',
    },
    'code': {
        'type': 'dict',
        'schema': {
            'core': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'code',
                    'field': '_id',
                    'embeddable': True,
                },
            },
            'profile': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'code',
                    'field': '_id',
                    'embeddable': True,
                },
            },
            'package': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'code',
                        'field': '_id',
                        'embeddable': True,
                    },
                }
            },
        },
    },
    'dates': {
        'type': 'dict',
        'schema': {
            # See https://docs.python.org/2/library/datetime.html#datetime.datetime for datetime
            # format.
            'created': {
                'type': 'datetime',
            },
            'assigned': {
                'type': 'datetime',
            },
            'launched': {
                'type': 'datetime',
            },
            'locked': {
                'type': 'datetime',
            },
            'taken_down': {
                'type': 'datetime',
            },
        },
    },
    'statistics': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'statistics',
            'field': '_id',
            'embeddable': True,
            'unique': True,
        },
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}

statistics_schema = {
    'instance': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'instance',
            'field': '_id',
        },
        'required': True,
        'unique': True,
    },
    'name': {
        'type': 'string',
        'minlength': 1,
    },
    'status': {
        'type': 'string',
        'minlength': 1,
    },
    'nodes_total': {
        'type': 'integer',
    },
    'nodes_by_type': {
        'type': 'dict',
        'schema': {
            'page': {'type': 'integer'},
            'file': {'type': 'integer'},
            'faqs': {'type': 'integer'},
            'content_list_page': {'type': 'integer'},
            'webform': {'type': 'integer'},
            'article': {'type': 'integer'},
            'article_list_page': {'type': 'integer'},
            'person': {'type': 'integer'},
            'person_list_page': {'type': 'integer'},
            'photo_gallery': {'type': 'integer'},
        },
    },
    'nodes_other': {
        'type': 'string',
    },
    'days_since_last_edit': {
        'type': 'integer',
    },
    'beans_total': {
        'type': 'integer',
    },
    'beans_by_type': {
        'type': 'dict',
        'schema': {
            'hero_unit': {'type': 'integer'},
            'slider': {'type': 'integer'},
            'block': {'type': 'integer'},
            'content_list': {'type': 'integer'},
            'feature_callout': {'type': 'integer'},
            'quicktab': {'type': 'integer'},
            'video_reveal': {'type': 'integer'},
            'block_row': {'type': 'integer'},
            'block_section': {'type': 'integer'},
            'cu_events_calendar_block': {'type': 'integer'},
            'events_calendar_grid': {'type': 'integer'},
            'rss': {'type': 'integer'},
            'articles': {'type': 'integer'},
            'article_feature': {'type': 'integer'},
            'article_grid': {'type': 'integer'},
            'article_slider': {'type': 'integer'},
            'people_list_block': {'type': 'integer'},
            'social_links': {'type': 'integer'},
            'facebook_activity': {'type': 'integer'},
            'facebook_like_button': {'type': 'integer'},
            'twitter_block': {'type': 'integer'},
        },
    },
    'beans_other': {
        'type': 'string',
    },
    'context': {
        'type': 'dict',
        'schema': {
            'condition': {
                'type': 'dict',
                'schema': {
                    'context': {'type': 'integer'},
                    'context_all': {'type': 'integer'},
                    'default': {'type': 'integer'},
                    'layout': {'type': 'integer'},
                    'menu': {'type': 'integer'},
                    'node': {'type': 'integer'},
                    'node_taxonomy': {'type': 'integer'},
                    'path': {'type': 'integer'},
                    'query_param': {'type': 'integer'},
                    'query_string': {'type': 'integer'},
                    'sitewide': {'type': 'integer'},
                    'sitewide_public': {'type': 'integer'},
                    'taxonomy_term': {'type': 'integer'},
                    'user': {'type': 'integer'},
                    'user_page': {'type': 'integer'},
                    'views': {'type': 'integer'},
                },
            },
            'reaction': {
                'type': 'dict',
                'schema': {
                    'backstretch': {'type': 'integer'},
                    'block': {'type': 'integer'},
                    'breadcrumb': {'type': 'integer'},
                    'column_override': {'type': 'integer'},
                    'cu_share': {'type': 'integer'},
                    'menu': {'type': 'integer'},
                    'region': {'type': 'integer'},
                    'template_suggestions': {'type': 'integer'},
                    'theme': {'type': 'integer'},
                    'theme_html': {'type': 'integer'},
                    'title_image': {'type': 'integer'},
                },
            },
        },
    },
    'context_other_conditions': {
        'type': 'string',
    },
    'context_other_reactions': {
        'type': 'string',
    },
    'variable_cron_last': {
        'type': 'integer',
    },
    'variable_site_403': {
        'type': 'string',
    },
    'variable_site_404': {
        'type': 'string',
    },
    'variable_theme_default': {
        'type': 'string',
    },
    'variable_ga_account': {
        'type': 'string',
    },
    'variable_livechat_license_number': {
        'type': 'string',
    },
    'profile_module_manager': {
        'type': 'string',
    },
    'express_code_version': {
        'type': 'string',
    },
    'express_core_schema_version': {
        'type': 'integer',
    },
    'theme_is_responsive': {
        'type': 'boolean',
    },
    'overridden_features': {
        'type': 'dict',
    },
    'drupal_system_status': {
        'type': 'boolean',
    },
    'custom_logo_settings': {
        'type': 'boolean',
    },
    'users': {
        'type': 'dict',
        'schema': {
            'email_address': {
                'type': 'dict',
                'schema': {
                    'content_editor': {
                        'type': 'list',
                        'nullable': True,
                    },
                    'site_contact': {
                        'type': 'list',
                        'nullable': True,
                    },
                },
            },
            'username': {
                'type': 'dict',
                'schema': {
                    'content_editor': {
                        'type': 'list',
                    },
                    'site_contact': {
                        'type': 'list',
                    },
                },
            },
            'no_valid_owner': {
                'type': 'boolean',
            },
            'count': {
                'type': 'integer',
            },
        },
    },
    'bundles': {
        'type': 'dict',
        'schema': {
            'cu_advanced_content_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_advanced_design_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_advanced_layout_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_events_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_feeds_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_forms_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_news_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_people_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_photo_gallery_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_seo_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_social_media_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_seo_admin_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_test_content_admin_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'cu_debug_admin_bundle': {
                'type': 'dict',
                'schema': {
                    'schema_version': {
                        'type': 'integer',
                    },
                },
            },
            'other': {
                'type': 'string',
            },
        },
    },
    'webforms': {
        'type': 'dict',
        'schema': {
            'total_submissions': {'type': 'integer'},
            'active_forms': {'type': 'integer'},
            'inactive_forms': {'type': 'integer'},
        },
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}

command_schema = {
    'name': {
        'type': 'string',
        'minlength': 3,
        'required': True,
    },
    'command': {
        'type': 'string',
        'minlength': 3,
        'required': True,
    },
    # String that is stored needs to be posted with Unicode character encodings
    'query': {
        'type': 'string',
        'minlength': 9,
    },
    'single_server': {
        'type': 'boolean',
        'required': True,
        'default': True,
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}


# If a route is created and is 'active' and 'active_on_launch'; launch the associated instance and
# make any other 'active_on_launch' routes active as well.
route_schema = {
    'route_type': {
        'type': 'string',
        'allowed': ['poolb-express', 'poolb-homepage', 'legacy', 'redirect'],
        'required': True,
    },
    'route_status': {
        'type': 'string',
        'allowed': ['active', 'inactive'],
        'required': True,
    },
    'active_on_launch': {
        'type': 'boolean',
        'required': True,
    },
    # We reserve the phrase 'domainroot' to allow routing to an instance at the root of the domain
    # like www.example.com/.
    # Cannot change this value after creation. See run.pre_patch_route_callback()
    'source': {
        'type': 'string',
        'required': True,
        'unique': True,
    },
    'destination': {
        'type': 'string',
    },
    'regex': {
        'type': 'boolean',
    },
    'path_preserving': {
        'type': 'boolean',
    },
    'response_code': {
        'type': 'string',
        'allowed': [
            301,
            302,
            307
        ],
    },
    'instance_id': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'instance',
            'field': '_id',
        },
    },
    'site_id': {
        'type': 'objectid',
        'data_relation': {
            'resource': 'site',
            'field': '_id',
        },
    },
    'dates': {
        'type': 'dict',
        'schema': {
            # See https://docs.python.org/2/library/datetime.html#datetime.datetime for datetime
            # format.
            'created': {
                'type': 'datetime',
            },
        },
    },
    'tag': {
        'type': 'list',
    },
    'created_by': {
        'type': 'string',
    },
    'modified_by': {
        'type': 'string',
    },
}

"""
Definitions of Resources.
Tells Eve what methods and schemas apply to a given resource.
"""
# Code resource
code = {
    'item_title': 'code',
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'soft_delete': True,
    'schema': code_schema,
}

# Instance resource
instance = {
    'item_title': 'instance',
    # Allow lookup by 'sid' in addition to '_id'
    'additional_lookup': {
        'url': 'regex("[\w]+")',
        'field': 'sid'
    },
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'soft_delete': True,
    'schema': instance_schema,
}

# Query resource
query = {
    'item_title': 'query',
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'schema': query_schema,

}

# Site resource
site = {
    'item_title': 'site',
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'soft_delete': True,
    'schema': site_schema,
}

# Statistics resource
statistics = {
    'item_title': 'statistics',
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'soft_delete': True,
    'schema': statistics_schema,
}

# Command resource
# Empty public_item_methods means that you can't call actual commands without
# authentication. Anonymous users can list the commands, but not call them.
commands = {
    'item_title': 'commands',
    'public_methods': ['GET'],
    'public_item_methods': [],
    'versioning': True,
    'schema': command_schema,
}

# Route resource
route = {
    'item_title': 'route',
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'versioning': True,
    'soft_delete': True,
    'schema': route_schema,
}

#
# Domain definition. Tells Eve what resources are available on this domain.
#
DOMAIN = {
    'site': site,
    'instance': instance,
    'code': code,
    'commands': commands,
    'query': query,
    'statistics': statistics,
    'route': route,
}
