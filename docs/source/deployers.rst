.. _deployers:

Deployers
=========

Forseti has a flexible deployment system, which can be expanded with different deployment strategies and operations. Forseti already comes geared with two different deployers that you can use out of the box, also you can create yours it they don't fit you and submit a PR if you want.

Deploy and snapshot
-------------------

The `deploy and snapshot deployer <https://github.com/ticketea/forseti/blob/master/forseti/deployers/deploy_and_snapshot.py>`_ is the easiest way of deployment. The process goes as follows:

- Deploy the application code on the instances belonging to an autoscale group.
- Select a random instance of the group
- Remove that instance from the load balancers of the autoscale group.
- Create an AMI from it (This will reboot the instance).
- Create a new autoscaling configuration with that new AMI.
- Update the autoscaling group to use the new configuration.

The biggest drawback is that it works better for already existing autoscale groups. Also, it requires a minimum of two running instances in the group in order to use this deployer (remember that one of the instances will be rebooted). If your number of instances vs load is tight your service could be anavailable meanwhile.

You can skip any specific instance to be selected for AMI creation by adding a tag ``forseti:avoid_ami_creation`` with value `True` to that instance. This can be useful if the instances are not simetric. For example imagine you have some specific cron tasks in only one of the instances belonging to the autoscale group.

Golden instance
---------------

The `golden instance deployer <https://github.com/ticketea/forseti/blob/master/forseti/deployers/golden_instance.py>`_ process is similar to:

- Launch an instance with the gold AMI (defined later). This is called ``golden instance``.
- Deploy the application code on this new instance.
- Generate a new AMI from that golden instance. This is called ``golden AMI``.
- Create a new autoscaling configuration with the new golden AMI.
- Create or update an autoscaling group to use the new configuration.
- Create or update the autoscaling policies to specify how AWS will scale up or down.
- Create or update the CloudWatch alarms which will trigger the autoscaling policies.
- Wait until the autoscaling group has the new instances with the golden AMI.
- Deregister the old instances.

Before using this deployer
~~~~~~~~~~~~~~~~~~~~~~~~~~

Forseti's ``golden instance`` deployer uses a ``gold AMI``, which is an AMI packed with all the software you need, except your application specific code. Unfortunately, forseti currently is not able to generate a gold AMI for you, so you'll need to create one manually.

This is actually a very easy operation, so don't panic. All you need to do is create a new EC2 Instance from an AMI with EBS root and provision it with all the software you need (apache, nginx, nodejs...) and its configurations (virtualhosts or similars). Once you've installed everything, create an AMI from the instance by right clicking on it on the AWS Console and select ``"Create Image (EBS AMI)"``. There you go, you now have a gold AMI!
