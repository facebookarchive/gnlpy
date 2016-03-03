#!/usr/bin/env python

# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# unicode literals breaks distutils.core.setup
# @lint-avoid-python-3-compatibility-imports

from setuptools import setup

setup(
    name='gnlpy',
    version='0.1.1',
    description='Generic NetLink PYthon library',
    author='Alex Gartrell',
    author_email='agartrell@fb.com',
    url='http://github.com/facebook/gnlpy',
    license='BSD+',
    packages=['gnlpy'],
    package_dir={'gnlpy': '.'},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='generic netlink library',
)
