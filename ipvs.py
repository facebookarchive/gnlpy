# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""IPVS module

This module exists as a pure-python replacement for ipvsadm.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import socket
import struct
import gnlpy.netlink as netlink

# IPVS forwarding methods
IPVS_MASQUERADING = 0
IPVS_LOCAL = 1
IPVS_TUNNELING = 2
IPVS_ROUTING = 3

IPVS_METHODS = set([
    IPVS_MASQUERADING,
    IPVS_LOCAL,
    IPVS_TUNNELING,
    IPVS_ROUTING
])

# These are attr_list_types which are nestable.  The command attribute list
# is ultimately referenced by the messages which are passed down to the
# kernel via netlink.  These structures must match the type and ordering
# that the kernel expects.

IpvsStatsAttrList = netlink.create_attr_list_type(
    'IpvsStatsAttrList',
    ('CONNS', netlink.U32Type),
    ('INPKTS', netlink.U32Type),
    ('OUTPKTS', netlink.U32Type),
    ('INBYTES', netlink.U64Type),
    ('OUTBYTES', netlink.U64Type),
    ('CPS', netlink.U32Type),
    ('INPPS', netlink.U32Type),
    ('OUTPPS', netlink.U32Type),
    ('INBPS', netlink.U32Type),
    ('OUTBPS', netlink.U32Type),
)

IpvsStatsAttrList64 = netlink.create_attr_list_type(
    'IpvsStatsAttrList64',
    ('CONNS', netlink.U64Type),
    ('INPKTS', netlink.U64Type),
    ('OUTPKTS', netlink.U64Type),
    ('INBYTES', netlink.U64Type),
    ('OUTBYTES', netlink.U64Type),
    ('CPS', netlink.U64Type),
    ('INPPS', netlink.U64Type),
    ('OUTPPS', netlink.U64Type),
    ('INBPS', netlink.U64Type),
    ('OUTBPS', netlink.U64Type),
)

IpvsServiceAttrList = netlink.create_attr_list_type(
    'IpvsServiceAttrList',
    ('AF', netlink.U16Type),
    ('PROTOCOL', netlink.U16Type),
    ('ADDR', netlink.BinaryType),
    ('PORT', netlink.Net16Type),
    ('FWMARK', netlink.U32Type),
    ('SCHED_NAME', netlink.NulStringType),
    ('FLAGS', netlink.BinaryType),
    ('TIMEOUT', netlink.U32Type),
    ('NETMASK', netlink.U32Type),
    ('STATS', IpvsStatsAttrList),
    ('PE_NAME', netlink.NulStringType),
    ('STATS64', IpvsStatsAttrList64),
)

IpvsDestAttrList = netlink.create_attr_list_type(
    'IpvsDestAttrList',
    ('ADDR', netlink.BinaryType),
    ('PORT', netlink.Net16Type),
    ('FWD_METHOD', netlink.U32Type),
    ('WEIGHT', netlink.I32Type),
    ('U_THRESH', netlink.U32Type),
    ('L_THRESH', netlink.U32Type),
    ('ACTIVE_CONNS', netlink.U32Type),
    ('INACT_CONNS', netlink.U32Type),
    ('PERSIST_CONNS', netlink.U32Type),
    ('STATS', IpvsStatsAttrList),
    ('ADDR_FAMILY', netlink.U16Type),
    ('STATS64', IpvsStatsAttrList64),
)

IpvsDaemonAttrList = netlink.create_attr_list_type(
    'IpvsDaemonAttrList',
    ('STATE', netlink.U32Type),
    ('MCAST_IFN', netlink.NulStringType),
    ('SYNC_ID', netlink.U32Type),
)


IpvsInfoAttrList = netlink.create_attr_list_type(
    'IpvsInfoAttrList',
    ('VERSION', netlink.U32Type),
    ('CONN_TAB_SIZE', netlink.U32Type),
)

IpvsCmdAttrList = netlink.create_attr_list_type(
    'IpvsCmdAttrList',
    ('SERVICE', IpvsServiceAttrList),
    ('DEST', IpvsDestAttrList),
    ('DAEMON', IpvsDaemonAttrList),
    ('TIMEOUT_TCP', netlink.U32Type),
    ('TIMEOUT_TCP_FIN', netlink.U32Type),
    ('TIMEOUT_UDP', netlink.U32Type),
)

