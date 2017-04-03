#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from gnlpy.cgroupstats import CgroupstatsClient

import re
import unittest


CGROUP_PATH = '/proc/self/cgroup'
CGROUP_CPU_PATH = '/sys/fs/cgroup/cpu/'


def check_cpu_cgroup_presence():
    with open(CGROUP_PATH, mode='r') as f:
        file_contents = f.read()
        if re.search('[,:]cpu[,:]', file_contents) is None:
            return False
        else:
            return True


CPU_CGROUP_PRESENT = check_cpu_cgroup_presence()


class CgroupstatsTestCase(unittest.TestCase):

    @unittest.skipUnless(CPU_CGROUP_PRESENT, "CPU cgroup is not present")
    def test_get_cgroup_stats(self):
        try:
            client = CgroupstatsClient()
            client.get_cgroup_stats(CGROUP_CPU_PATH)
        except Exception as e:
            self.fail("Raised unexpected exception: %s" % e)


if __name__ == '__main__':
    unittest.main()
