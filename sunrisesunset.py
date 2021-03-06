#!/usr/bin/env python
#
# sunrisesunset.py
#
# This code is valid for dates from 1901 to 2099, and will not calculate
# sunrise/sunset times for latitudes above/below 63/-63 degrees.
#
# No external packages are used when using the class SunriseSunset. If you
# run the tests you will need to install pytz as shown below or use your
# package installer if it's available.
#
# $ sudo easy_install --upgrade pytz
#
# CVS/SVN Info
# ----------------------------------
# $Author: cnobile $
# $Date: 2009-08-03 00:47:13 $
# $Revision: 1.9 $
# ----------------------------------
#
# Contributions by:
#    Darryl Smith -- Noticed a bug with atan fixed with atan2.
#
##########################################################################
# Copyright (c) 2009 Carl J. Nobile.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# This Copyright covers only the implimentation of the algorithm used in
# this code and does not cover the algorithm itself which is in the
# public domain.
#
# Contributors:
#    Carl J. Nobile - initial API and implementation
##########################################################################

from __future__ import absolute_import
from __future__ import print_function
import datetime
from math import degrees, radians, atan2, cos, sin, pi, sqrt, fabs


class SunriseSunset(object):
    """
    This class determines the sunrise and sunset for zenith standards for the
    given day. It can also tell you if the given time is during the night or
    day.
    """
    __ZENITH = {'official': -0.833,
                'civil': -6.0,
                'nautical': -12.0,
                'amateur': -15.0,
                'astronomical': -18.0}

    def __init__(self, date, lat, lon, zenith='official'):
        """
        Set the values for the sunrise and sunset calculation.

        @param date: A localized datetime object that is timezone aware.
        @param lat: The latitude.
        @param lon: The longitude.
        @keyword zenith: The zenith name.
        """
        if not isinstance(date, datetime.datetime) or date.tzinfo is None:
            msg = "The date must be a datetime object with timezone info."
            raise ValueError(msg)

        if zenith not in self.__ZENITH:
            msg = "Invalid zenith name [%s] must be one of: %s"
            raise ValueError(msg % (zenith, list(self.__ZENITH.keys())))

        if abs(lat) > 67:
            raise ValueError('Invalid latitude: %s' % lat)

        self.__dateLocal = date
        self.__lat = lat
        self.__lon = lon
        self.__zenith = zenith
        local_tuple = date.timetuple()
        utc_tuple = date.utctimetuple()
        self.__offsetUTC = (local_tuple[3] - utc_tuple[3]) + \
                           (local_tuple[4] - utc_tuple[4]) / 60.0
        self.__sunrise = None
        self.__sunset = None
        self.__determine_riseset()

    def is_night(self, collar=0):
        """
        Check if it is day or night. If the 'collar' keyword argument is
        changed it will skew the results to either before or after the real
        sunrise and sunset. This is useful if lead and lag timea are needed
        around the actual sunrise and sunset.

        Note::
            If collar == 30 then this method will say it is daytime 30
            minutes before the actual sunrise and likewise 30 minutes after
            sunset it would indicate it is night.

        @keyword collar: The minutes before or after sunrise and sunset.
        @return: True if it is night else False if day.
        """
        result = False
        # delta = datetime.timedelta(minutes=collar)

        # if (self.__sunrise - delta) > self.__dateLocal or \
        #        self.__dateLocal > (self.__sunset + delta):
        #     result = True
        #
        # return result

        #  Above comment out and below code modified by Sean Burns Aug 2014 to give a better is_night calc

        """To determine if it is day or night we need to find the last transition (sunrise or sunset)
        that occurred before the time in question.
        If the last transition was a sunrise then it is day, if it was a sunset then it is night"""

        # move forward a day, then start working backwards until a sunrise or a sunset or both occur
        # before the datetime in question
        one_day = datetime.timedelta(days=1)
        working_date = self.__dateLocal + one_day
        next_sunriseset = SunriseSunset(working_date, self.__lat, self.__lon, self.__zenith)
        while next_sunriseset.get_sunriseset()[0] > self.__dateLocal \
                and next_sunriseset.get_sunriseset()[1] > self.__dateLocal:
            working_date = working_date - one_day
            next_sunriseset = SunriseSunset(working_date, self.__lat, self.__lon, self.__zenith)

        if next_sunriseset.get_sunriseset()[0] < self.__dateLocal \
                and next_sunriseset.get_sunriseset()[1] < self.__dateLocal:
            # both sunrise and sunset occur before
            if next_sunriseset.get_sunriseset()[1] > next_sunriseset.get_sunriseset()[0]:
                # sunset is the last occurrence
                result = True
        else:
            # only one of the two transitions occurs before
            if next_sunriseset.get_sunriseset()[1] < self.__dateLocal:
                # sunset occured before
                result = True

        return result

    def get_sunriseset(self):
        """
        Get the sunrise and sunset.

        @return: A C{datetime} object in a tuple (sunrise, sunset).
        """
        return self.__sunrise, self.__sunset

    def __determine_riseset(self):
        """
        Determine both the sunrise and sunset.
        """
        year = self.__dateLocal.year
        month = self.__dateLocal.month
        day = self.__dateLocal.day
        # Ephemeris
        ephem2000_day = 367 * year - (7 * (year + (month + 9) / 12) / 4) + \
            (275 * month / 9) + day - 730531.5
        self.__sunrise = self.__determine_rise_or_set(ephem2000_day, 1)
        self.__sunset = self.__determine_rise_or_set(ephem2000_day, -1)

    def __determine_rise_or_set(self, ephem2000_day, rs):
        """
        Determine either the sunrise or the sunset.

        @param ephem2000_day: The Ephemeris from the beginning of the
                             21st century.
        @param rs: The factor that determines either sunrise or sunset where
                   1 equals sunrise and -1 sunset.
        @return: Either the sunrise or sunset as a C{datetime} object.
        """
        utold = pi
        utnew = 0
        altitude = self.__ZENITH[self.__zenith]
        sin_alt = sin(radians(altitude))  # solar altitude
        sin_phi = sin(radians(self.__lat))  # viewer's latitude
        cos_phi = cos(radians(self.__lat))  #
        lon = radians(self.__lon)  # viewer's longitude
        ct = 0
        # print rs, ephem2000Day, sin_alt, sin_phi, cos_phi, lon

        while fabs(utold - utnew) > 0.001 and ct < 35:
            ct += 1
            utold = utnew
            days = ephem2000_day + utold / (2 * pi)
            t = days / 36525
            # The magic numbers are orbital elements of the sun.
            ell = self.__get_range(4.8949504201433 + 628.331969753199 * t)
            g = self.__get_range(6.2400408 + 628.3019501 * t)
            ec = 0.033423 * sin(g) + 0.00034907 * sin(2 * g)
            lam = ell + ec
            e = -1 * ec + 0.0430398 * sin(2 * lam) - 0.00092502 * sin(4 * lam)
            obl = 0.409093 - 0.0002269 * t
            delta = sin(obl) * sin(lam)
            delta = atan2(delta, sqrt(1 - delta * delta))
            gha = utold - pi + e
            cosc = (sin_alt - sin_phi * sin(delta)) / (cos_phi * cos(delta))

            if cosc > 1:
                correction = 0
            elif cosc < -1:
                correction = pi
            else:
                correction = atan2((sqrt(1 - cosc * cosc)), cosc)

            # print cosc, correction, utold, utnew
            utnew = self.__get_range(utold - (gha + lon + rs * correction))

        decimal_time = degrees(utnew) / 15
        # print utnew, decimal_time
        return self.__get_24_hour_local_time(rs, decimal_time)

    def __get_range(self, value):
        """
        Get the range of the value.

        @param value: The domain.
        @return: The resultant range.
        """
        tmp1 = value / (2.0 * pi)
        tmp2 = (2.0 * pi) * (tmp1 - int(tmp1))
        if tmp2 < 0.0:
            tmp2 += (2.0 * pi)
        return tmp2

    def __get_24_hour_local_time(self, rs, decimal_time):
        """
        Convert the decimal time into a local time (C{datetime} object)
        and correct for a 24 hour clock.

        @param rs: The factor that determines either sunrise or sunset where
                   1 equals sunrise and -1 sunset.
        @param decimal_time: The decimal time.
        @return: The C{datetime} objects set to either sunrise or sunset.
        """
        decimal_time += self.__offsetUTC
        # print decimalTime

        if decimal_time < 0.0:
            decimal_time += 24.0
        elif decimal_time > 24.0:
            decimal_time -= 24.0

        # print decimalTime
        hour = int(decimal_time)
        tmp = (decimal_time - hour) * 60
        minute = int(tmp)
        tmp = (tmp - minute) * 60
        second = int(tmp)
        micro = int(round((tmp - second) * 1000000))
        local_dt = self.__dateLocal.replace(hour=hour, minute=minute,
                                            second=second, microsecond=micro)
        return local_dt
