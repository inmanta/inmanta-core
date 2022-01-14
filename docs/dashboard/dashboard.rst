.. warning::
    The Inmanta dashboard has been deprecated in favour of the `Inmanta Web Console <../../extensions/inmanta-ui/index.html>`_.

The project overview
--------------------

When opening the dashboard the project overview page will be the first page greeting you.
It has several elements:

.. figure:: /dashboard/images/img_1.png
   :width: 100%
   :align: center
   :alt: The project overview

   The project overview page

Let's go over what some of these buttons do:

1. The "inmanta logo" button: takes you back to this page.
2. List of created projects: Lists all existing projects. For more on projects see :doc:`the glossary <../glossary>`.
   Clicking on the name of a project will take you to its page.
3. Project delete button:
   Deletes the project and all the environments it contains.
   This will delete the history and environments, but it will not purge the system of changes made or managed by the orchestrator.
4. Report an issue:
   If you run into any issues/bugs, this button will take you to a page where you can open a new issue.

.. figure:: /dashboard/images/img_2.png
   :width: 100%
   :align: center
   :alt: The project overview

   The project overview page

5. Environment navigation button:
   Displays a list of projects and their environments.
   Allows navigation to any environment managed by this orchestrator, by simply clicking it's name.
6. Add new project button:
   This will take you through the creation of a new project and the creation of its first environment.
7. Green checkmark:
   This will take you to the orchestrator status page, displaying all sorts of useful information about the orchestrator instance.
   If the dashboard loses its connection to the server, this green checkmark will turn into a red cross.

Create a new project
--------------------

Using the ``Add new project`` button we can create new projects:

.. figure:: /dashboard/images/img_3.png
   :width: 100%
   :align: center
   :alt: Adding a new project

   Adding a new project

Once ``Create`` is pressed, you are immediately taken to the "Create a new Environment" screen.
This will help you set up your first environment.
Pressing cancel will leave the project empty.

.. figure:: /dashboard/images/img_4.png
   :width: 100%
   :align: center
   :alt: Creating a new Environment

   Creating a new Environment

The two screenshots above are equivalent to the following inmanta-cli commands:

.. code-block:: sh
  :linenos:

  inmanta-cli project create -n dashboard-test
  inmanta-cli environment create -n quickstart-env -p quickstart -r https://github.com/inmanta/quickstart.git -b master

When in an environment, a new button at the bottom will appear:

.. figure:: /dashboard/images/img_17.png
   :width: 100%
   :align: center
   :alt: The stop button

   The emergency stop button

This big red button will stop all of the orchestrator's operations for the current environment.


The Environment Portal
----------------------

Once you press the create button, you will be taken to the portal of the newly created environment:

.. figure:: /dashboard/images/img_5.png
   :width: 100%
   :align: center
   :alt: A newly created environment

   A newly created environment

This environment is currently empty because the model has not been compiled yet.
We can use the ``Recompile`` button to do this.
This will clone the repository if it hadn't been already and then compile the current model.
There is also an extra option for the recompile, which is ``Update project & Recompile``.
This will pull in any new commits and then compile the model.

Once the compile has succeeded, the orchestrator will automatically deploy the model.  The deployment state is then shown in the portal.

Using the ``Compile Reports`` button we can diagnose problems if our compile failed.

.. figure:: /dashboard/images/img_6.png
   :width: 100%
   :align: center
   :alt: A compile report

   A compile report

You can click the arrow icon next to any item to expand it and see the output of the executed command.

Next, we have the ``Force deploy`` and ``Force repair`` buttons.
Those are similar in function, and can be confusing to new users:

- The ``Force deploy`` button will go through *Every* resource and redeploy the resource.
- The ``Force repair`` button by contrast, will only go through resources that are currently not in a deployed state.

Finally we have the ``Decommission``, ``Edit``, ``Clone`` and ``Clear`` buttons, found under the ``Decommission`` dropdown menu:

- Decommission: pushes a model that purges all resources deployed by the model.
- Edit: change the configuration of the environment, such as the git repo url or what branch to use.
- Clone: create a new environment using the same git repo and branch
- Clear: Clears the environment. This will remove all versions and compilations. It does not decommission the currently deployed model.

.. note::
    When using ``Clear`` followed by a ``Recompile``, the version number will be incremented as if the previous versions were still there, but these versions will no longer be present.

The Version Overview
--------------------

Below the ``Portal`` we have the ``Versions``.
This will take us to an overview of all previously compiled versions of the model and their state.
Do note that a version is created for every compile and this is not tied to the model being updated in git.

