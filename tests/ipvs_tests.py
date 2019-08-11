#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from gnlpy.ipvs import IpvsClient
from gnlpy import ipvs

import json
import six
import socket
import unittest


class BaseIpvsTestCase(unittest.TestCase):
    '''
    Base class allowing to setup and tear down environment.
    This class will correctly tear down fwmark based services.
    '''
    verbose = False

    def setUp(self):
        '''
        Set up environment by creating a client and cleaning up services
        '''
        self.client = IpvsClient(verbose=BaseIpvsTestCase.verbose)
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
            if service.fwmark() is None:
                self.client.del_service(
                    service.vip(),
                    service.port(),
                    protocol=service.proto_num())
            else:
                self.client.del_fwm_service(service.fwmark(), af=service.af())


class BaseJsonTestCase(unittest.TestCase):
    '''
    Base class that will load pools from json.
    This allows testing Pool, Service, Dest classes'special methods.
    '''
    def setUp(self, content=None):
        content = '''[
    {
        "service": {
            "proto": "TCP",
            "port": 80,
            "vip": "1.1.1.1"
        },
        "dests": [
            {
                "ip": "2.2.2.1",
                "weight": 1
            },
            {
                "ip": "2.2.2.2",
                "weight": 100
            }

        ]
    },
    {
        "service": {
            "proto": "UDP",
            "port": 80,
            "vip": "1.1.1.1"
        },
        "dests": [
            {
                "ip": "2.2.2.1",
                "weight": 1
            },
            {
                "ip": "2.2.2.2",
                "weight": 100
            }
        ]
    },
    {
        "service": {
            "fwmark": 10,
            "af": 2
        },
        "dests": [
            {
                "ip": "2.2.2.1",
                "weight": 1
            },
            {
                "ip": "2.2.2.2",
                "weight": 100
            }
        ]
    }
]''' if content is None else content
        self.json = json.loads(content)
        self.pools = ipvs.Pool.load_pools_from_json_list(self.json)


class TestAddingServices(BaseIpvsTestCase):

    def test_add_service_udp(self):
        '''
        Test that we can create UDP service.
        '''
        self.client.add_service('1.1.1.1', 80, protocol=socket.IPPROTO_UDP)
        pools = self.client.get_pools()
        self.assertEqual(pools[0].service().proto().lower(), 'udp')
        self.assertEqual(pools[0].service().af(), socket.AF_INET)

    def test_add_service_udp_ops(self):
        '''
        Test that we can create UDP service with One-packet scheduling.
        '''
        self.client.add_service('1.1.1.1', 80, protocol=socket.IPPROTO_UDP,
                                ops=True)
        pools = self.client.get_pools()
        self.assertEqual(pools[0].service().proto().lower(), 'udp')
        self.assertEqual(pools[0].service().af(), socket.AF_INET)

    def test_add_service_tcp_ops(self):
        '''
        Test that we *cannot* create TCP service with One-packet scheduling.
        '''
        with self.assertRaises(AssertionError):
            self.client.add_service('1.1.1.1', 80,
                                    protocol=socket.IPPROTO_TCP, ops=True)

    def test_add_service_tcp(self):
        '''
        Test that we can create TCP service.
        '''
        self.client.add_service('1.1.1.1', 80, protocol=socket.IPPROTO_TCP)
        pools = self.client.get_pools()
        self.assertEqual(pools[0].service().proto().lower(), 'tcp')
        self.assertEqual(pools[0].service().af(), socket.AF_INET)

    def test_add_service_tcp_default(self):
        '''
        Test that we service default to TCP.
        '''
        self.client.add_service('1.1.1.1', 80)
        pools = self.client.get_pools()
        self.assertEqual(pools[0].service().proto().lower(), 'tcp')
        self.assertEqual(pools[0].service().af(), socket.AF_INET)

    def test_add_service_ipv6_default(self):
        '''
        Test that we service default to TCP.
        '''
        self.client.add_service('2001:0DB8::1', 80)
        pools = self.client.get_pools()
        self.assertEqual(pools[0].service().proto().lower(), 'tcp')
        self.assertEqual(pools[0].service().af(), socket.AF_INET6)


