"""Constants for the ADS-B Aircraft Tracker integration."""

DOMAIN = "adsb_tracker"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PATH = "path"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_LATITUDE = "receiver_latitude"
CONF_LONGITUDE = "receiver_longitude"

CONF_AIRCRAFT = "aircraft"  # list of {tail_number, name} stored in config entry options
CONF_TAIL_NUMBER = "tail_number"
CONF_NAME = "name"

DEFAULT_HOST = "192.168.7.52"
DEFAULT_PORT = 8080
DEFAULT_PATH = "/data/aircraft.json"
DEFAULT_SCAN_INTERVAL = 15

ATTR_FLIGHT = "flight"
ATTR_HEX = "hex"
ATTR_ALTITUDE = "altitude_ft"
ATTR_GROUND_SPEED = "ground_speed_kt"
ATTR_TRACK = "track_deg"
ATTR_LAT = "latitude"
ATTR_LON = "longitude"
ATTR_DISTANCE = "distance_nm"
ATTR_SQUAWK = "squawk"

EVENT_AIRCRAFT_SEEN = "adsb_tracker_aircraft_seen"
