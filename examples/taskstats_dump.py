from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import sys
from gnlpy.taskstats import TaskstatsClient

def main(argv):
    c = TaskstatsClient()
    stats = c.get_pid_stats(int(argv[1]))
    print(stats)

if __name__ == '__main__':
    main(sys.argv)
