import datetime as dt

import numpy as np

from .wfs import download_stored_query

# import time


def get_air_pollution_data(latitude_city, longitude_city, square_side=100, time=None):
    """
    Fetch and parse weather data for a neighborhood around a specified location.

    This function retrieves weather data for a square area centered around a given geographical
    location specified by its latitude and longitude. The size of the area can be adjusted.

    Parameters:
    - latitude_city (float): The latitude of the city or location of interest.
    - longitude_city (float): The longitude of the city or location of interest.
    - square_side (int, optional): The length of the side of the square area for
    which the weather data
      is to be retrieved, in kilometers. Default is 20 kilometers.

    Returns:
    - filtered_latest_observations: A dictionary containing the parsed weather data for
    the specified area.
    Example:
     {'Pirkkala Tampere-Pirkkala lentoasema': {datetime.datetime(2024, 3, 10, 19, 38):
     {'Air temperature': {'value': -1.9, 'units': 'degC'},
     'Wind speed': {'value': 0.5, 'units': 'm/s'} }

    - locations: A dictionary containing names, IDs and coordinates of the weather stations
     Example:
     {'Pirkkala Tampere-Pirkkala lentoasema':
     {'fmisid': 101118, 'latitude': 61.4194, 'longitude': 23.62256},
     'Tampere Härmälä': {'fmisid': 101124, 'latitude': 61.46561, 'longitude': 23.74678},
     'Tampere Siilinkari': {'fmisid': 101311, 'latitude': 61.51757, 'longitude': 23.75388}}

    """
    # Get current time and define time range for weather data retrieval
    if time is None:
        end_time = dt.datetime.utcnow()
    else:
        end_time = time

    start_time = end_time - dt.timedelta(minutes=100)

    # print(start_time, end_time)

    # Convert times to ISO format
    start_time_iso = start_time.isoformat(timespec="seconds") + "Z"
    end_time_iso = end_time.isoformat(timespec="seconds") + "Z"

    # Calculate latitude and longitude boundaries for filtering locations
    lat_max = latitude_city + square_side / 111
    lat_min = latitude_city - square_side / 111
    lon_max = longitude_city + square_side / (111 * np.cos(latitude_city * np.pi / 180))
    lon_min = longitude_city - square_side / (111 * np.cos(latitude_city * np.pi / 180))

    # print("Privet!")

    # Download weather data for the specified time range and bounding box

    obs = download_stored_query(
        "urban::observations::airquality::hourly::multipointcoverage",
        args=[
            f"bbox={lon_min},{lat_min},{lon_max},{lat_max}",
            "starttime=" + start_time_iso,
            "endtime=" + end_time_iso,
        ],
    )

    # print(obs)

    #     'urban::observations::airquality::hourly::multipointcoverage',
    # 'fmi::forecast::silam::airquality::surface::point::multipointcoverage',
    #  'fmi::observations::airquality::hourly::multipointcoverage',

    # Filter locations within the specified square area
    locations = {
        key: value
        for key, value in obs.location_metadata.items()
        if lat_min <= value["latitude"] <= lat_max
        and lon_min <= value["longitude"] <= lon_max
    }

    # print("Privet!")

    # Filter observations for selected locations
    filtered_observations = {}
    for key in obs.data.keys():
        value = obs.data[key]
        for loc_key in locations.keys():
            if loc_key in value:
                if loc_key not in filtered_observations:
                    filtered_observations[loc_key] = []
                filtered_observations[loc_key].append({key: value[loc_key]})

    # Extract latest observations for each location
    filtered_latest_observations = {
        loc_key: observations[-1]
        for loc_key, observations in filtered_observations.items()
    }

    # print(locations)

    return filtered_latest_observations, locations


