# gnlpy: Generic NetLink in PYthon

netlink sockets are used to communicate with various kernel subsystems as
an RPC system.  [`man 7 netlink`](http://man7.org/linux/man-pages/man7/netlink.7.html)
for more information.  You can also see a detailed description of how this
library works in the documentation for the netlink.py python file.

This project provides a python-only implementation of generic netlink
sockets.  It was written for ipvs initially, but can be easily adapted to
other implementations (taskstats.py is provided as an example).

## Example Implementation (taskstats.py)

See
[linux/Documentation/accounting/taskstats.txt](https://www.kernel.org/doc/Documentation/accounting/taskstats.txt)
for information about what taskstats actually is and look at taskstats.py
for the full implementation.

    class Taskstats:
        fields = ['version', 'exitcode', ...]

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __repr__(self):
            arr = ['%s=%s' % (f, repr(self.__dict__[f])) for f in self.fields]
            return 'TaskStats(%s)' % ', '.join(arr)

        @staticmethod
        def unpack(val):
            fmt = 'HIBBQQQQQQQQ32sQxxxIIIIIQQQQQQQQQQQQQQQQQQQQQQQ'
            attrs = dict(zip(Taskstats.fields, struct.unpack(fmt, val)))
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

    class TaskstatsClient:
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

### Using it (taskstats_dump.py)

    from gnlpy.taskstats import TaskstatsClient

    def main(argv):
        c = TaskstatsClient()
        stats = c.get_pid_stats(int(argv[1]))
        print(stats)

### Contributing
Contribututions to gnlpy are more than welcome. [Read the guidelines in CONTRIBUTING.md](CONTRIBUTING.md).
Make sure you've [signed the CLA](https://code.facebook.com/cla) before sending in a pull request.

### Whitehat

Facebook has a [bounty program](https://www.facebook.com/whitehat/) for
the safe disclosure of security bugs. If you find a vulnerability, please
go through the process outlined on that page and do not file a public issue.
