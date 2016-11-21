Changelog
=========

v1.3.0 (2016-11-21)
-------------------

- Update changelog. [Martin Raspaud]

- Bump version: 1.2.2 → 1.3.0. [Martin Raspaud]

- Merge branch 'master' into release-v1.2.3. [Martin Raspaud]

- Update changelog. [Martin Raspaud]

- Bump version: 1.2.1 → 1.2.2. [Martin Raspaud]

- Generalize docstrings. [Panu Lahtinen]

- Move Listener and ListenerContainer from trollduction to posttroll.
  [Panu Lahtinen]

v1.2.2 (2016-11-10)
-------------------

- Update changelog. [Martin Raspaud]

- Bump version: 1.2.1 → 1.2.2. [Martin Raspaud]

- Make publishing thread-safe through locking. [Martin Raspaud]

- Merge branch 'master' into develop. [Martin Raspaud]

- Do address fetching after address listener has been started (fixes #5)
  [Martin Raspaud]

- Reorganize imports in subcriber.py. [Martin Raspaud]

- Add lock around subscriber's address handling. [Martin Raspaud]

v1.2.1 (2016-10-27)
-------------------

- Update changelog. [Martin Raspaud]

- Bump version: 1.2.0 → 1.2.1. [Martin Raspaud]

- Add bumpversion and gitchangelog config files. [Martin Raspaud]

- Add a logger. [Martin Raspaud]

- Added a couple log messages. [Martin Raspaud]

- Import _strptime for thread incompatibility workaround. [Martin
  Raspaud]

- Change repo to pytroll/posttroll. [Martin Raspaud]

v1.2.0 (2016-05-04)
-------------------

- Update changelog. [Martin Raspaud]

- Bump version: 1.1.0 → 1.2.0. [Martin Raspaud]

- Merge branch 'develop' into release-v1.1.1. [Martin Raspaud]

  Conflicts:
  	posttroll/address_receiver.py

- Perform a minor cosmetic fix. [Martin Raspaud]

- Merge pull request #1 from pnuu/develop. [Martin Raspaud]

  Fault tolerance for network errors

- Fault tolerance for network errors, logger -> LOGGER. [Panu Lahtinen]

- Allow the MC troup to be provided as an envvariable. [Martin Raspaud]

- Merge pull request #3 from khunger/dwd-develop. [Martin Raspaud]

  Fixed dangerous default value [] as argument

- Fixed dangerous default value [] as argument. [Christian Kliche]

- Merge pull request #2 from khunger/dwd-develop. [Martin Raspaud]

  Optional deactivation of multicasting

- Optional deactivation of multicasting. [Christian Kliche]

  Added new command line parameter "--no-multicast" to disable listening
  on address messages via multicasting. Instead nameserver listens for
  direct socket connections on specified port.
  Furthermore (client side), new argument "nameservers" added to ctor of NoisyPublisher.
  When non-empty, the NoisyPublisher does not use multicast to send
  own address to nameservers. Instead, NoisyPublisher connects to each nameserver
  directly to promote own address. Specification of nameserver port
  is possible. If no port was defined, the default broadcasting bport will be used (21200)
  for example: nameservers=['localhost','backupns:1234']


v1.1.0 (2016-01-28)
-------------------

Fix
~~~

- Bugfix: assigning the namesever arg to the nameserve kw... [Martin
  Raspaud]

Other
~~~~~

- Update changelog. [Martin Raspaud]

- Bump version: 1.0.2 → 1.1.0. [Martin Raspaud]

- Nameserver port can be specified as an environment variable (5557
  otherwise) [Martin Raspaud]

- Changed nameserver port to 5557 (to avoid conflict with HP data
  protector) [Martin Raspaud]

- Add a renew_context function for multithreading/processing cases.
  [Martin Raspaud]

- Rename logger to pytroll-logger to avoid system conflicts. [Martin
  Raspaud]

- Add setup.cfg for easy rpm generation. [Martin Raspaud]

- Subscriber can now request addresses from a nameserver on another
  host. [Martin Raspaud]

  This is done using the "nameserver" keyword.

v1.0.2 (2015-02-19)
-------------------

- Update changelog. [Martin Raspaud]

- Bump version: 1.0.1 → 1.0.2. [Martin Raspaud]

- Merge branch 'master' into develop. [Martin Raspaud]

  Conflicts:
  	posttroll/version.py

- Fix version formatting. [Martin Raspaud]

- Style cleanup. [Martin Raspaud]

- Style cleanup. [Martin Raspaud]

- Upgrade "publisher started on port" message to info. [Martin Raspaud]

- Print out publisher port when initialized for debug. [Martin Raspaud]

- Don't show message broadcasting advertizing messages. [Martin Raspaud]

- Allow unicode strings also. [Martin Raspaud]

v1.0.1 (2014-09-22)
-------------------

- Bump up version number. [Martin Raspaud]

- Update deployment info. [Martin Raspaud]

v1.0.0 (2014-09-22)
-------------------

- Bump up version number. [Martin Raspaud]

- Style. [Martin Raspaud]

- Add another publishing test. [Martin Raspaud]

- Publisher has default port setup to 0 (random) [Martin Raspaud]

- Style cleaning. [Martin Raspaud]

- Change "type" to "service" to reflect the more accurate use of
  posttroll. [Martin Raspaud]

- Correct tests to reflect the change in name vs aliases management.
  [Martin Raspaud]

- Add name to the list of aliases for the nameserver. [Martin Raspaud]

- Bug fix. [Martin Raspaud]

  mixed up Logger and logging.Logger.

- Add a few options to logger, and make a running script (entry point)
  [Martin Raspaud]

- Make context global to posttroll. [Martin Raspaud]

- Make pytroll formatter follow formatter standards. [Martin Raspaud]

- Logger cleanup. [Martin Raspaud]

- Fix logger. [Martin Raspaud]

- Add logger to posttroll. [Martin Raspaud]

- Set socket linger to 0 on exit. [Martin Raspaud]

- Cleanup. [Martin Raspaud]

- Update the doc and cleanup. [Martin Raspaud]

- Requesting on service "" now returns all addresses. [Martin Raspaud]

v0.2.0 (2014-03-24)
-------------------

- Check valid data in the message in right order. [Martin Raspaud]

- Style fix. [Martin Raspaud]

- Add smarter subscriber and publisher classes with NoisyPublisher and
  NSSubscriber. [Martin Raspaud]

- Documentation improvements to prepare the switch to new syntax.
  [Martin Raspaud]

- Fixing a broken test. (remove None poller by mistake) [Martin Raspaud]

- Cleanup. [Martin Raspaud]

- Updated version. [Martin Raspaud]

- Do not crash get_own_ip if we are disconnected. [Martin Raspaud]

  Conflicts:

  	posttroll/publisher.py


- Feature: centralized version number. [Martin Raspaud]

- Merge branch 'develop' into feature-no-datatypes. [Martin Raspaud]

- Add a noisy publisher. [Martin Raspaud]

- Change semaphore to a lock. [Martin Raspaud]

- Add a semaphore to avoid concurrency. [Martin Raspaud]

- Merge branch 'feature-dynamic-subscriber' into develop. [Martin
  Raspaud]

- Do not crash get_own_ip if we are disconnected. [Martin Raspaud]

- Add new streams in subscriber as they appear in the nameserver.
  [Martin Raspaud]

- Fix the documentation. [Martin Raspaud]

- Fix documentation. [Martin Raspaud]

- Change pwd to getpass for windows compatibility. [Martin Raspaud]

- Feature: Implemented a "status" daemon option. [Martin Raspaud]

- DOC: mentionned the nameserver. [Martin Raspaud]

- Updated version and license. [Martin Raspaud]

- Style: making pylint happy. [Martin Raspaud]

- Style: cleaning up. [Martin Raspaud]

- Removed printing, using logging instead. [Martin Raspaud]

- Daemonizing the nameserver. [Martin Raspaud]

- Feature: centralized version number. [Martin Raspaud]

- Documentation and code style. [Martin Raspaud]

- Reorg: put the TimeoutError in __init__.py. [Martin Raspaud]

- Doc: improved docstrings for message_broadcaster. [Martin Raspaud]

- Test update. [Martin Raspaud]

- TEST: fixed the unit tests. [Martin Raspaud]

- Merge branch 'feature-no-datatypes' of github.com:mraspaud/posttroll
  into feature-no-datatypes. [Martin Raspaud]

- Add coverall.io badge. [Martin Raspaud]

- Typo in docstring. [Martin Raspaud]

- Minor cleanup. [Martin Raspaud]

- Adapting check_age minimum interval to the max_age argument. [Martin
  Raspaud]

- Test and clean. [Martin Raspaud]

- More cleanup. [Martin Raspaud]

- Logging to console if not to file. [Martin Raspaud]

- A subscribe context doesn't need a publisher to start anymore. [Martin
  Raspaud]

