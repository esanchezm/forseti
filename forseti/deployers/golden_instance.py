from forseti.deployers.base import BaseDeployer
from forseti.models import GoldenEC2Instance
from forseti.utils import Balloon


class GoldenInstanceDeployer(BaseDeployer):
    """Deployer for ticketea's infrastructure"""

    def __init__(self, configuration):
        super(GoldenInstanceDeployer, self).__init__(configuration)
        self.gold_instance = None

    def create_ami_from_golden_instance(self, application):
        """
        Create an AMI from a golden EC2 instance
        """
        self.gold_instance = GoldenEC2Instance(
            application,
            self.configuration.get_gold_instance_configuration(application)
        )

        self.gold_instance.launch_and_wait()
        self.gold_instance.provision()
        ami_id = self.gold_instance.create_image()
        self.gold_instance.terminate()
        self.gold_instance = None

        return ami_id

    def setup_autoscale(self, application, ami_id):
        """
        Creates or updates the autoscale group, launch configuration, autoscaling
        policies and CloudWatch alarms.

        :param application: Application name
        :param ami_id: AMI id used for the new autoscale system
        """
        group = super(GoldenInstanceDeployer, self).setup_autoscale(application, ami_id)

        print "Waiting until instances are up and running"
        group.apply_launch_configuration_for_deployment()
        print "All instances are running"

    def deploy(self, application, ami_id=None):
        """
        Do the code deployment in a golden instance and setup an autoscale group
        with an AMI created from it.
        """
        balloon = Balloon("")
        if not ami_id:
            ami_id = self.create_ami_from_golden_instance(application)
            print "New AMI %s from golden instance" % ami_id
        self.setup_autoscale(application, ami_id)

        balloon.finish()
        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)
