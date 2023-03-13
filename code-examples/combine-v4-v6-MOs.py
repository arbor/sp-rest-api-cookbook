#!/usr/bin/env python

"""show how to use the new keys / functionality provided by CoMO

Because MOs are a licensed quantity in SP, it can be helpful to make the best
possible use of the MOs, and with the Combined IPv4/IPv6 Managed Objects
available in SP8.4 MOs that were previously separate to support IPv4 and IPv6
match criteria can now be combined.

Look for IPv6 matches, determine that no functionality is lost, and produce the
JSON for a PATCH to cust02 to move the IPv6 stuff into it. (e.g., if cust02_v6
and cusot02 both exist, can they safely be merged? What would be new MO look
like?) Take a list of MOs that looks like:

     [
         {
             "v4": "cust01_v4",
             "v6": "cust01_v6"
         },
         {
             "v4": "cust02",
             "v6": "cust02_v6"
         },
         {
             "v4": "cust03-4",
             "v6": "cust04"
         },
         {
             "v4": "cust-04",
             "v6": "cust6-04"
         },
         {
             "v4": "cust4-05",
             "v6": "cust6-05"
         }
     ]

and see if the MOs tagged "v6" can be merged into the MO tagged v4 """

from __future__ import print_function
import json
import os
import sys
import requests
from copy import deepcopy
import slenv


def get_mos(leader, apikey, certfile, page=1, mos=[]):
    """gather up all of the MOs on the deployment and return them"""

    url = "https://{}/api/sp/managed_objects/?page={}".format(
        leader, page)

    response = requests.get(
        url,
        headers={"X-Arbux-APIToken": apikey,
                 "Content-Type": "application/vnd.json+api"},
        verify=certfile)

    if response.status_code is not requests.codes.ok:
        print("API request for alerts returned {} ({})".format(
            response.reason, response.status_code),
            file=sys.stderr)
        return None

    response = response.json()

    mos = response['data']

    if 'next' in response['links']:
        print ("Getting page {} from the "
               "managed_objects endpoint".format(page+1))
        mos += get_mos(leader, apikey, certfile, page+1, mos)

    return mos


def get_mos_to_check(MOS_FILE):
    """Load the MOs to check from a file or print MO names

    Try to load the MOs from a JSON file called "./mos_to_check.json";
    if that file doesn't exist, then just print a list of MOs and
    exit.
    """
    if not os.path.isfile(MOS_FILE):
        msg = """
Please create a file called %s and populate it with
a JSON-formatted list of names of MOs to evaluate for
combining.
The list should look like:
[
    {
        "v4": "mo1_name_v4",
        "v6": "mo1_name_v6"
    },
    {
        "v4": "mo2_name_v4",
        "v6": "mo2_name_v6"
    }
]"""
        print (msg % (MOS_FILE))
        print ("Your MOs are:")
        for (t, n) in sorted(type_and_name):
            print ("{:<15} {}".format(t, n))

        sys.exit(0)

    # no error checking. live fast, leave a beautiful traceback
    with open(MOS_FILE, "rb") as f:
        mos_to_check = json.load(f)

    return mos_to_check


def get_type_and_name(mos):
    """parse the MO json from SP and return type and name for each one

    This is just for reporting to the console what is happening, and for
    some basic error checking
    """
    type_and_name = []
    for mo in mos:
        if 'match_type' in mo['attributes']:
            match_type = mo['attributes']['match_type']
            if (match_type == 'cidr_blocks' or
                    match_type == 'cidr_v6_blocks'):
                type_and_name.append([mo['attributes']['match_type'],
                                      mo['attributes']['name']])

    num_v6 = 0
    for (t, n) in type_and_name:
        if t == 'cidr_v6_blocks':
            num_v6 += 1

    return type_and_name, num_v6


def check_mos(mos, mos_to_check):
    """Make sure the MOs to check from the file actually exist"""
    mo_names = [mo['attributes']['name'] for mo in mos]

    matched_mos = []
    for mo in mos_to_check:
        if mo['v4'] in mo_names and mo['v6'] in mo_names:
            matched_mos.append(mo)
        else:
            print ('<'*70)
            print ("The following MO will not be evaluated "
                   "for combining because one ")
            print ("or both of the MO names is not configured "
                   "on the SP system.")
            print (json.dumps(mo, indent=4))
            print ('>'*70)

    return matched_mos


def index_mos_by_name(mos):
    """It is useful to have MOs indexed by name, so do that"""
    mos_by_name = {}
    for mo in mos:
        mos_by_name[mo['attributes']['name']] = mo

    return mos_by_name


