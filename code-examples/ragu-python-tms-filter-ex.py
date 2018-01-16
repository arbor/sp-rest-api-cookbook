from __future__ import print_function
import sys
import getopt
import requests  # version: 2.18.4
import json  # version: 2.0.9

CERT_FILE = './https_active.crt'


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
        sys.exit(1)

    # Convert the response to JSON and return it
    api_response = api_response.json()
    return api_response['data']


def parse_blacklist(api_response):
    """ Parse a TMS filter list to extract drop prefixes

    Args:
        api_response: results from a 'GET' request on the desired
            TMS filter list

    Returns: List of string prefixes and unmodified tms filter list
        blacklist entries
    """

    attr = api_response['attributes']
    if attr['filter_type'] != 'black_white':
        print("""Designated tms_filter_list is not of type
            'black_white'\n Exiting.""")
        sys.exit(1)

    entries = attr['entries']
    prefixes = []
    new_entries = []
    for entry in entries:
        parts = entry.split(' ')
        # Split entry string into just prefix
        if (len(parts) == 3 and
                parts[0] == 'drop' and
                parts[1] == 'net'):
            prefixes.append(parts[2])
        else:
            # Store entries that shouldn't be modified
            new_entries.append(entry)

    return prefixes, new_entries


def merge_entries(entries, prefixes):
    """ Format prefixes into filter entries

    Args:
        entries: pre-existing non-prefix blacklist items
        prefixes: prefixes that have been acted on by the script

    Returns: list containing tms filter list formatted prefix
        blacklist
    """

    entries
    for prefix in prefixes:
        entries.append("drop net {}".format(prefix))

    return entries


def retrieve_filterlist(url, key):
    """ Retrieve a TMS filter list from an SP Leader

    Args:
        url: SP leader and TMS filter list to query
        key: API key generated on the given SP leader

    Returns: string formatted prefixes and list containing original
        tms filter list entries
    """

    print('Retrieving tms_filter_list')
    response = api_request(url, key)
    prefixes, entries = parse_blacklist(response)

    return prefixes, entries


def add_prefixes(new_prefixes):
    """ Add to the existing list of drop prefixes

    Args:
        new_prefixes: space delimited string containing
            drop prefixes

    Returns: Callback function that returns the current prefixes
        plus the new user entered prefixes
    """

    print('Adding prefixes to tms_filter_list')

    def add_to_blacklist(current_prefixes):
        # Concatenate the sets of prefixes, removing duplicates
        prefixes = set(new_prefixes.split(' ') + current_prefixes)
        prefixes = list(prefixes)

        return prefixes

    return add_to_blacklist


def remove_prefixes(target_prefixes):
    """ Remove from the existing list of drop prefixes

    Args:
        target_prefixes: space delimited string containing
            drop prefixes

    Returns: Callback function that returns the current prefixes
        minus the user entered target prefixes
    """

    print('Removing prefixes from tms_filter_list')

    def remove_from_blacklist(current_prefixes):
        # Remove target_prefixes from current_prefixes
        prefixes = list(set(current_prefixes) ^
                        set(target_prefixes.split(' ')))

        return prefixes

    return remove_from_blacklist


def replace_prefixes(new_prefixes):
    """ Replace the existing list of drop prefixes

    Args:
        new_prefixes: space delimited string containing
            drop prefixes

    Returns: Callback function that returns only the user entered
        prefixes, replacing the old prefixes if valid
    """

    print('Replacing prefixes in tms_filter_list')

    def replace_blacklist(current_prefixes):
        return new_prefixes.split(' ')

    return replace_blacklist


def view_prefixes(filter_list_id):
    """ View the existing list of drop prefixes

    Args:
        filter_list_id: ID of the tms filter list

    Returns: Callback function to print out prefixes
    """

    def view(prefixes):
        print(prefixes)

    print('Printing blacklisted prefixes of filter list {}'.format(
        filter_list_id))

    return view


def dispatch_actions(url, key, actions):
    """ Dispatch queued actions

    An action is a callback function describing the action
    that should be taken for each script argument. Every action will
    be preceded by retrieving a list of blacklisted prefixes from the
    sp leader. This list will be passed into whatever function is
    designated by the action.

    Lifecycle:
        Retrieve blacklisted prefixes as list -> pass into callback
        function -> (optional) format callback's returned prefixes
        into PATCHable JSON to the TMS filter list

    Args:
        leader: SP leader from which the appliances exist
        key: API key generated on the given SP leader
        actions: list of actions to be performed sequentially
    """
    for action in actions:

        # Retrieve tms filter list's blacklisted prefixes
        prefixes, entries = retrieve_filterlist(url, key)
        # Pass prefixes into action callback
        new_prefixes = action(prefixes)

        # PATCH action results if any are generated
        if new_prefixes is not None:
            # Modify the original entries to reflect changes
            new_entries = merge_entries(entries, new_prefixes)
            body = {
                "data": {
                    "attributes": {
                        "entries": new_entries
                    }
                }
            }
            response = api_request(url, key, json.dumps(body))
            print("{} process completed".format(action.__name__))


def main(argv):
    help_msg_simple = ("usage: {} filter_list_id [-hva:r:R:] " +
        "'prefix(es)'").format(argv[0])
    help_msg = ( help_msg_simple +
    """
    Modify TMS blacklists to drop prefixes.
    Space delimited string of prefixes required.
    Arguments:
    -a    : Add provided prefix string to the current TMS list
    -r    : Remove provided prefix string from current TMS list
            if the prefix(es) exist.
    -v    : View list of prefixes (at call time, depending on order
            of argument placement)
    -R    : Replace provided prefix string from current TMS list
    """)

    try:
        # Extract arguments and options using getopt
        options, args = getopt.getopt(argv[1:], "hva:r:R:")
    except getopt.GetoptError:
        print('Error parsing arguments')
        sys.exit(2)

    if not options or not args:
        print(help_msg)
        sys.exit()

    SP_LEADER = 'leader.example.com'
    API_KEY = 'BukdiSbZB3v8Pb9NtKGMoUlmMLHkJ1_A6fTJQDpy'
    flid = args[0]  # Filter List ID
    filter_uri = "/api/sp/tms_filter_lists/{}".format(flid)
    URL = "https://" + SP_LEADER + filter_uri

    # Translate options and their args into actions
    actions = []
    for opt, arg in options:
        if opt == '-h':
            print(help_msg)
            sys.exit()
        elif opt == '-a':
            actions.append(add_prefixes(arg))
        elif opt == '-r':
            actions.append(remove_prefixes(arg))
        elif opt == '-R':
            actions.append(replace_prefixes(arg))
        elif opt == '-v':
            actions.append(view_prefixes(flid))
        else:
            print("Unknown option {}".format(arg))
            print(help_msg_simple)
            sys.exit(1)

    dispatch_actions(URL, API_KEY, actions)


if __name__ == '__main__':
    # Call the main function with all args
    main(sys.argv)
