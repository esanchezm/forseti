"""
Forseti configuration
"""
import json

from forseti.exceptions import ForsetiConfigurationException


class ForsetiConfiguration(object):
    """
    Forseti configuration handler
    """

    APPLICATIONS_KEY = 'applications'
    AUTOSCALE_KEY = 'autoscale'
    CONFIGS_KEY = 'configs'
    GROUPS_KEY = 'groups'
    POLICIES_KEY = 'policies'
    ALARMS_KEY = 'alarms'

    # Application configuration keys
    GOLD_KEY = 'gold'
    AUTOSCALE_GROUP_KEY = 'autoscale_group'
    SCALING_POLICIES_KEY = 'scaling_policies'
    LOAD_BALANCER_KEY = 'elb'
    DEPLOYMENT_STRATEGY = 'deployment_strategy'
    SNS_ARN = 'sns_notification_arn'

    def __init__(self, forseti_configuration):
        super(ForsetiConfiguration, self).__init__()
        self.forseti_configuration = forseti_configuration
        self.applications = {}
        self.application_names = []
        self.autoscale_groups = {}
        self.autoscale_group_names = []
        self.launch_configurations = {}
        self.launch_configuration_names = []
        self.policies = {}
        self.policy_names = []
        self.alarms = {}
        self.alarm_names = []

        self._parse_configuration()

    def _parse_configuration(self):
        """
        Parse the forseti configuration file
        """
        self._parse_applications_configuration()
        self._parse_autoscale_configuration()

    def _parse_applications_configuration(self):
        """
        Parse the applications configuration and fill in `applications` and
        `application_names` properties. Raises `ForsetiConfigurationException`
        in case some error is found.
        """
        self.applications = self._get_key_in_configuration(
            self.forseti_configuration,
            self.APPLICATIONS_KEY
        )
        self.application_names = self.applications.keys()

    def _parse_autoscale_configuration(self):
        """
        Parse the autoscale configuration and fill in `autoscale_groups`,
        `autoscale_group_names`, `launch_configurations`, `launch_configuration_names`,
        `policies`, `policy_names`, `alarms` and `alarm_names` properties.
        Raises `ForsetiConfigurationException` in case some error is found.
        """
        autoscale = self._get_key_in_configuration(
            self.forseti_configuration,
            self.AUTOSCALE_KEY
        )

        self._parse_autoscale_groups(autoscale)
        self._parse_autoscale_launch_configurations(autoscale)
        self._parse_autoscale_policies(autoscale)
        self._parse_autoscale_alamrs(autoscale)

    def _parse_autoscale_groups(self, autoscale):
        """
        Parse the autoscale groups configuration and fill in `autoscale_groups`
        and `autoscale_group_names` properties. Raises `ForsetiConfigurationException`
        in case some error is found.
        """
        self.autoscale_groups = self._get_key_in_configuration(
            autoscale,
            self.GROUPS_KEY
        )
        self.autoscale_group_names = self.autoscale_groups.keys()

    def _parse_autoscale_launch_configurations(self, autoscale):
        """
        Parse the autoscale launch configurations' configuration and fill in `launch_configurations`
        and `launch_configuration_names` properties. Raises `ForsetiConfigurationException`
        in case some error is found.
        """
        self.launch_configurations = self._get_key_in_configuration(
            autoscale,
            self.CONFIGS_KEY
        )
        self.launch_configuration_names = self.launch_configurations.keys()

    def _parse_autoscale_policies(self, autoscale):
        """
        Parse the autoscale policies and fill in `policies` and `policy_names`
        properties. Raises `ForsetiConfigurationException` in case some error
        is found.
        """

        self.policies = self._get_key_in_configuration(
            autoscale,
            self.POLICIES_KEY
        )
        self.policy_names = self.policies.keys()

    def _parse_autoscale_alamrs(self, autoscale):
        """
        Parse the autoscale alarms and fill in `alarms` and `alarm_names`
        properties. Raises `ForsetiConfigurationException` in case some error
        is found.
        """
        self.alarms = self._get_key_in_configuration(autoscale, self.ALARMS_KEY)
        self.alarm_names = self.alarms.keys()

    def _get_key_in_configuration(self, configuration, key):
        """
        Get a `key` from a `configuration` checking if it exists and if the value
        is a dictionary. Raises a `ForsetiConfigurationException` if any of
        the conditions are not met.
        """
        if key not in configuration:
            raise ForsetiConfigurationException("%s key not found" % key)

        value = configuration[key]
        if not isinstance(value, dict):
            raise ForsetiConfigurationException("%s is not a dictionary" % key)

        return value

    def get_application_configuration(self, application):
        """
        Get the `application` configuration dictionary.
        Raises `ForsetiConfigurationException` if `application` is unknown.
        """
        if application not in self.application_names:
            return {}

        return self.applications[application]

    def get_autoscale_group(self, application):
        """
        Get the `application` autoscale group name.It returns only the name, not
        the autoscale group configuration. You should use `get_autoscale_group_configuration()`
        for that purpose.
        Raises `ForsetiConfigurationException` if `application` is unknown.
        """
        application_configuration = self.get_application_configuration(application)
        if self.AUTOSCALE_GROUP_KEY not in application_configuration:
            raise ForsetiConfigurationException(
                "Application `%s` configuration does not have `%s` key" %
                (application, self.AUTOSCALE_GROUP_KEY)
            )

        return application_configuration[self.AUTOSCALE_GROUP_KEY]

    def get_scaling_policies(self, application):
        """
        Get the `application` scaling policies. It returns only the names, not
        the policies configuration. You should use `get_policy_configuration()`
        for that purpose.
        Raises `ForsetiConfigurationException` if `application` is unknown or
        it has no `SCALING_POLICIES_KEY` defined.
        """
        application_configuration = self.get_application_configuration(application)
        if self.SCALING_POLICIES_KEY not in application_configuration:
            raise ForsetiConfigurationException(
                "Application `%s` configuration does not have `%s` key" %
                (application, self.SCALING_POLICIES_KEY)
            )

        return application_configuration[self.SCALING_POLICIES_KEY]

    def get_gold_instance_configuration(self, application):
        """
        Get the `application` gold image configuration.
        Raises `ForsetiConfigurationException` if `application` is unknown or
        it has no `GOLD_KEY` defined.
        """
        application_configuration = self.get_application_configuration(application)
        if self.GOLD_KEY not in application_configuration:
            raise ForsetiConfigurationException(
                "Application `%s` configuration does not have `%s` key" %
                (application, self.GOLD_KEY)
            )

        return application_configuration[self.GOLD_KEY]

    def get_autoscale_group_configuration(self, application):
        """
        Get the `application` autoscale group configuration.
        Raises `ForsetiConfigurationException` if `application` is unknown or
        it has no `AUTOSCALE_GROUP_KEY` defined.
        """
        application_configuration = self.get_application_configuration(application)
        if self.AUTOSCALE_GROUP_KEY not in application_configuration:
            raise ForsetiConfigurationException(
                "Application `%s` configuration does not have `%s` key" %
                (application, self.AUTOSCALE_GROUP_KEY)
            )

        group = application_configuration[self.AUTOSCALE_GROUP_KEY]
        if group not in self.launch_configuration_names:
            raise ForsetiConfigurationException(
                "Autoscale group `%s` configuration not found" % group
            )

        return self.autoscale_groups[group]

    def get_launch_configuration_configuration(self, application):
        """
        Get the `application` launch configuration' configuration.
        Note that the configuration forces to use the same name for launch
        configuration and autoscale groups.
        Raises `ForsetiConfigurationException` if `application` is unknown or
        it has no `AUTOSCALE_GROUP_KEY` defined.
        """
        if self.AUTOSCALE_GROUP_KEY not in self.applications[application]:
            raise ForsetiConfigurationException(
                "Application %s configuration does not have %s key" %
                (application, self.AUTOSCALE_GROUP_KEY)
            )

        group = self.applications[application][self.AUTOSCALE_GROUP_KEY]
        if group not in self.launch_configuration_names:
            raise ForsetiConfigurationException(
                "Launch configuration `%s` configuration not found" % group
            )

        return self.launch_configurations[group]

    def get_policy_configuration(self, policy):
        """
        Get the `policy` configuration dictionary.
        Raises `ForsetiConfigurationException` if `policy` is unknown.
        """
        if policy not in self.policy_names:
            raise ForsetiConfigurationException(
                "Policy %s not found" % policy
            )

        return self.policies[policy]

    def add_application(
        self,
        application_name,
        application_configuration,
        group_configuration,
        launch_configuration
    ):
        if application_name not in application_configuration.keys():
            raise ForsetiConfigurationException(
                ("Incorrect application name provided. The application_name",
                 "given is not present in the application_configuration")
            )

        self.forseti_configuration[self.APPLICATIONS_KEY].update(
            application_configuration
        )
        self.forseti_configuration[self.AUTOSCALE_KEY][self.GROUPS_KEY].update(
            group_configuration
        )
        self.forseti_configuration[self.AUTOSCALE_KEY][self.CONFIGS_KEY].update(
            launch_configuration
        )
        self.application_names.append(application_name)
        self.autoscale_group_names.extend(group_configuration.keys())
        self.launch_configuration_names.extend(launch_configuration.keys())

    def dump(self, pretty=False):
        """
        Dumps the configuration into a JSON
        """
        kwargs = {}
        if pretty:
            kwargs = {
                'sort_keys': True,
                'indent': 4,
                'separators': (',', ': '),
            }

        return json.dumps(self.forseti_configuration, **kwargs)
