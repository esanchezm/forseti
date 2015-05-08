from datetime import datetime
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection


class AWS(object):
    """
    AWS base class
    """

    def __init__(self, application, configuration=None, resource=None):
        self.configuration = configuration or {}
        self.application = application
        self.resource = resource
        self.today = datetime.today().strftime("%Y-%m-%d")


class EC2(AWS):
    """
    EC2 base class
    """

    def __init__(self, application, configuration=None, resource=None):
        super(EC2, self).__init__(application, configuration, resource)
        self.ec2 = EC2Connection()


class EC2AutoScale(EC2):
    """
    EC2 autoscale base class
    """

    def __init__(self, name, application, configuration=None, resource=None):
        super(EC2AutoScale, self).__init__(application, configuration, resource)
        self.autoscale = AutoScaleConnection()
        self.name = name

    @property
    def generated_name(self):
        return "%s-%s" % (self.name, self.today)


class ELB(AWS):
    """
    ELB base class
    """

    def __init__(self, name, application, configuration=None, resource=None):
        super(ELB, self).__init__(application, configuration, resource)
        self.elb = ELBConnection()
        self.name = name


class CloudWatch(AWS):
    """
    CloudWatch base class
    """

    def __init__(self, application, configuration=None, resource=None):
        super(CloudWatch, self).__init__(application, configuration, resource)
        self.cloudwatch = CloudWatchConnection()
