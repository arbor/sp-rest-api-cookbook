from __future__ import print_function
from datetime import datetime, timedelta
import sys
import requests  # version: 2.18.4
import json  # version: 2.0.9
import urllib  # version: 1.17

CERT_FILE = './https_active.crt'


def api_request(URL, key, body=None):
    """ General function for making GET and POST requests

    Response codes falling within 'requests.codes.ok' are assumed
    to have completed successfully. Supplying the optional 'body'
    parameter will change the request type to POST.

    Args:
        URL: valid URL to make request to
        key: API key generated on the given SP leader
        body (optional): JSON formatted string containing
            post body content

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
        api_response = requests.post(
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


def get_alerts(leader, key):
    """ Retrieve alerts from an SP leader

    Args:
        leader: SP leader from which the alerts originated
        key: API key generated on the given SP leader

    Returns:
        List of impact data containing alerts
    """

    print("Fetching ongoing alerts from {}".format(leader))

    # Craft the URL components, filtering based on ongoing dos alerts
    ALERT_URI = '/api/sp/alerts/?filter='
    FILTER = ("/data/attributes/ongoing = true AND " +
              "/data/attributes/alert_class = dos")

    # Percent-encode our filter query and combine URL components
    FILTER = urllib.quote(FILTER, safe='')
    URL = "https://" + leader + ALERT_URI + FILTER

    # Make the api request and return its results
    api_response = api_request(URL, key)
    return api_response


def create_annotation_msg(impact_data):
    """ Create an annotation message for impact data

    Args:
        impact_data: dict containing impact data in the form of,
        {
            'bps': bps,
            'pps': pps,
            'impact_boundary (optional)': boundary
        }

    Returns:
        String describing alert impact
    """

    # Add impact rates to annotation message
    msg = ("Impact in bps: {impact_bps}; " +
           "Impact in pps: {impact_pps};").format(
        impact_bps=impact_data['bps'],
        impact_pps=impact_data['pps'])

    # If alert data contains boundary info, include that as well
    if 'boundary' in impact_data:
        msg = ("Impact on boundary '{}'; {}").format(
            impact_data['boundary'],
            msg)

    return msg


def extract_impact_info(alert):
    """ Extract impact information from an alert

    Args:
        alert: alert in dict form that contains impact data

    Returns:
        dict containing impact data in the form of,
        {
            'bps',
            'pps',
            'impact_boundary' (depending on alert)
        }
    """

    # Pull impact information out of alert data
    attributes = alert['attributes']
    impact = {
        'bps': attributes['subobject']['impact_bps'],
        'pps': attributes['subobject']['impact_pps']
    }

    if 'impact_boundary' in attributes['subobject']:
        impact['boundary'] = attributes['subobject']['impact_boundary']

    return impact


def annotate(leader, key, alerts):
    """ Annotate a series of alerts from a given SP leader

    Each alert is annotated with its own impact data

    Args:
        leader: SP leader from which the alerts originated
        key: API key generated on the given SP leader
        alerts: list of impact data containing alerts to be annotated
    """

    print("Annotating {} ongoing alerts with impact data".format(
        len(alerts)))

    for alert in alerts:

        # Create the POST body for each annotation
        impact = extract_impact_info(alert)
        msg = create_annotation_msg(impact)
        post = {
            "data": {
                "attributes": {
                    "author": "API-Client",
                    "text": msg
                }
            }
        }

        # Create a unique URL for each annotation
        # Each one must reference the alert from which impact data
        # is being retreived
        ALERT_URI = ("/api/sp/alerts/{}/annotations/").format(
            alert['id'])
        URL = "https://" + leader + ALERT_URI

        # POST annotation
        api_response = api_request(
            URL, key, json.dumps(post))

        # Handle any API response
        if api_response:
            print("Alert {} annotated".format(
                alert['id']))
        else:
            print("Could not annotate Alert {}".format(
                alert['id']),
                file=sys.stderr)


#####################
# Start the Program #
#####################


def main():
    SP_LEADER = 'leader.example.com'
    API_KEY = 'okw_TF2PLL20ojZ1ptzazGh6TPS0C2MlqpO3LDzv'

    print('Starting auto-annotation script')
    alerts = get_alerts(SP_LEADER, API_KEY)
    if alerts:
        print('Alerts retrieved. Auto-annotating impact data')
        annotate(SP_LEADER, API_KEY, alerts)

    print('Done')

if __name__ == "__main__":
    main()
