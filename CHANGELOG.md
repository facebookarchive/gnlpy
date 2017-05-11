## 0.1.2 (2017-05-11)

* Add support for cgroup_stats (@alexdias)
* py3 compatible (@chantra)
* Add IpvsClient.get_service (@lavagetto)
* Add IpvsClient.get_pool (@lavagetto)
* Expose address family to Service (@vmauge)

## 0.1.1 (2016-03-02)

### ipvs

* Allow setting forwarding method
* Add support for 64 bits stats (introduced in kernel 4)
* Allow specifying different ports for destination.
* Fix Dest.from_attr_list to use `addr_family` attribute, not `af`
* Add unittests

## 0.1.0 (2015-05-18)

* Initial public release
