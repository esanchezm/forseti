Preface
===

From Wikipedia: `Forseti` (old norse "the presiding one") is an Æsir god of justice and reconciliation in Norse mythology. He is generally identified with Fosite, a god of the Frisians.

What is it?
===

`Forseti` is a utility to manage your AWS autoscaling groups and policies and allows you to create a AMI to be used for autoscaling purposes.

Requirements
===

* docopt
* boto
* paramiko
* progressbar

Install all of them, it's as easy as run:

```
pip install docopt boto paramiko progressbar
```

Configuration
===

Create a `~/.boto` or `/etc/boto.cfg` file with the following

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

Create a `forseti.json` file, you can use `forseti.example.json` file as a base.

Before using
===

`Forseti` uses a _gold AMI_, which is an AMI with all the software you need, except you application specific code. Unfortunately, `forseti` is not able to generate a gold AMI for you, so you'll need to create one.

This is actually a very easy operation. All you need to do is create a new EC2 Instance from an AMI with EBS root and provision it with all the software you need (apache, nginx, nodejs...) and its configurations (virtualhosts or similars). Once you've installed everything, create an AMI from the instance by right clicking on it on the AWS Console and select "Create Image (EBS AMI)". There you go, you have a gold AMI!

Running
===

Execute

```
python forsety.py deploy application
```

How does it works?
===

The deployment process is similar to:

- Create an instance with the gold AMI. This is called _golden instance_.
- Deploy the application code on the new instance.
- Generate a new AMI from that golden instance. This is called _golden AMI_.
- Create a new autoscaling configuration with the new golden AMI.
- Create or update an autoscaling group to use the new configuration.
- Create or update the autoscaling policies to specify how the system will grow or shrink.
- Create or update the CloudWatch alarms which will trigger the autoscaling policies.
- Wait until the autoscaling group has the new instances with the golden AMI.
- Deregister the old instances.