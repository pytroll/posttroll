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

.. contents::
   :local:
   :depth: 2



Use Example
-----------

The main use of this library is the :class:`posttroll.message.Message`,
:class:`posttroll.subscriber.Subscribe` and
:class:`posttroll.publisher.Publish` classes, but the `nameserver` script is
also necessary. The `nameserver` scripts allows to register data publishers and
then for the subscribers to find them. Here is the usage of the `nameserver`
script::

  usage: nameserver [-h] [-d {start,stop,status,restart}] [-l LOG] [-v]

  optional arguments:
    -h, --help            show this help message and exit
    -d {start,stop,status,restart}, --daemon {start,stop,status,restart}
                          Run as a daemon
    -l LOG, --log LOG     File to log to (defaults to stdout)
    -v, --verbose         print debug messages too
    --no-multicast        disable address broadcasting via multicasting


So, after starting the nameserver, making two processes communicate is fairly
easy. Here is an example of publishing code::

        from posttroll.publisher import Publish
        from posttroll.message import Message
        import time

        try:
            with Publish("a_service", 9000) as pub:
                counter = 0
                while True:
                    counter += 1
                    message = Message("/counter", "info", str(counter))
                    print "publishing", message
                    pub.send(str(message))
                    time.sleep(3)
        except KeyboardInterrupt:
            print "terminating publisher..."

And the subscribing code::

    from posttroll.subscriber import Subscribe

    with Subscribe("a_service", "counter",) as sub:
        for msg in sub.recv():
            print msg

There is also a threaded container for the listener that can be
used eg. inside a class for continuously monitoring incoming messages::

        from posttroll.publisher import NoisyPublisher
        from posttroll.listener import ListenerContainer
        from posttroll.message import Message
        import time

        pub = NoisyPublisher("test")
        pub.start()
        sub = ListenerContainer(topics=["/counter"])
        # Wait that both sub and pub to register to nameserver
        time.sleep(3)
        for counter in range(5):
            msg_out = Message("/counter", "info", str(counter))
            pub.send(str(msg_out))
            print "published", str(msg_out)
            msg_in = sub.output_queue.get(True, 1)
            print "received", str(msg_in), ""
        pub.stop()
        sub.stop()

If you do not want to broadcast addresses via multicasting to nameservers in your network,
you can start the nameserver with the argument *--no-multicast*. Doing that, you have
to specify the nameserver(s) explicitly in the publishing code::

        from posttroll.publisher import Publish
        from posttroll.message import Message
        import time

        try:
            with Publish("a_service", 9000, nameservers=['localhost']) as pub:
                counter = 0
                while True:
                    counter += 1
                    message = Message("/counter", "info", str(counter))
                    print "publishing", message
                    pub.send(str(message))
                    time.sleep(3)
        except KeyboardInterrupt:
            print "terminating publisher..."

.. seealso:: :class:`posttroll.publisher.Publish`
             and :class:`posttroll.subscriber.Subscribe`

Converting from older posttroll versions
----------------------------------------

Migrating from older versions of posttroll (pre v0.2), so some adaptations have
to be made. Instead of *data types*, the services now have *aliases*. So, for
the publishing, the following call::

  with Publish("a_service", ["data_type1", "data_type2"], 9000) as pub:

would translate into::

  with Publish("a_service", 9000, ["data_type1", "data_type2"]) as pub:

On the subscriber side, the following::

  with Subscribe("data_type1") as sub:


would have to be changed to::

  with Subscribe("a_service") as sub:

Note that the behaviour is changed: all the messages comming from the publisher
*a_service* would be iterated over, including messages that have another data
type than the one you want. This is why there is now the possibility to add a
subject filter directly inside the :class:`posttroll.subscriber.Subscribe`
call::

  with Subscribe("a_service", "data_type1") as sub:

This means that the subjects of the messages you are interested in should start
with "data_type1" though...


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

Name server
~~~~~~~~~~~

.. automodule:: posttroll.ns
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