def diff_mos(mos_by_name, mos_to_check):
    """Look for differences in pairs of v4 and v6 MOs

    The differences that will be highlighted are: 1. Different shared
    host detection sets; 2. Different family types

    You should be very careful to add other things to check here; this
    function is probably incomplete for your network and should be
    augmented to compare things between MOs that you need to make sure
    are OK to combine
    """

    results = {}
    for mo_name in mos_to_check:
        # Store results keys by combined MO names
        key = (mo_name['v4'], mo_name['v6'])
        if key not in results:
            results[key] = []
        # Check for matching family types
        if (mos_by_name[mo_name['v4']]['attributes']['family'] !=
                mos_by_name[mo_name['v6']]['attributes']['family']):
            results[key].append("Family types do not match")
        # Check for matching shared host detection sets
        v4_shds = mos_by_name[mo_name['v4']]['relationships'][
            'shared_host_detection_settings']['data']['id']
        v6_shds = mos_by_name[mo_name['v6']]['relationships'][
            'shared_host_detection_settings']['data']['id']
        if (v4_shds != v6_shds):
            results[key].append("Shared Host Detection Sets do not match")
        #
        # You will want to add other relevant checks here, to make sure that
        # your combined managed object makes sense in your network
        #
    return results


def combine_mos(mov4, mov6):
    """put v6 match values and v6 mit templs into cidr_block-match MO

    take the two MOs that can be combined and return the JSON for an MO
    that can be combined; create a name, comment, and tag that
    represents this, set the match values to all of the match values
    from both MOs, and set the v4/v6 auto/manual mitigation templates to
    the values from each of the initial MOs

    You should be very careful to add other things to combine here; this
    function is probably incomplete for your network and should be
    augmented to combine things between MOs that you need to make sure
    are needed in a combined managed object
    """
    mov4['attributes']['match'] += " " + mov6['attributes']['match']
    mov4['attributes']['name'] = "{} + {}".format(
        mov4['attributes']['name'],
        mov6['attributes']['name'])
    mov4['attributes']['description'] += " ---Combined Managed Object--- "
    mov4['attributes']['tags'].append("auto-combined")
    mov4['relationships']['mitigation_templates_manual_ipv6'] = (
        mov6['relationships']['mitigation_templates_manual_ipv6'])
    mov4['relationships']['mitigation_templates_auto_ipv6'] = (
        mov6['relationships']['mitigation_templates_auto_ipv6'])
    #
    # You will want to add other relevant combinaitions here, to make sure that
    # your combined managed object makes sense in your network
    #

    mo = {}
    mo['data'] = deepcopy(mov4)
    mo['data'].pop("links", None)
    mo['data'].pop("id", None)

    return mo


if __name__ == '__main__':

    LEADER = slenv.leader
    APIKEY = slenv.apitoken
    CERTFILE = './certfile'
    MOS_FILE = 'mos_to_merge.json'

    print("Collecting information on managed "
          "objects from {}.".format(LEADER))

    mos = get_mos(LEADER, APIKEY, CERTFILE)
    if mos is None:
        sys.exit(1)

    print ("There are {} MOs.".format(len(mos)))

    type_and_name, num_v6 = get_type_and_name(mos)

    if num_v6 == 0:
        print ("There aren't any IPv6 matches, so "
               "there is nothing to combine.")
        sys.exit(0)
    else:
        print ("There are {} out of {} MOs with CIDR matches "
               "that are IPv6 matches.".format(
                   num_v6, len(type_and_name)))

    mos_by_name = index_mos_by_name(mos)

    mos_to_check = get_mos_to_check(MOS_FILE)

    mos_to_check = check_mos(mos, mos_to_check)

    differences = diff_mos(mos_by_name, mos_to_check)

    uncombinable_mos = [mo for mo in differences if len(differences[mo]) > 0]
    for mo in uncombinable_mos:
        print ("{}:".format(mo))
        for diff in differences[mo]:
            print ("  - {}".format(diff))

    mos_to_combine = [mo for mo in differences if len(differences[mo]) == 0]

    print ("MOs that can be combined: {}".format(mos_to_combine))

    combined_mo = {}
    for mo in mos_to_combine:
        combined_mo[mo] = combine_mos(
            mos_by_name[mo[0]],
            mos_by_name[mo[1]])
        for name in mo:
            print ('DELETE http://{}/api/sp/managed_objects/{}'.format(
                LEADER,
                mos_by_name[name]['id']
                ))
        print ('POST http://{}/api/sp/managed_objects << \n{}'.format(
            LEADER,
            json.dumps(combined_mo[mo], indent=4)))