- Cleanup. [Martin Raspaud]

- Remove obsolete file. [Martin Raspaud]

- Make the json serialization test independent of json implementation.
  [Martin Raspaud]

- More robust nameserver thread in testing. [Martin Raspaud]

- Add the publish/subscribe test cases. [Martin Raspaud]

- Adding the .travis.yml file. [Martin Raspaud]

- Integrating changes from the zmq3 branch, adding logging, and readying
  for travis. [Martin Raspaud]

- Now,  service="" means all services and service=None means no
  services. [Lars Orum Rasmussen]

- Added address as optional argument top Subscribe. [Lars Orum
  Rasmussen]

- Better default topic 'pytroll:/' [Lars Orum Rasmussen]

- Better port 0 checking. [Lars Orum Rasmussen]

  Now possible to easy subclass Publish


- Improved address listener. [Lars Orum Rasmussen]

- Printing ZMQ exception. [Lars Orum Rasmussen]

- Now importing time. [Lars Orum Rasmussen]

- Preparing for publishing of removal of addresses. [Lars Orum
  Rasmussen]

- Cleaner interface to adding and removing addresses. [Lars Orum
  Rasmussen]

- Cosmetic. [Lars Orum Rasmussen]

- 'address' are prepended to message subject. [Lars Orum Rasmussen]

