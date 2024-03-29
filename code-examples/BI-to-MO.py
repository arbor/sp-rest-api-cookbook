from __future__ import print_function
import csv
import json
import requests  # version: 2.28.1
import sys
import slenv

CERTFILE="./certfile"

def api_request(URL, key, body=None):
    """ Creates and makes a post request to an SP
    api service

    Args:
        URL: A URL including an SP leader and
             SP resource
        key: An api key generated on the given
             SP leader
        body: JSON formatted string to be supplied
              as the request's body

    Returns:
        'data' value of an SP api response
    """

    headers = {
        'X-Arbux-APIToken': key,
        'Content-Type': 'application/vnd.api+json'
    }

    api_response = requests.post(
        URL,
        data=body,
        headers=headers,
        verify=CERTFILE
    )

    try:
        api_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(
            'An HTTP {} Error Occured:{}'.format(
                str(err),
                api_response.text),
            file=sys.stderr
        )

        return api_response.json()

    try:
        return api_response.json()['data']
    except ValueError as err:
        return {}


def get_request_body(managed_object):
    """Map a row in a csv to a nested dictionary
    that SP will accept as a managed object

    Args:
        managed_object: flat dictionary from csv
        representing a single managed object

    Returns:
        Nested dictionary representing a
        managed object in SP

    """

    return {
        'data': {
            'attributes': {
                'name': managed_object['name'],
                'family': 'customer',
                'match_type': 'cidr_block',
                'match': managed_object['prefix'],
                'tags': ['api', 'customer']
            },
            'relationships': {
                'mitigation_templates_auto_ipv4': {
                    'data': {
                        'id': '2',
                        'type': 'mitigation_template'
                    }
                }
            }
        }
    }


def get_managed_objects_from_csv(filename):
    """ Get a handler for managed object data
    from a csv file

    Args:
        filename: path / name for a csv file
        containing managed_object configurations.
        The first line of the csv is a header,
        containing "name,prefix". Similarly,
        subsequent lines represent managed objects.
        E.g., "Wind,74.182.59.3/32".

    Returns:
        A generator returning managed objects in
        nested dict form
    """

    with open(filename) as listings:
        for row in csv.DictReader(listings):
            yield get_request_body(row)


def create_managed_object(leader, key, managed_object):
    """ Crafts and makes an api request to create
    an SP managed object

    Args:
        leader: hostname of an SP leader
        key: api key, as generated by the
             SP leader
        managed_object: nested dict representing
                        the managed_object being
                        created

    Returns:
        Id as string of new managed object, or
        None if request was unsuccessful
    """

    object_json = json.dumps(managed_object)

    response = api_request(
        'https://{}/api/sp/managed_objects/'.format(leader),
        key,
        object_json
    )

    if 'errors' in response:
        print(
            'Could not create managed object...',
            file=sys.stderr
        )
        return None

    return response["id"]


def commit_config(leader, key):
    """ Crafts and makes an api request to commit an
        SP configuration

    Args:
        leader: hostname of an SP leader
        key: api key, as generated by said SP leader

    Returns:
        boolean indicating the success of the
        operation
    """
    print ("Committing configuration.")
    commit_msg = json.dumps({
        'data': {
            'attributes': {
                'commit_log_message':
                    'Added managed objects to deployment via SP API'
            }
        }
    })

    response = api_request(
        'https://{}/api/sp/config/'.format(leader),
        key,
        commit_msg
    )

    if 'errors' in response:
        print(
            "Could not commit configuration...",
            file=sys.stderr
        )
        return False

    print("Committed configuration.")
    return True


def main():
    LEADER = slenv.leader
    KEY = slenv.apitoken

    for listing in get_managed_objects_from_csv('main.csv'):
        create_managed_object(LEADER, KEY, listing)

    commit_config(LEADER, KEY)


if __name__ == "__main__":
    main()
