import json
import urllib.request
import helper_functions
import constants
import time
import datetime
import traceback

# TODO create a cron job to check each minute that this script is still running

try:

    # start by ensuring the SQL backend is set up
    helper_functions.create_sql_tables()

    while True:
        # check the weather
        weather = helper_functions.check_current_weather()

        # make the web request to pull the json data from our antenna
        req = urllib.request.Request(constants.live_data_url)
        try:
            data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print("HTTP Error: " + e.reason)
            data = None
        except urllib.error.URLError as e:
            print("URL Error: " + e.reason.strerror + "\nCheck network connections")
            data = None
        except Exception as e:
            print("General Exception. Error reaching " + constants.live_data_url)
            data = None

        # if we have valid aircraft data, run through each aircraft to see the details
        if data is not None and data['aircraft'].__len__():
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ": Parsing " + str(data['aircraft'].__len__()) + " aircraft")
            for airplane in data['aircraft']:
                # print("==============================")
                # print("ICAO code: " + airplane['hex'])
                # we can't get distance location without knowing where the plane is
                if 'lat' in airplane:
                    # ignore this aircraft if it's outside of our airspace
                    if helper_functions.get_distance(constants.home, (airplane['lat'], airplane['lon'])) <= \
                            constants.airspace_radius_km:
                        # grab squawk code
                        if 'squawk' in airplane:
                            squawk = airplane['squawk']
                        else:
                            squawk = "none"
                        # check if this aircraft already exists in our local database
                        if helper_functions.aircraft_exists(airplane['hex'], squawk):
                            print(airplane['hex'] + ": already in database")
                        else:
                            # grab additional details from flightaware based on the icao code
                            flight_info = helper_functions.get_flight_info(airplane)

                            # write this flight to the database
                            if flight_info != "ignore me":
                                print(airplane['hex'] + ": adding to database")
                                helper_functions.commit_flight_info(flight_info)
                            else:
                                print(airplane['hex'] + ": no useful data - Ignoring")
                    else:
                        print(airplane['hex'] + ": outside our airspace - Ignoring")
                else:
                    print(airplane['hex'] + ": missing location information - Ignoring")


        # now let's tweet about it
        helper_functions.tweet(weather)

        print("*************************")

        # now wait a bit before checking everything again
        time.sleep(constants.sleep_time)

except Exception as e:
    print(str(e))
    print(traceback.format_exc())
    print("Something broke")
