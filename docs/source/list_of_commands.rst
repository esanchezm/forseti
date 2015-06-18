.. _list_of_commands:

List of available oficial commands
==================================

Forseti command system is an extensible system so anyone can create their own commands and operations. We've created our own set of commands which are bundled by default. Those commands are common operations like creating, regenerating, deploying and showing the status of an application and its autoscaling group.

.. program:: forseti init

.. option:: init

    Initialize ``application`` in Forseti using an instance in AWS.

    **Parameters**:

        * ``application``: Application name to be deployed

        * ``instance_id``: Id of an instance in AWS to create an AMI from. The id is in the format ``i-xxxxxxxx``

        .. TODO: Add link to deployers documentation

        * ``--deployer``: This parameter is used to tell Forseti how to manage future deploys. For more information, please read our section about deployers.

    **Options**:

        * ``--no-reboot-instance``: By default, the instance will be rebooted to create the AMI. If you want to override this behaviour, use this flag. It's not recommended because it doesn't guarantee the filesystem integrity.

    **Examples**::

        forseti init backend i-1a23b4567 --deployer=deploy_and_snapshot

    Forseti will create an AMI using the given instance and setup a new autoscaling group. This new group won't have any effect because Forseti doesn't create any alarm to scale in or out the instances in the group.  ::

        forseti init backend i-1a23b4567 --deployer=deploy_and_snapshot --no-reboot-instance

    The same process but the instance will not be rebooted before creating the AMI.

.. program:: forseti deploy

.. option:: deploy

    Deploy an application and create or update an autoscaling group.

    **Parameters**:

        * ``application``: Application name to be deployed

    **Options**:

        * ``--ami=ami-id``: Use this specific AMI to create or update the autoscaling group

        * ``-- extra_arguments``: Extra arguments to be passed to the deploy command as parameters. **Note**: Please notice the ``--`` before passing the ``extra_arguments``

    **Examples**::

        forseti deploy backend

    Deploy the backend application. If it was deployed successfuly (that is, the deploy command returned 0) update or create the autoscaling group, configurations, policies and alarms. ::

        forseti deploy backend -- --no-verify-ssh

    Deploy the backend application and pass ``--no-verify-ssh`` to the deploy command. ::

        forseti deploy backend --ami=ami-xxxxxx

    Create or update the autoscaling group, configurations, policies and alarms of the application using a specific AMI.


.. program:: forseti deploy

.. option:: regenerate

    Rebuild the AMI of the instances belonging to an application and regenerate the autoscaling group, configuration, alarms and policies. Notice this doesn't deploy your application code.

    **Parameters**:

        * ``application``: Application name to be regenerated

.. program:: forseti status

.. option:: status

    Show the status of the application. This includes information about the instances belonging to the autoscaling group (including the status in the load balancers) and the latest actions which happened in it.

    **Parameters**:

        * ``application``: Application name to get the status from.

    **Options**:

        * ``--daemon``: Run the status in a loop process. By default, ``status`` command will print the status and finish, if you want to monitor the status of an application, you can use this option to do it.

        * ``--activities=<amount>``: Number of autoscaling activities to show.

        * ``--format=<format>``: Output format. By default, Forseti will print the status using terminal colors in a structured format. You can use other formats:

            * ``tree``: Default formatter.

            * ``json``: JSON formatter.

            * ``plain``: Plain format.

.. program:: forseti list_configurations

.. option:: list_configurations

    This command will print all the autoscaling launch configurations. You can also get only the configurations of a specific application.

    **Options**:

        * ``application``: Application name to get the autoscaling launch configurations.

.. program:: forseti cleanup_configurations

.. option:: cleanup_configurations

    Delete the autoscaling launch configurations to clean up AWS and avoid reaching their limit. By default it will remove launch configurations from all the applications, you can do it in only one application too.

    AWS has some soft limitations with the number of autoscaling elements you can create. The default limit for autoscaling launch configurations is 50, and considering that each deploy will create a new one, you may reach that limit sooner or later. This command will help you removing old launch configurations and freeing some space and resources.

    **Options**:

        * ``application``: Application name to delete the autoscaling launch configurations.

        * ``--desired_configurations=<desired>``: Number of launch configurations to leave.
