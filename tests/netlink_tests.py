#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from gnlpy import netlink

import unittest


def pack_unpack(kls, s):
    '''
    Helper function to pack an attr list and unpack it properly as if done via
    a Netlink Message.
    '''
    return kls.unpack(kls.pack(s).tostring())


class AttrListTestCase(unittest.TestCase):
    '''
    Test AttrListType class
    '''
    def setUp(self):
        self.AttrListTest = netlink.create_attr_list_type(
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
            nulstringtype='abcd',
        )

        b = pack_unpack(self.AttrListTest, a)
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