class TestAddingDest(BaseIpvsTestCase):

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

    def test_add_dest_defaut_tunnel(self):
        '''
        Dest used to hardcode Tunnel forwarding mode,
        https://github.com/facebook/gnlpy/pull/1 changed that but we will still
        default to Tunnel mode if not specified.
        '''
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1')
        self.assertEqual(
            self.client.get_pools()[0].dests()[0].fwd_method(),
            ipvs.IPVS_TUNNELING,
            'Destination should default to Tunnel mode'
        )

    def test_dest_forwarding_mode(self):
        '''
        Test that we can set any type of supported method and that we get the
        same method returned by netlink.
        '''
        dest_methods = {
            '2.2.2.2': ipvs.IPVS_MASQUERADING,
            '2.2.2.3': ipvs.IPVS_LOCAL,
            '2.2.2.4': ipvs.IPVS_TUNNELING,
            '2.2.2.5': ipvs.IPVS_ROUTING,
        }
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1')
        for k, v in six.iteritems(dest_methods):
            self.client.add_dest('1.1.1.1', 80, k, method=v)

        dests = self.client.get_pools()[0].dests()

        for dest in dests:
            exp_method = dest_methods.get(dest.ip(), ipvs.IPVS_TUNNELING)
            self.assertEqual(
                dest.fwd_method(),
                exp_method,
                '%s expected method %d, got %d' % (
                    dest.ip(), exp_method, dest.fwd_method()
                ),
            )

    def test_dest_port(self):
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1')
        self.client.add_dest('1.1.1.1', 80, '2.2.2.2', weight=100)

        service = self.client.get_pools()[0].service()
        dests = self.client.get_pools()[0].dests()
        for dest in dests:
            self.assertEqual(
                dest.port(),
                service.port(),
                'Destination port {0} should be the same then '
                'Service port {1}.'.format(dest.port(), service.port())
            )

    def test_dest_diff_port(self):
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1', 8080)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.2', 8080, weight=100)

        dests = self.client.get_pools()[0].dests()
        for dest in dests:
            self.assertEqual(
                dest.port(),
                8080,
                'Destination port {0} should be set '
                'to specified value {1}'.format(dest.port(), 8080)
            )

    def test_dest_diff_ports(self):
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1', 8080)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1', 8081, weight=100)

        dests = self.client.get_pools()[0].dests()
        self.assertEqual(
            dests[0].port(),
            8081,
            'Destination port should be set to 8081'
        )
        self.assertEqual(
            dests[1].port(),
            8080,
            'Destination port should be set to 8080'
        )


class TestFwmService(BaseIpvsTestCase):

    def test_fwmark_service(self):
        self.client.add_fwm_service(10)

        self.client.add_fwm_dest(10, '2.2.2.1')
        dests = self.client.get_pools()[0].dests()
        self.assertEqual(len(dests), 1)
        self.assertEqual(dests[0].weight(), 1)

        self.client.update_fwm_dest(10, '2.2.2.1', weight=2)
        dests = self.client.get_pools()[0].dests()
        self.assertEqual(len(dests), 1)
        self.assertEqual(dests[0].weight(), 2)

        # Cannot delete a service with a different port
        with self.assertRaises(OSError):
            self.client.del_fwm_dest(10, '2.2.2.1', port=80)

        dests = self.client.get_pools()[0].dests()
        self.assertEqual(len(dests), 1)

        self.client.del_fwm_dest(10, '2.2.2.1')
        dests = self.client.get_pools()[0].dests()
        self.assertEqual(len(dests), 0)

    def test_dest_port(self):
        self.client.add_fwm_service(10)
        self.client.add_fwm_dest(10, '2.2.2.1')
        for dest in self.client.get_pools()[0].dests():
            self.assertEqual(
                dest.port(),
                0,
                'Destination port in fwmark services should have a '
                'value of None, not {0}'.format(dest.port())
            )

    def test_fwmark_af_inet(self):
        self.client.add_fwm_service(10)
        service = self.client.get_pools()[0].service()
        self.assertEqual(service.af(), socket.AF_INET)

    def test_fwmark_af_inet6(self):
        self.client.add_fwm_service(10, af=socket.AF_INET6)
        service = self.client.get_pools()[0].service()
        self.assertEqual(service.af(), socket.AF_INET6)

    def test_add_fwmark_twice(self):
        self.client.add_fwm_service(10)
        with self.assertRaises(OSError):
            self.client.add_fwm_service(10)

    def test_add_fwmark_different_af(self):
        self.client.add_fwm_service(10)
        self.client.add_fwm_service(10, af=socket.AF_INET6)

    def test_del_fwmark_wrong_af(self):
        self.client.add_fwm_service(10, af=socket.AF_INET6)
        with self.assertRaises(OSError):
            self.client.del_fwm_service(10)
        self.client.add_fwm_service(11)
        with self.assertRaises(OSError):
            self.client.del_fwm_service(11, af=socket.AF_INET6)