IpvsMessage = netlink.create_genl_message_type(
    'IpvsMessage', 'IPVS',
    ('NEW_SERVICE', IpvsCmdAttrList),
    ('SET_SERVICE', IpvsCmdAttrList),
    ('DEL_SERVICE', IpvsCmdAttrList),
    ('GET_SERVICE', IpvsCmdAttrList),
    ('NEW_DEST', IpvsCmdAttrList),
    ('SET_DEST', IpvsCmdAttrList),
    ('DEL_DEST', IpvsCmdAttrList),
    ('GET_DEST', IpvsCmdAttrList),
    ('NEW_DAEMON', IpvsCmdAttrList),
    ('DEL_DAEMON', IpvsCmdAttrList),
    ('GET_DAEMON', IpvsCmdAttrList),
    ('SET_CONFIG', IpvsCmdAttrList),
    ('GET_CONFIG', IpvsCmdAttrList),
    ('SET_INFO', IpvsCmdAttrList),
    ('GET_INFO', IpvsCmdAttrList),
    ('ZERO', IpvsCmdAttrList),
    ('FLUSH', IpvsCmdAttrList),
    required_modules=['ip_vs'],
)


def verbose(f):
    def g(self, *args, **kwargs):
        if self.verbose:
            s_args = [repr(a) for a in args]
            s_args.extend(['{0}={1}'.format(k, repr(v))
                           for k, v in kwargs.items()])
            print('{0}({1})'.format(f.__name__, ', '.join(s_args)))
        return f(self, *args, **kwargs)
    return g


def _validate_ip(ip):
    try:
        socket.inet_pton(socket.AF_INET6 if ':' in ip else socket.AF_INET, ip)
        return True
    except socket.error:
        return False


def _to_af_union(ip):
    af = socket.AF_INET6 if ':' in ip else socket.AF_INET
    return af, socket.inet_pton(af, ip).ljust(16, str('\0'))


def _from_af_union(af, addr):
    n = 4 if af == socket.AF_INET else 16
    return socket.inet_ntop(af, addr[:n])


def _to_proto_num(proto):
    if proto is None:
        return None
    if proto.lower() == 'tcp':
        return socket.IPPROTO_TCP
    elif proto.lower() == 'udp':
        return socket.IPPROTO_UDP
    else:
        assert False, 'unknown proto %s' % proto


def _from_proto_num(n):
    if n is None:
        return None
    if n == socket.IPPROTO_TCP:
        return 'tcp'
    elif n == socket.IPPROTO_UDP:
        return 'udp'
    else:
        assert False, 'unknown proto num %d' % n


class Dest(object):
    """Describes a real server to be load balanced to."""

    def __init__(self, d={}, validate=False):
        self.ip_ = d.get('ip', None)
        self.weight_ = d.get('weight', None)
        self.port_ = d.get('port', None)
        self.fwd_method_ = d.get('fwd_method', IPVS_TUNNELING)

    def __repr__(self):
        return 'Dest(d=dict(ip="%s", weight=%d))' % (self.ip(), self.weight())

    def ip(self):
        return self.ip_

    def weight(self):
        return self.weight_

    def port(self):
        return self.port_

    def fwd_method(self):
        return self.fwd_method_

    def validate(self):
        assert _validate_ip(self.ip_)
        assert isinstance(self.weight_, int)
        assert self.weight_ >= -1
        assert self.fwd_method_ in IPVS_METHODS

    def to_dict(self):
        return {
            'ip': self.ip_,
            'weight': self.weight_,
        }

    def __eq__(self, other):
        return isinstance(other, Dest) and self.to_dict() == other.to_dict()

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def from_attr_list(lst, default_af=None):
        return Dest(
            d={
                'ip': _from_af_union(lst.get('addr_family', default_af),
                                     lst.get('addr')),
                'weight': lst.get('weight'),
                'port': lst.get('port'),
                'fwd_method': lst.get('fwd_method')
            },
            validate=True,
        )


