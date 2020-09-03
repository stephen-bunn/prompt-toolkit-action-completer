.. _getting-started:

===============
Getting Started
===============

| **Welcome to Action Completer!**
| This page should hopefully provide you with enough information to get you started
| with defining actions, groups, and parameters for use with prompt-toolkit.

Installation and Setup
======================

Installing the package should be super duper simple as we utilize Python's setuptools.

.. code-block:: bash

   $ poetry add prompt-toolkit-action-completer
   $ # or if you're old school...
   $ pip install prompt-toolkit-action-completer

Or you can build and install the package from the git repo.

.. code-block:: bash

   $ git clone https://github.com/stephen-bunn/prompt-toolkit-action-completer.git
   $ cd ./prompt-toolkit-action-completer
   $ poetry build
   $ pip install ./dist/*.whl
