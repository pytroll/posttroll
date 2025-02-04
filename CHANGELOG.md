## Version 1.12.0 (2025/02/04)

### Issues Closed

* [Issue 67](https://github.com/pytroll/posttroll/issues/67) - posttroll.listener should use hierarchical logger custom ([PR 68](https://github.com/pytroll/posttroll/pull/68) by [@pnuu](https://github.com/pnuu))
* [Issue 64](https://github.com/pytroll/posttroll/issues/64) - Timezone aware datetimes ([PR 69](https://github.com/pytroll/posttroll/pull/69) by [@pnuu](https://github.com/pnuu))
* [Issue 44](https://github.com/pytroll/posttroll/issues/44) - Delegate the environment variable reading to donfig

In this release 3 issues were closed.

### Pull Requests Merged

#### Bugs fixed

* [PR 72](https://github.com/pytroll/posttroll/pull/72) - Fix timezone aware datetimes backwards compatibility ([71](https://github.com/pytroll/posttroll/issues/71))
* [PR 66](https://github.com/pytroll/posttroll/pull/66) - Fix typo in secure backend documentation

#### Features added

* [PR 69](https://github.com/pytroll/posttroll/pull/69) - Switch to timezone aware datetimes ([64](https://github.com/pytroll/posttroll/issues/64))
* [PR 68](https://github.com/pytroll/posttroll/pull/68) - Fix `Listener` and `ListenerContainer` logger names ([67](https://github.com/pytroll/posttroll/issues/67))
* [PR 65](https://github.com/pytroll/posttroll/pull/65) - Fix Flake8 complaints and datetime imports
* [PR 56](https://github.com/pytroll/posttroll/pull/56) - Introduce authentication for zmq communications

In this release 6 pull requests were closed.


## Version 1.11.0 (2024/02/26)


### Pull Requests Merged

#### Bugs fixed

* [PR 63](https://github.com/pytroll/posttroll/pull/63) - Add a `heartbeat()` method to `NoisyPublisher`
* [PR 59](https://github.com/pytroll/posttroll/pull/59) - Fix testing publisher to only accept str to send
* [PR 58](https://github.com/pytroll/posttroll/pull/58) - Crash fake publisher when not started
* [PR 57](https://github.com/pytroll/posttroll/pull/57) - Make testing's patched_subscriber_recv  interruptible

#### Features added

* [PR 62](https://github.com/pytroll/posttroll/pull/62) - Update CI to use Python 3.10 - 3.12

In this release 5 pull requests were closed.


## Version 1.10.0 (2023/05/10)


### Pull Requests Merged

#### Bugs fixed

* [PR 46](https://github.com/pytroll/posttroll/pull/46) - Fix missed cleanup in last PR

#### Features added

* [PR 53](https://github.com/pytroll/posttroll/pull/53) - Add close methods for subscriber and publisher and testing utilities

In this release 2 pull requests were closed.


###############################################################################
## Version 1.9.0 (2022/10/19)


### Pull Requests Merged

#### Bugs fixed

* [PR 42](https://github.com/pytroll/posttroll/pull/42) - Fix Read the docs

#### Features added

* [PR 45](https://github.com/pytroll/posttroll/pull/45) - Use donfig for handling posttroll environment variables
* [PR 43](https://github.com/pytroll/posttroll/pull/43) - Set TCP keepalive to publisher and subscriber
* [PR 40](https://github.com/pytroll/posttroll/pull/40) - Instruct to create annotated tags

In this release 4 pull requests were closed.

###############################################################################


## Version 1.8.0 (2022/04/25)


### Pull Requests Merged

#### Features added

* [PR 39](https://github.com/pytroll/posttroll/pull/39) - Add a possibility to create subscribers using a dictionary of configuration options

In this release 1 pull request was closed.


## Version 1.7.1 (2021/12/23)


### Pull Requests Merged

#### Features added

* [PR 37](https://github.com/pytroll/posttroll/pull/37) -  Change tested Python versions to 3.8, 3.9 and 3.10

In this release 1 pull request was closed.


## Version 1.7.0 (2021/12/23)

### Issues Closed

* [Issue 38](https://github.com/pytroll/posttroll/issues/38) - Allow to use NoisyPublisher as a context manager

In this release 1 issue was closed.

### Pull Requests Merged

#### Bugs fixed

* [PR 33](https://github.com/pytroll/posttroll/pull/33) - Fix link te Github project

#### Features added

* [PR 36](https://github.com/pytroll/posttroll/pull/36) - Use GitHub Actions to run tests
* [PR 35](https://github.com/pytroll/posttroll/pull/35) - Make it possible to configure publisher with a dictionary of settings
* [PR 28](https://github.com/pytroll/posttroll/pull/28) - Leave Python 2 support and require Python 3.6 or higher

In this release 4 pull requests were closed.


## Version 1.6.1 (2020/03/04)


### Pull Requests Merged

#### Bugs fixed

* [PR 27](https://github.com/pytroll/posttroll/pull/27) - Fix argparse option name

In this release 1 pull request was closed.


## Version v1.6.0 (2020/03/04)

### Issues Closed

* [Issue 24](https://github.com/pytroll/posttroll/issues/24) - Subscriber does not correctly filter messages by the name of the service ([PR 25](https://github.com/pytroll/posttroll/pull/25))

In this release 1 issue was closed.

### Pull Requests Merged

#### Bugs fixed

* [PR 25](https://github.com/pytroll/posttroll/pull/25) - Fix filtering of messages by the name of service ([24](https://github.com/pytroll/posttroll/issues/24))

#### Features added

* [PR 22](https://github.com/pytroll/posttroll/pull/22) - Add `restrict_to_localhost` flag for the nameserver
* [PR 21](https://github.com/pytroll/posttroll/pull/21) - Make the range of automatic port selection user definable

In this release 3 pull requests were closed.


## Version v1.5.1 (2019/04/04)


### Pull Requests Merged

#### Bugs fixed

* [PR 19](https://github.com/pytroll/posttroll/pull/19) - Allow posttroll to be used in multiprocessing context

In this release 1 pull request was closed.


## Version v1.5.0 (2019/01/21)


### Pull Requests Merged

#### Bugs fixed

* [PR 17](https://github.com/pytroll/posttroll/pull/17) - Fix decoding utf-8 encoded raw messages
* [PR 16](https://github.com/pytroll/posttroll/pull/16) - Decode rawstr messages as utf-8
* [PR 15](https://github.com/pytroll/posttroll/pull/15) - Make sure messages are consistently encoded as unicode

#### Features added

* [PR 18](https://github.com/pytroll/posttroll/pull/18) - Add support for raw messages encoded in iso 8859-1
* [PR 14](https://github.com/pytroll/posttroll/pull/14) - Make MC TTL configurable
* [PR 13](https://github.com/pytroll/posttroll/pull/13) - Support both utf8 and byte strings from messages
* [PR 12](https://github.com/pytroll/posttroll/pull/12) - Change default behaviour of subscriber to listen to everything

In this release 7 pull requests were closed.


## Version 1.4.0 (2018/10/02)


### Pull Requests Merged

#### Features added

* [PR 10](https://github.com/pytroll/posttroll/pull/10) - Add Python 3 support

In this release 1 pull request was closed.
