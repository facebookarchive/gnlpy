# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Cgroupstats module

This module exists to expose the cgroupstats api to python
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# @lint-avoid-python-3-compatibility-imports
# from __future__ import unicode_literals

from contextlib import contextmanager
import os
import struct
import gnlpy.netlink as netlink


class Cgroupstats(object):
    __fields__ = [
        'nr_sleeping', 'nr_running', 'nr_stopped',
        'nr_uninterruptible', 'nr_iowait'
    ]

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        arr = ['%s=%s' % (f, repr(self.__dict__[f])) for f in self.__fields__]
        return 'Cgroupstats(%s)' % ', '.join(arr)

    @staticmethod
    def unpack(val):
        fmt = 'QQQQQ'  # as per __fields__ above, and they're uint64 each
        attrs = dict(zip(Cgroupstats.__fields__, struct.unpack(fmt, val)))
        return Cgroupstats(**attrs)


CgroupstatsType = netlink.create_attr_list_type(
    'CgroupstatsType',
    ('CGROUP_STATS', Cgroupstats)
)

CgroupstatsCmdAttrList = netlink.create_attr_list_type(
    'CgroupstatsAttrList',
    ('CGROUPSTATS_CMD_ATTR_FD', netlink.U32Type),
)


CgroupstatsMessage = netlink.create_genl_message_type(
    # the first field of the cgroupstats struct in the kernel is initialised to
    # __TASKSTATS_CMD_MAX, which in turn has the value of 3. The second field,
    # which is the GET command, will have a value of 4. In order for us to
    # correctly pass this to the kernel, we need to pad the message. As our
    # fields are initialised with values starting from 1, we need to insert
    # 3 padding fields in order to have the GET command correspond to 4.
    # see http://lxr.free-electrons.com/source/include/uapi/linux/cgroupstats.h
    'CgroupstatsMessage', 'TASKSTATS',
    ('PADDING1', None),
    ('PADDING2', None),
    ('PADDING3', None),
    ('GET', CgroupstatsCmdAttrList),
    ('NEW', CgroupstatsType),
    required_modules=[],
)


class CgroupstatsClient(object):
    """A python client to interact with cgroupstats
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.nlsock = netlink.NetlinkSocket(verbose=verbose)

    @contextmanager
    def open_fd(self, path):
        fd = os.open(path, os.O_RDONLY)
        try:
            yield fd
        finally:
            os.close(fd)

    def get_cgroup_stats(self, path):
        with self.open_fd(path) as fd:
            data = CgroupstatsCmdAttrList(cgroupstats_cmd_attr_fd=fd)
            message = CgroupstatsMessage(
                'GET', flags=netlink.MessageFlags.REQUEST,
                attr_list=data,
            )
            replies = self.nlsock.query(message)
            return replies[0].get_attr_list().get('CGROUP_STATS')