class Service(object):
    """Describes a load balanced service.
    """

    def __init__(self, d={}, validate=False):
        self.proto_ = d.get('proto', None)
        self.vip_ = d.get('vip', None)
        self.port_ = d.get('port', None)
        self.sched_ = d.get('sched', None)
        self.fwmark_ = d.get('fwmark', None)
        if validate:
            self.validate()

    def __repr__(self):
        if self.fwmark_ is not None:
            return 'Service(d=dict(fwmark=%d, sched="%s"))' % (
                self.fwmark(), self.sched())
        return 'Service(d=dict(proto="%s", vip="%s", port=%d, sched="%s"))' % (
            self.proto(), self.vip(), self.port(), self.sched())

    def fwmark(self):
        return self.fwmark_

    def proto(self):
        return self.proto_

    def proto_num(self):
        return _to_proto_num(self.proto_)

    def port(self):
        return self.port_

    def vip(self):
        return self.vip_

    def sched(self):
        return self.sched_

    def validate(self):
        if self.vip_ or self.port_ or self.proto_:
            assert self.proto_.lower() in ['tcp', 'udp']
            assert _validate_ip(self.vip_)
            assert isinstance(self.port_, int)
            assert self.port_ > 0 and self.port_ < (2 ** 16)
            assert self.fwmark_ is None
        else:
            assert isinstance(self.fwmark_, int)
            assert self.proto_ is None
            assert self.port_ is None
            assert self.vip_ is None
            assert self.fwmark_ > 0 and self.fwmark_ < (2 ** 32)

    def to_dict(self):
        self.validate()
        if self.fwmark_ is None:
            return {
                'proto': self.proto_,
                'vip': self.vip_,
                'port': self.port_,
                'sched': self.sched_,
            }
        else:
            return {
                'fwmark': self.fwmark_,
                'sched': self.sched_,
            }

    def __eq__(self, other):
        return isinstance(other, Service) and self.to_dict() == other.to_dict()

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def from_attr_list(lst):
        if lst.get('addr', None) is not None:
            d = dict(
                vip=_from_af_union(lst.get('af'), lst.get('addr')),
                proto=_from_proto_num(lst.get('protocol')),
                port=lst.get('port'),
                sched=lst.get('sched_name'),
            )
        else:
            d = dict(fwmark=lst.get('fwmark'), sched=lst.get('sched_name'))
        return Service(d=d, validate=True)


class Pool(object):
    """A tuple of a service and an array of dests for that service
    """

    def __init__(self, d={}, validate=False):
        self.service_ = Service(d.get('service', {}), validate)
        self.dests_ = [Dest(x, validate) for x in d.get('dests', [])]

    def service(self):
        return self.service_

    def dests(self):
        return self.dests_

    def validate(self):
        self.service_.validate()
        for dest in self.dests_:
            dest.validate()

    def to_dict(self):
        self.validate()
        return {
            'service': self.service_.to_dict(),
            'dests': [d.to_dict() for d in self.dests_],
        }

    @staticmethod
    def from_args(service=None, dests=[]):
        assert isinstance(service, Service)
        assert isinstance(dests, list)
        p = Pool()
        p.service_ = service
        p.dests_ = dests
        return p

    @staticmethod
    def load_pools_from_json_list(lst):
        return [Pool(i, True) for i in lst]


