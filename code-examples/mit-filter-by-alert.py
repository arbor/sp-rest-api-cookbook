#!/usr/bin/env python2
""" Get mitigations based on an alert id

In versions of the REST API prior to and including Sightline 9.0, the
`/mitigations/' REST API endpoint does not support filtering.

This program demonstrates a way to page through all of the mitigations on an
deployment, and return only those matching a particular alert id.

This program supports:
  - stopping after the first match
  - stopping after a certain number of "pages" of API results

It could be extended to look back a certain number of days, or between two
dates, or after a certain number of matches, etc.

This has been only lightly tested and may fail in odd ways.  There are
certainly some assumptions made about the type and structure of the data in
some places.  The obvious errors should be handled, but not all of them are.

"""
from __future__ import print_function
import argparse
import json
import requests
import sys
from urllib.parse import urlparse, parse_qs


def get_mits(leader, api_key, alert_id, get_all_mits, max_page,
             page=1, matched_mits=[]):
    """Recursively get migitaions from the pages of API output"""

    url = 'https://{}/api/sp/mitigations/?page={}'.format(leader, page)

    results = requests.get(
        url,
        headers={'X-Arbux-APIToken':
                 api_key,
                 'Content-Type':
                 'application/vnd.api+json'},
        verify='./certfile')

    if results.status_code != requests.codes.ok:
        print("API request was not OK: {} {}".format(
            results.status_code, results.reason),
              file=sys.stderr)
        print("Returning what we have as of page {}".format(page))
        return matched_mits

    mits = results.json()
    for mit in mits['data']:
        if 'relationships' not in mit:
            continue
        if 'alert' not in mit['relationships']:
            continue
        if mit['relationships']['alert']['data']['id'] == str(alert_id):
            matched_mits.append(mit)
            if not get_all_mits:
                return matched_mits
    if 'next' in mits['links']:
        next_page = int(
            parse_qs(
                urlparse(
                    mits['links']['next']).query)['page'][0])
        if next_page > max_page:
            return matched_mits
        print("Moving to page {} having found {} matching mitigations.".format(
            next_page, len(matched_mits)))
        get_mits(leader, api_key, alert_id, get_all_mits, max_page,
                 next_page, matched_mits)

    return matched_mits


def main():
    """main(): parse the arguments, call the GET function, print the results"""
    parser = argparse.ArgumentParser(
        description='Filter mitigations by alert id',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-a', '--alertid',
        dest="alert_id",
        required=True,
        help='the alert id to filter on')
    parser.add_argument(
        '--all',
        dest="get_all_mits",
        action='store_true',
        default=False,
        help='get more than just the first matching mitigation')
    parser.add_argument(
        '-l', '--leader',
        dest='leader',
        required=True,
        help='hostname of the deployment leader')
    parser.add_argument(
        '-k', '--apikey',
        dest='api_key',
        required=True,
        help='API key')
    parser.add_argument(
        '-p', '--maxpage',
        dest='max_page',
        default=1,
        type=int,
        help='stop when you reach this page number')
    args = parser.parse_args()

    mits = get_mits(args.leader, args.api_key,
                    args.alert_id, args.get_all_mits,
                    args.max_page)

    print(json.dumps(mits, indent=4))


if __name__ == '__main__':
    main()