class TestIpvsClient(BaseIpvsTestCase):
    '''
    This class tests IpvsClient methods not covered by the other service based
    classes.
    It also run with verbose set to True so we can test that print path in
    verbose decorator.
    '''
    @classmethod
    def setUpClass(cls):
        BaseIpvsTestCase.verbose = True

    def test_flush(self):
        '''
        Simply run the flush command.
        '''
        self.client.flush()

    def test_verbose_add_service(self):
        self.client.add_service('1.1.1.1', 80)


class TestIpvsClientQuery(BaseIpvsTestCase):

    def setUp(self):
        super(TestIpvsClientQuery, self).setUp()
        self.client.add_service('1.1.1.1', 80)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.1', 80, weight=10)
        self.client.add_dest('1.1.1.1', 80, '2.2.2.2', 80, weight=10)
        self.client.add_service('1.1.1.2', 8080)
        self.client.add_dest('1.1.1.2', 8080, '2.2.2.1', 8080, weight=10)
        self.client.add_dest('1.1.1.2', 8080, '2.2.2.2', 8080, weight=10)

    def test_get_pools(self):
        for p in self.client.get_pools():
            s = p.service()
            self.assertIn(s.vip(), ['1.1.1.1', '1.1.1.2'])
            for d in p.dests():
                self.assertIn(d.ip(), ['2.2.2.1', '2.2.2.2'])
        # No services defined return an empty list
        self.client.flush()
        self.assertEquals(self.client.get_pools(), [])

    def test_get_service(self):
        s = ipvs.Service({'vip': '1.1.1.2', 'port': 8080,
                          'proto': 'tcp', 'sched': 'rr'})
        self.assertEquals(
            self.client.get_service(s.to_attr_list()),
            s)
        # An inexistent service returns None
        s = ipvs.Service({'vip': '1.1.1.4', 'port': 8080,
                          'proto': 'tcp', 'sched': 'rr'})
        self.assertEquals(self.client.get_service(s.to_attr_list()),
                          None)

    def test_get_pool(self):
        s = ipvs.Service({'vip': '1.1.1.2', 'port': 8080,
                          'proto': 'tcp', 'sched': 'rr'})
        p = self.client.get_pool(s.to_attr_list())
        self.assertEquals(p.service(), s)
        self.assertEquals(len(p.dests()), 2)
        # An inexistent service returns None
        s.port_ = 9090
        self.assertEquals(self.client.get_pool(s.to_attr_list()), None)

    def test_get_dests(self):
        s = ipvs.Service({'vip': '1.1.1.2', 'port': 8080,
                          'proto': 'tcp', 'sched': 'rr'})
        # Generate the IpvsServiceAttrList
        srv = s.to_attr_list()
        res = self.client.get_dests(srv)
        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].weight(), 10)
        self.assertEquals(res[0].fwd_method(), ipvs.IPVS_TUNNELING)
        # An inexistent dest returns an empty list.
        s.vip_ = '2.2.2.4'
        # Generate new IpvsServiceAttrList
        srv = s.to_attr_list()
        self.assertEquals(self.client.get_dests(srv), [])


