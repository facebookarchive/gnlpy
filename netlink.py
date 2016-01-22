# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Netlink Module

netlink sockets are used to communicate with various kernel subsystems as
an RPC system.  `man 7 netlink` for more information.

You can read all about netlink in rfc 3549, but in general the format for
requests is a netlink message header followed by a specific header
(corresponding to type) followed by an attribute list.  This library was
primarily written for ipvs which uses the generalize protocol for netlink.
This means that type is not hardcoded based upon the message, but is
actually dynamic.  The first part of the exchange is discovering which type
(or family id) you'll need for your application, and then sing that forward.

Here is a typical (IPVS) netlink message

   0              1              2              3
  +--------------+--------------+--------------+--------------+
  |                    Total Message Length                   |
  +--------------+--------------+--------------+--------------+
  |             Type            |            Flags            |
  +--------------+--------------+--------------+--------------+
  |                      Sequence Number                      |
  +--------------+--------------+--------------+--------------+
  |                            PID                            |
  +--------------+--------------+--------------+--------------+
  |  Command ID  |    Version   |          RESERVED           |
  +--------------+--------------+--------------+--------------+
  |     Attribute Length        |        Attribute Type       |
  +--------------+--------------+--------------+--------------+
  |          ...  Attribute ... (Padded to 4 bytes)           |
  +--------------+--------------+--------------+--------------+
  |     Attribute Length        |        Attribute Type       |
  +--------------+--------------+--------------+--------------+
  |          ...  Attribute ... (Padded to 4 bytes)           |
  +--------------+--------------+--------------+--------------+

The thing that makes implementing this interesting is that the attribute
types are very application specific and context sensitive.  The type 1 in a
particular nested list might be a short while the type 1 in a different
nested list might be a single-letter nul-terminated string.  In that case,
both Attribute Length and Attribute Type would be the same, but they'd be
semantically very different.

So, for this all to work, we must create attribute lists that know how to
pack and unpack their values, and messages that know what type of attribute
lists they have.  This is accomplished with create_attr_list_type and
create_genl_message_type.

Usage:

    ListA = netlink.create_attr_list_type(
        'ListA',
        ('SOME_SHORT', netlink.U16Type),
        ('SOME_STRING', netlink.NulStringType),
    )

    ListB = netlink.create_attr_list_type(
        'ListB',
        ('ANOTHER_STRING', netlink.NulStringType),
        ('ANOTHER_SHORT', netlink.U16Type),
        ('LIST_A', ListA),
    )

    Msg = netlink.create_genl_message_type(
        'Msg', 'SPECIFIED_KERNEL_NAME',
        ('COMMAND_1', ListA),
        ('COMMAND_1', ListB),
    )

And at this point, you can begin sending and receiving `Msg`es to a netlink
socket.

    # assume that we send command_1 and get back a command_2
    sock.send(Msg('command_1', attr_list=ListA(
            another_string='foo', another_short=10)))
    reply = sock.recv()[0]
    reply.get_attr_list().get('some_short')  # is a short!
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import array
import errno
import logging
import os
import socket
import struct
import subprocess
import threading


def _unset(x):
    return x ** 2


class MessageFlags(object):
    REQUEST = 1
    MULTI = 2
    ACK = 4
    ECHO = 8
    DUMP_INTR = 16

    ROOT = 0x100
    MATCH = 0x200
    ATOMIC = 0x400
    DUMP = (ROOT | MATCH)

    REPLACE = 0x100
    EXCL = 0x200
    CREATE = 0x400
    APPEND = 0x800

    ACK_REQUEST = (REQUEST | ACK)
    MATCH_ROOT_REQUEST = (MATCH | ROOT | REQUEST)


def create_struct_fmt_type(fmt):
    class StructFmtType:
        @staticmethod
        def pack(val):
            return array.array(str('B'), struct.pack(str(fmt), val))

        @staticmethod
        def unpack(data):
            return struct.unpack(str(fmt), data)[0]

    return StructFmtType

