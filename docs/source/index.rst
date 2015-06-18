Forseti's documentation
=======================

Forseti is a two-in-one utility:

* A CLI tool to manage your AWS autoscaling groups, policies, etc. It allows you to easily deploy your code in AWS using your preferred strategy defined as a _deployer_. A _deployer_ is a class that, using previous models, defines a deployment strategy. More on this later.
* A set of classes wrapping boto, provinding friendly high level operations that allow you to easily do common administration operations.

Forseti is devops agnostic in the sense that it all their commands can be plugged with any orquestration tool you use, in ticketea we've used Chef, Puppet and Ansible in conjuction with it.


Contents:

.. toctree::
   :maxdepth: 2

   introduction
   quickstart
   configuring_forseti
   deployers
   list_of_commands
   questions_and_answers
   license


Internals documentation
~~~~~~~~~~~~~~~~~~~~~~~

If you are looking for information on a specific function, class or method, this part of the documentation is for you.

.. toctree::
    :maxdepth: 2

    models_helpers


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

