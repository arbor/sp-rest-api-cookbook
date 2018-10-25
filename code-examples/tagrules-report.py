#!/usr/bin/env python2.7
from __future__ import print_function
import requests
import json
import sys
from datetime import date
from dateutil.relativedelta import relativedelta


def make_query_totals_by_ipdest_tagrules(tagrules):
    query = {
         "limit": 11,
         "calculation": "average",
         "metric": "bps",
         "groupby_parameters": {},
         "groupby": [],
         "view_values": [],
         "view": "Network",
         "filters": {},
         "end": "",
         "start": ""
     }

    #
    # Add Dest IPv4 address to the other aspects (probably tagrules)
    #
    tagrules.append("Destination_IPv4_Address")
    tagrules.append("Source_IPv4_Address")
    query['groupby'] = tagrules

    #
    # Set the query time range to the last 4 days
    #
    today = date.today()
    three_days_ago_start = today + relativedelta(
        days=-3,
        hour=0)
    yesterday_end = today + relativedelta(
        hour=23,
        minute=59,
        second=59)

    query['start'] = "{}".format(three_days_ago_start.isoformat())
    query['end'] = "{}".format(yesterday_end.isoformat())

    return query


def get_insight_data(leader, apikey, query):
    url = 'https://{}/api/sp/insight/topn'.format(leader)
    results = requests.post(
        url,
        headers={'X-Arbux-APIToken':
                 apikey,
                 'Content-Type':
                 'application/vnd.api+json'},
        json=query,
        verify="./certfile")

    if results.status_code != requests.codes.ok:
        print("Insight query for tagged data failed: [{}] {}".format(
            results.status_code, results.reason),
              file=sys.stdout)
        sys.exit(1)

    return results.json()


def main(leader, apikey, tagrules):

    query = make_query_totals_by_ipdest_tagrules(tagrules)
    data = get_insight_data(leader, apikey, query)

    print("{:>6}  {:>15}  {:>15}  {:>15}".format(
        "Inc.#", "Dest IP Addr", "Src IP Addr", "In Traf (bps)"))
    for thing in data['data']:
        print("{:>6}  {:>15}  {:>15}  {:>15.2f}".format(
            thing['Incident'],
            thing['Destination_IPv4_Address'],
            thing['Source_IPv4_Address'],
            thing['bps']['average']['in']))


if __name__ == '__main__':
    leader = 'static.tb.arbor.net'
    apikey = 'Quafina'
    tagrules_to_groupby = ['Incident']
    main(leader, apikey, tagrules_to_groupby)
