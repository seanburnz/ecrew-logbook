import datetime
from sunrisesunset import SunriseSunset


def night_hours(dep_datetime, dep_lat, dep_lon, arr_datetime, arr_lat, arr_lon, zenith='civil'):
    """ routine to calculate the night hours on a flight from one location to
        another, returns datetime.timedelta for day and night hours and a boolean to say
        if the landing (arrival) occurred at night """

    one_day = datetime.timedelta(days=1)

    if dep_datetime.tzinfo is None:
        dep_datetime = dep_datetime.replace(tzinfo=UTC())

    if arr_datetime.tzinfo is None:
        arr_datetime = arr_datetime.replace(tzinfo=UTC())

    td_total = arr_datetime - dep_datetime

    dep_sunrise_sunset = SunriseSunset(dep_datetime, dep_lat, dep_lon, zenith)
    arr_sunrise_sunset = SunriseSunset(arr_datetime, arr_lat, arr_lon, zenith)

    is_night_dep = dep_sunrise_sunset.isNight()
    is_night_arr = arr_sunrise_sunset.isNight()

    if is_night_dep == is_night_arr:
        if is_night_dep:
            # all night time
            td_night = td_total
            td_day = datetime.timedelta(0)  # zero
        else:
            # all day time
            td_day = td_total
            td_night = datetime.timedelta(0)
    else:
        # night hour calculation necessary
        tp1 = dep_datetime
        tp2 = arr_datetime

        if is_night_arr:
            # day to night - get ts1 next sunset immediately after dep_datetime tp1
            working_date = dep_datetime - one_day
            next_sunrise_sunset = SunriseSunset(working_date, dep_lat, dep_lon, zenith)
            ts1 = next_sunrise_sunset.getSunRiseSet()[1]
            while ts1 < tp1:
                # move forward a day
                working_date = working_date + one_day
                next_sunrise_sunset = SunriseSunset(working_date, dep_lat, dep_lon, zenith)
                ts1 = next_sunrise_sunset.getSunRiseSet()[1]

            # calculate ts2 - the sunset immediately before arr_datetime tp2
            working_date = arr_datetime + one_day
            next_sunrise_sunset = SunriseSunset(working_date, arr_lat, arr_lon, zenith)
            ts2 = next_sunrise_sunset.getSunRiseSet()[1]
            while ts2 > tp2:
                # move back a day
                working_date = working_date - one_day
                next_sunrise_sunset = SunriseSunset(working_date, arr_lat, arr_lon, zenith)
                ts2 = next_sunrise_sunset.getSunRiseSet()[1]

        else:

            # night to day - get ts1 next sunrise after departure time
            working_date = dep_datetime - one_day
            next_sunrise_sunset = SunriseSunset(working_date, dep_lat, dep_lon, zenith)
            ts1 = next_sunrise_sunset.getSunRiseSet()[0]
            while ts1 < tp1:
                # move forward a day
                working_date = working_date + one_day
                next_sunrise_sunset = SunriseSunset(working_date, dep_lat, dep_lon, zenith)
                ts1 = next_sunrise_sunset.getSunRiseSet()[0]

            # night to day - ts2 = sunrise preceding arrival time
            working_date = arr_datetime + one_day
            next_sunrise_sunset = SunriseSunset(working_date, arr_lat, arr_lon, zenith)
            ts2 = next_sunrise_sunset.getSunRiseSet()[0]
            while ts2 > tp2:
                # move back a day
                working_date = working_date - one_day
                next_sunrise_sunset = SunriseSunset(working_date, arr_lat, arr_lon, zenith)
                ts2 = next_sunrise_sunset.getSunRiseSet()[0]

        # calculate t, the time the flight meets the sun transition
        """ tp1 = time plane departs
            tp2 = time plane arrives
            ts1 = time of sun transition at departure location
            ts2 = time of sun transition at arrival location
            t = time of intersection

            formula:
            t-tp1 = (ts1-tp1)*(tp2-tp1)/((tp2-tp1)-(ts2-ts1)) """
        tdp = (tp2 - tp1).total_seconds()
        tds = (ts2 - ts1).total_seconds()
        tdsp1 = (ts1 - tp1).total_seconds()

        tdttp1 = tdsp1 * tdp / (tdp - tds)  # seconds into flight that sunrise/sunset is met
        tdttp1 = datetime.timedelta(seconds=tdttp1)

        if is_night_arr:
            # day to night
            td_day = hhmm_td(td_hhmm(tdttp1))  # rounds to the nearest minute
            td_night = tp2 - tp1 - td_day
        else:
            # night to day
            td_night = hhmm_td(td_hhmm(tdttp1))
            td_day = tp2 - tp1 - td_night

    return td_day, td_night, is_night_arr


def td_hhmm(td):
    """ helper function to convert a timedelta to a string in the format 'hh:mm' """
    sec = td.total_seconds()
    hh = int(sec / 3600)
    mm = int(round((sec - 3600 * hh) / 60))
    if mm == 60:
        # rounding up from e.g. 02:59:35 would make 02:60 instead of 03:00
        hh += 1
        mm = 0
    hh = str(hh)
    mm = str(mm)
    while len(hh) < 2:
        hh = '0' + hh
    while len(mm) < 2:
        mm = '0' + mm
    hhmm = hh + ':' + mm
    return hhmm


def hhmm_td(hhmm):
    hh = int(hhmm[:hhmm.index(':')])
    mm = int(hhmm[hhmm.index(':') + 1:])
    td = datetime.timedelta(hours=hh, minutes=mm)
    return td


# A UTC tzinfo class.
class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)
