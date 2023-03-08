from __future__ import print_function
import sys
import requests  # version: 2.28.1
import json
import slenv

CERT_FILE = "./certfile"


def api_request(URL, key, body=None):
    """ General function for making GET and PATCH requests

    Response codes falling within 'requests.codes.ok' are assumed
    to have completed successfully. Supplying the optional 'body'
    parameter will change the request type to PATCH.

    Args:
        URL: valid URL to make request to
        key: API key generated on the given SP leader
        body (optional): JSON formatted string containing
            patch body content

    Returns:
        'Data' keyvalue of a requests.Response object
    """

    headers = {'X-Arbux-APIToken': key,
               'Content-Type': 'application/vnd.api+json'}
    if body is None:
        api_response = requests.get(
            URL,
            headers=headers,
            verify=CERT_FILE)
    else:
        api_response = requests.patch(
            URL,
            data=body,
            headers=headers,
            verify=CERT_FILE)

    # Handle any API error responses
    if (api_response.status_code != requests.codes.ok):
        print("API responded with this error: \n{}".format(
            api_response.text),
            file=sys.stderr)
        return []

    # Convert the response to JSON and return it
    api_response = api_response.json()
    return api_response['data']


def get_appliances(leader, key):
    """Retrieve appliances from an SP leader

    Args:
        leader: SP leader from which the appliances exist
        key: API key generated on the given SP leader

    Returns:
        List of appliances from the SP leader
    """

    print("Retrieving appliances from {}".format(leader))

    # Craft the URL components
    APPLIANCE_URI = '/api/sp/devices/'
    URL = "https://" + leader + APPLIANCE_URI

    # Make the api request and return its results
    api_response = api_request(URL, key)
    return api_response


def set_limits(leader, key, appliances):
    """ Configure the provided appliances with limits

    Args:
        leader: SP leader from which the appliances exist
        key: API key generated on the given SP leader
        appliances: List of appliances
    """

    for appliance in appliances:
        LIMIT = 'metrics_items_tracked_per_day_limit'
        LIMIT_VALUE = 15
        if LIMIT not in appliance['attributes']:
            patch = {
                "data": {
                    "attributes": {
                        LIMIT: LIMIT_VALUE
                    }
                }
            }

            # Create a unique URL for the appliance
            DEVICE_URI = ("/api/sp/devices/{}".format(
                appliance['id']))
            URL = "https://" + leader + DEVICE_URI

            # PATCH the appliance
            api_response = api_request(URL, key, json.dumps(patch))

            # Handle any API response
            if api_response:
                print("Device {id}: {limit} configured".format(
                    id=appliance['id'], limit=LIMIT))
            else:
                print("Could not configure device {}".format(
                    appliance['id']),
                    file=sys.stderr)

        else:
            print("Device {id}: {limit} is already configured".format(
                id=appliance['id'], limit=LIMIT))


#####################
# Start the Program #
#####################


def main():
    SP_LEADER = slenv.leader
    API_KEY = slenv.apitoken

    print('Starting appliance-limiting script')
    appliances = get_appliances(SP_LEADER, API_KEY)
    if appliances:
        print('Appliances retrieved. Configuring limits')
        set_limits(SP_LEADER, API_KEY, appliances)

    print('Done')

if __name__ == "__main__":
    main()
