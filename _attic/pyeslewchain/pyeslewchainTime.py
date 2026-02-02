# ESA (C) 2000-2020
# 
# This file is part of ESA's XMM-Newton Scientific Analysis System (SAS).
#
#    SAS is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    SAS is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SAS.  If not, see <http://www.gnu.org/licenses/>.

#eslewchainTime

# Time conversion functions for the eslewchain script.

def MRT_to_MJD(mrt):
    """
    Converts from Mission Reference Time to Modified Julian Day.
    Args:
        mrt: Mission Reference Time
    
    Output:
        mjd: the MJD time.
    """

    # Define the MJD where MRT is zero (actually 1997-12-31T23:58:56.816 UTC)
    mjd0 = 50813.9992687037
    mjd = mjd0 + mrt / 86400.0
    # Adds Leap seconds:
    mjd = add_leap_seconds(mjd)
    
    return mjd


def add_leap_seconds(mjd):
    """
    Adds the leap seconds dependeing on the given condition.
    
    Args: 
        mjd: the Modified Julian Day
    Output:
        mjd: the MJD modified counting leap seconds.
    """

    # Adds on defined leap seconds
    if mjd > 51179.0:
        mjd = mjd + 1.0 / 86400.0
    if mjd > 53736.0:
        mjd = mjd + 1.0 / 86400.0
    if mjd > 54832.0:
        mjd = mjd + 1.0 / 86400.0
    if mjd > 56109.0:
        mjd = mjd + 1.0 / 86400.0
    
    return mjd
