From Wikipedia: `Forseti` (old norse "the presiding one") is an Æsir god of justice and reconciliation in Norse mythology. He is generally identified with Fosite, a god of the Frisians.

## What is it?

`Forseti` is a two-in-one utility:

* A set of classes wrapping boto, provinding friendly high level operations that allow you to easily do common administration operations.
* A CLI tool to manage your AWS autoscaling groups, policies, etc. It allows you to easily deploy your code in AWS using your preferred strategy defined as a _deployer_. A _deployer_ is a class that using previous models, defines a deployment strategy, a default one explained later on is provided.

## Installation

To install forseti simply do:

``python setup.py install``

After this you will have forseti's CLI available in your path, but before using it, you need to set it up.

## Configuration

### Boto's configuration

As forseti depends on boto, you will have to configure it. Create a `~/.boto` or `/etc/boto.cfg` file with the following

```
[Credentials]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_PRIVATE_KEY

# Choose another region if you're using it.
ec2_region_name = eu-west-1
ec2_region_endpoint = ec2.eu-west-1.amazonaws.com

elb_region_name = eu-west-1
elb_region_endpoint = elasticloadbalancing.eu-west-1.amazonaws.com

cloudwatch_region_name = eu-west-1
cloudwatch_region_endpoint = monitoring.eu-west-1.amazonaws.com
```

### Forseti's configuration for deployment

In order to use the default deployer with the CLI you will need to create a `.forseti/config.json` file, you can use <a href="https://github.com/ticketea/forseti/blob/master/forseti/deployers/default-example.json">default-example.json</a> file as a base.

## Default deployer

The default deployer (located at `deployers/default.py`) process is similar to:

- Create an instance with the gold AMI. This is called _golden instance_.
- Deploy the application code on the new instance.
- Generate a new AMI from that golden instance. This is called _golden AMI_.
- Create a new autoscaling configuration with the new golden AMI.
- Create or update an autoscaling group to use the new configuration.
- Create or update the autoscaling policies to specify how the system will grow or shrink.
- Create or update the CloudWatch alarms which will trigger the autoscaling policies.
- Wait until the autoscaling group has the new instances with the golden AMI.
- Deregister the old instances.

### Before using

Forseti's default deployer uses a _gold AMI_, which is an AMI with all the software you need, except your application specific code. Unfortunately, forseti currently is not able to generate a gold AMI for you, so you'll need to create one manually.

This is actually a very easy operation. All you need to do is create a new EC2 Instance from an AMI with EBS root and provision it with all the software you need (apache, nginx, nodejs...) and its configurations (virtualhosts or similars). Once you've installed everything, create an AMI from the instance by right clicking on it on the AWS Console and select _"Create Image (EBS AMI)"_. There you go, you now have a gold AMI!

### Deploying

Once your file is configured, you can deploy your new application code with the CLI doing:

```
forsety deploy application_name
```
