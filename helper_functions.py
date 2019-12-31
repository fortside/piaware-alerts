import constants
import geopy.distance
import json
import urllib.request
import urllib.error
import sqlite3
import datetime
import requests
import twython
import traceback
import math
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_distance(my_location, remote_location):
    return geopy.distance.distance(my_location, remote_location).kilometers


# shamelessly taken from https://gist.github.com/jeromer/2005586
def get_bearing(pointA, pointB):
    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
                                           * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def speed_to_kph(speed):
    return speed * constants.knots_to_kph


def dt_to_datetime(dt):
    return datetime.datetime.fromtimestamp(int(dt)).strftime('%Y-%m-%d %H:%M:%S')


def datetime_to_dt(formatted_datetime):
    return int(datetime.datetime.strptime(formatted_datetime, '%Y-%m-%d %H:%M:%S').timestamp())


def heading_to_direction(heading):
    if heading > 348.75 or heading < 11.25:
        return "N"
    elif heading >= 11.25 and heading < 33.75:
        return "NNE"
    elif heading >= 33.75 and heading < 56.25:
        return "NE"
    elif heading >= 56.25 and heading < 78.75:
        return "ENE"
    elif heading >= 78.75 and heading < 101.25:
        return "E"
    elif heading >= 101.25 and heading < 123.75:
        return "ESE"
    elif heading >= 123.75 and heading < 146.25:
        return "SE"
    elif heading >= 146.25 and heading < 168.75:
        return "SSE"
    elif heading >= 168.75 and heading < 191.25:
        return "S"
    elif heading >= 191.25 and heading < 213.75:
        return "SSW"
    elif heading >= 213.75 and heading < 236.25:
        return "SW"
    elif heading >= 236.25 and heading < 258.75:
        return "WSW"
    elif heading >= 258.75 and heading < 281.25:
        return "W"
    elif heading >= 281.25 and heading < 303.75:
        return "WNW"
    elif heading >= 303.75 and heading < 326.25:
        return "NW"
    else:  # heading >= 326.25 and heading < 348.75
        return "NNW"


