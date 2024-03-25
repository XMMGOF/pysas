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

# eslewchainUtils

# Utilities for the eslewchain script.

import os
import subprocess
from astropy.io import fits

def delete_exposure_xtns(fill_file):
    """
    Removes exposure extensions from an event fle.
    
    Args:
        fill_file: name of the file.
    """

    with fits.open(fill_file, 'update') as fits_file:
        print('Deleting exposures from file: {}'.format(fill_file))
        try:
            del(fits_file['EXPOSU01'])
        except KeyError:
            print('Exposure 01 not deleted - not found')
        try:
            del(fits_file['EXPOSU02'])
        except KeyError:
            print('Exposure 02 not deleted - not found')
        try:
            del(fits_file['EXPOSU03'])
        except KeyError:
            print('Exposure 03 not deleted - not found')
        try:
            del(fits_file['EXPOSU04'])
        except KeyError:
            print('Exposure 04 not deleted - not found')
        try:
            del(fits_file['EXPOSU05'])
        except KeyError:
            print('Exposure 05 not deleted - not found')
        try:
            del(fits_file['EXPOSU06'])
        except KeyError:
            print('Exposure 06 not deleted - not found')
        try:
            del(fits_file['EXPOSU07'])
        except KeyError:
            print('Exposure 07 not deleted - not found')
        try:
            del(fits_file['EXPOSU08'])
        except KeyError:
            print('Exposure 08 not deleted - not found')
        try:
            del(fits_file['EXPOSU09'])
        except KeyError:
            print('Exposure 09 not deleted - not found')
        try:
            del(fits_file['EXPOSU10'])
        except KeyError:
            print('Exposure 10 not deleted - not found')
        try:
            del(fits_file['EXPOSU11'])
        except KeyError:
            print('Exposure 11 not deleted - not found')
        try:
            del(fits_file['EXPOSU12'])
        except KeyError:
            print('Exposure 12 not deleted - not found')
        fits_file.flush()

    print('Exposures deleted.')


def check_exp_extrns(event_file):
    """
    checks if all exposure extensions are present in the evt file
    Args:
        event_file: the event file.
    Output:
        str: an error if there are missing exposures.
    """

    exposure_count = 0
    with fits.open(event_file) as ev_file:
        for i in range(0, len(ev_file)):
            if 'EXPOSU' in ev_file[i].name:
                exposure_count = exposure_count + 1

    if exposure_count != 12:
        return 'The event file is missing at least one expousre.'
    else:
        print('Correct number of exposures.')


def rename_and_clean(obs, event_file):
    """
    Changes the name of some output files and removes other temporary files.
    
    Args:
        obs: observation number
        event_file: an event file.
    """

    att_file = 'P' + obs + 'OBX000ATTTSR0000.ds'
    os.system('mv ' + 'atthk.dat ' + '{}'.format(att_file))
    out_event_file = "P" + obs + "PNS" + "003" + "SLEVLI0000.ds"
    os.system('cp ' + event_file + ' ' + out_event_file)
    # once they have been renamed, now, remove the temporary files.
    os.system('rm ' + 'histo.fits ' + 'image.fits ' + 'spectrum.fits')

