# piaware-alerts
A twitter bot that works with PiAware (or any similar setup with a json feed from dump1090) to tweet out information about aircraft flying over your location.

# Requirements: 
- A working piaware or similar setup with an aircraft.json file that can be parsed
- External accounts- these are all free
    - Open Weather Map - to get local weather data
    - FlightXML account - The Flight Aware APIs are used to return details about specific aircraft. This can also be manually scraped from the FlightAware website, but that's against the ToS. Depending on your settings (location, chosen radius to monitor, squawk delay) you may exceed the free monthly API call limit.
    - Twitter - obviously required in order to send tweets
    - BitLy - Used to tweet out links to the relevant FA pages. Keeps the tweet within the character limit
- Python 3 modules needed
    - geopy
    - numpy
    - pandas

# Optional for MLAT tracking:
- An FR24 account. This functionality relies on a local copy of Junzi Sun's aircraft DB [https://github.com/junzis/aircraft-db][1] for quick hex code lookups. The best way to be license-compliant is to be a data provider for FR24 as well.

# How to use:
1. Install dependencies
2. Configure all API keys and OAuth tokens for the respective services that are used. Set your location, as well as the radius around it you want to track. The larger the radius, the more API hits to FXML.
    - If you want to track MLAT aircraft in addition to ADS-B, set the fr24_licensed flag to True, and grab a copy of [Junzi Sun][1]'s csv file. Set the relative path to the csv file in constants.py as well.
3. (optional backup) This repo also contains a bash script that can be set up as a cron job to save the sqlite DB to an FTP server somewhere. The longer the database is allowed to build, the fewer API hits need to be made regarding aircraft and airline types.
4. Run it: "python3 main.py"
 
[1]: https://github.com/junzis/aircraft-db