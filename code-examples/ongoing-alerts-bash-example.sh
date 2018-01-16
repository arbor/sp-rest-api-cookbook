#!/usr/bin/env bash
#
# Grabs ongoing SP alerts from the last day and outputs in json form.
#
# Options:
#   -t: Output alerts in tsv form
#   -c: Output alerts in csv form
#

# current ISO date - 24 hours
DATE=`date -v-1d +%Y-%m-%dT%H:%M:%S%z`

LEADER="leader.example.com"
TOKEN="i9fESeDtZTnBRI_ruE76K_Zg2FdJRvtwapxkN1_t"
CERTFILE="../certfile"
QUERY_PARAMS="?filter=%2Fdata%2Fattributes%2Fongoing%3Dtrue+AND+%2Fdata%2Fattributes%2Fstart_time%3E$DATE"


# query SP for ongoing alerts from the past 24 hours and filter down to type,
# start time, and description.
JSON=$(
	curl --cacert $CERTFILE --ssl --silent -X GET \
		https://$LEADER/api/sp/alerts/$QUERY_PARAMS \
		-H "Content-Type: application/vnd.api+json" \
		-H "x-arbux-apitoken: $TOKEN" \
	| jq "[.data[]?.attributes | {\
					alert_type: .alert_type,\
					start_time: .start_time,\
					description: .subobject.description\
				}]"
)


# gets a delimeter separated value form of the API return.
#
# Arguments:
#   $1: The original JSON response
#   $2: 'c' or 't', for comma or tab delimeted values
get_dsv () {
  echo $1 | jq -r "\
    [\"type\", \"start\", \"description\"], \
    (.[] | [.alert_type, .start_time, .description]) \
    | @${2}sv"
}


# Gather options passed in command line
while getopts ":tc" opt; do
	case $opt in
		[tc])
			get_dsv "$JSON" $opt
			exit 0
			;;
		\?)
			echo "Invalid option: -$OPTARG" >&2
			exit 2
			;;
	esac
done


# Simply return JSON if no options have been passed
echo "$JSON"

