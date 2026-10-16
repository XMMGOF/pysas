# lightcurve.py
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
# lightcurve.py

import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.units import Quantity
from astropy import units as u
from pathlib import Path

from pysas.xmmfiles import XMMFits
from pysas.sasutils import parse_value, set_unit
from pysas.logger import (_logger, 
                          _log_enable_terminal, 
                          _log_disable_terminal, 
                          _log_enable_file, 
                          _log_disable_file,)

class XMMLightCurve:
    """
    A class to generate, store, and manipulate XMM-Newton X-ray light curves.
    """

    ######
    # This class was created after looking at how other analysis codes 
    # handle light curves. Codes consulted include: SAS, Stingray, XGA, 
    # CIAO, HEASoft, and HENDRICS.
    # 
    # The outline of what was needed was turned into an AI prompt using 
    # ChatGSFC at NASA Goddard which created the basic structure of the 
    # class. The class was then extensively modified to handle all the 
    # instances where the AI had difficutly generating a solution.
    #
    
    def __init__(self,
                 time: list | NDArray | Quantity,
                 counts: list | NDArray | Quantity = None,
                 rate: list | NDArray | Quantity = None,
                 err: list | NDArray | Quantity = None,
                 dt: int | float | Quantity = None,
                 gti: list | tuple = None,
                 err_dist:str = "poisson",
                 instr: str = None,
                 **other_kw,
                ):
        
        self._xunit = u.second

        self._time = set_unit(time, self._xunit)

        if dt is None:
            dt = self._time[1] - self._time[0]

        self._dt = set_unit(dt, self._xunit)

        self._bin_lo = self._time[0]
        self._bin_hi = self._time[-1]

        if counts is None and rate is None:
            raise ValueError('Either a counts or rate array must be passed in.')

        if rate is None:
            self._yunit = u.photon
            self._counts = set_unit(counts, self._yunit)
            if err is not None:
                self._counts_err = set_unit(err, self._yunit)
            self._compute_from_counts()
        else:
            self._yunit = u.photon / u.second
            self._rate = set_unit(rate, self._yunit)
            if err is not None:
                self._rate_err = set_unit(err, self._yunit)
            self._compute_from_rate()

        self.instrument = instr

        self._meanrate = None
        self._meancounts = None
        self._n = None
        
        if self.dt <= 0:
            raise ValueError("Time resolution (dt) must be strictly positive.")
        if len(self._time) != len(self._counts):
            raise ValueError("Time and counts arrays must be the same length.")
            
        if gti is None:
            # Default GTI covers the whole observation
            gti = [(self.time[0],self.time[-1])]
        else:
            if isinstance(gti, tuple):
                gti = [gti]
            if not isinstance(gti, list):
                raise ValueError("GTIs must be a list of tuples with start and stop times.")
            for sgti in gti:
                if len(sgti) != 2:
                    raise ValueError("GTIs must be a list of tuples with start and stop times.")
        
        self._gti = gti

        # GTI masking computation
        self._gti_mask = self._compute_gti_mask()

    # --- Properties (Read-only to prevent accidental corruption) ---
    @property
    def time(self):
        return self._time.value

    @property
    def time_relative(self):
        return (self._time - self._bin_lo).value

    @property
    def counts(self):
        return self._counts.value

    @property
    def dt(self):
        return self._dt.value

    @property
    def gti(self):
        return self._gti.value

    @property
    def rate(self):
        return self._rate.value

    # --- Math & Internal Methods ---
    
    def _compute_gti_mask(self):
        """Creates a boolean mask for time bins falling within GTIs."""
        mask = np.zeros_like(self.time, dtype=bool)
        for sgti in self._gti:
            start, stop = sgti
            # Check if the bin center falls within the GTI
            in_gti = (self.time >= start) & (self.time <= stop)
            mask |= in_gti
        return mask

    def _compute_from_counts(self):
        self._rate = self._counts / self._dt
        # Add calc
        self._rate_err = None
        return

    def _compute_from_rate(self):
        self._counts = self._rate * self._dt
        # Add calc
        self._counts_err = None
        return

    @classmethod
    def lcurve_from_file(cls,
                         fits_file,
                         timecolumn='TIME',
                         countcolumn='COUNTS',
                         datahdu=1,
                         **kwargs,
                        ):
        lcfits = XMMFits(fits_file)
        data   = lcfits._data
        if datahdu != 1:
            data = lcfits.get_data(ext=datahdu)
        table = Table(data)
        if countcolumn in table.colnames:
            counts = Quantity(table[countcolumn],'photon')
        elif 'RATE' in table.colnames:
            counts = Quantity(table['RATE'],'photon/s')
        else:
            raise KeyError(f'Count column {countcolumn} not found in {fits_file}.')
        if timecolumn in table.colnames:
            time    = Quantity(table[timecolumn],'s')
            _dt     = lcfits.get_keyword('TIMEDEL', ext=1)
        else:
            t_start = lcfits.get_keyword('TSTART', ext=1)
            t_stop  = lcfits.get_keyword('TSTOP', ext=1)
            _dt     = lcfits.get_keyword('TIMEDEL', ext=1)
            if not all([t_start,t_stop,_dt]):
                raise ValueError(f'Could not find times in {fits_file}.')
            bins    = np.arange(t_start, t_stop + _dt, _dt)
            time    = Quantity(bins,'s')
        dt = Quantity(_dt,'s')

        if 'ERROR' in table.colnames:
            error = Quantity(table['ERROR'],counts.unit)
        else:
            error = Quantity([0]*len(counts),counts.unit)

        to_cls = {'time'  : time, 
                  'dt'    : dt, 
                  'err'   : error, 
                  'instr' : lcfits.instrument}
        
        if counts.unit == 'photon':
            to_cls['counts'] = counts
        else:
            to_cls['rate']   = counts

        to_cls.update(kwargs)

        return cls(**to_cls)

    def rebin(self, new_dt):
        """
        Rebins the light curve to a new time resolution.
        Uses Stingray's logic: new_dt must be an integer multiple of the current dt.
        """
        if new_dt <= self._dt:
            raise ValueError("new_dt must be greater than current dt.")
            
        rebin_factor = new_dt / self._dt
        if not rebin_factor.is_integer():
            raise ValueError("new_dt must be an exact multiple of current dt.")
            
        factor = int(rebin_factor)
        
        # Truncate arrays to be divisible by the factor
        new_len = len(self._time) // factor * factor
        
        # Reshape and compute
        new_time = self._time[:new_len].reshape(-1, factor).mean(axis=1)
        new_counts = self._counts[:new_len].reshape(-1, factor).sum(axis=1)
        
        return XMMLightCurve(time=new_time, counts=new_counts, dt=new_dt, gti=self._gti)

    # --- yt-style Plotting ---
    def plot(self,
             plot_rate=True,
             xmin=None,
             xmax=None,
             ymin=None,
             ymax=None,
             xscale='linear',
             yscale='linear',
             label=None,
             fontsize=18,
             lw=1.5,
             fig=None,
             ax=None,
             apply_mask=True,
             relative_time=False,
             title=None,
             **kwargs,):
        """
        Plots the lightcurve using yt's object-oriented Matplotlib philosophy.
        Provides publication-quality styling and handles missing data.
        """
        
        if fig is None:
            # Create Figure and Axes explicitly
            fig = plt.figure(figsize=(8, 5))
        if ax is not None:
            xscale = ax.get_xscale()
            yscale = ax.get_yscale()
        else:
            ax = fig.add_subplot(111)

        if relative_time:
            x = self.time_relative
        else:
            x = self.time

        if plot_rate:
            y = self.rate
            ylabel = f"Rate ({self._rate.unit})"
        else:
            y = self.counts
            ylabel = f"Counts ({self._counts.unit})"
        
        if apply_mask:
            # Apply mask to show gaps where GTIs are missing (turns data to NaNs)
            y = np.where(self._gti_mask, y, np.nan)

        if label is None:
            label = f'dt = {self._dt}'

        # yt-style styling: step plot, distinct colors, tick formatting
        ax.step(x, y, where='mid', color='#1f77b4', linewidth=lw, label=label)
        
        # Axis labeling and styling
        ax.set_xlabel(f"Time ({self._time.unit})", fontsize=fontsize-2, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=fontsize-2, fontweight='bold')
        if title is None:
            if self.instrument is not None:
                title = f"XMM-Newton {self.instrument} Light Curve"
            else:
                tinst = f"XMM-Newton Light Curve"
        ax.set_title(title, fontsize=fontsize, fontweight='bold')
        
        # Tick parameters
        ax.minorticks_on()
        ax.tick_params(which='major', length=6, width=1.5, direction='in')
        ax.tick_params(which='minor', length=3, width=1, direction='in')
        ax.grid(True, linestyle=':', alpha=0.6)
        
        ax.legend()
        
        # Adjust layout tightly, standard in yt
        fig.tight_layout()

        # fig.show()
        
        return fig, ax

    def write_fits(self, filename):
        """Writes the light curve to a FITS file."""
        lc_table = Table([self._time, self._counts], names=('TIME', 'COUNTS'))
        lc_table.meta['DT'] = self._dt
        lc_table.write(filename, format='fits', overwrite=True)