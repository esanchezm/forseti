from datetime import datetime
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection


class EC2(object):
    """
    EC2 base class
    """

    def __init__(self, configuration, application):
        self.ec2 = EC2Connection()
        self.configuration = configuration
        self.application = application
        self.resource = None
        self.version = datetime.today().strftime("%Y-%m-%d-%s")


class EC2AutoScale(EC2):
    """
    EC2 autoscale base class
    """

    def __init__(self, name, configuration, application):
        super(EC2AutoScale, self).__init__(configuration, application)
        self.autoscale = AutoScaleConnection()
        self.name = "%s-%s" % (name, self.version)


class ELB(EC2):
    """
    ELB base class
    """

    def __init__(self, name, configuration, application):
        super(ELB, self).__init__(configuration, application)
        self.elb = ELBConnection()
        self.name = name


class CloudWatch(EC2):
    """
    CloudWatch base class
    """

    def __init__(self, configuration, application):
        super(CloudWatch, self).__init__(configuration, application)
        self.cloudwatch = CloudWatchConnection()
