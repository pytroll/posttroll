.. PostTroll documentation master file, created by
   sphinx-quickstart on Tue Sep 11 12:58:14 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PostTroll
=========

PostTroll is a message system for pytroll_.

A typical use is for event-driven production chains, using messages for
notifications.

To get the software, take a look on github_.

.. _pytroll: http://www.pytroll.org
.. _github: http://github.com/mraspaud/posttroll


The main use of this library is the :class:`posttroll.message.Message`,
:class:`posttroll.subscriber.Subscribe` and
:class:`posttroll.publisher.Publish` classes, but the `nameserver` script can
be usefull too.

The `namesever` scripts allows to register data publishers and then for the
subscribers to find them. Here is the usage of the `nameserver` script::

  usage: nameserver [-h] [-d {start,stop,restart}] [-l LOG]

  optional arguments:
    -h, --help            show this help message and exit
    -d {start,stop,restart}, --daemon {start,stop,restart}
                          Run as a daemon
    -l LOG, --log LOG     File to log to



API
---


Publisher
~~~~~~~~~

.. automodule:: posttroll.publisher
   :members:
   :undoc-members:

Subscriber
~~~~~~~~~~

.. automodule:: posttroll.subscriber
   :members:
   :undoc-members:

Messages
~~~~~~~~

.. automodule:: posttroll.message
   :members:
   :undoc-members:

Address receiver
~~~~~~~~~~~~~~~~

.. automodule:: posttroll.address_receiver
   :members:
   :undoc-members:


Multicasting
~~~~~~~~~~~~

Context
+++++++

.. automodule:: posttroll.message_broadcaster
   :members:
   :undoc-members:

Multicast code
++++++++++++++

.. automodule:: posttroll.bbmcast
   :members:
   :undoc-members:


Connections
~~~~~~~~~~~

.. automodule:: posttroll.connections
   :members:
   :undoc-members:


Misc
~~~~

.. automodule:: posttroll
   :members:
   :undoc-members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

