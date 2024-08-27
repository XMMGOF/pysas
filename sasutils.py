# ESA (C) 2000-2024
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

# sasutils.py

"""
sasutils.py

Utility functions specific to SAS or pySAS.
"""

# Standard library imports
import os, subprocess, time

# Third party imports

# Local application imports



def update_calibration_files(repo='NASA'):
    """
    Function to download/update XMM calibration files.
    """

    sas_ccfpath = os.environ.get('SAS_CCFPATH')
    if not sas_ccfpath:
        raise Exception('SAS_CCFPATH not set. Please define it.')

    esa_or_nasa = repo.lower()

    esa = ['esa','e','es','europe']
    nasa = ['nasa','n','na','nas','ns','nsa','us','usa','heasarc','hea']

    if esa_or_nasa in esa:
        cmd = f'rsync -v -a --delete --delete-after --force --include=\'*.CCF\' --exclude=\'*/\' sasdev-xmm.esac.esa.int::XMM_VALID_CCF {sas_ccfpath}'
    elif esa_or_nasa in nasa:
        cmd = f'wget -nH --no-remove-listing -N -np -r --cut-dirs=4 -e robots=off -l 1 -R "index.html*" https://heasarc.gsfc.nasa.gov/FTP/xmm/data/CCF/ -P {sas_ccfpath}'
    print(f'Downloading calibration data using the command:\n{cmd}')
    print('This may take a while.')
    time.sleep(3)
    result = subprocess.run(cmd, shell=True)

    return result
