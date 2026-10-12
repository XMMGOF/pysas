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
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from astropy.units import Quantity
from pathlib import Path
import warnings

from pysas.pysasfcls import XMMFits

class XMMLightCurve(XMMFits):
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
                 time=None,
                 counts=None,
                 err=None,
                 input_counts=True,
                 gti=None,
                 err_dist="poisson",
                 bg_counts=None,
                 bg_ratio=None,
                 frac_exp=None,
                 dt=None,
                 instr=None,
                 header=None,
                 **other_kw,
                ):

        if 'fits_file' in other_kw.keys():
            super().__init__(other_kw['fits_file'])
            time_col=other_kw['time_col']
            ext_name=other_kw['ext_name']
            time,counts,dt,gti = self._lcurve_from_events(dt=dt,
                                                          time_col=time_col,
                                                          ext_name=ext_name)
        self._time = None
        self._mask = None
        self._counts = None
        self._counts_err = None
        self._countrate = None
        self._countrate_err = None
        self._meanrate = None
        self._meancounts = None
        self._bin_lo = None
        self._bin_hi = None
        self._n = None

        self._time = np.asarray(time, dtype=float)
        self._counts = np.asarray(counts, dtype=float)
        self._dt = float(dt)
        
        if self._dt <= 0:
            raise ValueError("Time resolution (dt) must be strictly positive.")
        if len(self._time) != len(self._counts):
            raise ValueError("Time and counts arrays must be the same length.")
            
        if gti is None:
            # Default GTI covers the whole observation
            self._gti = np.array([[self._time.min() - self._dt/2, 
                                   self._time.max() + self._dt/2]])
        else:
            self._gti = np.asarray(gti, dtype=float)
            if self._gti.ndim != 2 or self._gti.shape[1] != 2:
                raise ValueError("GTIs must be a 2D array of shape (N, 2).")

        # GTI masking computation
        # self._gti_mask = self._compute_gti_mask()

    # --- Properties (Read-only to prevent accidental corruption) ---
    @property
    def time(self):
        return self._time

    @property
    def counts(self):
        return self._counts

    @property
    def dt(self):
        return self._dt

    @property
    def gti(self):
        return self._gti

    @property
    def rate(self):
        """Returns the count rate (counts/sec)."""
        return self._counts / self._dt

    @property
    def rate_error(self):
        """Assumes Poisson statistics for errors."""
        return np.sqrt(self._counts) / self._dt

    # --- Math & Internal Methods ---
    def _compute_gti_mask(self):
        """Creates a boolean mask for time bins falling within GTIs."""
        mask = np.zeros_like(self._time, dtype=bool)
        for start, stop in self._gti:
            # Check if the bin center falls within the GTI
            in_gti = (self._time >= start) & (self._time <= stop)
            mask |= in_gti
        return mask

    @classmethod
    def lcurve_from_fits(cls,
                         fits_file,
                         timecolumn="TIME",
                         ratecolumn=None,
                         datahdu=1,
                         gtistring="GTI",
                         outfile=None,
                         outdir=None,
                         noclobber=False,):

        super().__init__(fits_file)

        return cls(time=time_centers, counts=counts, dt=dt, gti=gti)

    def _lcurve_from_events(self,
                            dt, 
                            time_col='TIME', 
                            ext_name='EVENTS'):
        """
        Reads an XMM-Newton event list, extracts events and GTIs, and bins them.
        XMM-Newton typically stores GTIs in extensions starting with 'STDGTI' or 'GTI'.
        """
        event_times = self.data[time_col]
        
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
        gti = None

        # 3. Bin the events into a lightcurve
        if gti is not None:
            t_start, t_stop = gti[:, 0].min(), gti[:, 1].max()
        else:
            t_start, t_stop = event_times.min(), event_times.max()

        bins = np.arange(t_start, t_stop + dt, dt)
        counts, edges = np.histogram(event_times, bins=bins)
        time_centers = edges[:-1] + (dt / 2)

        return time_centers, counts, dt, gti

    @classmethod
    def lcurve_from_events(cls, 
                           fits_file, 
                           dt, 
                           time_col='TIME', 
                           ext_name='EVENTS'):
        
        return cls(fits_file=fits_file,dt=dt,time_col=time_col,ext_name=ext_name)

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
    def plot(self, apply_mask=False, return_objs=False):
        """
        Plots the lightcurve using yt's object-oriented Matplotlib philosophy.
        Provides publication-quality styling and handles missing data.
        """
        # Create Figure and Axes explicitly
        fig, ax = plt.subplots(figsize=(8, 5))
        
        if apply_mask:
            # Apply mask to show gaps where GTIs are missing (turns data to NaNs)
            plot_rate = np.where(self._gti_mask, self.rate, np.nan)
        else:
            plot_rate = self.rate

        # yt-style styling: step plot, distinct colors, tick formatting
        ax.step(self._time, plot_rate, where='mid', color='#1f77b4', 
                linewidth=1.5, label=f'dt = {self._dt}s')
        
        # Axis labeling and styling
        ax.set_xlabel("Time (s)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Count Rate (counts s$^{-1}$)", fontsize=12, fontweight='bold')
        ax.set_title("XMM-Newton Light Curve", fontsize=14, fontweight='bold')
        
        # Tick parameters
        ax.minorticks_on()
        ax.tick_params(which='major', length=6, width=1.5, direction='in')
        ax.tick_params(which='minor', length=3, width=1, direction='in')
        ax.grid(True, linestyle=':', alpha=0.6)
        
        ax.legend(loc='upper right')
        
        # Adjust layout tightly, standard in yt
        fig.tight_layout()
        
        if return_objs:
            # yt heavily features returning plot objects for user manipulation
            return fig, ax
        else:
            plt.show()

    def write_fits(self, filename):
        """Writes the light curve to a FITS file."""
        lc_table = Table([self._time, self._counts], names=('TIME', 'COUNTS'))
        lc_table.meta['DT'] = self._dt
        lc_table.write(filename, format='fits', overwrite=True)