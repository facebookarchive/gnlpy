# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import sys
from gnlpy.taskstats import TaskstatsClient


def main(argv):
    parser = argparse.ArgumentParser(
        description='Show task information. Run as root.')
    parser.add_argument('pid', type=int, help='The process id to show')

    args = parser.parse_args(argv[1:])
    c = TaskstatsClient()
    stats = c.get_pid_stats(args.pid)
    print(stats)

if __name__ == '__main__':
    main(sys.argv)
