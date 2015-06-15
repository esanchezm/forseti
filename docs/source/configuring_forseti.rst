.. _configuring_forseti:

Configuring Forseti
===================

In this section you will find a deeper description on the Forseti's configuration. It has different sections very well defined but interrelated. Forseti looks for the configuration file in a very specific file inside the  First, let's see a basic example of a forseti configuration file.

.. literalinclude:: default-example.json
   :language: json

As you can see, Forseti configuration defines two sections: ``applications`` and ``autoscale``. In the first one, we define some aspects relevant to an application: how to deploy it, what ELB does it use... On the other section, we describe the autoscaling parts such as groups, policies, alarms...

In this example, we've defined a ``backend`` application and the minimum aspects to make it useful. Let's take a deeper look.

Application section
-------------------

The application section is a dictionary which can hold different applications. The key of each application is the name it receives for the Forseti commands, so the application is named ``backend`` here.

The first interesting part we have inside the application configuration is the strategy. In this case, we're using a deploy and snapshot strategy.

.. literalinclude:: default-example.json
   :language: json
   :lines: 8
   :dedent: 12

This strategy requires a ``deploy`` setting in which we define a ``command`` which will be the program that will be running inside ``working_directory``. This command can have the special token ``{dns_name}`` which will be replaced by a comma separated list of the EC2 instances public DNS.

.. literalinclude:: default-example.json
   :language: json
   :lines: 4-7
   :dedent: 12

From here, we have specific parts regarding autoscaling. We define the autoscaling group name and the policies it will have. We only list them because the configuration will be in other sections.

.. literalinclude:: default-example.json
   :language: json
   :lines: 9-13
   :dedent: 12

The next one (being optional) is relative to autoscaling notifications. We can setup the AWS autoscaling to publish messages through SNS whenever an action occured in the group (launching or terminating an instance). Multiple actions can be defined, just by adding them to the list:

.. literalinclude:: default-example.json
   :language: json
   :lines: 14-19
   :dedent: 12

The notifications can be setup to attend only some actions. To do so, you may use one or more of the following values in the ``type`` :

* ``autoscaling:EC2_INSTANCE_LAUNCH``
* ``autoscaling:EC2_INSTANCE_LAUNCH_ERROR``
* ``autoscaling:EC2_INSTANCE_TERMINATE``
* ``autoscaling:EC2_INSTANCE_TERMINATE_ERROR``
* ``autoscaling:TEST_NOTIFICATION``

And the last one is relative to Forseti's notifications. It can push messages to a topic in SNS whenever a deploy is being done. It will send a message when the deploy begins and ends, also when the AMI is being created and the last one when the autoscaling group is finished. To set it up, you have the following options. The section ``sns_extra_attributes`` can be used to attach different options to the message published to the SNS topic specified in ``sns_notification_arn``.

.. literalinclude:: default-example.json
   :language: json
   :lines: 20-26
   :dedent: 12