U8Type = create_struct_fmt_type('=B')
U16Type = create_struct_fmt_type('=H')
U32Type = create_struct_fmt_type('=I')
I32Type = create_struct_fmt_type('=i')
U64Type = create_struct_fmt_type('=Q')
Net16Type = create_struct_fmt_type('!H')
Net32Type = create_struct_fmt_type('!I')


class RecursiveSelf(object):
    pass


class IgnoreType(object):
    @staticmethod
    def unpack(val):
        return None


class BinaryType(object):
    @staticmethod
    def pack(val):
        return val

    @staticmethod
    def unpack(val):
        return val


class NulStringType(object):
    @staticmethod
    def pack(val):
        return val + '\0'

    @staticmethod
    def unpack(val):
        assert val[-1] == '\0'
        return val[:-1]


class AttrListPacker(object):
    pass


def create_attr_list_type(class_name, *fields):
    """Create a new attr_list_type which is a class offering get and set
    methods which is capable of serializing and deserializing itself from
    netlink message.  The fields are a bunch of tuples of name and a class
    which should provide pack and unpack (except for in the case where we
    know it will be used exclusively for serialization or deserialization).
    attr_list_types can be used as packers in other attr_list_types.  The
    names and packers of the field should be taken from the appropriate
    linux kernel header and source files.
    """
    name_to_key = {}
    key_to_name = {}
    key_to_packer = {}
    for i, (name, packer) in enumerate(fields):
        key = i + 1
        name_to_key[name.upper()] = key
        key_to_name[key] = name
        key_to_packer[key] = packer

    class AttrListType(AttrListPacker):
        def __init__(self, **kwargs):
            self.attrs = {}
            for k, v in kwargs.items():
                if v is not None:
                    self.set(k, v)

        def set(self, key, value):
            if not isinstance(key, int):
                key = name_to_key[key.upper()]
            self.attrs[key] = value

        def get(self, key, default=_unset):
            try:
                if not isinstance(key, int):
                    key = name_to_key[key.upper()]
                return self.attrs[key]
            except KeyError:
                if default is not _unset:
                    return default
                raise

        def __repr__(self):
            attrs = ['%s=%s' % (key_to_name[k].lower(), repr(v))
                     for k, v in self.attrs.items()]
            return '%s(%s)' % (class_name, ', '.join(attrs))

        @staticmethod
        def pack(attr_list):
            packed = array.array(str('B'))
            for k, v in attr_list.attrs.items():
                if key_to_packer[k] == RecursiveSelf:
                    x = AttrListType.pack(v)
                else:
                    x = key_to_packer[k].pack(v)
                alen = len(x) + 4

                # TODO(agartrell): This is scary.  In theory, we should OR
                # 1 << 15 into the length if it is an instance of
                # AttrListPacker, but this didn't work for some reason, so
                # we're not going to.

                packed.fromstring(struct.pack(str('=HH'), alen, k))
                packed.fromstring(x)
                packed.fromstring('\0' * ((4 - (len(x) % 4)) & 0x3))
            return packed

        @staticmethod
        def unpack(data):
            global global_nest
            attr_list = AttrListType()
            while len(data) > 0:
                alen, k = struct.unpack(str('=HH'), data[:4])
                alen = alen & 0x7fff
                if key_to_packer[k] == RecursiveSelf:
                    v = AttrListType.unpack(data[4:alen])
                else:
                    v = key_to_packer[k].unpack(data[4:alen])
                attr_list.set(k, v)
                data = data[((alen + 3) & (~3)):]
            return attr_list

    return AttrListType


