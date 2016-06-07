#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from gnlpy import netlink

try:
    from unittest import mock
except ImportError:
    import mock
import socket
import unittest


def pack_unpack(kls, s):
    '''
    Helper function to pack an attr list and unpack it properly as if done via
    a Netlink Message.
    '''
    return kls.unpack(kls.pack(s).tostring())


class AttrListTestCase(unittest.TestCase):
    '''
    Test AttrListType class.
    '''
    AttrListTest = netlink.create_attr_list_type(
        'AttrListTest',
        ('U8TYPE', netlink.U8Type),
        ('U16TYPE', netlink.U16Type),
        ('U32TYPE', netlink.U32Type),
        ('U64TYPE', netlink.U64Type),
        ('I32TYPE', netlink.I32Type),
        ('NET16TYPE', netlink.Net16Type),
        ('NET32TYPE', netlink.Net32Type),
        ('IGNORETYPE', netlink.IgnoreType),
        ('BINARYTYPE', netlink.BinaryType),
        ('NULSTRINGTYPE', netlink.NulStringType),
        ('RECURSIVESELF', netlink.RecursiveSelf),
    )

    def test_getter_no_default(self):
        a = self.AttrListTest()
        # Raises an exception if no default are given.
        with self.assertRaises(KeyError):
            a.get('FOO')
        # Returns the default otherwise.
        self.assertEqual(a.get('FOO', 5), 5)

    def test_packing(self):
        a = self.AttrListTest(
            u64type=2,
            binarytype=b'ABCD',
            nulstringtype='abcd',
        )

        b = pack_unpack(self.AttrListTest, a)
        self.assertEqual(b.get('u64type'), 2)
        self.assertEqual(b.get('binarytype'), b'ABCD')
        self.assertEqual(b.get('nulstringtype'), 'abcd')

    def test_recursive_self(self):
        a = self.AttrListTest(
            recursiveself=self.AttrListTest(
                nulstringtype='abcd',
            )
        )
        # Confirms our AttrListType structures get properly filed.
        self.assertEqual(a.get('recursiveself').get('nulstringtype'), 'abcd')

        # Confirmd that we can properly pack and unpack the AttrListType.
        b = pack_unpack(self.AttrListTest, a)
        self.assertEqual(b.get('recursiveself').get('nulstringtype'), 'abcd')


class MessageTypeTestCase(unittest.TestCase):
    '''
    Test MessageType class.
    '''
    AttrListTest = netlink.create_attr_list_type(
        'AttrListTest',
        ('U8TYPE', netlink.U8Type),
        ('U16TYPE', netlink.U16Type),
        ('U32TYPE', netlink.U32Type),
        ('U64TYPE', netlink.U64Type),
        ('I32TYPE', netlink.I32Type),
        ('NET16TYPE', netlink.Net16Type),
        ('NET32TYPE', netlink.Net32Type),
        ('IGNORETYPE', netlink.IgnoreType),
        ('BINARYTYPE', netlink.BinaryType),
        ('NULSTRINGTYPE', netlink.NulStringType),
        ('RECURSIVESELF', netlink.RecursiveSelf),
    )

    CtrlMessageTest = netlink.create_genl_message_type(
        'CtrlMessageTest',
        12345,
        ('CMD1', AttrListTest),
        ('CMD2', None),
    )

    def test_msg_type_init(self):
        attr = self.AttrListTest()
        # Raises a KeyError when the command is not supported by the message.
        with self.assertRaises(KeyError):
            self.CtrlMessageTest('CMD', attr_list=attr)

        # A message can be initialized with a CMD string
        ctrl = self.CtrlMessageTest('CMD1', attr_list=attr)
        self.assertEqual(ctrl.cmd, 1)

        # Or a command ID.
        ctrl2 = self.CtrlMessageTest(1, attr_list=attr)
        self.assertEqual(ctrl.cmd, ctrl2.cmd)

        # When initialized without an attribute list, it will create a default
        # attr_list for us.
        ctrl = self.CtrlMessageTest('CMD1')
        self.assertIsInstance(ctrl.attr_list, self.AttrListTest)
        # Unless the operation is not supported
        ctrl = self.CtrlMessageTest('CMD2')
        self.assertIsNone(ctrl.attr_list)

    def test_get_attr_list(self):
        ctrl = self.CtrlMessageTest('CMD1')
        self.assertIsInstance(ctrl.get_attr_list(), self.AttrListTest)

    def test_assert_on_message_redefinition(self):
        # Assert when redefining a MessageType
        with self.assertRaises(AssertionError):
            netlink.create_genl_message_type(
                'Foo',
                12345,
            )
        # Ok to create new MessageType ID.
        # class_name is only used in repr, it does not technically need to be
        # unique.
        netlink.create_genl_message_type('Foo', 12346)

    def test_new_message_by_name(self):
        # It is fine to create a message by using a family name.
        # It will be looked up later.
        netlink.create_genl_message_type('Foo', 'BAR')
        # But we should not be able to register twice!
        with self.assertRaises(AssertionError):
            netlink.create_genl_message_type('Foo', 'BAR')

    def test_packing(self):
        attr = self.AttrListTest(
            u64type=2,
            binarytype=b'ABCD',
            nulstringtype='abcd',
        )

        ctrl = self.CtrlMessageTest('CMD1', attr_list=attr)
        self.assertEqual(ctrl.cmd, 1)
        ctrl2 = pack_unpack(self.CtrlMessageTest, ctrl)
        # Check that we have the same command.
        self.assertEqual(ctrl.cmd, ctrl2.cmd)
        # And that we have the same attributes.
        self.assertEqual(
            ctrl.attr_list.get('binarytype'),
            ctrl2.attr_list.get('binarytype')
        )


class NetlinkSocketTestCase(unittest.TestCase):

    def test_asocket_open_close(self):
        with mock.patch.object(
                netlink.NetlinkSocket,
                'resolve_family',
                return_value=5) as mock_method:
            sock = netlink.NetlinkSocket()
            sock.close()
        mock_method.assert_called_once_with('BAR')

    def test_msg_query_exception_verbose(self):
        self.sock = mock.MagicMock(name='netlink.socket', spec=socket.socket)
        self.sock.recv.return_value = 'AAA'
        sock = netlink.NetlinkSocket(verbose=True)
        with self.assertRaises(AttributeError):
            sock.query('a')
        sock.close()

    def test_msg_execute_exception_verbose(self):
        self.sock = mock.MagicMock(name='netlink.socket', spec=socket.socket)
        self.sock.recv.return_value = 'AAA'
        sock = netlink.NetlinkSocket(verbose=True)
        with self.assertRaises(AttributeError):
            sock.execute('a')
        sock.close()


if __name__ == '__main__':
    unittest.main()