def check_current_weather():
    # grab the most recent entry in the weather cache database
    weather_query = "select * from weather order by datetime desc limit 1"
    conn = sqlite3.connect(constants.db_name)
    cur = conn.cursor()
    cur.execute(weather_query)
    newest_weather = cur.fetchone()

    # check to see if this weather info is stale, or even exists at all
    if (newest_weather is None) or \
                            newest_weather[0] + constants.weather_interval < \
                    datetime_to_dt(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
        print("Weather info is considered stale")
        # also check when we last queried the API. Only a finite number allowed daily so throttling is a must
        if (newest_weather is not None) and newest_weather[8] + constants.weather_api_check_frequency < \
                datetime_to_dt(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
            # it's been more than <weather_api_check_frequency> seconds, query the API again
            print("querying info from OWM API and attempting to update database")

            # make the web request to pull the json data
            req = urllib.request.Request(constants.OWM_URL)
            try:
                data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                print("HTTP Error: " + e.reason)
                data = None
            except urllib.error.URLError as e:
                print("OWM URL Error: " + e.reason.strerror + "\nCheck network connections")
                data = None
            except Exception as e:
                print("Error reaching " + constants.OWM_URL)
                print(str(e))
                print(traceback.format_exc())
                data = None
            if data is not None:
                weather_insert = "insert or replace into weather values (?,?,?,?,?,?,?,?,?);"
                # visibility is a calculated value and OWM may not always return it. We must handle this scenario
                if 'visibility' in data:
                    vis = data['visibility']
                else:
                    vis = -1
                weather_values = [data['dt'],
                                  data['coord']['lat'],
                                  data['coord']['lon'],
                                  data['weather'][0]['description'],
                                  data['main']['temp'],
                                  data['main']['pressure'],
                                  data['main']['humidity'],
                                  vis,
                                  datetime_to_dt(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                                  ]

                print("Updating database entry with timestamp of " + str(
                    datetime_to_dt(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
                cur.execute(weather_insert, weather_values)
                conn.commit()

                weather = {"visibility": vis * constants.meters_to_feet,
                           "desc": data['weather'][0]['description'],
                           "timestamp": dt_to_datetime(data['dt'])}
            else:
                print("Error accessing OWM API. Returning cached weather values")
                weather = {"visibility": int(newest_weather[7] * constants.meters_to_feet),
                           "desc": newest_weather[3],
                           "timestamp": dt_to_datetime(newest_weather[0])
                           }
        else:
            # don't bother checking the API, just return the current info
            print("OWM API was recently queried. Waiting before checking again. Returning cached weather values")
            weather = {"visibility": int(newest_weather[7] * constants.meters_to_feet),
                       "desc": newest_weather[3],
                       "timestamp": dt_to_datetime(newest_weather[0])
                       }
    else:
        weather = {"visibility": int(newest_weather[7] * constants.meters_to_feet),
                   "desc": newest_weather[3],
                   "timestamp": dt_to_datetime(newest_weather[0])
                   }
        print("Got weather info from cache")

    cur.close()
    conn.close()

    return weather


def create_sql_tables():
    weather_table = "Create table if not exists weather (" \
                    "datetime integer UNIQUE" \
                    ", lat real" \
                    ", long real" \
                    ", desc text" \
                    ", temp real" \
                    ", pressure integer" \
                    ", humidity integer" \
                    ", visibility integer" \
                    ", lastchecked integer" \
                    ")"

    aircraft_table = "Create table if not exists aircraft (" \
                     "aircraft_key text" \
                     ", aircraft text" \
                     ", tail_number text" \
                     ", flight_number text" \
                     ", desc text" \
                     ", fa_url text" \
                     ", speed real" \
                     ", altitude integer" \
                     ", heading integer" \
                     ", icao_code text" \
                     ", squawk text" \
                     ", tweet_status integer" \
                     ", time_entered text" \
                     ", time_exited text" \
                     ", lat real" \
                     ", lon real" \
                     ")"
    aircraft_details_table = "Create table if not exists aircraft_type_details (" \
                             "aircraft_type text" \
                             ", description text" \
                             ", engine_count integer" \
                             ", engine_type text" \
                             ", manufacturer text" \
                             ", type text" \
                             ")"

    airline_details_table = "Create table if not exists airline_details (" \
                            "airline_code text" \
                            ", callsign text" \
                            ", country text" \
                            ", location text" \
                            ", name text" \
                            ", phone text" \
                            ", shortname text" \
                            ", url text" \
                            ")"

    tail_owner_table = "Create table if not exists tail_owner (" \
                            "ident text" \
                            ", location text" \
                            ", location2 text" \
                            ", owner text" \
                            ", website text" \
                            ")"

    # connect to the database
    conn = sqlite3.connect(constants.db_name)

    # get the cursor so we can do stuff
    cur = conn.cursor()

    # create our tables
    cur.execute(weather_table)
    conn.commit()
    cur.execute(aircraft_table)
    conn.commit()
    cur.execute(aircraft_details_table)
    conn.commit()
    cur.execute(airline_details_table)
    conn.commit()
    cur.execute(tail_owner_table)
    conn.commit()

    # close the connections
    cur.close()
    conn.close()


def aircraft_exists(icao, squawk):
    # find the most recent entry for this aircraft
    query = "select * from aircraft where icao_code = (?) order by time_entered desc limit 1"
    # connect to the database
    conn = sqlite3.connect(constants.db_name)
    # get the cursor so we can do stuff
    cur = conn.cursor()
    cur.execute(query, [icao])

    # run the query to see if this one is entered yet
    this_aircraft = cur.fetchone()
    if this_aircraft is None:
        # this aircraft has never been in our airspace
        cur.close()
        conn.close()
        return False
    else:
        # we've seen this before, if it was in the last few minutes we should ignore it
        recent_timestamp = this_aircraft[0].split("$")[1]
        recent_squawk = this_aircraft[10]
        # if the newest entry in the database is older than X seconds ago, we know it's a new flight
        if (datetime_to_dt(recent_timestamp) + constants.squawk_delay < datetime_to_dt(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))):
            cur.close()
            conn.close()
            return False
        # if this squawk is the same as the previous one, this is already recorded
        elif recent_squawk == squawk:
            cur.close()
            conn.close()
            return True
        # if this is just a case of the aircraft turning off it's squawk code we should ignore it. Not a new entry
        elif recent_squawk != 'none' and squawk == 'none':
            cur.close()
            conn.close()
            return True
        # if this aircraft had no squawk and now does, let's update that but not record it as a new entry
        elif recent_squawk == 'none' and squawk != 'none':
            # send the update query to SQL
            update_aircraft_query = "update aircraft set squawk = (?) where aircraft_key = (?)"
            update_aircraft_values = [squawk, this_aircraft[0]]
            cur.execute(update_aircraft_query, update_aircraft_values)
            conn.commit()
            cur.close()
            conn.close()
            print(icao + ": set squawk value to " + squawk)
            return True
        # Last possible case is if the squawk code changed to a different valid value. Already cataloged.
        else:
            cur.close()
            conn.close()
            return True


def check_if_known(airplane, aircraft_db):
    url = "https://flightaware.com/live/modes/" + airplane['hex'] + "/redirect"
    try:
        redirect_url = urllib.request.urlopen(urllib.request.Request(url)).geturl()
    except urllib.error.HTTPError as e:
        print("HTTP Error: " + e.reason)
        return None
    except urllib.error.URLError as e:
        print("FlightAware URL Error: " + e.reason.strerror + "\nCheck network connections")
        return None
    except Exception as e:
        print("Error accessing flightaware.com. Unable to check aircraft")
        print(str(e))
        print(traceback.format_exc())
        return None

    known_info = {'fl_num': 'x', 'redirect_url': 'y'}
    # if the redirect gave us the flight details enter it
    if url != redirect_url:
        known_info['fl_num'] = redirect_url.split('/')[5]
        known_info['redirect_url'] = redirect_url
    # or possibly the flight number info is being sent by the aircraft itself
    elif 'flight' in airplane:
        known_info['fl_num'] = airplane['flight'].replace(' ', '')
        known_info['redirect_url'] = "https://flightaware.com/live/flight/" + known_info['fl_num']
    # next we can try to look up using the local FR24 aircraft DB if it's available
    elif aircraft_db is not None:
        # here we will check the csv file database file
        try:
            if '~' in airplane['hex']:
                airplane_hex = airplane['hex'][1:]
            else:
                airplane_hex = airplane['hex']
            # fancy way of finding the row in the DF with the hex code, and getting the ident string
            ident = aircraft_db.loc[aircraft_db['icao'] == airplane_hex]['regid'].values[0].replace(' ', '').replace('-', '').upper()
            # tail number != flight number but the URLs load the same page info, and return the same API data
            known_info['fl_num'] = ident
            known_info['redirect_url'] = "https://flightaware.com/live/flight/" + ident
            print(airplane_hex + ": Flight info retrieved from local FR24 db (Tail #" + ident + ")")
        except Exception as e:
            print("ICAO hex code " + airplane['hex'] + " missing from local FR24 db. No details available.")
            known_info = None
    else:
        known_info = None

    return known_info


def get_flight_info(airplane, aircraft_db):
    aircraft_type = None

    deets = check_if_known(airplane, aircraft_db)

    # If Flight Aware doesn't have detail on a specific flight we can't get any good details
    if deets is None:
        print(airplane['hex'] + ": flight unknown to FlightAware")
        flight_info = None
        no_details = True

    else:
        no_details = False

        # from the flight number we can get much more detail from the FA API
        payload = {'ident': deets['fl_num'], 'howMany': constants.fxml_flightinfo_limit}
        api_error = False
        try:
            response = requests.get(constants.fxmlUrl + "FlightInfoStatus", params=payload,
                                    auth=(constants.fa_username, constants.fxml_key))
        except requests.exceptions.RequestException as e:
            print("Error accessing FXML API")
            api_error = True

        if response.status_code == 200 and api_error == False:
            flight_data = response.json()
            # the flight data will contain up to 15 cataloged flights for this flight number. We only want
            #  the current in-progress flight
            if 'FlightInfoStatusResult' in flight_data:
                for flight in flight_data['FlightInfoStatusResult']['flights']:
                    # there is an edge case here where all flights are inactive. Consider this an 'unknown flight'
                    if 0 <= flight['progress_percent'] < 100:
                        if 'full_aircrafttype' in flight:
                            aircraft_type = flight['full_aircrafttype']
                        elif 'aircrafttype' in flight:
                            aircraft_type = flight['aircrafttype']
                        else:
                            aircraft_type = "Unknown"
                        if 'airline' in flight:
                            airline = get_airline_info(flight['airline'])
                            if 'airline_iata' in flight:
                                iata = flight['airline_iata']
                            else:
                                iata = flight['airline']
                            origin = flight['origin']['airport_name']
                            destination = flight['destination']['airport_name']
                            flight_num = flight['flightnumber']
                        else:
                            airline = "Private Flight"
                            iata = "n/a"
                            flight_num = deets['fl_num']
                        if flight['origin']['airport_name'] == '':
                            origin = flight['origin']['code']
                        else:
                            origin = flight['origin']['airport_name']
                        if flight['destination']['airport_name'] == '':
                            destination = flight['destination']['code']
                        else:
                            destination = flight['destination']['airport_name']
                        flight_desc = airline + " (" + iata + ") #" + flight_num + " from " + origin + " to " + \
                                      destination
                        fa_url = deets['redirect_url']
                        if 'tailnumber' in flight:
                            tail_number = flight['tailnumber']
                        else:
                            tail_number = flight_num
                        break;
                # possible that no flights show as active. FXML would not be returning accurate data if so.
                if aircraft_type is None:
                    print(airplane['hex'] + ": no active flights found")
                    flight_desc = "unknown flight"
                    fa_url = "unknown flight"
                    tail_number = deets['fl_num']
            else:
                print(airplane['hex'] + ": this aircraft has requested to not be tracked")
                #check if we have owner information for this tail number yet
                query = "select * from tail_owner where ident = (?) limit 1"
                # connect to the database
                conn = sqlite3.connect(constants.db_name)
                # get the cursor so we can do stuff
                cur = conn.cursor()
                cur.execute(query, [deets['fl_num']])

                # run the query to see if this one is entered yet
                this_ident = cur.fetchone()
                if this_ident is not None:
                    # set the flight info based on what the table says
                    flight_desc = "Private flight: " + deets['fl_num'] + " - is unavailable for public tracking\n" + \
                                  "Owner: " + this_ident[3] + " (" + this_ident[1] + ")"
                    cur.close()
                    conn.close()
                    print(deets['fl_num'] + " found in Tail Owners table. No need to query FXML API")
                else:
                    # this aircraft has never been in our airspace, check the API
                    payload = {'ident': deets['fl_num']}
                    # no error checking here. Bold assumption that if the API call above worked, this one will too
                    response = requests.get(constants.fxmlUrl + "TailOwner", params=payload,
                                            auth=(constants.fa_username, constants.fxml_key))
                    aircraft_data = response.json()
                    flight_desc = "Private flight: " + deets['fl_num'] + " - is unavailable for public tracking\n" + \
                                  "Owner: " + aircraft_data['TailOwnerResult']['owner'].replace('&quot;', '"') + " (" + \
                                  aircraft_data['TailOwnerResult']['location'] + ")"
                    # we must also update the tail_owner table so next time the API doesn't need to be queried
                    tail_insert = "insert or ignore into tail_owner values (?,?,?,?,?);"
                    tail_values = [deets['fl_num'],
                                   aircraft_data['TailOwnerResult']['location'],
                                   aircraft_data['TailOwnerResult']['location2'],
                                   aircraft_data['TailOwnerResult']['owner'].replace('&quot;', '"'),
                                   aircraft_data['TailOwnerResult']['website']
                                   ]
                    cur.execute(tail_insert, tail_values)
                    conn.commit()
                    cur.close()
                    conn.close()
                    print(deets['fl_num'] + " added to Tail Owners table")

                aircraft_type = "Unknown"
                fa_url = "private flight"
                tail_number = deets['fl_num']

            # now we can start building the dict
            if aircraft_type is None:
                print("wait")
            flight_info = {"aircraft": aircraft_type,
                           "flight_number": deets['fl_num'],
                           "desc": flight_desc,
                           "fa_url": fa_url,
                           "tail_number": tail_number
                           }
        else:
            print(airplane['hex'] + ": Error retrieving data upstream")
            flight_info = None

    if no_details:
        flight_info = "ignore me"
    else:
        # pull out the squawk code
        if 'squawk' in airplane:
            squawk = airplane['squawk']
        else:
            squawk = "none"

        if 'gs' in airplane:
            speed = round(speed_to_kph(airplane['gs']), 2)
        else:
            speed = 0
        if 'track' in airplane:
            track = airplane['track']
        else:
            track = 0

        if flight_info is not None:
            # fill the dict with all other relevant values, direct from the aircraft itself
            flight_info['aircraft_key'] = create_aircraft_key(airplane['hex'], squawk)
            flight_info['speed'] = speed
            flight_info['altitude'] = airplane['alt_baro']
            flight_info['heading'] = track
            flight_info['icao_code'] = airplane['hex']
            flight_info['squawk'] = squawk
            flight_info['tweet_status'] = 0
            flight_info['time_entered'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flight_info['time_exited'] = ''
            flight_info['lat'] = airplane['lat']
            flight_info['lon'] = airplane['lon']

        else:
            # there's not much data available for this one. grab in what we can
            if 'gs' in airplane:
                speed = round(speed_to_kph(airplane['gs']), 2)
            else:
                speed = 0
            if 'alt_baro' in airplane:
                alt = airplane['alt_baro']
            else:
                alt = 0
            if 'heading' in airplane:
                head = airplane['track']
            else:
                head = 0
            flight_info = {"aircraft_key": create_aircraft_key(airplane['hex'], squawk),
                           "aircraft": 'none',
                           "tail_number": 'none',
                           "flight_number": 'none',
                           "desc": 'none',
                           "fa_url": 'none',
                           "speed": speed,
                           "altitude": alt,
                           "heading": head,
                           "icao_code": airplane['hex'],
                           "squawk": squawk,
                           "tweet_status": 0,
                           "time_entered": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           "time_exited": '',
                           "lat": airplane['lat'],
                           "lon": airplane['lon']
                           }

    return flight_info


def commit_flight_info(flight_dict):
    key = create_aircraft_key(flight_dict['icao_code'], flight_dict['squawk'])

    conn = sqlite3.connect(constants.db_name)
    cur = conn.cursor()
    aircraft_insert = "insert or ignore into aircraft values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"
    # (aircraft_key, aircraft, tail_number, flight_number, desc, fa_url, speed, altitude. heading, icao_code, squawk, tweet_status, lat, lon)
    aircraft_values = [flight_dict['aircraft_key'],
                       flight_dict['aircraft'],
                       flight_dict['tail_number'],
                       flight_dict['flight_number'],
                       flight_dict['desc'],
                       flight_dict['fa_url'],
                       flight_dict['speed'],
                       flight_dict['altitude'],
                       flight_dict['heading'],
                       flight_dict['icao_code'],
                       flight_dict['squawk'],
                       flight_dict['tweet_status'],
                       flight_dict['time_entered'],
                       flight_dict['time_exited'],
                       flight_dict['lat'],
                       flight_dict['lon']
                       ]

    cur.execute(aircraft_insert, aircraft_values)
    conn.commit()
    print(flight_dict['icao_code'] + ": written to aircraft table")

    # also find out more details about the type of aircraft
    # TODO must deal with the edge case where this is NoneType. Check icao c036d2 from flightinfostatus API
    if flight_dict['aircraft'] != "none" and flight_dict['aircraft'] != "Unknown":
        if flight_dict['aircraft'] is None:
            print("problem")
        else:
            get_aircraft_info(flight_dict['aircraft'])

    # close the connections
    cur.close()
    conn.close()


def create_aircraft_key(icao, squawk):
    return icao + "$" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_aircraft_info(aircraft_type):
    # check the database first
    query = "select * from aircraft_type_details where aircraft_type = (?)"
    # connect to the database
    conn = sqlite3.connect(constants.db_name)
    # get the cursor so we can do stuff
    cur = conn.cursor()
    cur.execute(query, [aircraft_type])
    # run the query to see if this one is written yet
    this_aircraft = cur.fetchone()

    if this_aircraft is None:
        print("No details for " + aircraft_type + ". Querying FlightXML")
        payload = {'type': aircraft_type}
        api_error = False
        try:
            response = requests.get(constants.fxmlUrl + "AircraftType", params=payload,
                                    auth=(constants.fa_username, constants.fxml_key))
        except requests.exceptions.RequestException as e:
            api_error = True
        if response.status_code == 200 and api_error == False and 'AircraftTypeResult' in response.json():
            data = response.json()
            # parse this out and write to the database
            aircraft_type_insert = "insert or ignore into aircraft_type_details values (?,?,?,?,?,?);"
            # aircraft_type text, description text, engine_count integer, engine_type text, manufacturer text
            aircraft_type_values = [aircraft_type,
                                    data['AircraftTypeResult']['description'],
                                    data['AircraftTypeResult']['engine_count'],
                                    data['AircraftTypeResult']['engine_type'],
                                    data['AircraftTypeResult']['manufacturer'],
                                    data['AircraftTypeResult']['type']
                                    ]
            cur.execute(aircraft_type_insert, aircraft_type_values)
            conn.commit()
            print(aircraft_type + ": written to aircraft_type_details table")

        else:
            print("Error accessing FlightXML. No details for " + aircraft_type)

    else:
        print("Aircraft type details exist for " + aircraft_type + ". No need to query FXML API")

    cur.close()
    conn.close()


def tweet(weather):
    query = "select * from aircraft where tweet_status = 0 and aircraft is not null and aircraft != 'none' order by time_entered asc"
    conn = sqlite3.connect(constants.db_name)
    # get the cursor so we can do stuff
    cur = conn.cursor()
    cur.execute(query)
    # run the query to see if this one is entered yet
    aircrafts_to_tweet = cur.fetchall()

    twitter = twython.Twython(constants.twitter_app_key, constants.twitter_app_secret,
                              constants.twitter_token, constants.twitter_token_secret)

    for aircraft in aircrafts_to_tweet:
        direction = heading_to_direction(get_bearing(constants.home, (aircraft[14], aircraft[15])))
        message = "Incoming from the " + direction + "!\n"
        # flight description
        message += aircraft[4] + "\n"  # desc
        # aircraft type
        if aircraft[1] == "Unknown":  # aircraft type (ex. B737 or A320)
            message += "Aircraft type: unavailable\n"
        else:
            message += "Flight # " + aircraft[3] + "\n"
            # look up the plane details in the other DB table
            query = "select * from aircraft_type_details where aircraft_type = (?)"
            cur.execute(query, [aircraft[1]])
            details = cur.fetchone()
            if details is None:
                message += "Aircraft: Unknown \n"
            else:
                message += "Aircraft: " + details[4] + " " + details[5] + "\n"
        # FA url
        if aircraft[5].__contains__("https"):
            link = shorten_link(aircraft[5])
            if link is not None:
                message += "Details: " + link + "\n"
        # additional nice to know details
        message += "Tail # " + aircraft[2] + "\n"
        message += "Speed: " + str(int(aircraft[6])) + " km/hr heading " + heading_to_direction(aircraft[8]) + "\n"
        message += "Alt: " + str(aircraft[7]) + " ft\n"
        message += "Weather: " + weather['desc'] + "\n"
        # message += "Ceiling: " + str(weather['visibility']) + " ft\n" # this value doesn't seem accurate
        # TODO check other weather APIs, or if there's a better measure available from OWM

        message += constants.hashtags + "\n"

        print("Tweet character count: " + str(message.__len__()))
        # super ugly temp fix. tweet should be split into 2 messages.
        if message.__len__() > 279:
            message = message[:278]
        result = None
        try:
            result = twitter.update_status(status=message)
        except Exception as e:
            print("Error tweeting: " + str(e))
            email_problem(str(e))
        if result is not None:
            # now lets set the tweet_status for this aircraft to 1 so it won't be sent out again
            update_query = "update aircraft set tweet_status = 1 where aircraft_key = (?)"
            cur.execute(update_query, [aircraft[0]])
            conn.commit()
            print(aircraft[9] + ": tweet sent. Status updated in database")

def get_airline_info(airline_code):
    # check the database first
    query = "select * from airline_details where airline_code = (?)"
    # connect to the database
    conn = sqlite3.connect(constants.db_name)
    # get the cursor so we can do stuff
    cur = conn.cursor()
    cur.execute(query, [airline_code])
    # run the query to see if this one is written yet
    this_airline = cur.fetchone()

    if this_airline is None:
        print("No details for " + airline_code + ". Querying FlightXML")
        payload = {'airline_code': airline_code}
        api_error = False
        try:
            response = requests.get(constants.fxmlUrl + "AirlineInfo", params=payload,
                                    auth=(constants.fa_username, constants.fxml_key))
        except requests.exceptions.RequestExeption as e:
            api_error = True
        if response.status_code == 200 and api_error == False and 'AirlineInfoResult' in response.json():
            data = response.json()
            # parse this out and write to the database
            airline_insert = "insert or ignore into airline_details values (?,?,?,?,?,?,?,?);"
            # aircraft_type text, description text, engine_count integer, engine_type text, manufacturer text
            airline_values = [airline_code,
                              data['AirlineInfoResult']['callsign'],
                              data['AirlineInfoResult']['country'],
                              data['AirlineInfoResult']['location'],
                              data['AirlineInfoResult']['name'],
                              data['AirlineInfoResult']['phone'],
                              data['AirlineInfoResult']['shortname'],
                              data['AirlineInfoResult']['url']
                              ]
            cur.execute(airline_insert, airline_values)
            conn.commit()
            print(airline_code + ": written to airline_details table")
            # ideally we use the shortname for an airline. Use the full name if no shortname exists
            if data['AirlineInfoResult']['shortname'] == '':
                airline_name = data['AirlineInfoResult']['name']
            else:
                airline_name = data['AirlineInfoResult']['shortname']

        else:
            print("Error accessing FlightXML. No details for " + airline_code)
            airline_name = airline_code

    else:
        print("Airline details exist for " + airline_code + ". No need to query FXML API")
        if this_airline[6] == '':
            airline_name = this_airline[4]
        else:
            airline_name = this_airline[6]

    cur.close()
    conn.close()
    return airline_name


def shorten_link(url):
    # use bitly API to shorten the FA urls
    payload = {'access_token': constants.bitly_token, 'longUrl': url}
    api_error = False
    try:
        response = requests.get(constants.bitly_URL, params=payload, verify=True)
    except requests.exceptions.RequestException as e:
        print("Error accessing bitly API")
        api_error = True
    if not api_error and response.status_code == 200:
        data = response.json()

        if response.status_code == 200 and 'data' in data and 'url' in data['data']:
            short_link = data['data']['url']
            return short_link
        else:
            print(response.text)
            return None
    else:
        return None

def email_problem(exception_reason):
    
    #build the message object
    msg = MIMEMultipart('alternative')
    msg['Subject'] = constants.subject
    msg['From'] = constants.send_from
    msg['To'] = constants.send_to

    text = "No plain text option available. Use an HTML email client."
    html = str(exception_reason)

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    #Attach parts into message container. According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    
    #now connect and send the email out
    server = smtplib.SMTP(constants.smtp_server, constants.smtp_port)
    server.ehlo()
    server.sendmail(constants.send_from, constants.send_to, msg.as_string())
    server.quit()