Each version has 4 buttons on the right to interact with it:

.. figure:: /dashboard/images/img_7.png
   :width: 100%
   :align: center
   :alt: Version buttons

They are, in order from left to right:

- Perform dry run: the orchestrator will go through all resources in the model and compare their current state to their desired state. This can be useful to double-check what effect the deployment of a version might have on your current environment.
- Dry run report: will take you to the report of the last performed dry run, without performing a new one.
- Release version: If ``auto-deploy`` in the ``environment settings`` is set to ``False``, this button can be used to deploy the model, otherwise this button will be grayed out.
- Remove version: removes the selected version from the inmanta environment.

Finally, clicking the version number will take us to the overview of that particular version.
It gives the same options as the version overview does and it displays a list of all resources and their current state.

.. figure:: /dashboard/images/img_8.png
   :width: 100%
   :align: center
   :alt: Resource overview

Using the filters we can filter for resources by type, by agent used to deploy the resource, by value and by deploy state.
This display is continuously updated, both during deploys and after, when the orchestrator goes through all resources to make sure they remain in the desired state.

Taking a closer look at the a specific resource, there are 2 important buttons, the ``Dependency`` button and a ``magnifying glass``.
The ``Dependency`` button is only available if a resource depends on other resources.
When pressed, it will add lines to the table displaying each dependency and it's current state:

.. figure:: /dashboard/images/img_9.png
   :width: 100%
   :align: center
   :alt: Resource dependencies

   Resource dependencies

The `magnifying glass` icon will take us to an in depth overview of the resource.
This will show a complete breakdown of the resource's desired state at the top and an action log at the bottom.

The desired state breakdown allows for easy inspection of the impact the resource will have.
For example, the resource in the image below will deploy a file with path `/etc/my.cnf` and file permission `644`.
We can even inspect the file's content.

.. figure:: /dashboard/images/img_10.png
   :width: 100%
   :align: center
   :alt: Resource view

   Resource desired state view

The action log shows a log of actions taken on the given resource.
This varies from dry-runs to deploys.
This log will typically start filling up with deploys due to the orchestrator enforcing the desired state.
Again we can further inspect an action by pressing the drop down arrow.

.. figure:: /dashboard/images/img_11.png
   :width: 100%
   :align: center
   :alt: Resource action

   Resource action view

Each of these logs can then be further analyzed by pressing the ``magnifying glass``.

The Resources Overview
----------------------

The resources overview, not to be confused with the similar resource version overview, gives an overview of all known resources.
This is not only for resources of the currently deployed model, but potentially resources from older models and the state they are in.

.. figure:: /dashboard/images/img_12.png
   :width: 100%
   :align: center
   :alt: Resources Overview

   The Resources Overview

While not as in depth as the resource version overview, it does link every resource to its deployed version, so the resource can be inspected there.

The Parameters View
-------------------

The parameter overview gives a list of parameters.
Parameters are part of the model, but their value may or may not be known at compile time.
For example, the IP address of a virtual machine that is created by the model.

.. figure:: /dashboard/images/img_13.png
   :width: 100%
   :align: center
   :alt: Parameter overview

   The Parameter overview

Each parameter can be individually inspected or deleted.
Inspecting the resource allows us to read additional metadata if any is available.

The Agent Overview
------------------

The agent overview shows different agents and the state they are in.

.. figure:: /dashboard/images/img_14.png
   :width: 100%
   :align: center
   :alt: Agent overview

   The Agent overview

This overview allows us to ``Force deploy`` and ``Force repair`` resources on a per agent basis.
Pausing an agent stops deployments for that agent.
Useful when, for example, diagnosing problems on the machine the agent deploys to, without having to stop enforcement of the whole model.

The Agent Processes overview, lists the different processes running agents.
Clicking on the ``magnifying glass`` allows us to inspect each process in more detail:

.. figure:: /dashboard/images/img_15.png
   :width: 100%
   :align: center
   :alt: Agent process inspection

   Agent process inspection

Here we can find the process ``pid``, the ip addresses the server has bound to and what version of Python inmanta is running on, amongst other things.

Environment Settings
--------------------

The settings menu shows settings that are configured per environment.

.. figure:: /dashboard/images/img_16.png
   :width: 100%
   :align: center
   :alt: Environment settings

   The Environment settings

Hovering over the information icon tells you what each setting does,
the edit icon allows for updating the setting and the delete button clears the setting and applies a default value if available.
