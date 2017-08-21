Design of Atlas
========================

Goal is to write down why we did things so that we can remeber later when we have regrets.

Notes on specific endpoints
--------------------------------

Code
~~~~~~~~~~~~~~~~




Sites
~~~~~~~~~~~~~~~~

A Site is a set of Instances and Routes.

* Only one Instance can be ``active`` per Site.
* You cannot change the ``primary_route`` of an Site after it is made ``active``.
* You cannot deactivate the ``primary_route`` for an ``active`` Site.
* When a Site is deleted, related Routes and Instances are deleted.

Instances
~~~~~~~~~~~~~~~~

An Instance is an individual installation of Drupal.

* Only one Instance can be ``active`` per Site.
* When a Site is deleted, related Instances are deleted.
* Instances can be cloned from any state.
* Instances are created with the following:

    .. code-block:: python

        'instance': {
            'state': 'provision',
            'needs_work': true,
            'instance_active': false,
            'site_id': null
        }

* After an Instance is created on the servers and the Drupal installation is run:

    .. code-block:: python

        'instance': {
            'state': 'provision',
            'needs_work': false,
            'instance_active': false,
            'site_id': null
        }

    * Cron is not run on these instances and packages cannot be added to instances in this state.

* An Instance is allocated to a Site
    * The settings files for the instance is updated.
    * Cron is run on instances in this state.
    * State ends on ``installed`` and packages can now be added.
* ``launching`` requires a ``primary_route``
    * Update settings files.
    * Activates any associated routes that are ``active_on_launch: True``.
    * Create symlinks from route ``source`` in the web root to the code root.


Routes
~~~~~~~~~~~~~~~~

A Route represents an entry in the load balancer or on the redirect server.

* Only active routes are added to the load balancer.
* You cannot change the ``source`` of a Route after it has been created.
* You cannot change the ``site_id`` of a Route when it is active. 
* You cannot deactivate the ``primary_route`` for an active Site.
* When a Site is deactivated, related Routes are not changed.
* When a Site is deleted, related Routes are deleted.


State flow
----------------------

* Cron keeps several Instances ready to use.

    .. code-block:: python

        'instance': {
            'state': 'provision',
            'instance_active': false
        }

* User creates a new Site and an Instance is allocated to the Site.

    .. code-block:: python

        'site': {
            'site_active': false,
            'instance': ['instance_id']
        }

        'instance': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'path': instance['sid']
        }

* User reserves a Route to access the Instance in the future.

    .. code-block:: python

        'site': {
            'site_active': false
            'instance': ['instance_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': false
        }

        'instance': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'path': instance['sid']
        }

* User makes Instance accessible via Route.

    .. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance': {
            'state': 'allocate',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src']
        }

* User allocates a second Instance and locks the original.

    .. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_id' ,'instance_2_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance': {
            'state': 'lock',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src']
        }

        'instance_2': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'path': instance_2['sid']
        }

* User makes a second Instance accessible via Route.

    .. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_id' ,'instance_2_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance': {
            'state': 'lock',
            'instance_active': false,
            'site': 'site_id',
            'path': instance['sid']
        }

        'instance_2': {
            'state': 'allocate',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src']
        }

* User archives the first Instance.

    .. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_id' ,'instance_2_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance': {
            'state': 'archive',
            'instance_active': false,
            'site': 'site_id',
            'path': instance['sid']
        }

        'instance_2': {
            'state': 'allocate',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src']
        }

* User deletes the first Instance.

    .. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_2_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance_2': {
            'state': 'allocate',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src']
        }


General Notes
-----------------------

Training instances
~~~~~~~~~~~~~~~~~~~

Can be setup as clones of an active Instance.

.. code-block:: python

        'site': {
            'site_active': true,
            'instance': ['instance_id' ,'instance_2_id','instance_3_id','instance_4_id'],
            'primary_route': 'route_id'
        }

        'route': {
            'route_active': true
        }

        'instance': {
            'state': 'allocate',
            'instance_active': true,
            'site': 'site_id',
            'path': route['src'],
            'description': 'Master instance to clone for training.'
        }

        'instance_2': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'description': 'Instance for Bill - Training on June 10, 2017'
        }

        'instance_3': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'description': 'Instance for Jane - Training on June 10, 2017'
        }

        'instance_4': {
            'state': 'allocate',
            'instance_active': false,
            'site': 'site_id',
            'description': 'Instance for Pat - Training on June 10, 2017'
        }
