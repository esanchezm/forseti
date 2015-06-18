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

### Deploying

Once your forseti configuration file is ready, you can deploy your new application code with the CLI doing:

```
forseti deploy <application_name>
```

## License

Forseti is licensed under BSD license. See [LICENSE](LICENSE) for more information.
