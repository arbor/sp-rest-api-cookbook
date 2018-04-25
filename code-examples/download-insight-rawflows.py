from __future__ import print_function
import argparse
import requests
import json
import sys
from datetime import datetime
from dateutil.parser import parse


def parse_cmdline_args():
    """Parse the command line options and set some useful defaults"""
    parser = argparse.ArgumentParser(
        description='Download raw flows from SP Insight to a CSV file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-s', '--start_time',
        dest='start',
        required=True,
        help='Start date and time for rawflows')
    parser.add_argument(
        '-e', '--end_time',
        dest='end',
        required=True,
        help='End date and time for rawflows')
    parser.add_argument(
        '-l', '--sp_leader',
        dest='leader',
        required=True,
        help='Hostname or IP address of the SP leader')
    parser.add_argument(
        '-k', '--api_key',
        dest='apikey',
        required=True,
        help='SP REST API key for the leader')
    parser.add_argument(
        '-n', '--number_of_raw_flow_records',
        type=int,
        default=5000,
        dest='num_records',
        help='Maximum number of raw flows records to return')
    parser.add_argument(
        '-p', '--perspective',
        default='network',
        dest='perspective',
        help='Perspective from which to get the raw flows')
    parser.add_argument(
        '-v', '--view',
        default='Network',
        dest='view',
        help='View from which to get the raw flows')
    parser.add_argument(
        '-o', '--output_file',
        default='raw_flows.csv',
        dest='output_file',
        help='Path and filename for rawflows CSV data')
    parser.add_argument(
        '-c', '--cert_file',
        default='/Users/acaird/certfile',
        dest='certfile',
        help='Path to and name of the SSL certificate file')

    return parser.parse_args()


if __name__ == '__main__':

    args = parse_cmdline_args()

    leaderurl = 'https://{}/api/sp/insight/rawflows'.format(args.leader)

    # Use Python's parse/fuzzy date interpreter to try to get useful dates
    try:
        start = parse(args.start, fuzzy=True).isoformat()
        end = parse(args.end, fuzzy=True).isoformat()
    except ValueError:
        print ("ERROR: I couldn't parse the dates you provided ("
               "start: {}, end: {}), please try another format.".format(
                   args.start, args.end))
        sys.exit(1)

    query = {
        "start": start,
        "end": end,
        "dimensions": [
            "IP_Protocol",
            "Source_IPv4_Address",
            "Source_Port",
            "Destination_IPv4_Address",
            "Destination_Port"
        ],
        "limit": args.num_records,
        "perspective": args.perspective,
        "view": args.view
    }

    print ("  Querying {} for {} raw flows records between {} and {}...".
           format(
               args.leader,
               args.num_records,
               start,
               end))

    query_start = datetime.now()
    answer = requests.post(leaderurl,
                           headers={"X-Arbux-APIToken": args.apikey,
                                    "Content-Type": "application/vnd.api+json",
                                    "Accept": "text/csv"},
                           data=json.dumps(query), verify=args.certfile,
                           stream=True)
    query_end = datetime.now()
    with open(args.output_file, "wb") as f:
        for i, chunk in enumerate(answer.iter_content(chunk_size=262144)):
            print ("  Writing chunk #{} to {}".format(i, args.output_file),
                   end='\r')
            f.write(chunk)

    write_end = datetime.now()

    # Print some timing information
    print ('')
    print ("Query time: {0:10.1f} seconds".format(
        ((query_end-query_start).total_seconds())))
    print ("Write time: {0:10.1f} seconds".format(
        ((write_end-query_end).total_seconds())))
    print ("Total time: {0:10.1f} seconds".format(
        ((write_end-query_start).total_seconds())))
