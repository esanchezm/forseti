class ForsetiException(Exception):
    pass


class EC2InstanceException(ForsetiException):
    pass


class EC2AutoScaleException(ForsetiException):
    pass


class ForsetiConfigurationException(ForsetiException):
    pass


class ForsetiDeployException(ForsetiException):
    pass
