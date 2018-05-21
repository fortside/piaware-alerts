
# name of database to store historical information
db_name = "piplanes.db"

# the aircraft DB file should only be used if the user is licensed for FR24, since that's the original data source
# set this value to True if you're feeding FR24 as well. Leave as False otherwise
fr24_licensed = True

# name of csv file containing mappings of ICAO hex IDs to unique aircraft idents
aircraft_db_name = "aircraft_db.csv"

# pi-aware local JSON feed with cleansed input
live_data_url = "http://192.168.1.207:8080/dump1090-fa/data/aircraft.json"

# basic conversions
knots_to_kph = 1.852
meters_to_feet = 3.28084

# antenna location
my_lat = 53.7
my_lon = -113.3
home = (my_lat, my_lon)

# how big of a range do we want to report on
airspace_radius_km = 20

# how long to wait between polling the antenna data
sleep_time = 10

# how long of a window to allow the squawk to changes from a value to none
 # this prevents duplicate entries
squawk_delay = 900

# open weather map settings
OWM_key = "open weather map api key"
OWM_URL = "https://api.openweathermap.org/data/2.5/weather?lat="+str(my_lat)+"&lon="+str(my_lon)+"&units=metric&APPID="+OWM_key
weather_interval = 1800
weather_api_check_frequency = 600

# flightaware keys
fxml_key = "flightxml api key"
fa_username = "flightaware username"
fxmlUrl = "https://flightxml.flightaware.com/json/FlightXML3/"
fxml_flightinfo_limit = 15

# twitter details
twitter_app_key = "consumer key"
twitter_app_secret = "consumer secret"
twitter_token = "access token"
twitter_token_secret = "access token secret"

# bitly details
bitly_token = "bitly token"
bitly_URL = "https://api-ssl.bitly.com/v3/shorten"