class IpvsClient(object):
    """A python client to use instead of shelling out to ipvsadm
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.nlsock = netlink.NetlinkSocket(verbose=verbose)

    def __modify_service(self, method, vip, port, protocol, **svc_kwargs):
        af, addr = _to_af_union(vip)
        netmask = ((1 << 32) - 1) if af == socket.AF_INET else 128
        out_msg = IpvsMessage(
            method, flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=IpvsCmdAttrList(
                service=IpvsServiceAttrList(
                    af=af,
                    port=port,
                    protocol=protocol,
                    addr=addr,
                    netmask=netmask,
                    flags=struct.pack(str('=II'), 0, 0),
                    **svc_kwargs
                )
            )
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_service(self, vip, port, protocol=socket.IPPROTO_TCP,
                    sched_name='rr'):
        self.__modify_service('new_service', vip, port, protocol,
                              sched_name=sched_name, timeout=0)

    @verbose
    def del_service(self, vip, port, protocol=socket.IPPROTO_TCP):
        self.__modify_service('del_service', vip, port, protocol)

    def __modify_fwm_service(self, method, fwmark, af, **svc_kwargs):
        netmask = ((1 << 32) - 1) if af == socket.AF_INET else 128
        out_msg = IpvsMessage(
            method, flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=IpvsCmdAttrList(
                service=IpvsServiceAttrList(
                    fwmark=fwmark,
                    flags=struct.pack(str('=II'), 0, 0),
                    af=af,
                    netmask=netmask,
                    **svc_kwargs
                )
            )
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_fwm_service(self, fwmark, sched_name='rr', af=socket.AF_INET):
        self.__modify_fwm_service('new_service', fwmark,
                                  sched_name=sched_name, timeout=0, af=af)

    @verbose
    def del_fwm_service(self, fwmark, af=socket.AF_INET):
        self.__modify_fwm_service('del_service', fwmark, af=af)

    def __modify_dest(self, method, vip, port, rip,
                      protocol=socket.IPPROTO_TCP, **dest_kwargs):
        vaf, vaddr = _to_af_union(vip)
        raf, raddr = _to_af_union(rip)
        out_msg = IpvsMessage(
            method, flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=IpvsCmdAttrList(
                service=IpvsServiceAttrList(
                    af=vaf,
                    port=port,
                    protocol=protocol,
                    addr=vaddr,
                ),
                dest=IpvsDestAttrList(
                    addr_family=raf,
                    addr=raddr,
                    port=port,
                    **dest_kwargs
                ),
            ),
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_dest(self, vip, port, rip,
                 protocol=socket.IPPROTO_TCP, weight=1, method=IPVS_TUNNELING):
        self.__modify_dest('new_dest', vip, port, rip,
                           protocol=protocol, weight=weight,
                           fwd_method=method, l_thresh=0, u_thresh=0)

    @verbose
    def update_dest(self, vip, port, rip, protocol=socket.IPPROTO_TCP,
                    weight=None, method=IPVS_TUNNELING):
        self.__modify_dest('set_dest', vip, port, rip, protocol, weight=weight,
                           l_thresh=0, u_thresh=0, fwd_method=method)

    @verbose
    def del_dest(self, vip, port, rip, protocol=socket.IPPROTO_TCP):
        self.__modify_dest('del_dest', vip, port, rip, protocol)

    def __modify_fwm_dest(self, method, fwmark, rip, vaf, port,
                          **dest_kwargs):
        raf, raddr = _to_af_union(rip)
        out_msg = IpvsMessage(
            method, flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=IpvsCmdAttrList(
                service=IpvsServiceAttrList(
                    fwmark=fwmark,
                    af=vaf,
                ),
                dest=IpvsDestAttrList(
                    addr_family=raf,
                    addr=raddr,
                    port=port,
                    **dest_kwargs
                ),
            ),
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_fwm_dest(self, fwmark, rip, vaf=socket.AF_INET, port=0, weight=1):
        self.__modify_fwm_dest('new_dest', fwmark, rip, weight=weight,
                               port=port, vaf=vaf, l_thresh=0, u_thresh=0,
                               fwd_method=2)

    @verbose
    def update_fwm_dest(self, fwmark, rip, vaf=socket.AF_INET, weight=None,
                        port=0):
        self.__modify_fwm_dest('set_dest', fwmark, rip, weight=weight,
                               vaf=vaf, port=port, l_thresh=0, u_thresh=0,
                               fwd_method=2)

    @verbose
    def del_fwm_dest(self, fwmark, rip, vaf=socket.AF_INET, port=0):
        self.__modify_fwm_dest('del_dest', fwmark, rip, vaf=vaf, port=port)

    def flush(self):
        out_msg = IpvsMessage('flush', flags=netlink.MessageFlags.ACK_REQUEST)
        self.nlsock.execute(out_msg)

    def get_pools(self):
        pools = []

        req = IpvsMessage(
            'get_service', flags=netlink.MessageFlags.MATCH_ROOT_REQUEST)
        for msg in self.nlsock.query(req):
            svc_lst = msg.get_attr_list().get('service')
            service = Service.from_attr_list(svc_lst)
            dests = []
            out_msg = IpvsMessage(
                'get_dest', flags=netlink.MessageFlags.MATCH_ROOT_REQUEST,
                attr_list=IpvsCmdAttrList(service=svc_lst)
            )
            for dst_msg in self.nlsock.query(out_msg):
                dst_lst = dst_msg.get_attr_list().get('dest')
                dests.append(Dest.from_attr_list(dst_lst, svc_lst.get('af')))

            pools.append(Pool.from_args(
                service=service,
                dests=dests
            ))

        return pools
