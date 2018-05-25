#!/usr/bin/env python
""" Report on number of attacks by CIDR block

This program has some constants defined at the bottom of it that set the SP
Leader, the SP REST API Token for that leader, the path to the SSL certificate
file, the start and end times for finding alerts, and the netmask lengths for
IPv4 networks and IPv6 networks.

It then pages through the SP REST API's /alerts/ endpoint and collects
addresses from the alert information.  Those addresses are then collected in to
CIDR blocks and a simple table is printed.

"""

from __future__ import print_function
import ipaddress
import requests
import sys
from datetime import datetime


def iso8601_to_datetime(iso8601_string):
    """annoyingly, Python can produce but not read ISO8601 datestamps

    this function does some pretty dumb things to convert that format
    back into a Python datetime object
    """
    return datetime.strptime(
        iso8601_string.split('+')[0],
        '%Y-%m-%dT%H:%M:%S')


def get_attacked_addresses(leader, token, cert,
                           start, end,
                           page=1, addrs=[]):
    """Get the `host_address` field from alerts between start and end

    Page through the `/alerts/` endpoint and gather up the
    `host_address` addresses into a list, this function calls itself
    until the last alert in the list started before the `start` time
    """

    url = 'https://{}/api/sp/v2/alerts/?page={}'.format(leader, page)
    start_dt = iso8601_to_datetime(start)
    end_dt = iso8601_to_datetime(end)

    r = requests.get(url,
                     headers={
                         "X-Arbux-APIToken": token,
                         "Content-Type": 'application/vnd.json+api'
                         },
                     verify=cert)

    if r.status_code is not requests.codes.ok:
        print("API request for alerts returned {} ({})".format(
            r.reason, r.status_code), file=sys.stderr)
        return None

    alerts = r.json()

    for alert in alerts['data']:
        if 'attributes' in alert and 'subobject' in alert['attributes']:
            if 'host_address' in alert['attributes']['subobject']:
                alert_time = iso8601_to_datetime(
                    alerts['data'][-1]['attributes']['start_time']
                    )
                if alert_time > start_dt and alert_time < end_dt:
                    addrs.append(
                        alert['attributes']['subobject']['host_address']
                        )

    last_alert = iso8601_to_datetime(
        alerts['data'][-1]['attributes']['start_time'])
    if last_alert > start_dt:
        print ("paging to page {}; # addresses so far: {}".format(
            page+1, len(addrs)))
        get_attacked_addresses(leader, token, cert, start,
                               end, page+1, addrs)

    return addrs


def bundle_addresses(addrs, netmasks):
    """Use the ipaddress library to put addresses into CIDR blocks

    coerce the address into a CIDR block with the correct netmask for
    its IP version (4 or 6), and then put that CIDR into a dictionary
    where occurances are counted.  See
    https://github.com/phihag/ipaddress and/or `pip install ipaddress`
    """
    networks = {}
    for addr in addrs:
        addr = ipaddress.ip_address(addr)
        network = str(addr)+"/"+netmasks[str(addr.version)]
        network = ipaddress.ip_network(network, strict=False)
        if str(network) in networks:
            networks[str(network)] += 1
        else:
            networks[str(network)] = 1

    return networks


if __name__ == '__main__':
    SPLEADER = 'spleader.example.com'
    APITOKEN = 'MySecretAPItoken'
    CERTFILE = './certfile'

    START_DATE = '2018-05-23T12:00:00+00:00'
    END_DATE = '2018-05-23T23:00:00+00:00'

    IPv4_MASK = '24'
    IPv6_MASK = '116'

    addresses = get_attacked_addresses(SPLEADER,
                                       APITOKEN,
                                       CERTFILE,
                                       START_DATE,
                                       END_DATE)
    print ("# addresses found between {} and {}: {}".format(
        START_DATE,
        END_DATE,
        len(addresses)))

    cidrs = bundle_addresses(addresses, {'4': IPv4_MASK,
                                         '6': IPv6_MASK})

    print("{:>25}-+-{}".format("-"*25, "---------"))
    print("{:>25} | {}".format("Subnet", "# Attacks"))
    print("{:>25}-+-{}".format("-"*25, "---------"))
    for cidr in sorted(cidrs):
        print("{:>25} | {:>8}".format(cidr, cidrs[cidr]))
