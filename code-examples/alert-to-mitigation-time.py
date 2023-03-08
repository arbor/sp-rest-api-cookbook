from __future__ import print_function
import requests
from datetime import datetime, timedelta
from sys import stderr
from time import mktime, strptime
import urllib.parse
from urllib.parse import urlparse, parse_qs
import slenv


CERT_FILE = "./certfile"
TIMEFMT = "%a %b %d %H:%M:%S %Y"


def get_mitigations(leader, key, start,
		    end, page=1, perPage=50):
    """Recursively get pages of mitigations until
    the start date is reached or the last page is
    reached

    """

    # set up the query string keys and values
    qs = dict()
    if page:
        qs['page'] = page
    if perPage:
        qs['perPage'] = perPage

    # build the URL
    MITIGATION_URI = '/api/sp/mitigations/?'
    URL = "https://" + leader + MITIGATION_URI
    URL += urllib.parse.urlencode(qs)

    # make the API request
    api_response = requests.get(
		URL,
		headers={'X-Arbux-APIToken':
			key},
		verify=CERT_FILE)

    # check the API response
    if api_response.status_code != requests.codes.ok:
        print("[ERROR] API responded with this error: "
			"{}\n(url: {})".
			format(api_response.reason, URL),
			file=stderr)
        return []

    # convert the response to JSON and
    # get the 'data' element
    api_response = api_response.json()
    data = api_response['data']

    # check if we're done or if we need
    # to call ourselves again
    specified_start = string_to_date(start)
    oldest_mit_on_this_page = None
    if 'start' in data[-1]['attributes']:
        oldest_mit_on_this_page = data[-1]['attributes']['start']
        oldest_mit_on_this_page = string_to_date(
			oldest_mit_on_this_page)

    if (oldest_mit_on_this_page is None
		or oldest_mit_on_this_page > specified_start):
		#
		# parse out the last page from the links section
		#
        last_page = None
        if ('links' in api_response and
			'last' in api_response['links']):
            last_page = int(
				parse_qs(
					urlparse(
						api_response['links']['last']).query
				)['page'][0]
			)
        if last_page is not None and page < last_page:
            page += 1
			# call ourselves again to get the next page
            d = get_mitigations(leader, key, start, end, page)
            data += d

    return data


def get_alerts_from_mits(mits):
    """Not all mitigations have alerts, those
    will just be skipped, otherwise the alerts
    will be retrieved and a dictionary with
    mitigation information and alert start
    time will be populated and returned

    """
    alerts = {}

    for mit in mits:
        if 'relationships' not in mit or 'alert' not in mit['relationships']:
            continue  # there is no alert related to this mitigation
        if 'start' not in mit['attributes']:
            continue  # mitigation was created but never started
        alert_id = mit[
            'relationships']['alert']['data']['id']
        if alert_id not in alerts:
            alerts[alert_id] = {}
            mit_start_time = string_to_date(
        		mit['attributes']['start'])

            alerts[alert_id][
        		'mit_start_time'] = mit_start_time
            alerts[alert_id][
        		'mit_type'] = mit['attributes']['subtype']
            if 'user' in mit['attributes']:
                alerts[alert_id][
                    'started_by'] = mit['attributes']['user']
            else:
                alerts[alert_id][
                    'started_by'] = "null"

    return alerts


def print_report(alerts, mitigations, sp_leader, start, end):
    """ print a simplistic report with a table of alerts """

    print ("The time range for the report is")
    print ("                 from:",
		   start.strftime(TIMEFMT))
    print ("                   to:",
		   end.strftime(TIMEFMT))

    print ("Out of {} mitigations on {}, "
		   "{} have associated alerts".
		   format(
				len(mitigations),
				sp_leader,
				len(alerts.keys())
		   ))

    # re-organize alerts for printing
    by_user_type_time = {}
    for alert in alerts:
        started_by = alerts[alert]['started_by']
        mit_type = alerts[alert]['mit_type']
        a_to_m_secs = alerts[alert]['alert_to_mit_seconds']
        if started_by not in by_user_type_time:
            by_user_type_time[started_by] = {}
        if mit_type not in by_user_type_time[started_by]:
            by_user_type_time[started_by][mit_type] = {}
        if a_to_m_secs not in by_user_type_time[started_by][mit_type]:
            by_user_type_time[started_by][mit_type][a_to_m_secs] = []

        by_user_type_time[started_by][mit_type][a_to_m_secs].append(alert)

    # print the header row
    print ("{0:>20} | {1:<10} | {2:11} | {3}".format(
		"Mit. Started By",
		"Mit. Type",
		"Secs to Mit",
		"Alert Ids")
    )
    print ("{0:>20} | {1:<10} | {2:11} | {3}".format(
		"-"*20,
		"-"*10,
		"-"*11,
		"-"*18)
    )
    # Step through the re-organized data and print it
    for started_by in sorted(by_user_type_time):
        tmp_user = started_by
        for mit_type in sorted(by_user_type_time[started_by]):
            tmp_mit_type = mit_type
            for a_to_m_secs in sorted(
            		by_user_type_time[started_by][mit_type]):
                print ("{0:>20} | {1:<10} | {2:11} | {3}".
						format(
							tmp_user,
							tmp_mit_type,
							a_to_m_secs,
							", ".join(by_user_type_time[
								started_by][
									mit_type][
										a_to_m_secs])))
                tmp_mit_type = ''
                tmp_user = ''


