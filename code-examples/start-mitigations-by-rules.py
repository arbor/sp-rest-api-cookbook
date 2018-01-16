from __future__ import print_function
from datetime import datetime, timedelta
from sys import stderr
import requests
import json
import urllib

CERT_FILE = './certfile'


def api_request(URL, key, body=None):
    """Define a function for making API GET
    Requests If body is supplied,
    request type will be POST

    """

    api_response = None
    if body is None:
	api_response = requests.get(
	    URL,
	    headers={'X-Arbux-APIToken':
		     key,
		     'Content-Type':
		     'application/vnd.api+json'},
	    verify=CERT_FILE)
    else:
	api_response = requests.post(
	    URL,
	    data=body,
	    headers={'X-Arbux-APIToken':
		     key,
		     'Content-Type':
		     'application/vnd.api+json'},
	    verify=CERT_FILE)

    # Handle any API error responses
    if (api_response.status_code < requests.codes.ok or
	    api_response.status_code >= requests.codes.multiple_choices):
	print("API responded with this error: \n{}"
	      .format(
		  api_response.text),
	      file=stderr)

	return []

    # Convert the response to JSON and return it
    api_response = api_response.json()
    return api_response['data']


def get_alerts(leader, key, period):
    """Define a function for retrieving
    alerts from an SP Leader

    """

    timefmt = '%a %b %d %H:%M:%S %Y'
    time = period.strftime(timefmt)
    iso_time = period.isoformat()

    print("Fetching alerts from {} onwards"
	  .format(time))

    # Craft the URL components, filtering
    # based on time period

    ALERT_URI = "/api/sp/alerts/?filter="
    FILTER = "/data/attributes/start_time > " + iso_time

    # Percent-encode our filter query and combine URL components
    FILTER = urllib.quote(FILTER, safe='')
    URL = "https://" + leader + ALERT_URI + FILTER

    # Make the api request and return its results
    api_response = api_request(URL, key)
    return api_response


def apply_rules(alerts):
    """Define a function for filtering
    alerts based on rules

    """

    filtered_alerts = []

    # Return alerts that match the following rules:
    # Importance = High, Ongoing = True, Alert Type = DOS
    for alert in alerts:
	attributes = alert['attributes']
	if (attributes['importance'] == 2 and
		attributes['ongoing'] is True and
		attributes['alert_type'] == 'dos_host_detection'):
	    filtered_alerts.append(alert)

    print("{} alert(s) match mitigation criterion"
	  .format(len(filtered_alerts)))
    return filtered_alerts


def extract_mitigation_attr(alert):
    """Define a function for extracting
    mitigation attributes from alerts

    """

    # Configure mitigation information for the current alert
    name = "Alert {} Auto-API-Mitigation".format(
	alert['id'])
    description = "Mitigation triggered by script via REST API"
    ongoing = True
    ip_version = alert['attributes']['subobject']['ip_version']
    protection_cidr = '/32'
    if ip_version == 6:
	protection_cidr = '/128'
    subobject = {
	'bgp_announce': False,
	'protection_prefixes':
	    [alert['attributes']['subobject']['host_address'] +
	     protection_cidr]
    }
    subtype = 'tms'
    attributes = {
	"name": name,
	"description": description,
	"ongoing": ongoing,
	"ip_version": ip_version,
	"subobject": subobject,
	"subtype": subtype
    }

    return attributes


def mitigate(leader, key, alerts):
    """Define a function for mitigating alerts"""

    mitigations = []
    # Create a POST body for each mitigation to make
    for alert in alerts:
	attributes = extract_mitigation_attr(alert)
	post = {
	    "data": {
		"attributes": attributes,
		"alert": {
		    "data": {
			"id": alert['id'],
			"type": "alert"
		    }
		},
		"relationships": {
		    "tms_group": {
			"data": {
			    "id": "3",
			    "type": "tms_group"
			}
		    }
		}
	    }
	}
	mitigations.append(post)

    MIT_URI = '/api/sp/mitigations/'
    URL = "https://" + leader + MIT_URI
    # POST mitigations for each POST body created
    for mitigation in mitigations:
	api_response = api_request(URL,
				   key,
				   json.dumps(mitigation))

	# Handle any API responses
	if len(api_response) > 0:
	    print("{} started"
		  .format(mitigation['data']['attributes']['name']))
	else:
	    print("Could not start mitigation: {}"
		  .format(mitigation['data']['attributes']['name']))

###################
# Start the program #
###################
SP_LEADER = 'leader.example.com
API_KEY = 'viZqKYlEPKSWSpvzftr3Bs8Lqu_7u7_l8yiwxaD9'

TIMEFRAME = datetime.now() - timedelta(minutes=15)

print("Starting auto-mitigation script")
alerts = get_alerts(SP_LEADER, API_KEY, TIMEFRAME)
if len(alerts) > 0:
    print("Alerts retrieved. Filtering on configured ruleset")
    target_alerts = apply_rules(alerts)

    if len(target_alerts) > 0:
	print("Mitigating alerts")
	mitigate(SP_LEADER, API_KEY, target_alerts)
	print("Done")
else:
    print("No alerts were found in the requested period")