def create_genl_message_type(class_name, family_id_or_name, *fields,
                             **kwargs):
    """Create a new genl_message_type which is a class offering the appropriate
    members and is capable of serializing and deserializing itself from
    netlink protocol.  The fields are a bunch of tuples of command name and
    a class which should provide pack and unpack (except for in the case
    where we know it will be used exclusively for serialization or
    deserialization).  AFAICT, the packer should always be an
    attr_list_type.  The names and attr_list packers of the field should be
    taken from the appropriate linux kernel header and source files.

    This method further registers the new message type using the
    @message_class decorator, which allows us to serialize and deserialize
    it from any appropriate netlink socket instance.
    """

    name_to_key = {}
    key_to_name = {}
    key_to_attr_list_type = {}
    for i, (name, attr_list_type) in enumerate(fields):
        key = i + 1
        name_to_key[name.upper()] = key
        key_to_name[key] = name
        key_to_attr_list_type[key] = attr_list_type

    @message_class
    class MessageType:
        family = family_id_or_name
        required_modules = kwargs.get('required_modules', [])

        def __init__(self, cmd, attr_list=_unset, version=0x1,
                     flags=MessageFlags.ACK_REQUEST):
            if not isinstance(cmd, int):
                self.cmd = name_to_key[cmd.upper()]
            else:
                self.cmd = cmd

            self.version = version
            self.flags = flags

            if attr_list is _unset:
                self.attr_list = key_to_attr_list_type[self.cmd]()
            else:
                self.attr_list = attr_list

        def get_attr_list(self):
            return self.attr_list

        def __repr__(self):
            return '%s(cmd=%s, attr_list=%s, version=0x%x, flags=0x%x)' % (
                class_name, repr(key_to_name[self.cmd]), repr(self.attr_list),
                self.version, self.flags)

        @staticmethod
        def unpack(data):
            cmd, version = struct.unpack(str('=BBxx'), data[:4])
            attr_list = key_to_attr_list_type[cmd].unpack(data[4:])
            return MessageType(cmd, attr_list)

        @staticmethod
        def pack(msg):
            s = array.array(
                str('B'), struct.pack(str('=BBxx'), msg.cmd, msg.version))
            s.extend(key_to_attr_list_type[msg.cmd].pack(msg.attr_list))
            return s

    return MessageType

# This is a global map of unpackers.  The @message_class decorator inserts
# new message classes into this map so it can be used for the purpose of
# deserializing netlink messages from NetlinkSocket::recv
__cmd_unpack_map = {
}
__to_lookup_on_init = set()


def message_class(msg_class):
    if msg_class.family in __cmd_unpack_map:
        return
    if msg_class in __to_lookup_on_init:
        return

    if not isinstance(msg_class.family, int):
        __to_lookup_on_init.add(msg_class)
    else:
        __cmd_unpack_map[msg_class.family] = msg_class

    return msg_class


def setup_message_classes(nlsock):
    for msg_class in __to_lookup_on_init:
        if not isinstance(msg_class.family, int):
            msg_class.family = nlsock.resolve_family(msg_class.family)
            __cmd_unpack_map[msg_class.family] = msg_class
    __to_lookup_on_init.clear()
    for family_id, msg_class in __cmd_unpack_map.iteritems():
        for mod in getattr(msg_class, 'required_modules', []):
            subprocess.check_call(['modprobe', mod])


def deserialize_message(data):
    (n, typ, flags, seq, pid) = struct.unpack(str('=IHHII'), data[:16])
    if typ not in __cmd_unpack_map:
        raise Exception("Unregistered netlink type: %d" % typ)
    msg = __cmd_unpack_map[typ].unpack(data[16:n])
    msg.flags = flags
    return msg, data[n:]


def serialize_message(msg, port_id, seq):
    family = msg.__class__.family
    flags = msg.flags
    s = msg.__class__.pack(msg)
    t = struct.pack(str('=IHHII'), len(s) + 16, family, flags, seq, port_id)
    p = array.array(str('B'), t)
    p.extend(s)
    return p

# In order to discover family IDs, we'll need to exchange some Ctrl
# messages with the kernel.  We declare these message types and attribute
# list types below.

CtrlOpsAttrList = create_attr_list_type(
    'CtrlOpsAttrList',
    ('ID', U32Type),
    ('FLAGS', U32Type),
)

CtrlMcastGroupAttrList = create_attr_list_type(
    'CtrlMcastGroupAttrList',
    ('NAME', NulStringType),
    ('ID', U32Type),
)

