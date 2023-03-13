"""Example SP API script to retrieve and summarize device system alerts."""
from __future__ import print_function
import arrow           # version: 1.2.3
import sys
import re
import requests        # version: 2.28.1
import urllib.parse    # version: 1.26.13
import slenv

CERT_FILE = "./certfile"


def get_page_from_link(link):
    """Extract a page number from an API link."""
    match = re.search(r'page=(\d+)', link)
    return int(match.group(1)) if match else None


def api_request(url, key, body=None):
    """General function for making GET and POST requests.

    Response codes falling within 'requests.codes.ok' are assumed
    to have completed successfully. Supplying the optional 'body'
    parameter will change the request type to POST.

    Args:
        url (str): Valid URL to make request to.
        key (str): API key generated on the given SP leader.
        body (str): JSON formatted string containing
            post body content.

    Returns:
        dict: 'data' keyvalue of a requests.Response object.
        dict: 'meta' keyvalue of a requests.Response object.
        dict: 'links' keyvalue of a requests.Response object.
    """
    headers = {'X-Arbux-APIToken': key,
               'Content-Type': 'application/vnd.api+json'}
    if body is None:
        api_response = requests.get(
            url,
            headers=headers,
            verify=CERT_FILE)
    else:
        api_response = requests.post(
            url,
            data=body,
            headers=headers,
            verify=CERT_FILE)

    # Handle any API error responses.
    if (api_response.status_code != requests.codes.ok):
        print("API responded with this error: \n{}".format(
            api_response.text),
            file=sys.stderr)
        return ([], {}, {})

    # Convert the response to JSON and return it
    api_response = api_response.json()
    return (api_response['data'], api_response['meta'], api_response['links'])


def get_alerts(leader, key, start_time):
    """Retrieve alerts from an SP leader.

    Args:
        leader (str): SP leader from which the alerts originated
        key (str): API key generated on the given SP leader
        start_time (obj): arrow time object to be used
            a start_time filter for alerts.

    Returns:
        list: Alerts from the SP leader.
    """
    alerts = list()

    # Retrieve the first page of data.
    (first_page, meta, links) = get_alerts_page(leader, key, start_time, 1)
    alerts.extend(first_page)

    # Retrieve first and last page numbers from the returned links.
    last_page_number = get_page_from_link(links["last"])
    current_page_number = get_page_from_link(links["self"])

    # Get all remaining pages, add the data
    while (current_page_number != last_page_number):
        current_page_number = current_page_number + 1
        (current_page, meta, links) = get_alerts_page(leader, key,
                                                      start_time,
                                                      current_page_number)
        alerts.extend(current_page)

    return alerts


def get_alerts_page(leader, key, start_time, page=1):
    """Retrieve a specific page of alerts from an SP leader.

    Args:
        leader (str): SP leader from which the alerts originated
        key (str): API key generated on the given SP leader
        start_time (obj): arrow time object to be used
            a start_time filter for alerts.
        page (int): The specific page of alerts to request.

    Returns:
        list: A specific page of alerts from the leader.
    """
    # Craft the URL components. Filter on alert class and starting time.
    alert_uri = '/api/sp/alerts/'
    filter_value = ("/data/attributes/alert_class = system AND "
                    "/data/attributes/start_time > {0}".format(
                        start_time.format('YYYY-MM-DD:HH:mm:ss')))

    # Percent-encode our filter query.
    filter_value = urllib.parse.quote(filter_value, safe='')

    # Add the parameters to the request url.
    params = list()
    filter_param = "filter={0}".format(filter_value)
    page_param = "page={0}".format(page)
    params = [filter_param, page_param]

    url = "https://{0}{1}?{2}".format(leader, alert_uri, "&".join(params))

    # Make the api request and return its results.
    return api_request(url, key)


def get_devices(leader, key):
    """Retrieve devices from an SP leader.

    Args:
        leader (str): SP leader to retrieve devices from.
        key (str): API key generated on the given SP leader

    Returns:
        list: Device data from the leader.
    """
    device_uri = '/api/sp/devices/'

    url = "https://{0}{1}".format(leader, device_uri)

    # Make the api request and return its results.
    (devices, meta, links) = api_request(url, key)
    return devices


def main():
    """Print a list of devices sorted by system alert count."""
    SP_LEADER = slenv.leader
    API_KEY = slenv.apitoken

    # Create a start date one week before the current time.
    arrow_now = arrow.utcnow()
    start_time = arrow_now.shift(weeks=-1)

    # Get a list of all the system alerts starting later than
    # one week ago.
    alerts = get_alerts(SP_LEADER, API_KEY, start_time)

    # Get a list of all devices on the leader.
    devices = get_devices(SP_LEADER, API_KEY)

    # Transform the list into a dictionary keyed by device id.
    device_dict = {device["id"]: device["attributes"] for device in devices}

    # Create a dict keyed by device id containing a count
    # of system errors associated with that device.
    # We will use this data when displaying our list of collectors.
    alert_counts = {}
    for alert in alerts:
        try:
            device_id = alert["relationships"]["device"]["data"]["id"]
        except KeyError:
            continue

        alert_counts[device_id] = (
            alert_counts[device_id] + 1 if device_id in alert_counts else 1)

    # Transform the dict into list of dicts containing id
    # and alert_count for each device.
    alert_count_list = [{"id": key, "alert_count": value}
                        for key, value in alert_counts.items()]

    # Sort the list in decending order by alert count.
    alert_count_list.sort(reverse=True, key=lambda k : k['alert_count'])

    # Display a report of collectors sorted by the number of system alerts
    # found on each collector.
    header_format_string = (
        "==== {alert_count:=<24} {name:=<20} "
        "{device_type:=<20} {ip_address:=<20}")

    # Display a header.
    print(header_format_string.format(alert_count="System Alert Count ",
                                      name="Device Name ",
                                      device_type="Device Type ",
                                      ip_address="IP Address "))

    format_string = (
        "     {alert_count:<24} {name:20} "
        "{device_type:20} {ip_address:20}")

    # Display a row for each device with alerts.
    for device in alert_count_list:
        # Roll in our previously retrieved device data.
        device.update(device_dict[device["id"]])
        print(format_string.format(**device))

if __name__ == "__main__":
    main()