- Easy access to all nameserver addresses. [Lars Orum Rasmussen]

- Better handling of adding and removing addresses. [Lars Orum
  Rasmussen]

- Longer default timeout. [Lars Orum Rasmussen]

- Now genreral heartbeat for Publisher. [Lars Orum Rasmussen]

  Better handling of adding and removing addresses


- Renamed old publisher and subscriber. [Lars Orum Rasmussen]

- More generic publisher and subscriber. [Lars Orum Rasmussen]

- Changes 'data_type' to 'name' [Lars Orum Rasmussen]

- Added a heartbeat (optional) [Lars Orum Rasmussen]

- Now test is updated for new Message.py. [Lars Orum Rasmussen]

- Mocking zmq. [Martin Raspaud]

- Doc: remove mock. [Martin Raspaud]

- Doc: update for rtd. [Martin Raspaud]

- Rtd compatibility? [Martin Raspaud]

- Doc: added the build scripts for documentation. [Martin Raspaud]

- Feature: added the nameserver to posttroll. [Martin Raspaud]

- Feature: broadcasting can be switched off. [Martin Raspaud]

- Bugfix format and type. [Martin Raspaud]

- Exchange the place of type and format. [Martin Raspaud]

- Changed setup name to posttroll... [Martin Raspaud]

- Updated documentation and setup.py. [Martin Raspaud]

- Adding setup.py. [Martin Raspaud]

- Merge branch 'master' of github.com:mraspaud/posttroll. [Martin
  Raspaud]

- Initial commit. [Martin Raspaud]

- Feature: messages in posttroll can encode and decode python datetimes.
  [Martin Raspaud]

- Merge branch 'master' of github.com:mraspaud/pytroll. [safusr.u]

- Some upgrades to posttroll. [Martin Raspaud]

  * Creates text/ascii messages if the binary flag is not set and data is a string
  * Adds an address translation feature for subscribers
  * Add new publishers to listen to while running.
  * Bugfixes


- Adress receiver is publishing new adresses. [Martin Raspaud]

- Fixed c++ lib. [Martin Raspaud]

- Cleanup posttroll++ [Martin Raspaud]

- C++ version of posttroll :) [Martin Raspaud]

- Support binary messages. [Martin Raspaud]

- Nameserver fix. [Martin Raspaud]

- Updating networking. [Martin Raspaud]

