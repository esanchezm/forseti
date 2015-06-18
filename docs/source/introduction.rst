.. _introduction:

Introduction
============

Forseti development began in 2011. We needed a tool to manage `Amazon Web Services <https://aws.amazon.com/>`_ (AWS) EC2 [1]_ auto-scale groups and at that time the web interface was lacking of support. The only way to manage autoscaling was using their API, which was very complete and well documented. We looked for third party tools but all of them were too much, with a lot of requirements, a complicated UI and a lot of effort in order to get started. We only wanted an easy CLI tool, one that did one task and did it right. And Foserti was born.

.. _terminology:

Terminology and basic concepts
------------------------------

It's not the objective of this guideline to explain all concepts regarding AWS but considering it's a tool to manage a very specific part of it, you need to be familiar with some of its concepts and how they work.

* EC2 instance: Virtual machine running inside AWS system.

* EBS root instance: It's an EC2 instance in which the root device is inside an EBS volume.

* `Autoscaling group <http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AutoScalingGroup.html>`_: A collection of homogeneous EC2 instances which can scale up or down.

* `Launch configuration <http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/LaunchConfiguration.html>`_: Associated to an autoscaling group, there are launch configurations, which define which AMI will be used when an instance is launched, including its size, SSH key and others.

* `Autoscaling policy <http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html#as-scaling-policies>`_: A policy defines how an autoscaling group will scale up or down. AWS offers three different types: increasing/decreasing the capacity using a number, change it to a specified number of instances or increasing/decreasing in percentual ranges.

* `Alarms <http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/policy_creating.html#policy-creating-scalingpolicies-console>`_: Using AWS Cloudwatch you can define some alarms to trigger the autoscaling policies to scale in or out the number of instances in a group. This is the key part because it allows you to manage the capacity automatically with no human intervetion, usually named autoscaling.

What Forseti can do for you?
----------------------------

Forseti is built on top of `boto <http://boto.readthedocs.org/en/latest/index.html>`_, a great Python library to interact with AWS apis, offering a complete access to all the services Amazon offers. On top of boto, we've built a programatic system to manage all the autoscale items, from autoscaling groups, configurations and policies to `CloudWatch <https://aws.amazon.com/cloudwatch/>`_ alarms and `SNS <https://aws.amazon.com/sns/>`_ messages.

Forseti is able to deploy your application code (using any external tool available) into the instances you want and build an autoscaling group, allowing you to scale up or down the number of instances to fit the load you require. Using autoscaling is a must nowadays if you want to offer a stable service, but setting up AWS autoscaling is a complicated process in which Forseti can help you.

After deploying your application code into all the instances you want, Forseti will select one randomly to create an AMI [2]_ from it and setting up the autoscale group the way you want.

We built forseti as an abstraction of boto classes, providing high level operations and introducing a new concept, the application.

What Forseti can't do for you?
------------------------------

Forseti was not thought to orchestrate machines, it's not a deploy utility, it can't run operations in your machines. You have better tools for that: `ansbile <http://www.ansible.com/home>`_, `puppet <https://puppetlabs.com/>`_, `chef <https://www.chef.io/chef/>`_, `capistrano <http://capistranorb.com/>`_... name yours. Forseti is a tool to manage AWS EC2 autoscaling, nothing more, nothing less.


.. [1] Elastic Compute Cloud
.. [2] Amazon Machine Images. An autoscale group uses AMIs to launch new instances.
