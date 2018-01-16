<?php

/**
 * Make an API request GET or POST (default method GET).
 *
 * @param[in] $url a URL including an SP leader and SP resource
 * @param[in] $key an api key used to access the SP api
 * @param[in] $body json post data if any
 * @param[in] $method HTTP method is GET by default
 *
 * @return json decoded response
 */
function makeRequest($url, $key, $body = false, $method = "GET") {
	// Initialize curl handle
	$curl = curl_init($url);

	// Set HTTP headers
	$headers = [
		"X-Arbux-APIToken: " . $key,
		"Content-Type: application/vnd.api+json"
	];
	curl_setopt($curl, CURLOPT_HTTPHEADER, $headers);

	// Set request type (GET/POST)
	curl_setopt($curl, CURLOPT_CUSTOMREQUEST, $method);
	if ($body) {
		curl_setopt($curl, CURLOPT_POSTFIELD);
	}
	// return result instead of outputting it.
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, TRUE);

	// use arbor cert
	curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, TRUE);
	curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, 2);
	curl_setopt($curl, CURLOPT_CAPATH, getcwd() . "/https_active.crt");

	// Grab result and close cURL session
	$result = curl_exec($curl);
	curl_close($curl);

	return json_decode($result, TRUE);
}

/**
 * Print a table of information about TMS ports
 */
function listTmsPortsInfo() {
	$api_key = 'JskW5QLVUMkNn4ruVwXOM0hQdyXCtOwnpkOjOev4';
	$sp_leader = 'https://leader.example.com/api/sp/tms_ports/';
	$json = makeRequest($sp_leader, $api_key);

	// Grab data from response and print table
	$table_format = "|%-10s |%-10.50s | %-25s | %-10s | %-20s |\n";
	printf(
		$table_format,
		'Port Name',
		'Port Type',
		'TMS',
		'TMS Model',
		'TMS Deployment Type'
	);

	foreach ($json['data'] as $tms_port) {
		$port_attributes = $tms_port['attributes'];
		$port_name = $port_attributes['name'];
		$port_type = $port_attributes['port_type'];
		// Use relationship link to get more information about the related TMS
		$tms_link = $tms_port['relationships']['tms']['links']['related'];
		$tms_json = makeRequest($tms_link, $api_key);
		$tms_attributes = $tms_json['data']['attributes'];
		$tms_name = $tms_attributes['name'];
		$tms_full_model = $tms_attributes['full_model'];
		$tms_deployment_type = $tms_attributes['deployment_type'];
		// Print data table
		printf(
			$table_format,
			$port_name,
			$port_type,
			$tms_name,
			$tms_full_model,
			$tms_deployment_type
		);
	}
}

listTmsPortsInfo();
?>
