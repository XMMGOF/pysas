# xmmfiles.py
#
# Written by: Ryan Tanner
# email: ryan.tanner@nasa.gov
#
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
# 
# xmmfiles.py
# 
# Contains classes for different files used by SAS and pySAS.

import os
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.units import Quantity
from pathlib import Path

from pysas.sasutils import parse_value, set_unit

class XMMFits:
    """
    A utility class for managing and extracting data from XMM-Newton FITS files.
    """
    
    def __init__(self, filename):

        if isinstance(filename, str):
            fits_file = Path(filename)
        elif isinstance(filename, fits.hdu.hdulist.HDUList):
            fits_file = Path(filename.filename())
        elif isinstance(filename, pathlib.PosixPath):
            fits_file = filename
        else:
            if not os.path.exists(filename):
                raise FileNotFoundError(f"File not found: {filename}")

        self._fits_file = fits_file
        self._filename  = fits_file.name
        self._file_dir  = fits_file.parent
        self._extension = fits_file.suffix
        
        if not self._fits_file.exists():
            raise FileNotFoundError(f"File not found: {self._fits_file}")

        try:
            self._xmmhdul = fits.open(self._fits_file)
        except Exception as e:
            raise ValueError(f"{self._filename} not recognized as a FITS file: {e}")

        self._telescope     = None
        self._instrument    = None
        self._obs_id        = None
        self._exposure_time = None
        self._data          = None
            
        # Verify it's actually an XMM file upon initialization
        self._telescope = self.get_keyword('TELESCOP', ext=0)
        if self._telescope != 'XMM':
            print(f"Warning: TELESCOP keyword is '{self._telescope}', expected 'XMM'.")
        else:
            self._primary_head  = self.get_header()
            self._instrument    = self.get_keyword('INSTRUME', ext=0)
            self._obs_id        = self.get_keyword('OBS_ID', ext=0)
            keyword = 'ONTIME'
            if not self.has_keyword(keyword, ext=1): keyword = 'EXPOSURE'
            et = self.get_keyword(keyword, ext=1, default=0.0)
            self._exposure_time = set_unit(et,'s')
            self._data          = self.get_data()

    # ---------------------------------------------------------
    # Properties (Quick access to common XMM metadata)
    # ---------------------------------------------------------
    @property
    def telescope(self):
        """For XMM files should be 'XMM'."""
        return self._telescope

    @property
    def instrument(self):
        """Returns the instrument name (e.g., EPN, EMOS1, EMOS2)."""
        return self._instrument

    @property
    def obs_id(self):
        """Returns the Observation ID."""
        return self._obs_id
        
    @property
    def exposure_time(self):
        """Returns the total exposure time in seconds."""
        return self._exposure_time.value

    @property
    def filename(self):
        """Returns the filename (and path if included)."""
        return str(self._fits_file)

    # ---------------------------------------------------------
    # Header Methods
    # ---------------------------------------------------------
    def has_keyword(self, keyword, ext=0):
        """
        Checks if a keyword exists in the header of a specific extension.
        'ext' can be an integer (0 for primary) or a string (e.g., 'EVENTS').
        """
        with fits.open(self._fits_file) as hdul:
            try:
                header = hdul[ext].header
                return keyword in header
            except KeyError:
                raise KeyError(f"Extension '{ext}' not found in the FITS file.")

    def get_keyword(self, keyword, ext=0, default=None):
        """
        Retrieves the value of a header keyword. 
        Returns 'default' if the keyword doesn't exist.
        """
        with fits.open(self._fits_file) as hdul:
            try:
                header = hdul[ext].header
                return header.get(keyword, default)
            except KeyError:
                raise KeyError(f"Extension '{ext}' not found in the FITS file.")

    def get_header(self, ext=0):
        """
        Returns the entire header for a given extension as an astropy Header object.
        """
        with fits.open(self._fits_file) as hdul:
            return hdul[ext].header.copy()

    # ---------------------------------------------------------
    # Data Retrieval Methods
    # ---------------------------------------------------------

    def get_data(self, ext=1):
        """
        Extracts data by default from the first extension.
        """
        with fits.open(self._fits_file) as hdul:
            data = hdul[ext].data
            if data is None:
                raise ValueError(f"No data found in extension {ext}.")
            # Return a copy so the array remains accessible after the file closes
            return data.copy()

    def get_column(self, col_name, ext=1):
        """
        Shortcut to extract a single column of data (e.g., 'TIME', 'PI', 'RAWX') 
        as a numpy array.
        """
        with fits.open(self._fits_file) as hdul:
            try:
                data = hdul[ext].data
                return np.array(data[col_name])
            except KeyError:
                raise KeyError(f"Column '{col_name}' not found in extension '{ext}'.")

    # ---------------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------------
    def info(self):
        """Prints a summary of the FITS file extensions and properties."""
        print(f"--- XMM FITS Info: {self._filename} ---")
        print(f"Instrument : {self.instrument}")
        print(f"Obs ID     : {self.obs_id}")
        print("-" * 40)
        # astropy has a built-in info method that prints HDU structure
        with fits.open(self._fits_file) as hdul:
            hdul.info()

class XMMEventList(XMMFits):

    def __init__(self,fits_file):
        super().__init__(fits_file)

    def create_light_curve(self,
                           dt, 
                           time_col='TIME', 
                           ext_name='EVENTS',
                           gti=None):
        """
        Reads an XMM-Newton event list, extracts events and GTIs, and bins them.
        XMM-Newton typically stores GTIs in extensions starting with 'STDGTI' or 'GTI'.
        """

        from pysas.lightcurve import XMMLightCurve

        event_times = self._data[time_col]
        
        # 2. Search for XMM-Newton GTI extensions
        # gti_list = []
        # for hdu in self._xmmhdul:
        #     if 'GTI' in hdu.name: # Catches STDGTI, GTI, STDGTI04, etc.
        #         gti_list.append(np.column_stack((hdu.data['START'], hdu.data['STOP'])))
        
        # if gti_list:
        #     # If multiple GTI extensions exist (e.g., different CCDs), 
        #     # we stack and use the bounding boxes, or simply take the first one.
        #     # For a basic class, we take the primary/first GTI extension.
        #     gti = gti_list[0] 
        # else:

        # 3. Bin the events into a lightcurve
        if gti is not None:
            t_start, t_stop = gti[:, 0].min(), gti[:, 1].max()
        else:
            t_start, t_stop = event_times.min(), event_times.max()

        bins = np.arange(t_start, t_stop + dt, dt)
        counts, edges = np.histogram(event_times, bins=bins)
        time_centers = edges[:-1] + (dt / 2)

        self.light_curve = XMMLightCurve(time=edges[:-1], counts=counts, dt=dt, err=None, instr=self.instrument)

        return self.light_curve
