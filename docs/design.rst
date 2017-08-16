Design of Atlas
========================

Goal is to write down why we did things so that we can remeber later when we have regrets.

Sites
~~~~~~~~~~~~~~~~

A Site is a set of Instances and Routes.

* Only 1 Instance can be ``active`` per Site
* 

Instances
~~~~~~~~~~~~~~~~

An Instance is an individual installation of Drupal.

* 


Routes
~~~~~~~~~~~~~~~~

A Route represents an entry in the load balancer or on the redirect server.

* You cannot change the ``source`` of a Route after it has been created. 
