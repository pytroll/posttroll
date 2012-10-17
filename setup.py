#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2011, 2012.

# Author(s):
 
#   The pytroll team:
#   Martin Raspaud <martin.raspaud@smhi.se>

# This file is part of pytroll.

# This is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup
import sys

requirements = ['pyzmq']
if sys.version_info < (2, 6):
    requirements.append('simplejson')

setup(name="posttroll",
      version=0.1,
      description='Messaging system for pytroll',
      author='The pytroll team',
      author_email='martin.raspaud@smhi.se',
      packages=['posttroll'],
      scripts = ['bin/nameserver'],
      zip_safe=False,
      install_requires=requirements,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python',
          'Operating System :: OS Independent',
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering',
          'Topic :: Communications'
          ]
      )
