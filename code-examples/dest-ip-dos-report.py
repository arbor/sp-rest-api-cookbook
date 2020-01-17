#!/usr/bin/env python3

import json
import logging
import requests
import sys
from os import environ


class DoSHostAlerts:
    """A class that loads DoS Host Alerts

    It exposes one variable, `victim_ips` that is a json list of victim
    IPs plus some other alert details

    This is also an example of using the `include` URL parameter and
    caching data

    What you do with it next is sort of up to you
    """

    def __init__(self, api_host, token, alerts_to_load=25, perPage=25):
        self.api_host = api_host
        self.api_token = token
        self.per_page = perPage
        self.alerts_to_load = alerts_to_load
        self.results = []
        self.included_cache = {}
        self.victim_ips = {}
        self.url = f"https://{self.api_host}/api/sp/alerts/"
        self.url_params = {
            "filter": "/data/attributes/alert_type=dos_host_detection",
            "perPage": self.per_page,
            "include": "traffic.dest_prefixes",
        }

    def _get_victim_ips(self):
        """assemble victim IP data; return a json list

        This uses the cache from the `include` URL parameter to get the
        related traffic/dest_prefixes information
        """
        victim_ips = []
        for alert in self.results:
            dest_ip = []
            # This is the top-level alert information
            id_ = alert["id"]
            start = alert["attributes"]["start_time"]
            if alert["attributes"]["ongoing"]:
                end = ""
            else:
                end = alert["attributes"]["stop_time"]

            # it's just shorted to type `traffic_cache`
            cache_key = (
                alert["relationships"]["traffic"]["data"]["type"],
                alert["relationships"]["traffic"]["data"]["id"],
            )
            if cache_key in self.included_cache:
                traffic_cache = self.included_cache[cache_key]
                # This traverses the "traffic" relationship to the "dest_prefixes"
                # relationship and builds a list of destination prefixes (aka
                # attacked prefixes) out of the cached data that came back from the
                # one API call with the `include` parameter
                if "traffic" in alert["relationships"]:
                    if "dest_prefixes" in traffic_cache["relationships"]:
                        dest_prefs = traffic_cache["relationships"]["dest_prefixes"]
                        # I think it's *always* a list, but just in case...
                        if isinstance(dest_prefs["data"], list):
                            for dest_pref in dest_prefs["data"]:
                                key = tuple([dest_pref["type"], dest_pref["id"]])
                                if key in self.included_cache:
                                    dest_ip.append(
                                        self.included_cache[key]["attributes"]["view"][
                                            "network"
                                        ]["unit"]["bps"]["name"]
                                    )
                        else:
                            key = tuple(
                                dest_prefs["data"]["type"], dest_prefs["data"]["id"]
                            )
                            if key in self.included_cache:
                                dest_ip.append(
                                    self.included_cache[key]["attributes"]["view"][
                                        "network"
                                    ]["unit"]["bps"]["name"]
                                )

            victim_ips.append(
                {"id": id_, "start": start, "end": end, "dest_ips": dest_ip,}
            )

        return victim_ips

    def _populate_cache(self, included):
        """Store the `"included"` block by type/id tuple"""
        cache = {}
        for detail in included:
            if "type" in detail and "id" in detail:
                type_ = detail["type"]
                id_ = detail["id"]
                cache[(type_, id_)] = detail

        return cache

    def load(self):
        """Load the alerts, populate the cache, find the victim_ips

        This really should just load the alerts and populate the cache,
        probably, but I don't know how to populate a variable when it is
        referenced.

        Also, we scrap alerts that are on the last page but beyond the
        limit set in `alerts_to_load`

        This returns the number of alerts loaded
        """
        headers = {"X-Arbux-APIToken": self.api_token}
        try:
            self.r = requests.get(self.url, params=self.url_params, headers=headers)
        except requests.exceptions.ConnectionError as e:
            log.fatal(f"Connection failed; Attempted URL was: {self.url}")
            sys.exit(1)
        self.r = self.r.json()
        self.results += self.r["data"]
        if "next" in self.r["links"] and len(self.results) < self.alerts_to_load:
            logging.debug("loading next page of results")
            self.url = self.r["links"]["next"]
            self.url_params = {}
            self.load()

        self.results = self.results[: self.alerts_to_load]

        self.included_cache.update(self._populate_cache(self.r["included"]))

        self.victim_ips = self._get_victim_ips()

        return len(self.results)


if __name__ == "__main__":

    # useful logging levels are:
    #  - DEBUG :  print debugging information
    #  - INFO  :  don't print too much
    #  - WARN  :  only print critical errors and the results
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    SIGHTLINE_HOST = "my-sp-leader.example.com"
    NUMBER_OF_ALERTS = 15
    ALERTS_PER_PAGE = 10
    logging.debug(
        f"Loading {NUMBER_OF_ALERTS} alerts {ALERTS_PER_PAGE} alerts at a time."
    )
    if "SIGHTLINE_HOST" in environ:
        SIGHTLINE_HOST = environ["SIGHTLINE_HOST"]
    if "API_TOKEN" in environ:
        API_TOKEN = environ["API_TOKEN"]
    else:
        logging.fatal(
            'Please set the environment variable "API_TOKEN" to your SP REST API Token'
        )
        sys.exit(1)

    dos_host_alerts = DoSHostAlerts(
        SIGHTLINE_HOST, API_TOKEN, NUMBER_OF_ALERTS, ALERTS_PER_PAGE
    )
    num_alerts = dos_host_alerts.load()
    logging.info(f"Loaded {num_alerts} alerts")
    logging.info("Victim IPs:")
    print("{}".format(json.dumps(dos_host_alerts.victim_ips, indent=4)))
