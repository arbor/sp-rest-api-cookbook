#!/usr/bin/env python2.7
from __future__ import print_function
import requests
import json
import sys
from copy import deepcopy
from itertools import cycle
from datetime import date
from dateutil.relativedelta import relativedelta


def get_yesterdays_top_talkers(leader, apikey, number=2):

    yesterdays_top_talkers = []
    url = 'https://{}/api/sp/insight/topn'.format(leader)
    # Query template for Source IPv4 Addresses
    query = {
        "limit": 3,
        "calculation": "average",
        "metric": "bps",
        "groupby_parameters": {
            "Source_IPv4_Address": {
                "output_mask_length": 32
                }
         },
        "groupby": [
                "Source_IPv4_Address"
        ],
        "view_values": [],
        "view": "Network",
        "filters": {
            },
        "start": "",
        "end": ""
        }
    # set the size of the query
    query['limit'] = number

    # set the time range of the query with a hard-coded "yesterday"
    today = date.today()
    yesterday_start = today + relativedelta(days=-1,
                                            hour=0)
    yesterday_end = today + relativedelta(days=-1,
                                          hour=23,
                                          minute=59,
                                          second=59)
    query['start'] = yesterday_start.isoformat()
    query['end'] = yesterday_end.isoformat()

    # post the query to the SL/Insight REST API
    results = requests.post(
        url,
        headers={'X-Arbux-APIToken':
                 apikey,
                 'Content-Type':
                 'application/vnd.api+json'},
        json=query,
        verify="./certfile")

    if results.status_code != requests.codes.ok:
        print("API query for yesterdays top talkers failed: [{}] {}".format(
            results.status_code, results.reason),
              file=sys.stdout)
        sys.exit(1)
    results = results.json()

    # Extract the IP addresses from the results
    for top_talker in results['data']:
        ipaddress = top_talker['Source_IPv4_Address'].split('/')[0]
        yesterdays_top_talkers.append(ipaddress)

    return yesterdays_top_talkers


def create_tag_rules(leader, apikey, ipaddrs):
    url = 'https://{}/api/sp/insight/tagrules/'.format(leader)
    #
    # Create some fake incident data and a tagrules template for it
    #
    today = date.today()
    yesterday_start = today + relativedelta(days=-1, hour=0)
    a_week_from_today = today + relativedelta(days=+7, hour=0)
    #
    # These fake incident IDs are important for this example; we will query the
    # new "Incident" dimension in Insight and expect to get these IDs back with
    # some data attached to them once the data has been processed
    #
    fake_incidents = cycle(
        [("12345", "{}".format(yesterday_start.isoformat())),
         ("54321", "{}".format(yesterday_start.isoformat()))])
    ott_incident_template = {
        "data": {
            "attributes": {
                "valid_from": "",
                "valid_until": "",
                "tags": {
                    "Incident": ""
                    },
                "filter_criteria": {
                    "Source_IPv4_Address": ""
                }
            }
        }
    }

    #
    # create a bulk tagrules (Over-the-Top, ott) posting body
    #
    bulk_ott = []
    for ipaddr in ipaddrs:
        incident = next(fake_incidents)
        ott = deepcopy(ott_incident_template)
        ott['data']['attributes']['valid_from'] = incident[1]
        ott['data']['attributes']['tags']['Incident'] = incident[0]
        ott['data']['attributes']['valid_until'] = "{}".format(
            a_week_from_today)
        ott['data']['attributes']['filter_criteria']['Source_IPv4_Address'] = (
            ipaddr)
        bulk_ott.append(ott['data'])
    bulk_ott = {'data': bulk_ott}
    headers = {'X-Arbux-APIToken': apikey,
               'Accept': '*/*; ext="spbulk"',
               'Content-Type':
               'application/vnd.api+json'}
    results = requests.post(
        url,
        headers=headers,
        data=json.dumps(bulk_ott),
        verify="./certfile")
    if (results.status_code is requests.codes.ok or
        results.status_code is requests.codes.created or
        results.status_code is requests.codes.accepted):

        return results.json()
    else:
        print(results.status_code, results.reason)
        return {'data': []}


def main(leader, apikey):
    #
    # get N top talkers from whatever complete day was yesterday
    #
    yesterdays_top_talkers = get_yesterdays_top_talkers(leader, apikey, 4)

    #
    # with those IP addresses, create some tag rules with fake incidents
    #
    new_tag_rules = create_tag_rules(leader, apikey, yesterdays_top_talkers)

    #
    # Print out a table of the new tagrules
    #
    format_str = "{:>4}  {:>15}  {:>25}  {:>25}  {:>10}"
    print(format_str.format(
        "ID", "Source IP", "Valid from", "Valid until", "Incident"
        ))

    for tag_rule in new_tag_rules['data']:
        print(format_str.format(
            tag_rule['id'],
            tag_rule['attributes']['filter_criteria']['Source_IPv4_Address'],
            tag_rule['attributes']['valid_from'],
            tag_rule['attributes']['valid_until'],
            tag_rule['attributes']['tags']['Incident']
            ))


if __name__ == '__main__':
    leader = 'sightline-leader.example.com'
    apikey = 'My_API_Token'
    main(leader, apikey)
