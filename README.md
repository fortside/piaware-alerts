# piaware-alerts
A twitter bot that works with PiAware (or any similar setup with a json feed from dump1090) to send out information about aircraft flying over your location.

Requirements:
-A working piaware or similar setup with an aircraft.json file that can be parsed

External accounts- these are all free.

Open Weather Map - to get local weather data

FlightXML account - The Flight Aware APIs are used to return details about specific aircraft. This can also be manually scraped from the FlightAware website, but that's against the ToS. Depending on your settings (location, chosen radius to monitor, squawk delay) you may exceed the monthly API call limit. 

Twitter - obviously required in order to send tweets

BitLy  - Used to tweet out links to the relevant FA pages. Keeps the tweet within the character limit