def get_air_pollution_data_timeInterval(
    latitude_city, longitude_city, square_side=20, start=None, end=None
):
    """
    Fetch and parse weather data for a neighborhood around a specified location.

    This function retrieves weather data for a square area centered around a given geographical
    location specified by its latitude and longitude. The size of the area can be adjusted.

    Parameters:
    - latitude_city (float): The latitude of the city or location of interest.
    - longitude_city (float): The longitude of the city or location of interest.
    - square_side (int, optional): The length of the side of the square area for
    which the weather data
      is to be retrieved, in kilometers. Default is 20 kilometers.

    Returns:
    - filtered_latest_observations: A dictionary containing the parsed weather data for
    the specified area.
    Example:
     {'Pirkkala Tampere-Pirkkala lentoasema': {datetime.datetime(2024, 3, 10, 19, 38):
     {'Air temperature': {'value': -1.9, 'units': 'degC'},
     'Wind speed': {'value': 0.5, 'units': 'm/s'} }

    - locations: A dictionary containing names, IDs and coordinates of the weather stations
     Example:
     {'Pirkkala Tampere-Pirkkala lentoasema':
     {'fmisid': 101118, 'latitude': 61.4194, 'longitude': 23.62256},
     'Tampere Härmälä': {'fmisid': 101124, 'latitude': 61.46561, 'longitude': 23.74678},
     'Tampere Siilinkari': {'fmisid': 101311, 'latitude': 61.51757, 'longitude': 23.75388}}

    """
    # Get current time and define time range for weather data retrieval
    if end is None:
        end_time = dt.datetime.now()
    else:
        end_time = end

    if start is None:
        start_time = end_time - dt.timedelta(minutes=100)
    else:
        start_time = start

    # Convert times to ISO format
    start_time_iso = start_time.isoformat(timespec="seconds") + "Z"
    end_time_iso = end_time.isoformat(timespec="seconds") + "Z"

    # Calculate latitude and longitude boundaries for filtering locations
    # geolocator = Nominatim(user_agent="geoapiExercises")
    # location = geolocator.geocode(place)

    # latitude_city = location.latitude
    # longitude_city = location.longitude

    lat_max = latitude_city + square_side / 111
    lat_min = latitude_city - square_side / 111
    lon_max = longitude_city + square_side / (111 * np.cos(latitude_city * np.pi / 180))
    lon_min = longitude_city - square_side / (111 * np.cos(latitude_city * np.pi / 180))

    # Download weather data for the specified time range and bounding box
    # obs = download_stored_query("fmi::observations::weather::multipointcoverage",
    #                            args=[f"bbox={lon_min},{lat_min},{lon_max},{lat_max}",
    #                              "starttime=" + start_time_iso,
    #                              "endtime=" + end_time_iso])

    obs = download_stored_query(
        "urban::observations::airquality::hourly::multipointcoverage",
        args=[
            f"bbox={lon_min},{lat_min},{lon_max},{lat_max}",
            "starttime=" + start_time_iso,
            "endtime=" + end_time_iso,
        ],
    )

    # Filter locations within the specified square area
    locations = {
        key: value
        for key, value in obs.location_metadata.items()
        if lat_min <= value["latitude"] <= lat_max
        and lon_min <= value["longitude"] <= lon_max
    }

    # print(lat_max, lat_min, lon_max, lon_min)

    # Filter observations for selected locations
    filtered_observations = {}
    for key in obs.data.keys():
        value = obs.data[key]
        for loc_key in locations.keys():
            if loc_key in value:
                if loc_key not in filtered_observations:
                    filtered_observations[loc_key] = []
                filtered_observations[loc_key].append({key: value[loc_key]})

    # Extract latest observations for each location
    filtered_latest_observations = {
        loc_key: observations for loc_key, observations in filtered_observations.items()
    }

    # print(locations)

    return filtered_latest_observations, locations


def get_weather_data(latitude_city, longitude_city, square_side=5, time=None):
    """
    Fetch and parse weather data for a neighborhood around a specified location.

    This function retrieves weather data for a square area centered around a given geographical
    location specified by its latitude and longitude. The size of the area can be adjusted.

    Parameters:
    - latitude_city (float): The latitude of the city or location of interest.
    - longitude_city (float): The longitude of the city or location of interest.
    - square_side (int, optional): The length of the side of the square area for
    which the weather data
      is to be retrieved, in kilometers. Default is 20 kilometers.

    Returns:
    - filtered_latest_observations: A dictionary containing the parsed weather data for
    the specified area.
    Example:
     {'Pirkkala Tampere-Pirkkala lentoasema': {datetime.datetime(2024, 3, 10, 19, 38):
     {'Air temperature': {'value': -1.9, 'units': 'degC'},
     'Wind speed': {'value': 0.5, 'units': 'm/s'} }

    - locations: A dictionary containing names, IDs and coordinates of the weather stations
     Example:
     {'Pirkkala Tampere-Pirkkala lentoasema':
     {'fmisid': 101118, 'latitude': 61.4194, 'longitude': 23.62256},
     'Tampere Härmälä': {'fmisid': 101124, 'latitude': 61.46561, 'longitude': 23.74678},
     'Tampere Siilinkari': {'fmisid': 101311, 'latitude': 61.51757, 'longitude': 23.75388}}

    """
    # Get current time and define time range for weather data retrieval
    if time is None:
        end_time = dt.datetime.utcnow()
    else:
        end_time = time

    start_time = end_time - dt.timedelta(minutes=60)

    # print(start_time, end_time)

    # Convert times to ISO format
    start_time_iso = start_time.isoformat(timespec="seconds") + "Z"
    end_time_iso = end_time.isoformat(timespec="seconds") + "Z"

    # Calculate latitude and longitude boundaries for filtering locations
    lat_max = latitude_city + square_side / 111
    lat_min = latitude_city - square_side / 111
    lon_max = longitude_city + square_side / (111 * np.cos(latitude_city * np.pi / 180))
    lon_min = longitude_city - square_side / (111 * np.cos(latitude_city * np.pi / 180))

    # print("Privet!")

    # Download weather data for the specified time range and bounding box
    obs = download_stored_query(
        "fmi::observations::weather::multipointcoverage",
        args=[
            f"bbox={lon_min},{lat_min},{lon_max},{lat_max}",
            "starttime=" + start_time_iso,
            "endtime=" + end_time_iso,
        ],
    )

    # Filter locations within the specified square area
    locations = {
        key: value
        for key, value in obs.location_metadata.items()
        if lat_min <= value["latitude"] <= lat_max
        and lon_min <= value["longitude"] <= lon_max
    }

    # print("Privet!")

    # Filter observations for selected locations
    filtered_observations = {}
    for key in obs.data.keys():
        value = obs.data[key]
        for loc_key in locations.keys():
            if loc_key in value:
                if loc_key not in filtered_observations:
                    filtered_observations[loc_key] = []
                filtered_observations[loc_key].append({key: value[loc_key]})

    # Extract latest observations for each location
    filtered_latest_observations = {
        loc_key: observations[-1]
        for loc_key, observations in filtered_observations.items()
    }

    # print(locations)

    return filtered_latest_observations, locations


