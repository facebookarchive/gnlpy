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

import sys
import argparse
import re
import socket
from gnlpy.ipvs import IpvsClient


def ip_string_eq(ip1, ip2):
    def fam(ip):
        return socket.AF_INET6 if ':' in ip else socket.AF_INET
    f1, f2 = fam(ip1), fam(ip2)
    return f1 == f2 and socket.inet_pton(f1, ip1) == socket.inet_pton(f2, ip2)


def match_arg(s, ip, port):
    m = re.match(r"^\[([a-fA-F0-9:]+)\]:(\d+)$", s)
    m = m or re.match(r"^([\d\.]+):(\d+)$", s)
    if m:
        return ip_string_eq(m.group(1), ip) and int(m.group(2)) == port

    m = re.match(r"^\[?([a-fA-F0-9:]+)\]?$", s)
    m = m or re.match(r"^([\d\.]+)$", s)
    if m:
        return ip_string_eq(m.group(1), ip)

    raise Exception("malformed address: " + s)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--service', default=None,
                        help='service to dump')
    parser.add_argument('-d', '--dest', default=None,
                        help='destination to dump')
    args = parser.parse_args(argv[1:])
    pools = IpvsClient().get_pools()
    for p in pools:
        s = p.service()
        if args.service is not None or args.dest is not None:
            if (args.service is not None and
                    not match_arg(args.service, s.vip(), s.port())):
                continue
            if (args.dest is not None and
                not any([match_arg(args.dest, d.ip(), s.port())
                         for d in p.dests()])):
                continue
        print(s)
        for d in p.dests():
            if args.dest is None or match_arg(args.dest, d.ip(), s.port()):
                print('->', d)

if __name__ == '__main__':
    main(sys.argv)
