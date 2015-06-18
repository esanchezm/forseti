.. _configuring_forseti:

Configuring Forseti
===================

In this section you will find a deeper description on the Forseti's configuration. It has different sections very well defined but interrelated. Forseti looks for the configuration file in a very specific path inside the ``~/.forseti/config.json``. First, let's see a basic example of a Forseti configuration file.

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

The next one (being optional) is relative to autoscaling notifications. We can setup the AWS autoscaling to publish messages through SNS whenever an action occurs in the group (launching or terminating an instance). Multiple actions can be defined, just by adding them to the list:

.. literalinclude:: default-example.json
   :language: json
   :lines: 14-19
   :dedent: 12

The notifications can be setup to attend only some actions. To do so, you may use one or more of the following values within ``type`` :

* ``autoscaling:EC2_INSTANCE_LAUNCH``
* ``autoscaling:EC2_INSTANCE_LAUNCH_ERROR``
* ``autoscaling:EC2_INSTANCE_TERMINATE``
* ``autoscaling:EC2_INSTANCE_TERMINATE_ERROR``
* ``autoscaling:TEST_NOTIFICATION``

And the last one is relative to Forseti's notifications. It can push messages to a topic in SNS whenever when a deploy is being done. It will send a message when the deploy begins and ends, also when the AMI is being created and the last one when the autoscaling group is finished. To set it up, you have the following options. The section ``sns_extra_attributes`` can be used to attach different options to the message published to the SNS topic specified in ``sns_notification_arn``.

.. literalinclude:: default-example.json
   :language: json
   :lines: 20-26
   :dedent: 12

Autoscale section
-------------------

The other part of the configuration file defines all the autoscaling elements. It's divided in four groups.

Groups
^^^^^^

In this section, you'll define the autoscaling groups, ideally one per application. Keep in mind that any application you define, must have an ``autoscale_group`` key and it must reference one group inside this section.

All the parameters available for an autoscaling group are the same one that `boto defines in its API <http://boto.readthedocs.org/en/latest/ref/autoscale.html#boto.ec2.autoscale.group.AutoScalingGroup>`_. We've defined some in this example and you can find the meaning of each one in the boto documentation.

.. literalinclude:: default-example.json
   :language: json
   :lines: 30-48
   :dedent: 8

Configurations
^^^^^^^^^^^^^^

Every autoscaling group has one or more launch configurations and again all the parameters Forseti accepts are the same ones `documented in boto <http://boto.readthedocs.org/en/latest/ref/autoscale.html#boto.ec2.autoscale.launchconfig.LaunchConfiguration>`_.

.. literalinclude:: default-example.json
   :language: json
   :lines: 49-58
   :dedent: 8

Policies
^^^^^^^^

Policies defines how to scale in or out a group. You can do it in absolute numbers and chaning the group capacity in percentual ranges, whatever fits your application needs. All the policies listed for an application must be defined here. The parameters to define a policy are once again defined in the `boto documentation regarding autoscaling policies <http://boto.readthedocs.org/en/latest/ref/autoscale.html#boto.ec2.autoscale.policy.ScalingPolicy>`_.

.. literalinclude:: default-example.json
   :language: json
   :lines: 59-70
   :dedent: 8

Alarms
^^^^^^

The last section defines what CloudWatch alarms will trigger the autoscaling policies. In this example, we have two alarms, one that will trigger the increase of instances and another one to decrease them. The important token when defining this alarms is the ``alarm_actions``, which should refer to the autocaling policy to trigger in case the alarm fails. Creating an alarm is easy and all the parameters are defined in the `boto documentation as well <http://boto.readthedocs.org/en/latest/ref/cloudwatch.html#boto.ec2.cloudwatch.alarm.MetricAlarm>`_.

.. literalinclude:: default-example.json
   :language: json
   :lines: 71-92
   :dedent: 8
