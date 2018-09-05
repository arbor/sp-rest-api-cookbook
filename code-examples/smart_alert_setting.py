from __future__ import print_function
import json
import requests
from sys import stderr

CERT_FILE = "./certfile"

SMART_ALERT_SETTING_BODY = {
    "data": {
        "attributes": {
            "name": "example",
            "unit": "bps",
            "calculation": "pct95",
            "view": "network",
            "filters": [
                {
                    "facet": "View",
                    "operator": "=",
                    "values": [],
                    "parameters": {
                    }
                },
                {
                    "facet": "Protocol",
                    "operator": "=",
                    "hidden": True,
                    "values": [],
                    "parameters": {
                    }
                }
            ],
            "thresholds": {
                "medium": 239
            },
            "alert_view": {
                "calculation": "average",
                "y_axis_scale": "relative",
                "tab_view": "Relationships",
                "unit": "pps",
                "threshold": 1111,
                "graph_type": "line",
                "top_contributors": [
                    "Profile"
                ],
                "view": "peer",
                "filters": [
                    {
                        "facet": "Destination IPv4 Address",
                        "operator": "=",
                        "hidden": False,
                        "values": [
                            "::"
                        ],
                        "parameters": {
                            "output_mask_length": 24
                        }
                    }
                ]
            }
        }
    }
}


def post_smart_alert_setting(leader, key):
    """POST a smart alert to given leader with given API key.

    Args:
        leader(string): box to use to create the smart alert setting
        key(string): an API token granting permission to POST a smart alert on
            the given leader.

    Returns:
        string: id of created smart_alert_setting
    """
    # build the URL
    URL = 'https://{leader}/api/sp/smart_alert_settings/'.format(
        leader=leader)

    # make the API request
    api_response = requests.post(
        URL,
        data=json.dumps(SMART_ALERT_SETTING_BODY),
        headers={
            'X-Arbux-APIToken': key,
            'Content-Type': 'application/vnd.api+json'
        },
        verify=CERT_FILE)

    # check the API response
    if api_response.status_code != requests.codes.created:
        print("[POST ERROR] API responded with this error: "
              "{}\n(url: {})".
              format(api_response.reason, URL),
              file=stderr)
        return []

    # convert the response to JSON and
    # get the 'data' element
    api_response = api_response.json()
    data = api_response['data']

    return data.get('id', None)


def get_triggered_smart_alerts(leader, key, smart_alert_setting_id,
                               triggered_smart_alerts=[], page=1):
    """Get the smart alert triggered with the given smart alert setting id

    This is in this example to show that the smart alert setting was created
        with the correct attributes.

    Args:
        leader(string): box to use to create the smart alert setting
        key(string): an API token granting permission to POST a smart alert on
            the given leader.
        smart_alert_setting_id(string): id of the smart alert setting to get
        triggered_smart_alerts(list(string)): ids of smart alerts triggered by
            the given smart alert setting
        page(int): current page of alerts

    Returns:
        list(string): the ids of the triggered alerts
    """
    # Python quirk
    if triggered_smart_alerts is None:
        triggered_smart_alerts = []

    # build the URL, filtering on only smart alerts (of type smart_thresh)
    URL = ('https://{leader}/api/sp/alerts/?'
           'filter=/data/attributes/alert_type=smart_thresh&'
           'page={page}').format(
        leader=leader,
        resource=smart_alert_setting_id,
        page=page)

    # make the API request
    api_response = requests.get(
        URL,
        headers={
            'X-Arbux-APIToken': key
        },
        verify=CERT_FILE)

    # check the API response code
    if api_response.status_code != requests.codes.ok:
        print("[GET ERROR] API responded with this error: "
              "{}\n(url: {})".
              format(api_response.reason, URL),
              file=stderr)
        return None

    # convert the response to JSON and get the 'data' element
    api_response = api_response.json()
    data = api_response['data']
    if data == []:
        # No more results
        return triggered_smart_alerts

    for resource in data:
        if ('relationships' in resource and
                'smart_alert_setting' in resource['relationships']):
            id_ = (resource['relationships']
                   ['smart_alert_setting']['data']['id'])
            if id_ == smart_alert_setting_id:
                triggered_smart_alerts.append(resource['id'])

    # iterate over pages of alerts to find the triggered alert with the given
    # smart alert setting
    page += 1
    return get_triggered_smart_alerts(
        leader, key, smart_alert_setting_id, triggered_smart_alerts, page)


if __name__ == '__main__':
    #
    # set the SP leader hostname and API key
    #
    SP_LEADER = 'leader.example.com'
    API_KEY = 'eFvokphdyGHA_M4oLlLtfDnlIf9bpjFnn0mWlDqw'

    #
    # Create a smart_alert_setting
    #
    smart_alert_setting_id = post_smart_alert_setting(
        SP_LEADER, API_KEY)

    #
    # GET the triggered smart alert
    # NOTE: There would normally be a time delay between the creation of the
    # smart_alert_setting and the smart alert. For the purposes of this example
    # we assume that the time has passed and that the traffic has met the
    # required settings, such that a smart alert is actually triggered.
    #
    smart_alert_ids = get_triggered_smart_alerts(
        SP_LEADER, API_KEY, smart_alert_setting_id)

    print("Created Smart Alert Setting: {}.".format(smart_alert_setting_id))
    if smart_alert_ids:
        print("Triggered Smart Alerts: {}.".format(", ".join(smart_alert_ids)))
    else:
        print("No triggered smart alerts.")
