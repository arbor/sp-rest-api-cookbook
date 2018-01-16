from __future__ import print_function
from sys import stderr
import requests  # version 2.18.4
import arrow  # version 0.10.0
import datetime
import matplotlib  # version 2.0.2
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange

ALERT_ID = 870


def render_matplotlib_png(alert_router_id, points, start, end, step):
    """Render a graph PNG based on timeseries data using matplotlib.

    Args:
        alert_router_id: a alert_id-router_gid string
        points: timeseries traffic data points
        start: arrow object representing the start time of the alert
        end: arrow object reprsenting the end time of the alert
        step: the time period each entry in the timeseries data spans
    """
    # every day
    days = DayLocator()
    # every hour
    hours = HourLocator(interval=9)
    delta = datetime.timedelta(seconds=step)
    # calculate x axis points based on step and start time
    dates = drange(start, end, delta)

    # using AGG
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.plot_date(dates, points, '.-')
    ax.grid(True)
    ax.xaxis.set_major_locator(days)
    ax.xaxis.set_minor_locator(hours)
    ax.xaxis.set_major_formatter(DateFormatter('%a'))
    ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))
    ax.set_xlabel('time')
    ax.set_ylabel('bps')
    ax.set_title('Router Traffic - {}'.format(alert_router_id))
    fig.autofmt_xdate()
    fig.savefig('{}.png'.format(alert_router_id))


def api_get_request(url, api_key):
    """Build an API GET request.

    Args:
        url: a valid SP box url to make the request
        api_key: API token used to access and use the SP API

    Returns:
        Dict value for 'data' entry of JSON response
    """
    api_response = None
    api_response = requests.get(
            url,
            headers={
                'X-Arbux-APIToken': api_key,
                'Content-Type': 'application/vnd.api+json'
            },
            verify=False
        )

    # Handle API error responses
    if (api_response.status_code < requests.codes.ok or
            api_response.status_code >= requests.codes.multiple_choices):
        print("API responded with this error: \n{}".format(api_response.text),
              file=stderr)
        return []

    # Convert the response to JSON and return
    api_response = api_response.json()
    return api_response['data']


def get_alert_traffic_data_router(sp_leader, api_key, alert_id):
    """Get router interface Traffic for alert.

    Args:
        sp_leader: a valid SP box domain name
        api_key: API token used to access and use the SP API

    Returns:
        The API response
    """
    alert_uri = "/api/sp/alerts/{}/router_traffic/".format(alert_id)
    url = "https://" + sp_leader + alert_uri

    # Make API request and reutrn results
    api_response = api_get_request(url, api_key)
    return api_response


def graph_timeseries_data_per_router(router_traffic):
    """Grab appropriate data from API response then build graph.

    Args:
        router_traffic: the dict value for 'data' entry of JSON response
    """
    if not router_traffic:
        return

    for router in router_traffic:
        data = router['attributes']['view']['network']['unit']['bps']

        step = data['step']
        # Find the end time. Create arrow datetime objects for start and end.
        start_time = arrow.get(data['timeseries_start'])
        seconds_after = (step * len(data['timeseries']))
        start, end = start_time.span('second', count=seconds_after)

        # Build timeseries graph
        render_matplotlib_png(router['id'], data['timeseries'], start, end,
                              step)
    return


if __name__ == '__main__':
    sp_leader = 'leader.example.com'
    api_key = 'JskW5QLVUMkNn4ruVwXOM0hQdyXCtOwnpkOjOev4'
    print("Getting traffic data for alert {} ...".format(ALERT_ID))
    # get router traffic timeseries
    router_traffic = get_alert_traffic_data_router(sp_leader, api_key, ALERT_ID)
    print("Rendering graph PNGs...")
    graph_timeseries_data_per_router(router_traffic)
    print("Done.")