class TestMiscClasses(BaseJsonTestCase):

    def test_load_pools_from_json(self):
        self.assertEqual(
            len(self.pools),
            len(self.json),
            'Expected to load %d pools from json, got %d' % (
                len(self.json), len(self.pools))
        )

    def test_service_equality(self):
        s0 = self.pools[0].service()
        s1 = self.pools[1].service()
        self.assertNotEqual(
            s0, s1, '%s %s should be different' % (s0, s1)
        )

    def test_service_proto_num(self):
        s0 = self.pools[0].service()
        s1 = self.pools[1].service()
        s2 = self.pools[2].service()
        self.assertEqual(s0.proto_num(), socket.IPPROTO_TCP)
        self.assertEqual(s1.proto_num(), socket.IPPROTO_UDP)
        self.assertIsNone(s2.proto_num())

    def test_dest_equality(self):
        d0 = self.pools[0].dests()[0]
        d1 = self.pools[0].dests()[1]
        d2 = self.pools[1].dests()[0]
        self.assertNotEqual(
            d0, d1, '%s %s should be different.' % (d0, d1)
        )
        self.assertEqual(
            d0, d2, '%s %s should be equal.' % (d0, d2)
        )

    def test_dest_validate(self):
        sample = {
            'ip': '321.0.0.1',
            'weight': None,
            'port': None,
            'fwd_method': 10,
        }
        d = ipvs.Dest(sample)
        # invalid ip
        with self.assertRaises(AssertionError):
            d.validate()

        sample['ip'] = '1.1.1.1'
        d = ipvs.Dest(sample)
        # invalid weight (None)
        with self.assertRaises(AssertionError):
            d.validate()

        sample['weight'] = -2
        d = ipvs.Dest(sample)
        # invalid weight < -1
        with self.assertRaises(AssertionError):
            d.validate()

        sample['weight'] = -1
        d = ipvs.Dest(sample)
        # invalid fwd_method
        with self.assertRaises(AssertionError):
            d.validate()

        sample['fwd_method'] = ipvs.IPVS_TUNNELING
        d = ipvs.Dest(sample)
        # valid Dest
        d.validate()

    def test_pool_to_dict(self):
        p = self.pools[0].to_dict()
        self.assertIn('service', p)
        self.assertIn('dests', p)
        # We only have the 'service' and 'dests' keys
        self.assertEqual(len(p.keys()), 2)

    def test_service_to_dict(self):
        s = self.pools[0].service().to_dict()
        # non fwmark service
        self.assertIn('proto', s)
        self.assertIn('port', s)
        self.assertIn('vip', s)
        self.assertIn('sched', s)
        self.assertIn('af', s)
        self.assertEqual(len(s.keys()), 5)

        s = self.pools[2].service().to_dict()
        # fwmark service
        self.assertIn('fwmark', s)
        self.assertIn('sched', s)
        self.assertIn('af', s)
        self.assertEqual(len(s.keys()), 3)

    def test_service_repr(self):
        s = self.pools[0].service()
        # non fwmark service
        self.assertRegexpMatches(str(s), r'^Service\(.*vip.*')

        s = self.pools[2].service()
        # fwmark service
        self.assertRegexpMatches(str(s), r'^Service\(.*fwmark.*')


class TestHelperFunc(unittest.TestCase):

    def test_validate_ip(self):
        items = {
            '::1': True,
            'A::1': True,
            'Z::1': False,
            '1.1.1.1': True,
            '323.1.1.1': False,
        }
        for k, v in six.iteritems(items):
            self.assertEqual(
                ipvs._validate_ip(k), v,
                '%s valid IP: %s' % (k, not v)
            )

    def test_to_proto_num(self):
        h = {
            'tcp': socket.IPPROTO_TCP,
            'TCP': socket.IPPROTO_TCP,
            'Tcp': socket.IPPROTO_TCP,
            'udp': socket.IPPROTO_UDP,
            'UDP': socket.IPPROTO_UDP,
            'Udp': socket.IPPROTO_UDP,
            None: None,
        }

        for k, v in six.iteritems(h):
            self.assertEqual(
                ipvs._to_proto_num(k), v,
                '{0} is not matching the right proto num {1}'.format(k, v))

        with self.assertRaises(AssertionError):
            ipvs._to_proto_num('foo')

    def test_from_proto_num(self):
        h = {
            socket.IPPROTO_TCP: 'tcp',
            socket.IPPROTO_UDP: 'udp',
            None: None,
        }

        for k, v in six.iteritems(h):
            self.assertEqual(
                ipvs._from_proto_num(k), v,
                'proto num {0} is not matching {1}'.format(k, v))

        with self.assertRaises(AssertionError):
            ipvs._from_proto_num(socket.IPPROTO_RSVP)


if __name__ == '__main__':
    unittest.main()
