# xmmfiles.py
#
# Written by: Ryan Tanner
# email: ryan.tanner@nasa.gov
#
# ESA (C) 2000-2026
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

# Standard library imports
import os, warnings
from pathlib import Path

# Third party imports
import numpy as np
from numpy.typing import NDArray
from astropy.io import fits
from astropy.table import Table
from astropy.units import Quantity
from astropy import units as u
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.utils.exceptions import AstropyWarning

# Local application imports
from pysas.sasutils import (parse_value, 
                            set_unit,
                            validate_event_list_pattern,)
from pysas.logger import (_logger, 
                          _log_enable_terminal, 
                          _log_disable_terminal, 
                          _log_enable_file, 
                          _log_disable_file,)

class XMMFits:
    """
    A utility class for managing and extracting data from XMM-Newton FITS files.
    """
    
    def __init__(self, filename):

        self._remote  = False
        self._xmmhdul = None

        if isinstance(filename, str):
            if self._check_if_aws_s3(filename):
                self._remote = True
                # If the file is remote we have to keep 
                # the path and name literal because pathlib
                # will mess it up.
                fits_file = filename
            else:
                fits_file = Path(filename)
        elif isinstance(filename, fits.hdu.hdulist.HDUList):
            fits_file = Path(filename.filename())
            self._xmmhdul = filename
        elif isinstance(filename, pathlib.PosixPath):
            fits_file = filename
        else:
            if not os.path.exists(filename):
                raise FileNotFoundError(f"File not found: {filename}")

        self._fits_file = fits_file
        
        if not self._remote and not os.path.exists(self.filename):
            raise FileNotFoundError(f"File not found: {self._fits_file}")

        try:
            if self._xmmhdul is None:
                self._xmmhdul = fits.open(self._fits_file, 
                                          use_fsspec=True, 
                                          fsspec_kwargs={"anon": True})
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
            ext = ''
            ext_names = ['EVENTS','RATE','COUNTS','SPECTRUM','SPECRESP',
                         'BADPIX','STDGTI','ATTHK','CALINDEX','MATRIX',
                         'EBOUNDS',
                         ]
            for extnm in ext_names:
                if extnm in self._xmmhdul:
                    ext = extnm
                    break
            if ext:
                self._data      = self.get_data(ext=ext)
                self._data_head = self.get_header(ext=ext)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', AstropyWarning)
                    self._wcs       = WCS(self._data_head, keysel=['pixel'])
            else:
                self._data      = self.get_data(ext=0)
                if self._data is not None:
                    self._data_head = self.get_header(ext=0)
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', AstropyWarning)
                        self._wcs   = WCS(self._data_head)
                else:
                    self._data_head = None
                    self._wcs = None

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
        if isinstance(self._fits_file, str):
            return self._fits_file
        else:
            return str(self._fits_file)

    @property
    def _filepath(self):
        """Returns the file path."""
        if isinstance(self._fits_file, str):
            return os.path.dirname(self._fits_file)
        else:
            return self._fits_file.parent

    @property
    def _filename(self):
        """Returns *just* the filename (no path)."""
        if isinstance(self._fits_file, str):
            return os.path.basename(self._fits_file)
        else:
            return self._fits_file.name

    @property
    def _extension(self):
        """Returns the file extension."""
        if isinstance(self._fits_file, str):
            _, extension = os.path.splitext(self._fits_file)
            return extension
        else:
            return self._fits_file.suffix

    @property
    def primary_header(self):
        return self._primary_head

    @property
    def data(self):
        return self._data

    @property
    def data_header(self):
        return self._data_head

    @property
    def wcs(self):
        return self._wcs

    # ---------------------------------------------------------
    # Header Methods
    # ---------------------------------------------------------
    def has_keyword(self, keyword, ext=0):
        """
        Checks if a keyword exists in the header of a specific extension.
        'ext' can be an integer (0 for primary) or a string (e.g., 'EVENTS').
        """
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
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
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
            try:
                header = hdul[ext].header
                return header.get(keyword, default)
            except KeyError:
                raise KeyError(f"Extension '{ext}' not found in the FITS file.")

    def get_header(self, ext=0):
        """
        Returns the entire header for a given extension as an astropy Header object.
        """
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
            return hdul[ext].header.copy()

    # ---------------------------------------------------------
    # Data Retrieval Methods
    # ---------------------------------------------------------

    def get_data(self, ext=1):
        """
        Extracts data by default from the first extension.
        """
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
            data = hdul[ext].data
            if data is None:
                raise ValueError(f"No data found in extension {ext}.")
            # Return a copy so the array remains accessible after the file closes
            if isinstance(hdul[ext], fits.BinTableHDU):
                return Table(data.copy())
            else:
                return data.copy()

    def get_column(self, col_name, ext=1):
        """
        Shortcut to extract a single column of data (e.g., 'TIME', 'PI', 'RAWX') 
        as a numpy array.
        """
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
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
        with fits.open(self._fits_file,use_fsspec=True,fsspec_kwargs={"anon": True}) as hdul:
            hdul.info()

    def _check_if_aws_s3(self,filename):
        return filename[:32] == 's3://nasa-heasarc/xmm/data/rev0/'


