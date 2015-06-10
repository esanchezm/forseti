Introduction
============

Forseti development began in 2011. We needed a tool to manage `Amazon Web Services <https://aws.amazon.com/>`_ (AWS) EC2[1]_ auto-scale groups and at that time the web interface was lacking of support. The only way to manage autoscaling was using their API, which was very complete and well documented. We looked for third party tools but all of them were too much, with a lot of requirements, a complicated UI and a lot of effort in order to get started. We only wanted an easy CLI tool, one that do one task and do it right. And Foserti was born.

What Forseti can do for you?
============================

Forseti is built on top of `boto <http://boto.readthedocs.org/en/latest/index.html>`_, a great Python library to interact with AWS library, offering a complete access to all the services Amazon offers. On top of boto, we've built a programatic system to manage all the autoscale items, from autoscaling groups, configurations and policies to `CloudWatch <https://aws.amazon.com/cloudwatch/>`_ alarms and `SNS <https://aws.amazon.com/sns/>`_ messages.

Forseti is able to deploy your application code (using any external tool available) into the instances you want and build an autoscaling group, allowing you to scale up or down the number of instances to fit the load you require. Using autoscaling is a must nowadays if you want to offer a stable service, but setting up AWS autoscaling is a complicated process in which Forseti can help you.

After deploying your application code into all the instances you want, Forseti will select one randomly to create an AMI[2]_ from it and setting up the autoscale group the way you want.

We built forseti as a wrapper of boto classes, providing high level operations and introducing a new concept, the application.

What Forseti can't do for you?
==============================

Forseti was not thought to orchestrate machines, it's not a deploy utility, it can't run operations in your machines. You have better tools for that: `ansbile <http://www.ansible.com/home>`_, `puppet <https://puppetlabs.com/>`_, `chef <https://www.chef.io/chef/>`_, `capistrano <http://capistranorb.com/>`_... name yours. Forseti is a tool to manage AWS EC2 autoscaling, nothing more, nothing less.


.. [1] Elastic Compute Cloud
.. [2] Amazon Machine Images. An autoscale group uses AMIs to launch new instances.
