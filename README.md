[![Documentation Status](https://readthedocs.org/projects/forseti/badge/?version=latest)](https://readthedocs.org/projects/forseti/?badge=latest)

From Wikipedia: `Forseti` (old norse "the presiding one") is an Æsir god of justice and reconciliation in Norse mythology. He is generally identified with Fosite, a god of the Frisians.

## What is it?

`Forseti` is a two-in-one utility:

* A CLI tool to manage your AWS autoscaling groups, policies, etc. It allows you to easily deploy your code in AWS using your preferred strategy defined as a _deployer_. A _deployer_ is a class that, using previous models, defines a deployment strategy. More on this later.
* A set of classes wrapping boto, provinding friendly high level operations that allow you to easily do common administration operations.

Forseti is devops agnostic in the sense that it all their commands can be plugged with any orquestration tool you use, in ticketea we've used Chef, Puppet and Ansible in conjuction with it.

## Installation

We recommend you to use forseti inside a virtualenv.

```bash
pip install virtualenv virtualenvwrapper
mkvirtualenv forseti
workon forseti
```

To install forseti simply do:

```bash
python setup.py install
```

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

# Choose another region if you're using it.
elb_region_name = eu-west-1
elb_region_endpoint = elasticloadbalancing.eu-west-1.amazonaws.com

# Choose another region if you're using it.
cloudwatch_region_name = eu-west-1
cloudwatch_region_endpoint = monitoring.eu-west-1.amazonaws.com

# Choose another region if you're using it.
sns_region_name = eu-west-1
sns_region_endpoint = sns.eu-west-1.amazonaws.com
```

### Forseti's configuration for deployment

In order to use forsetì with the CLI you will need to create a `.forseti/config.json` file, you can use [default-example.json](docs/source/default-example.json) file as a base. But first you may need information on how Forseti works. Beforehand you will need to grok some concepts to be able to adjust it to your needs.

## Deployers

Forseti has a flexible deployment system, which can be expanded with different deployment strategies and operations. Forseti already comes geared with two different deployers that you can use out of the box, also you can create yours it they don't fit you and submit a PR if you want.

### Deploy and snapshot

The [deploy and snapshot deployer](forseti/deployers/deploy_and_snapshot.py) is the easiest way of deployment. The process goes as follows:

- Deploy the application code on the instances belonging to an autoscale group.
- Select a random instance of the group
- Remove that instance from the load balancers of the autoscale group.
- Create an AMI from it (This will reboot the instance).
- Create a new autoscaling configuration with that new AMI.
- Update the autoscaling group to use the new configuration.

The biggest drawback is that it works better for already existing autoscale groups. Also, it requires a minimum of two running instances in the group in order to use this deployer (remember that one of the instances will be rebooted). If your number of instances vs load is tight your service could be anavailable meanwhile.

You can skip any specific instance to be selected for AMI creation by adding a tag `forseti:avoid_ami_creation` with value `True` to that instance. This can be useful if the instances are not simetric. For example imagine you have some specific cron tasks in only one of the instances belonging to the autoscale group.

### Golden instance

The [golden instance deployer](forseti/deployers/golden_instance.py) process is similar to:

- Launch an instance with the gold AMI (defined later). This is called _golden instance_.
- Deploy the application code on this new instance.
- Generate a new AMI from that golden instance. This is called _golden AMI_.
- Create a new autoscaling configuration with the new golden AMI.
- Create or update an autoscaling group to use the new configuration.
- Create or update the autoscaling policies to specify how AWS will scale up or down.
- Create or update the CloudWatch alarms which will trigger the autoscaling policies.
- Wait until the autoscaling group has the new instances with the golden AMI.
- Deregister the old instances.

#### Before using this deployer

Forseti's _golden instance_ deployer uses a _gold AMI_, which is an AMI packed with all the software you need, except your application specific code. Unfortunately, forseti currently is not able to generate a gold AMI for you, so you'll need to create one manually.

This is actually a very easy operation, so don't panic. All you need to do is create a new EC2 Instance from an AMI with EBS root and provision it with all the software you need (apache, nginx, nodejs...) and its configurations (virtualhosts or similars). Once you've installed everything, create an AMI from the instance by right clicking on it on the AWS Console and select _"Create Image (EBS AMI)"_. There you go, you now have a gold AMI!

### Deploying

Once your forseti configuration file is ready, you can deploy your new application code with the CLI doing:

```
forseti deploy <application_name>
```

## Q&A

### Why did we call it Forseti?

We like to use god's names for our internal projects. We began using only Norse gods, but currently we have also Greek and Roman gods. In the Norse mythology, Forseti is "the presiding one" and we thought it has some coincidences with the purpose of this application. Forseti is the president of our applications, the utility which rules them all.

### Why did you create Forseti instead of using other utilities or AWS official tools such as CloudFormation or CodeDeploy?

We began building Forseti in 2013 and at that time there were no AWS official tools nor an interface to EC2 Autoscale. There was a good API to create images, alarms and autoscale groups but we missed an easy tool to mix everything. We did some research with [Netflix' asgard](https://github.com/Netflix/asgard) but it was a bit too much for us. So we started building Forseti to fit our needs and make it quick.

## License

Forseti is licensed under BSD license. See [LICENSE](LICENSE) for more information.
