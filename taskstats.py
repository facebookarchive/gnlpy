# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Taskstats module

This module exists to expose the taskstats api to python
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# @lint-avoid-python-3-compatibility-imports
# from __future__ import unicode_literals

import struct
import gnlpy.netlink as netlink

# These are attr_list_types which are nestable.  The command attribute list
# is ultimately referenced by the messages which are passed down to the
# kernel via netlink.  These structures must match the type and ordering
# that the kernel expects.


class Taskstats(object):
    __fields__ = [
        'version', 'exitcode', 'flag', 'nice', 'cpu_count',
        'cpu_delay_total', 'blkio_count', 'blkio_delay_total',
        'swapin_count', 'swapin_delay_total',
        'cpu_run_real_total', 'cpu_run_virtual_total', 'comm',
        'sched', 'uid', 'gid', 'pid', 'ppid', 'btime', 'etime',
        'utime', 'stime', 'minflt', 'majflt', 'coremem',
        'virtmem', 'hiwater_rss', 'hiwater_vm', 'read_char',
        'write_char', 'read_syscalls', 'write_syscalls',
        'read_bytes', 'write_bytes', 'cancelled_write_bytes',
        'nvcsw', 'nivcsw', 'utimescaled', 'stimescaled',
        'cpu_scaled_run_real_total', 'freepages_count',
        'freepages_delay_total'
    ]

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        arr = ['%s=%s' % (f, repr(self.__dict__[f])) for f in self.__fields__]
        return 'TaskStats(%s)' % ', '.join(arr)

    @staticmethod
    def unpack(val):
        fmt = 'HIBBQQQQQQQQ32sQxxxIIIIIQQQQQQQQQQQQQQQQQQQQQQQ'
        attrs = dict(zip(Taskstats.__fields__, struct.unpack(fmt, val)))
        assert attrs['version'] == 8, "Bad version: %d" % attrs["version"]
        attrs['comm'] = attrs['comm'].rstrip('\0')
        return Taskstats(**attrs)

TaskstatsType = netlink.create_attr_list_type(
    'TaskstatsType',
    ('PID', netlink.U32Type),
    ('TGID', netlink.U32Type),
    ('STATS', Taskstats),
    ('AGGR_PID', netlink.RecursiveSelf),
    ('AGGR_TGID', netlink.RecursiveSelf),
    ('NULL', netlink.IgnoreType),
)

TaskstatsAttrList = netlink.create_attr_list_type(
    'TaskstatsAttrList',
    ('PID', netlink.U32Type),
    ('TGID', netlink.U32Type),
    ('REGISTER_CPUMASK', netlink.IgnoreType),
    ('DEREGISTER_CPUMASK', netlink.IgnoreType),
)

TaskstatsMessage = netlink.create_genl_message_type(
    'TaskstatsMessage', 'TASKSTATS',
    ('GET', TaskstatsAttrList),
    ('NEW', TaskstatsType),
    required_modules=[],
)


class TaskstatsClient(object):
    """A python client to interact with taskstats
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.nlsock = netlink.NetlinkSocket()

    def get_pid_stats(self, pid):
        replies = self.nlsock.query(TaskstatsMessage(
            'GET', flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=TaskstatsAttrList(pid=pid)
        ))
        return replies[0].get_attr_list().get('aggr_pid').get('stats')