def get_weather_data_timeInterval(
    latitude_city, longitude_city, square_side=20, start=None, end=None
):
    """
    Fetch and parse weather data for a neighborhood around a specified location.

    This function retrieves weather data for a square area centered around a given geographical
    location specified by its latitude and longitude. The size of the area can be adjusted.

    Parameters:
    - latitude_city (float): The latitude of the city or location of interest.
    - longitude_city (float): The longitude of the city or location of interest.
    - square_side (int, optional): The length of the side of the square area for
    which the weather data
      is to be retrieved, in kilometers. Default is 20 kilometers.

    Returns:
    - filtered_latest_observations: A dictionary containing the parsed weather data for
    the specified area.
    Example:
     {'Pirkkala Tampere-Pirkkala lentoasema': {datetime.datetime(2024, 3, 10, 19, 38):
     {'Air temperature': {'value': -1.9, 'units': 'degC'},
     'Wind speed': {'value': 0.5, 'units': 'm/s'} }

    - locations: A dictionary containing names, IDs and coordinates of the weather stations
     Example:
     {'Pirkkala Tampere-Pirkkala lentoasema':
     {'fmisid': 101118, 'latitude': 61.4194, 'longitude': 23.62256},
     'Tampere Härmälä': {'fmisid': 101124, 'latitude': 61.46561, 'longitude': 23.74678},
     'Tampere Siilinkari': {'fmisid': 101311, 'latitude': 61.51757, 'longitude': 23.75388}}

    """
    # Get current time and define time range for weather data retrieval
    if end is None:
        end_time = dt.datetime.now()
    else:
        end_time = end

    if start is None:
        start_time = end_time - dt.timedelta(minutes=100)
    else:
        start_time = start

    # Convert times to ISO format
    start_time_iso = start_time.isoformat(timespec="seconds") + "Z"
    end_time_iso = end_time.isoformat(timespec="seconds") + "Z"

    # Calculate latitude and longitude boundaries for filtering locations
    # geolocator = Nominatim(user_agent="geoapiExercises")
    # location = geolocator.geocode(place)

    # latitude_city = location.latitude
    # longitude_city = location.longitude

    lat_max = latitude_city + square_side / 111
    lat_min = latitude_city - square_side / 111
    lon_max = longitude_city + square_side / (111 * np.cos(latitude_city * np.pi / 180))
    lon_min = longitude_city - square_side / (111 * np.cos(latitude_city * np.pi / 180))

    # Download weather data for the specified time range and bounding box
    obs = download_stored_query(
        "fmi::observations::weather::multipointcoverage",
        args=[
            f"bbox={lon_min},{lat_min},{lon_max},{lat_max}",
            "starttime=" + start_time_iso,
            "endtime=" + end_time_iso,
        ],
    )

    # print(obs)

    # Filter locations within the specified square area
    locations = {
        key: value
        for key, value in obs.location_metadata.items()
        if lat_min <= value["latitude"] <= lat_max
        and lon_min <= value["longitude"] <= lon_max
    }

    # print(lat_max, lat_min, lon_max, lon_min)

    # Filter observations for selected locations
    filtered_observations = {}
    for key in obs.data.keys():
        value = obs.data[key]
        for loc_key in locations.keys():
            if loc_key in value:
                if loc_key not in filtered_observations:
                    filtered_observations[loc_key] = []
                filtered_observations[loc_key].append({key: value[loc_key]})

    # Extract latest observations for each location
    filtered_latest_observations = {
        loc_key: observations for loc_key, observations in filtered_observations.items()
    }

    # print(locations)

    return filtered_latest_observations, locations