def get_alert_start_time(leader, key, alert):
    """Get an individual alert via the API and return its start time in
    python datetime format

    """

    ALERT_URI = '/api/sp/alerts/'
    URL = "https://" + leader + ALERT_URI + alert

    api_response = requests.get(
		URL,
		headers={'X-Arbux-APIToken':
				key},
		verify=CERT_FILE)

    if api_response.status_code != requests.codes.ok:
        print("[WARNING] In retrieving information "
              "about alert {}, the API responded `{}'".
              format(api_response.reason, alert),
              file=stderr)
        return None

    api_response = api_response.json()

    alert_start_time = string_to_date(
		api_response['data']['attributes']['start_time'])

    return alert_start_time


def string_to_date(date_string):
    """Convert a string in the format YYYY-MM-DDThh:mm:ss to a Python
    datetime format

    """

    if type(date_string) is datetime:
        return date_string
    # drop the time offset; if you are using different time zones,
    # don't do this
    date_string = date_string.split('+')[0]
    date_string = date_string.split('.')[0]
    # convert the time string into a Python datetime object
    date_string = strptime(date_string,
						   "%Y-%m-%dT%H:%M:%S")
    date_string = datetime.fromtimestamp(
		mktime(date_string)
    )
    return date_string


if __name__ == '__main__':
    #
    # Set the start time to two weeks ago
    # and the end time to now
    #
    END_TIME = datetime.now()
    START_TIME = END_TIME + timedelta(-14)

    #
    # set the SP leader hostname and API key
    #
    SP_LEADER = slenv.leader
    API_KEY = slenv.apitoken

    mitigations = get_mitigations(SP_LEADER, API_KEY,
				  START_TIME, END_TIME)
    if not mitigations:
        exit

    #
    # Create a dictionary of alert IDs that contains mitigation start
    # time and (later) the alert start time, the JSON of which would
    # look like:
    #   { "<alert_id>":
    #      { "mit_start_time": "<mitigation_start_time>",
    #        "alert_start_time": "<alert_start_time>",
    #        "mit_type": "{tms,blackhole,flowspec}"
    #      }
    #   }
    #
    alerts = get_alerts_from_mits(mitigations)

    alerts_to_remove = list()

    for alert in alerts:
		# Get the alert start time for each alert that appears in a
		# mitigation
        alerts[alert]['alert_start_time'] = get_alert_start_time(
			SP_LEADER,
			API_KEY,
			alert
		)
        alert_start_time = alerts[alert]['alert_start_time']
        if not alert_start_time:
            alerts[alert]['alert_to_mit_seconds'] = 'n/a'
            continue
        alert_start_time = string_to_date(alert_start_time)
        if alert_start_time < START_TIME or alert_start_time > END_TIME:
            alerts_to_remove.append(alert)
            # alerts[alert]['alert_to_mit_seconds'] = 'n/a'
            continue
        # Get the different in seconds between the
        # alert start and the mitigation start
        alerts[alert]['alert_to_mit_seconds'] = (
        	alerts[alert]['mit_start_time'] -
        	alerts[alert]['alert_start_time']
        ).total_seconds()

    # delete alerts from the list that are outside of the specific
    # time; this is needed because the mitigations come back in pages,
    # not necessarily scoped to the specified time frame
    for alert in alerts_to_remove:
        del alerts[alert]

    print_report(alerts,
				 mitigations,
				 SP_LEADER,
				 START_TIME,
				 END_TIME)
