.. _list_of_commands:

List of available oficial commands
==================================

Forseti commands system is extendible system so anyone can create their own commands and operations. We've created our own commands which are bundled by default. Those commands are common operations like creating, regenerating, deploying and showing the status of an application and its autoscaling group.

.. program:: forseti init

.. option:: init application instance_id --deployer=deploy_and_snapshot|golden_instances [--no-reboot-instance]

    Initialize ``application`` in Forseti using an instance.

    **Parameters**:

        * ``application``: Application name to be deployed

        * ``instance_id``: Id of an instance in AWS to create an AMI from. The id is in the format ``i-xxxxxxxx``

    **Options**:

        * ``--ami=ami-id``: Use this specific AMI to create or update the autoscaling group

        * ``-- extra_arguments``: Extra arguments to be passed to the deploy command as parameters. **Note**: Please notice the ``--`` before passing the ``extra_arguments``


    **Examples**::

        forseti deploy backend

    Deploy the backend application. If it was deployed successfuly (that is, the deploy command returned 0) update or create the autoscaling group, configurations, policies and alarms. ::

        forseti deploy backend -- --no-verify-ssh

    Deploy the backend application and pass ``--no-verify-ssh`` to the deploy command. ::

        forseti deploy backend --ami=ami-xxxxxx

    Create or update the autoscaling gruoup, configurations, policies and alarms of the application using a specific AMI.



.. program:: forseti deploy

.. option:: deploy application [--ami=ami-id] [-- extra_arguments]

    Deploy ``application`` and create or update an autoscaling group.

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

    Create or update the autoscaling gruoup, configurations, policies and alarms of the application using a specific AMI.


