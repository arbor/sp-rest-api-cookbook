var http = require('http');
var https = require('https');
var fs = require('fs');

var API_TOKEN = 'SuperSecretToken';
var LEADER = 'youbox.domain.com';
var TMS_MIT_ID = 'tms-0';

/**
 * Running `node server.js` will serve to localhost:5000
 *
 * This code parses the request paths from the client code in new.js
 * and servers the correct file for the response to the client.
 */
var server = http.createServer(function(req, res) {
  // Makes an API request to SP API
  if (req.url === '/get_stats_by_country') {
    var path = '/api/sp/mitigations/' + TMS_MIT_ID + '/statistics_by_country/';
    var options = {
      method: 'GET',
      hostname: LEADER,
      path: path, 
      port: 443,
      headers: {
        'X-Arbux-APIToken': API_TOKEN,
        'Accept': 'application/json'
      },
    };
    var rawData = '';
    var req = https.request(options, function(response) {
      console.log('getting API data...');
      response.on('data', function(chunk) {
        rawData += chunk;
      });
      response.on('end', function() {
        var parsedJson = null;
        try {
          parsedJson = JSON.parse(rawData);
        } catch(error) { throw error; }
        if (parsedJson != null) {
          res.writeHead(200, {
            'Content-Type': 'application/json',
          });
        }
        res.end(JSON.stringify(parsedJson));
      });
    });
    req.on('error', function(e) {
      console.error(e);
    });
    req.end();
  }
  // The index.html file which includes our client js code
  else if (req.url === '/') {
    res.writeHead(200, {'Content-Type': 'text/html'});
    fs.readFile(__dirname + '/index.html', null, function(error, data) {
      if (error) {
        res.writeHead(404);
        res.write('File not found: index.html');
      } else {
        res.write(data);
      }
      res.end();
    });
  }
  // Regex used to server other js file dependencies
  else if (/^\/[\.a-zA-Z0-9\/]*.js$/.test(req.url.toString())) {
    console.log(req.url);
    res.writeHead(200, {'Content-Type': 'text/js'});
    var filename = req.url.toString();
    fs.readFile(__dirname + filename, null, function(error, data) {
      if (error) {
        res.writeHead(404);
        res.write('File not found: ' + filename);
      } else {
        res.write(data);
      }
      res.end();
    });
  }
  // File contains map of 2-letter country codes to 3-letter country codes
  else if (req.url === '/iso3.json') {
    console.log(req.url);
    res.writeHead(200, {'Content-Type': 'application/json'});
    var filename = req.url.toString();
    fs.readFile(__dirname + filename, null, function(error, data) {
      if (error) {
        res.writeHead(404);
        res.write('File not found: ' + filename);
      } else {
        res.write(data);
      }
      res.end();
    });
  }
});
// Listen on port 5000
server.listen(5000);
