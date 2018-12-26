'use strict';

(function() {
  /*
   * Create Country Code map to convert SP's 2 letter country codes to 3 letter
   * country codes used by datamaps code.
   */
  var iso2to3Map = loadJSON(function(response) {
    iso2to3Map = JSON.parse(response);
    return JSON.parse(response);
  });

  /* GET API data (function defined further down). */
  getAPIData('statistics_by_country/');

  /* Load iso3 json from JSON file on disk */
  function loadJSON(callback) {
    var xobj = new XMLHttpRequest();
    xobj.open('GET', '/iso3.json', true);
    xobj.onreadystatechange = function(e) {
      if (xobj.readyState === 4 && xobj.status === 200) {
        callback(xobj.responseText);
      }
    };
    xobj.send(null);
  }

  /*
   * Calls our nodejs "server" to make SP API calls.
   *
   * We transform API data for pps dropped to the format needed by
   * the datamaps library:
   * {
   *   MX: {
   *    fillColor: #000,
   *    numberOfThings: 9999
   *   },
   *   USA: {
   *     fillColor: #FFF,
   *     numberOfThings: 42
   *   }
   * }
   */
  function getAPIData(endpoint) {
    var request = new Request({
      method: 'GET',
      headers: new Headers({
        'Content-Type': 'application/json'
      })
    });
    // make request to server.js
    fetch('/get_stats_by_country', request)
      .then(function(resp) {
        return resp.json();
      })
      .then(function(json) {
        var dataset = {};
        var averages = [];

        // use average pps dropped per country
        json.data.forEach(function(i, k) {
          var avg = i.attributes.ip_location_filterlist.drop.pps.average;
          averages.push(avg);
        });
        var minValue = Math.min.apply(null, averages);
        var maxValue = Math.max.apply(null, averages);

        // create color palette scale
        var paletteScale = d3.scale.quantize()
            .domain([minValue, maxValue])
            .range(colorbrewer.Greens[6]);

        json.data.forEach(function(i, k) {
          var attrs = i.attributes;
          var countryCode = iso2to3Map[attrs.country_code];
          var avgDropped = attrs.ip_location_filterlist.drop.pps.average;
          dataset[countryCode] = {
            numberOfThings: avgDropped,
            fillColor: paletteScale(avgDropped)
          };
        });

        // Define our datamap
        // datamaps repo: https://github.com/markmarkoh/datamaps
        var map = new Datamap({
          element: document.getElementById('container'),
          scope: 'world',
          projection: 'mercator',
          geographyConfig: {
            borderColor: '#DEDEDE',
            highlightBorderWidth: 2,
            highlightFillColor: function(geo) {
              return geo['fillColor'] || '#F5F5F5';
            },
            highlightBorderColor: '#B7B7B7',
            popupOnHover: true,
            popupTemplate: function(geo, data) {
              // don't show tooltip if country doesn't have data
              if (data) {
                return ['<div class="hoverinfo">',
                  '<strong>', geo.properties.name, '</strong>',
                  '<br>Average Dropped: <strong>', data.numberOfThings, ' pps</strong>',
                  '</div>'
                ].join('');
              }
            },
            highlightOnHover: true
          },
          fills: {
            defaultFill: '#F5F5F5',
          },
          data: dataset
        });
        // grab svg using d3 so we can append our own d3 legend
        var svg = d3.select('svg');
        // create legend color fills
        var colorLegend = d3.legend.color()
          .labelFormat(d3.format('.1r'))
          .scale(paletteScale)
          .shapePadding(5)
          .shapeWidth(25)
          .shapeHeight(20)
          .labelOffset(12)
          .labelDelimiter('-');

        svg.append('g')
          .attr('class', 'legend')
          .attr('transform', 'translate(42, 420)');
        svg.select('.legend').call(colorLegend);
      })
      .catch(function(error) { throw error; });
  }
})();
