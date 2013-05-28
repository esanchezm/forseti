from datetime import datetime
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection


class EC2(object):
    """
    EC2 base class
    """

    def __init__(self, application, configuration=None):
        self.ec2 = EC2Connection()
        self.configuration = configuration or {}
        self.application = application
        self.resource = None
        self.today = datetime.today().strftime("%Y-%m-%d")


class EC2AutoScale(EC2):
    """
    EC2 autoscale base class
    """

    def __init__(self, name, application, configuration=None):
        super(EC2AutoScale, self).__init__(application, configuration)
        self.autoscale = AutoScaleConnection()
        self.name = "%s-%s" % (name, self.today)


class ELB(EC2):
    """
    ELB base class
    """

    def __init__(self, name, application, configuration=None):
        super(ELB, self).__init__(application, configuration)
        self.elb = ELBConnection()
        self.name = name


class CloudWatch(EC2):
    """
    CloudWatch base class
    """

    def __init__(self, application, configuration=None):
        super(CloudWatch, self).__init__(application, configuration)
        self.cloudwatch = CloudWatchConnection()
