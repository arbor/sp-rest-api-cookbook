#! /usr/bin/env node

// Requires a node version of at least 8.4.0

// This NodeJS program uses the SP REST API to configure a
// DNS Filter List built from a DNS zone transfer initiated
// by SP.

// The four `const`s `LEADER`, `API_TOKEN`, `NAMESERVER`,
// and `DNS_ZONE` should be changed to match your environment.


'use strict';

const https = require('https');
const fs = require('fs');

const LEADER = 'arbor.example.com';
const API_TOKEN = 'my_SeCrEt_ApI_ToKeN';
const NAMESERVER = 'nameserver.example.com';
const DNS_ZONE = 'zone-to-block.example.com';

/*
 * Wrap https.request to make API calls a bit simpler
 */
class HttpsClient {
  constructor(leader, apiToken) {
    this.leader = leader;
    this.apiToken = apiToken;
  }

  _craftOptions(method, endpoint, headers = {}) {
    return {
      hostname: this.leader,
      port: 443,
      method: method.toUpperCase(),
      path: `/api/sp/${endpoint}`,
      ca: [ fs.readFileSync('path/to/certfile') ],
      headers: {
        'X-Arbux-APIToken': this.apiToken,
        ...headers
      }
    }
  }

  _makeRequest(options, body) {
    return new Promise((resolve, reject) => {
      let responseData = '';

      const request = https.request(options, res => {
        res.setEncoding('utf-8');

        res.on('data', chunk => {
          responseData += chunk.toString();
        });

        res.on('end', () => resolve(responseData));
      });

      request.on('error', err => {
        console.error(
          `Error with ${options.method} request to ${options.path}: ${err}`
        );

        reject(err);
      });

      if (body) {
        request.write(body);
      }

      request.end();
    });
  }

  async post(path, body) {
    const options = this._craftOptions(
      'POST',
      path,
      {
        'Content-Type': 'application/vnd.api+json',
        'Content-Length': Buffer.byteLength(body)
      }
    );

    return await this._makeRequest(options, body);
  }

  async get(path) {
    const options = this._craftOptions(
      'GET',
      path,
      { Accept: 'application/json' }
    );

    return await this._makeRequest(options);
  }
};

async function genDnsZoneFlist(client, server, zone) {
  /*
   * Request SP create a DNS filter list from the records within a managed DNS
   * zone
   */
  const endpoint = 'tms_filter_list_requests/';
  const requestResponse = await client.post(
    endpoint,
    JSON.stringify({
      data: {
        attributes: {
          request_type: 'generate_dns_filter_list',
          details: { server, zone }
        }
      }
    })
  );

  const requestId = JSON.parse(requestResponse).data.id;

  let isComplete = false;
  let attributes;

  /*
   *  Query for request status every few moments until SP is done processing it
   */
  while (!isComplete) {
    await new Promise(res => setTimeout(res, 1500));

    attributes = JSON.parse(await client.get(
      `${endpoint}${requestId}`,
    )).data.attributes;

    if (attributes.error) {
      throw new Error(attributes.error);
    }

    isComplete = attributes.completed;
  }

  return attributes.result;
}

(async () => {
  const apiClient = new HttpsClient(LEADER, API_TOKEN);

  console.log(await genDnsZoneFlist(apiClient, NAMESERVER, DNS_ZONE));
})();
