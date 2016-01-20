#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from gnlpy.ipvs import IpvsClient

import unittest


class TestAddingDest(unittest.TestCase):

    def test_add_dest_tunnel(self):
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1')
        self.client.add_dest('1.1.1.1', 80, '2.2.2.2', weight=100)

        # modify
        self.client.update_dest('1.1.1.1', 80, '2.2.2.1', weight=100)

        # delete
        self.client.del_dest('1.1.1.1', 80, '2.2.2.1')

        dests = self.client.get_pools()[0].dests()
        self.assertTrue(dests[0].ip() == '2.2.2.2')

    def setUp(self):
        '''
        Set up environment by creating a client and cleaning up services
        '''
        self.client = IpvsClient()
        self.cleanup()

    def tearDown(self):
        '''
        Clean up services when tearing down test
        '''
        self.cleanup()

    def cleanup(self):
        '''
        helper function that clear ALL services from ipvs
        '''
        pools = self.client.get_pools()
        for pool in pools:
            service = pool.service()
            self.client.del_service(service.vip(), service.port())


if __name__ == '__main__':
    unittest.main()