CtrlAttrList = create_attr_list_type(
    'CtrlAttrList',
    ('FAMILY_ID', U16Type),
    ('FAMILY_NAME', NulStringType),
    ('VERSION', U32Type),
    ('HDRSIZE', U32Type),
    ('MAXATTR', U32Type),
    ('OPS', IgnoreType),  # TODO: CtrlOpsAttrList
    ('MCAST_GROUPS', CtrlMcastGroupAttrList),
)

CtrlMessage = create_genl_message_type(
    'CtrlMessage',
    16,
    ('NEWFAMILY', CtrlAttrList),
    ('DELFAMILY', None),
    ('GETFAMILY', CtrlAttrList),
    ('NEWOPS', None),
    ('DELOPS', None),
    ('GETOPS', None),
    ('NEWMCAST_GRP', None),
    ('DELMCAST_GRP', None),
    ('GETMCAST_GRP', None),
)


@message_class
class ErrorMessage(object):
    family = 2

    def __init__(self, error, msg):
        self.error = error
        self.msg = msg

    def __repr__(self):
        return 'ErrorMessage(error=%s, msg=%s)' % (
            repr(self.error), repr(self.msg))

    def __str__(self):
        try:
            error_str = '%s: %s' % (errno.errorcode[-self.error],
                                    os.strerror(-self.error))
        except KeyError:
            error_str = str(self.error)
        return '%s. Extra info: %s' % (error_str, self.msg)

    @staticmethod
    def unpack(data):
        error = struct.unpack(str('=i'), data[:4])[0]
        try:
            msg = deserialize_message(data[4:])
        except:
            msg = None
        return ErrorMessage(error=error, msg=msg)


@message_class
class DoneMessage(object):
    family = 3

    def __init__(self):
        pass

    @staticmethod
    def unpack(data):
        assert len(data) == 4
        return DoneMessage()

    @staticmethod
    def pack():
        return '\0\0\0\0'


class NetlinkSocket(object):
    def __init__(self, verbose=False):
        # NETLINK_GENERIC = 16
        self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, 16)
        self.sock.bind((0, 0))
        self.port_id = self.sock.getsockname()[0]
        self.seq = 0
        self.lock = threading.Lock()
        self.verbose = verbose
        setup_message_classes(self)

    def close(self):
        self.sock.close()
        self.sock = None

    def resolve_family(self, family):
        msg = CtrlMessage('getfamily', flags=MessageFlags.REQUEST)
        msg.get_attr_list().set('family_name', family)
        reply = self.query(msg)[0]
        return reply.get_attr_list().get('family_id')

    def _send(self, msg):
        self.sock.send(serialize_message(msg, self.port_id, self.seq))
        self.seq += 1

    def _recv(self):
        messages = []
        while True:
            # A big buffer to avoid truncating message.
            # The size is borrowed from libnetlink.
            data = self.sock.recv(16384)
            while len(data) > 0:
                msg, data = deserialize_message(data)
                if len(messages) == 0 and msg.flags & 0x2 == 0:
                    return [msg]
                elif isinstance(msg, DoneMessage):
                    return messages
                messages.append(msg)

        return messages

    def query(self, request):
        with self.lock:
            try:
                messages = None
                self._send(request)
                messages = self._recv()
                for message in messages:
                    if isinstance(message, ErrorMessage):
                        raise RuntimeError(str(message))
                return messages
            except Exception as e:
                if self.verbose:
                    logging.error("Netlink query failed: %s" % e)
                    logging.error("Sent Request: %s" % request)
                    logging.error("Recv Messages: %s" % messages)
                raise

    def execute(self, request):
        with self.lock:
            try:
                self._send(request)
                messages = self._recv()
                assert len(messages) == 1
                assert isinstance(messages[0], ErrorMessage)
                if messages[0].error != 0:
                    eno = -messages[0].error
                    raise OSError(eno, os.strerror(eno))
            except Exception as e:
                if self.verbose:
                    logging.error("Netlink execute failed: %s" % e)
                    logging.error("Sent Request: %s" % request)
                    logging.error("Recv Messages: %s" % messages)
                raise
