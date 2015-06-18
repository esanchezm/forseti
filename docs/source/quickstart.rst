.. _quickstart:

Quickstart and first steps
==========================

Configuring AWS access
----------------------

The first thing you need to do is configure your AWS credentials and the region you want to use. Forseti depends on boto, so you can read their `getting started guideling <http://boto.readthedocs.org/en/latest/getting_started.html#configuring-boto-credentials>`_ to get all the information you need. The minimum setup that Forseti requires is creating a file in `~/.boto` with this content::

    [Boto]
    autoscale_region_name = eu-west-1
    autoscale_endpoint = autoscaling.eu-west-1.amazonaws.com

    ec2_region_name = eu-west-1
    ec2_region_endpoint = ec2.eu-west-1.amazonaws.com

    elb_region_name = eu-west-1
    elb_region_endpoint = elasticloadbalancing.eu-west-1.amazonaws.com

    cloudwatch_region_name = eu-west-1
    cloudwatch_region_endpoint = monitoring.eu-west-1.amazonaws.com

    sns_region_name = eu-west-1
    sns_region_endpoint = sns.eu-west-1.amazonaws.com

    [Credentials]
    aws_access_key_id = <YOUR_AWS_KEY>
    aws_secret_access_key = <YOUR_AWS_SECRET>

.. note::

    In this example, we've chosen `eu-west-1` region, change it to use other region if that's your case

Setting up a Forseti application
--------------------------------

If you're already running instances in AWS, the best way to start with Forseti is using the `init` command. This command will help you creating an application using an instance (it could be running or stopped)::

    forseti init <application_name> i-xxxxxxxx --deployer=deploy_and_snapshot

This will create for you an autoscaling group, using an AMI created from the selected instance. That information will be added to the Forseti configuration file, located in `~/.forseti/config.json`. Move to :ref:`configuring_forseti`

If you want more information about this command, please refer to the :ref:`list_of_commands`.
