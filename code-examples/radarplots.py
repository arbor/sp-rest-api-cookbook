#!/usr/bin/env python
"""An example program that collects data on alerts and plots radar (or
spider) plots with that data

This makes use of the expanded alert data that was added in SP 8.4 APIv4

"""
from __future__ import print_function
import requests
import sys
import matplotlib.pyplot as plt
import pandas as pd
from math import pi, ceil
import slenv

LEADER = slenv.leader
APITOKEN = slenv.apitoken
PER_PAGE = 12
ONGOING = True
INCLUDE = ['source_ip_addresses']
FILTER = 'filter=/data/attributes/alert_class=dos'
RADAR_FIELDS = ['impact_bps', 'impact_pps', 'severity_percent',
                'misuse_types', 'source_ips']


def get_alerts(leader, apitoken, per_page, ongoing, include):
    """Return alerts and included data

    Fetch `per_page` alerts via the API provided by `leader` using
    `apitoken`.  If `ongoing` is true, only get ongoing alerts.  If
    there are elements in the `include` list, include those in the
    output making use of the `include` URL parameter to retrieve that
    data in one HTTP GET request
    """

    url = 'https://{}/api/sp/alerts/?perPage={}&{}'.format(
        leader, per_page, FILTER
    )
    if ONGOING:
        url += 'AND /data/attributes/ongoing=True'
    if include:
        url += '&include={}'.format(",".join(include))

    results = requests.get(
        url,
        headers={
            "X-Arbux-APIToken": apitoken,
            "Content-Type": "application/vnd.api+json"
        },
        verify=False
    )

    if results.status_code != requests.codes.ok:
        print ("Results: {} ({})".format(
            results.reason,
            results.status_code), file=sys.stderr)
        return None

    return (results.json())


def make_included_dictionary(alerts):
    """reorganize the data included with the alert

    extract the data from included into a dict of dicts that looks
    like:

        alert_1:
            included_field_1: list
            included_field_2: list
        alert_2:
            included_field_1: list
            included_field_2: list

    this is one recommended way of using `include`d data: put it into a
    dictionary by alert ID so later it can be easily related to the
    alert
    """
    included = dict()
    for alert in alerts['included']:
        id = alert['relationships']['parent']['data']['id']
        included[id] = dict()
        for type in alert['attributes']:
            included[id][type] = alert['attributes'][type]

    return included


def make_spiders(df):
    """Take a dataframe, produce a file called plot.pdf

    Use the data in the dataframe and turn it into an array of radar
    plots and write it to a file; with much thanks to
    https://python-graph-gallery.com/392-use-faceting-for-radar-chart/
    """
    max_cols = 3
    my_dpi = 96
    plt.figure(figsize=(1000/my_dpi, 1200/my_dpi), dpi=my_dpi)
    plt.subplots_adjust(left=0.125, bottom=0.1, right=0.9,
                        top=0.9, wspace=0.6, hspace=0.2)
    my_palette = plt.cm.get_cmap("Set2", len(list(df)))

    # number of variable
    categories = df.index
    N = len(categories)
    rows = ceil(float(len(list(df))) / max_cols)
    # print ("N: {}; rows: {}".format(N, rows))

    # What will be the angle of each axis in the plot? (we divide the
    # plot / number of variable)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # loop starts here, probably
    row = 0
    for axkey in [str(m) for m in sorted([int(n) for n in df.keys()],
                                         reverse=True)]:
        # print ("{}: {}".format(
        #     axkey, df[axkey].values.flatten().tolist()))

        # Initialise the spider plot
        ax = plt.subplot(rows, max_cols, row+1, polar=True, )

        # If you want the first axis to be on top:
        ax.set_theta_offset(pi / 2)
        ax.set_theta_direction(-1)

        # Draw one axe per variable + add labels labels yet
        plt.xticks(angles[:-1], categories, color='grey', size=8)

        # Draw ylabels
        ax.set_rlabel_position(0)
        plt.yticks([20, 40, 60, 80, 100],
                   ["20", "40", "60", "80", "100"],
                   color="grey", size=7)
        plt.ylim(0, 100)

        # Ind1
        # values = df.loc[row].drop('group').values.flatten().tolist()
        values = df[axkey].values.flatten().tolist()
        values += values[:1]
        ax.plot(angles, values, color=my_palette(row),
                linewidth=2, linestyle='solid')
        ax.fill(angles, values, color=my_palette(row), alpha=0.4)

        # Add a title
        title = "Alert {}".format(axkey)
        plt.title(title, size=11, color=my_palette(row), y=1.1)

        row += 1

    plt.savefig('radar.pdf')


def get_radar_fractions(data):
    """ normalize data across the alert properties
    """
    maxval = dict()
    for alert_id in data:
        for key in data[alert_id].keys():
            if key not in maxval or data[alert_id][key] > maxval[key]:
                maxval[key] = data[alert_id][key]

    frac_data = dict()
    for alert_id in data:
        frac_data[alert_id] = dict()
        for key in data[alert_id].keys():
            frac_data[alert_id][key] = (float(data[alert_id][key]) /
                                        maxval[key]) * 100.
    return frac_data


def get_radar_data(alerts, fields):
    """given a list of alerts from the API and a list of fields extract
    the data from each field of each alert and put it into a
    dictionary with two sub-keys for each field: one with the raw
    value and one with the value relative to all of the others in the
    list

    """

    data = dict()

    included = make_included_dictionary(alerts)

    for alert in alerts['data']:
        alert_id = alert['id']
        data[alert_id] = dict()
        for field in fields:
            if field in alert['attributes']:
                data[alert_id][field] = alert['attributes'][field]
            elif field in alert['attributes']['subobject']:
                data[alert_id][field] = alert['attributes']['subobject'][field]
            elif alert_id in included and field in included[alert_id]:
                data[alert_id][field] = included[alert_id][field]
            else:
                data[alert_id][field] = 0
            # for alert attributes that are not values but are lists of things,
            # report the length of the list
            if type(data[alert_id][field]) is list:
                data[alert_id][field] = len(data[alert_id][field])

    return data


if __name__ == '__main__':

    print ("Retrieving alert data", file=sys.stderr)
    alerts = get_alerts(
        LEADER, APITOKEN, PER_PAGE, ONGOING, INCLUDE)

    if not alerts:
        print ("Did not retrieve any valid DoS "
               "alerts from most recent {} alerts".format(PER_PAGE),
               file=sys.stderr)
        sys.exit(0)

    print ("Processing radar data for {} alerts".format(
        len(alerts['data'])), file=sys.stderr)
    radar_data = get_radar_data(alerts, RADAR_FIELDS)

    radar_fractions = get_radar_fractions(radar_data)

    df = pd.DataFrame(radar_fractions)

    print ("Plotting radar data", file=sys.stderr)
    make_spiders(df)

    print ("Done")
