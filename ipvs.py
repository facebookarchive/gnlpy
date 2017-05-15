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

import six
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

# IPVS Flags
IPVS_SVC_F_PERSISTENT = 0x0001
IPVS_SVC_F_HASHED = 0x0002
IPVS_SVC_F_ONEPACKET = 0x0004
IPVS_SVC_F_SCHED1 = 0x0008
IPVS_SVC_F_SCHED2 = 0x0010
IPVS_SVC_F_SCHED2 = 0x0020

IPVS_SVC_F_SCHED_SH_FALLBACK = IPVS_SVC_F_SCHED1
IPVS_SVC_F_SCHED_SH_PORT = IPVS_SVC_F_SCHED2

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
                           for k, v in six.iteritems(kwargs)])
            print('{0}({1})'.format(f.__name__, ', '.join(s_args)))
        return f(self, *args, **kwargs)
    return g


def _validate_ip(ip):
    try:
        socket.inet_pton(_to_af(ip), ip)
        return True
    except socket.error:
        return False


def _to_af(ip):
    return socket.AF_INET6 if ':' in ip else socket.AF_INET


def _to_af_union(ip):
    af = _to_af(ip)
    return af, socket.inet_pton(af, ip).ljust(16, b'\0')


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

    def to_attr_list(self):
        af, addr = _to_af_union(self.ip_)
        return IpvsDestAttrList(addr_family=af,
                                addr=addr,
                                port=self.port_,
                                fwd_method=self.fwd_method_)

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
        self.flags_ = d.get('flags', 0)
        default_af = None
        if self.vip_:
            default_af = _to_af(self.vip_)
        self.af_ = d.get('af', default_af)
        if validate:
            self.validate()

    def __repr__(self):
        if self.fwmark_ is not None:
            return (
                'Service(d=dict(fwmark=%d, sched="%s", af="%s", flags="%d"))' %
                (self.fwmark(), self.sched(), self.af(), self.flags())
            )
        return (
            'Service(d=dict(proto="%s", vip="%s", port=%d, sched="%s", '
            'flags="%d"))' % (
                self.proto(), self.vip(), self.port(), self.sched(),
                self.flags()
            )
        )

    def af(self):
        return self.af_

    def fwmark(self):
        return self.fwmark_

    def flags(self):
        return self.flags_

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
        assert self.af_ in [socket.AF_INET, socket.AF_INET6]
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
                'af': self.af_,
                'flags': self.flags_,
            }
        else:
            return {
                'fwmark': self.fwmark_,
                'sched': self.sched_,
                'af': self.af_,
                'flags': self.flags_,
            }

    def to_attr_list(self):
        if self.fwmark_ is None:
            af, addr = _to_af_union(self.vip_)
            netmask = ((1 << 32) - 1) if af == socket.AF_INET else 128
            proto = self.proto_num()
            return IpvsServiceAttrList(af=af, addr=addr, protocol=proto,
                                       netmask=netmask, port=self.port_,
                                       sched_name=self.sched_,
                                       flags=struct.pack(
                                            str('=II'), self.flags_, 0xFFFFFFFF
                                       ))
        else:
            netmask = ((1 << 32) - 1)
            return IpvsServiceAttrList(fwmark=self.fwmark_, af=self.af_,
                                       netmask=netmask, sched_name=self.sched_,
                                       flags=struct.pack(
                                            str('=II'), self.flags_, 0xFFFFFFFF
                                       ))

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
                af=lst.get('af'),
                flags=struct.unpack('=II', lst.get('flags'))[0],
            )
        else:
            d = dict(
                fwmark=lst.get('fwmark'),
                sched=lst.get('sched_name'),
                af=lst.get('af'),
                flags=struct.unpack('=II', lst.get('flags'))[0],
            )
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

    def __modify_service(self, method, vip, port, protocol,
                         flags=0, **svc_kwargs):
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
                    flags=struct.pack(str('=II'), flags, 0xFFFFFFFF),
                    **svc_kwargs
                )
            )
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_service(self, vip, port, protocol=socket.IPPROTO_TCP,
                    sched_name='rr', flags=0):
        self.__modify_service('new_service', vip, port, protocol,
                              sched_name=sched_name, timeout=0, flags=flags)

    @verbose
    def del_service(self, vip, port, protocol=socket.IPPROTO_TCP):
        self.__modify_service('del_service', vip, port, protocol)

    def __modify_fwm_service(self, method, fwmark, af, flags=0, **svc_kwargs):
        netmask = ((1 << 32) - 1) if af == socket.AF_INET else 128
        out_msg = IpvsMessage(
            method, flags=netlink.MessageFlags.ACK_REQUEST,
            attr_list=IpvsCmdAttrList(
                service=IpvsServiceAttrList(
                    fwmark=fwmark,
                    flags=struct.pack(str('=II'), flags, 0xFFFFFFFF),
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

    def __modify_dest(self, method, vip, port, rip, rport=None,
                      protocol=socket.IPPROTO_TCP, **dest_kwargs):
        vaf, vaddr = _to_af_union(vip)
        raf, raddr = _to_af_union(rip)
        rport = rport or port
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
                    port=rport,
                    **dest_kwargs
                ),
            ),
        )
        self.nlsock.execute(out_msg)

    @verbose
    def add_dest(self, vip, port, rip, rport=None,
                 protocol=socket.IPPROTO_TCP, weight=1, method=IPVS_TUNNELING):
        self.__modify_dest('new_dest', vip, port, rip, rport,
                           protocol=protocol, weight=weight,
                           fwd_method=method, l_thresh=0, u_thresh=0)

    @verbose
    def update_dest(self, vip, port, rip, rport=None,
                    protocol=socket.IPPROTO_TCP, weight=None,
                    method=IPVS_TUNNELING):
        self.__modify_dest('set_dest', vip, port, rip, rport, protocol,
                           weight=weight, l_thresh=0, u_thresh=0,
                           fwd_method=method)

    @verbose
    def del_dest(self, vip, port, rip, rport=None,
                 protocol=socket.IPPROTO_TCP):
        self.__modify_dest('del_dest', vip, port, rip, rport, protocol)

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
        """
        Get all the pools configured
        """
        pools = []

        req = IpvsMessage(
            'get_service', flags=netlink.MessageFlags.MATCH_ROOT_REQUEST)
        for msg in self.nlsock.query(req):
            svc_lst = msg.get_attr_list().get('service')
            service = Service.from_attr_list(svc_lst)
            dests = self.get_dests(svc_lst)
            pools.append(Pool.from_args(
                service=service,
                dests=dests
            ))

        return pools

    def get_pool(self, svc_lst):
        s = self.get_service(svc_lst)
        if s is None:
            return None
        dests = self.get_dests(s.to_attr_list())
        return Pool.from_args(service=s, dests=dests)

    def get_service(self, svc_lst):
        out_msg = IpvsMessage(
            'get_service', flags=netlink.MessageFlags.REQUEST,
            attr_list=IpvsCmdAttrList(service=svc_lst))
        try:
            res = self.nlsock.query(out_msg)
            svc_lst = res[0].get_attr_list().get('service')
            return Service.from_attr_list(svc_lst)
        except RuntimeError:
            # If the query failed because the service is not present
            # simply return None
            return None

    def get_dests(self, svc_lst):
        assert isinstance(svc_lst, IpvsServiceAttrList)
        dests = []
        out_msg = IpvsMessage(
            'get_dest', flags=netlink.MessageFlags.MATCH_ROOT_REQUEST,
            attr_list=IpvsCmdAttrList(service=svc_lst)
        )
        try:
            for dst_msg in self.nlsock.query(out_msg):
                dst_lst = dst_msg.get_attr_list().get('dest')
                dests.append(Dest.from_attr_list(dst_lst, svc_lst.get('af')))
            return dests
        except RuntimeError:
            # Typically happens if the service is not defined
            return None