- Support for multiple data types for one Publish instance. [Kristian
  Rune Larsen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Martin Raspaud]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Adam.Dybbroe]

- Bind to any network interface in Publish. [Martin Raspaud]

- A little better check for ISO formatted time string. [Lars Orum
  Rasmussen]

- Corrected check for Python 2.6. [Lars Orum Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Adam.Dybbroe]

- WIP: nasty product getting further. [Martin Raspaud]

  subscriber support multiple addresses
  new datasources for hrit and safmsg
  new cloudtype_e producer.


- Merge branch 'master' of github.com:mraspaud/pytroll. [Martin Raspaud]

  Conflicts:
  	posttroll/address_receiver.py


- Now tests works under python 2.5. [Lars Orum Rasmussen]

- Better isoformated string decoding for python2.5. [Lars Orum
  Rasmussen]

- Better swicth between json and simplejson. [Lars Orum Rasmussen]

- Mods for python2.5. [Lars Orum Rasmussen]

- Corrected handling of username. [Lars Orum Rasmussen]

- After pylint. [Lars Orum Rasmussen]

- WIP: Started the new nasty product prototype. [Martin Raspaud]

- Handling merge conflict. [Lars Orum Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Cosmetic. [Lars Orum Rasmussen]

- Fixed bugs so that unittests pass. [Martin Raspaud]

- Pylintized. [Lars Orum Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Changed kwargs dict to explicit argument names. [Kristian Rune Larsen]

- Merge branch 'master' of https://github.com/mraspaud/pytroll. [Esben
  S. Nielsen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Refactoring data_center. [Lars Orum Rasmussen]

- Merge branch 'master' of https://github.com/mraspaud/pytroll. [Esben
  S. Nielsen]

- Merge conflict solved. [Esben S. Nielsen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Merge branch 'master' of https://github.com/mraspaud/pytroll. [Esben
  S. Nielsen]

- Merge branch 'master' of github.com:mraspaud/pytroll. [Lars Orum
  Rasmussen]

- Merge branch 'master' of https://github.com/mraspaud/pytroll. [Esben
  S. Nielsen]

- Tests for bbmcast.py. [Martin Raspaud]

- Cosmetics and documentation. [Martin Raspaud]

- Added copyright/gpl. [Martin Raspaud]

- Displacing the dummy producer to the producer directory. [Martin
  Raspaud]

- More unittests for message. [Martin Raspaud]

- Cosmetics and change to posttroll. [Martin Raspaud]

- Change libpy to posttroll (troll equivalent of a postman) and add a
  dummy producer example. [Martin Raspaud]

- Removed send methode. [Lars Orum Rasmussen]

- Cosmetic. [Lars Orum Rasmussen]

- Now a general message broadcaster, which I broke. [Lars Orum
  Rasmussen]

- Extracted address broadcaster from datacenter. [Lars Orum Rasmussen]

- Cosmetic. [Lars Orum Rasmussen]

- All servers are using the same port for address broadcasting. [Lars
  Orum Rasmussen]

- New format and handling of magick word. [Lars Orum Rasmussen]

- Extracted the address receiver from the producer. [Lars Orum
  Rasmussen]

- Had forgotten to ci test data. [Lars Orum Rasmussen]

- Added a 'SocketTimeout', so user don't need to import sockets.timeout.
  [Lars Orum Rasmussen]

- Cosmetic. [ras]

- Also add SO_REUSEADDR to sender. [ras]

- Better handling of broadcast group in receiver. [ras]

- More flexible interface to bbmcast.py. [ras]

- Check for python version >= 2.6. [ras]

- Now using bbmcast. [ras]

- Bare bone multicast. [ras]

- Now with a non blocking socket. [Lars Orum Rasmussen]

- It's double dash. [Lars Orum Rasmussen]

- First proof of concept. [Lars Orum Rasmussen]

- Added an __init__.py file. [Lars Orum Rasmussen]

- Messages is now versionized. [Lars Orum Rasmussen]

- Manicure. [Lars Orum Rasmussen]

- More flexible decoding. [Lars Orum Rasmussen]

- Cosmetic. [Lars Orum Rasmussen]

- Adding libpy and a Message object. [Lars Orum Rasmussen]


