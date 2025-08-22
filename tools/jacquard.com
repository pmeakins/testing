{
  "input_query": "jacquard.com",
  "is_ip": false,
  "dns": {
    "A": [
      "162.159.135.42"
    ],
    "AAAA": []
  },
  "lookups": [
    {
      "ip": "162.159.135.42",
      "rdns": null,
      "providers": {
        "whoisxml": {
          "ip": "162.159.135.42",
          "domain": null,
          "continent": null,
          "country": "US",
          "country_code": null,
          "region": "California",
          "city": "South Beach",
          "postal_code": null,
          "lat": 37.78298,
          "lon": -122.38969,
          "timezone": "-07:00",
          "isp": "Cloudflare",
          "org": null,
          "connection_type": "",
          "asn": null,
          "as_org": null,
          "reverse_domains": [
            "0-16.unn.edu.ng",
            "0-25.snowdropsolutions.co.uk",
            "0-cms-hfjdlopii4dojbasa-csg-euo-cloud.lego.puyecliffdwellings.com",
            "0-courier.snapdragonproseries.com",
            "0-dl.sciencesocieties.org.library.unn.edu.ng"
          ],
          "raw": {
            "ip": "162.159.135.42",
            "location": {
              "country": "US",
              "region": "California",
              "city": "South Beach",
              "lat": 37.78298,
              "lng": -122.38969,
              "postalCode": "",
              "timezone": "-07:00",
              "geonameId": 5326621
            },
            "domains": [
              "0-16.unn.edu.ng",
              "0-25.snowdropsolutions.co.uk",
              "0-cms-hfjdlopii4dojbasa-csg-euo-cloud.lego.puyecliffdwellings.com",
              "0-courier.snapdragonproseries.com",
              "0-dl.sciencesocieties.org.library.unn.edu.ng"
            ],
            "as": {
              "asn": 13335,
              "name": "CLOUDFLARENET",
              "route": "162.159.128.0/19",
              "domain": "https://www.cloudflare.com",
              "type": "Content"
            },
            "isp": "Cloudflare",
            "connectionType": ""
          }
        },
        "ipinfo": {
          "ip": "162.159.135.42",
          "country": "US",
          "region": "California",
          "city": "San Francisco",
          "lat": 37.7621,
          "lon": -122.3971,
          "org": "AS13335 Cloudflare, Inc.",
          "asn": "13335",
          "as_org": "Cloudflare, Inc.",
          "timezone": "America/Los_Angeles",
          "raw": {
            "ip": "162.159.135.42",
            "city": "San Francisco",
            "region": "California",
            "country": "US",
            "loc": "37.7621,-122.3971",
            "org": "AS13335 Cloudflare, Inc.",
            "postal": "94107",
            "timezone": "America/Los_Angeles",
            "anycast": true
          }
        }
      },
      "discrepancies": {
        "city": {
          "whoisxml": "South Beach",
          "ipinfo": "San Francisco"
        },
        "coord_distance_km": 2.4
      },
      "headline_location": {
        "country": "US",
        "region": "California",
        "city": "South Beach",
        "lat": 37.78298,
        "lon": -122.38969,
        "source": "whoisxml"
      }
    }
  ],
  "domain_lookup_used": false
}
