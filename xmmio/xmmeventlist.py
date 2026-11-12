# xmmeventlist.py
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
# xmmeventlist.py
# 
# Contains a class and methods for working with an XMM Event List.

# Standard library imports
import os, warnings, re, operator
from pathlib import Path
from datetime import datetime

# Third party imports
import matplotlib.pyplot as plt
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
                            validate_event_list_pattern,
                            XMMFilterExpression,)
from pysas.logger import (_logger, 
                          _log_enable_terminal, 
                          _log_disable_terminal, 
                          _log_enable_file, 
                          _log_disable_file,)

from .xmmfits import XMMFits
from .xmmlightcurve import XMMLightCurve


class XMMEventList(XMMFits):

    def __init__(self,fits_file):
        super().__init__(fits_file)

        self.light_curve = None
        self.__recalc_light_curve = True
        self._applied_filters = []

    def filter_on_pattern(self,expression,return_mask=False,apply_mask=True):

        if not isinstance(expression,(int,float,list,tuple,str)):
            print('The expression must be a str, list, tuple, or an int.')
            return
        
        if isinstance(expression,(int,float)):
            pattern = int(expression)
            expression = f'PATTERN == {pattern}'
        elif isinstance(expression,(list,tuple)):
            if len(expression) > 2:
                print('The expression must be a list or tuple of length 2.')
                return
            lo = expression[0]
            hi = expression[1]
            expression = f'PATTERN in [{lo}:{hi}]'
            
        
        mask = self.filter_on_expression(expression,
                                         return_mask = True,
                                         apply_mask = False)
        if apply_mask:
            self._apply_mask_to_data(mask)

        if return_mask:
            return mask

        return
    
    def filter_on_flag(self,expression,return_mask=False,apply_mask=True):
    
        if not isinstance(expression,(int, float, str)):
            print('The expression must be a str or an int.')
            return
        
        if isinstance(expression,(int,float)):
            flag = int(expression)
            expression = f'FLAG == {flag}'
        
        mask = self.filter_on_expression(expression,
                                         return_mask = True,
                                         apply_mask = False)
        if apply_mask:
            self._apply_mask_to_data(mask)

        if return_mask:
            return mask

        return
    
    def filter_on_energy(self,expression,return_mask=False,apply_mask=True):

        if isinstance(expression,(int,float)):
            # If in keV instead of eV
            if expression < 100: expression *= 1000
            # Convert to a small range.
            lo = expression-5
            hi = expression+5
            expression = [lo,hi]
            
        if isinstance(expression,(list,tuple)):
            if len(expression) > 2:
                print('The expression must be a list or tuple of length 2.')
                return
            # If in keV instead of eV
            for i, en in enumerate(expression):
                if en < 100:
                    expression[i] = en * 1000
            lo = expression[0]
            hi = expression[1]
            expression = f'PI in [{lo}:{hi}]'

        mask = self.filter_on_expression(expression,
                                         return_mask = True,
                                         apply_mask = False)
        if apply_mask:
            self._apply_mask_to_data(mask)

        if return_mask:
            return mask

        return

    def filter_on_gti(self,gti,return_mask=False,apply_mask=True):

        # Check if file
        if isinstance(gti,str):
            try:
                if os.path.exists(gti):
                    gti = self._read_xmm_gti(gti)
            except:
                pass

        if not self._is_valid_gti_format(gti):
            _logger.error('Not valid GTI format.')
            return

        mask = self._compute_gti_mask(gti)

        expression_list = []
        for sgti in gti:
            start, stop = sgti
            expression_list.append(f'(TIME in [{start}:{stop}])')
        expression = ' && '.join(expression_list)
        self._applied_filters.append(expression)

        if apply_mask:
            self._apply_mask_to_data(mask)

        if return_mask:
            return mask

        return
    
    def filter_on_expression(self, 
                             expr: str,
                             return_mask: bool = False,
                             apply_mask: bool = True):

        expr_obj = XMMFilterExpression(expr,self.data,self.data_header)
        self._applied_filters.append(expr_obj.expression)

        if apply_mask:
            self._apply_mask_to_data(expr_obj.mask)

        if return_mask:
            return expr_obj.mask

    def _apply_mask_to_data(self,mask,add_hist=True):

        data = self._data
        original_count = len(data)
        filtered_data = data[mask]
        filtered_count = len(filtered_data)

        self._data = filtered_data

        # Update the header to reflect the new number of rows
        self.data_header['NAXIS2'] = filtered_count

        self.__recalc_light_curve = True

        if add_hist:
            self._add_history(slctexpr=self._applied_filters)

        return
    
    def create_light_curve(self,
                           dt=100, 
                           time_col='TIME', 
                           ext_name='EVENTS',
                           gti=None,
                           **kwargs,
                           ):
        """
        Reads an XMM-Newton event list, extracts events and GTIs, and bins them.
        XMM-Newton typically stores GTIs in extensions starting with 'STDGTI' or 'GTI'.
        """
        # Only recalculate the light curve if there was a change.
        if self.__recalc_light_curve:
            from pysas.lightcurve import XMMLightCurve
            event_times = self._data[time_col]

            if gti is not None:
                t_start, t_stop = gti[:, 0].min(), gti[:, 1].max()
            else:
                t_start, t_stop = event_times.min(), event_times.max()

            bins = np.arange(t_start, t_stop + dt, dt)
            counts, edges = np.histogram(event_times, bins=bins)
            time_centers = edges[:-1] + (dt / 2)
            
            to_lc = {'time'   : edges[:-1], 
                    'counts' : counts, 
                    'dt'     : dt, 
                    'err'    : None, 
                    'instr'  : self.instrument}

            to_lc.update(kwargs)

            self.light_curve = XMMLightCurve(**to_lc)

            self.__recalc_light_curve = False

        return self.light_curve

    def _get_skyxy_maxmin(self):
        x = np.array([0,0,0])
        for i,key in enumerate(['REFXLMIN','REFXCRPX','REFXLMAX']):
            x[i] = self.primary_header[key]
        y = np.array([0,0,0])
        for i,key in enumerate(['REFYLMIN','REFYCRPX','REFYLMAX']):
            y[i] = self.primary_header[key]
        return x, y
    
    def _create_2dhist_from_data(self,
                                 nbins, 
                                 xlim=None,
                                 ylim=None,):
        """
        Generates a 2D histogram from the event list.

        Parameters
        ----------
        nbins : tuple
            The number of bins in the x and y directions.
        xlim : list, optional
            Max/min limits in pixel sky coordinates (X), by default None
        ylim : list, optional
            Max/min limits in pixel sky coordinates (Y), by default None

        Returns
        -------
        H : ndarray, shape(nx, ny)
            The bi-dimensional histogram of `X` and `Y`. Values in `X`
            are histogrammed along the first dimension and values in `Y` are
            histogrammed along the second dimension.
        xedges : ndarray, shape(nx+1,)
            The bin edges along the first dimension.
        yedges : ndarray, shape(ny+1,)
            The bin edges along the second dimension.
        
        """

        # Use the X and Y projected sky columns directly
        x = self.data['X']
        y = self.data['Y']
        xnbins = nbins[0]
        ynbins = nbins[1]
        
        # Get the actual pixel boundaries of the data
        skyx,skyy = self._get_skyxy_maxmin()
        xmin, xmax = skyx.min(), skyx.max()
        ymin, ymax = skyy.min(), skyy.max()

        if xlim is not None:
            xmin = xlim[0]
            xmax = xlim[1]
            mask = (x >= xmin) & (x <= xmax)
            x    = x[mask] 
        if ylim is not None:
            ymin = ylim[0]
            ymax = ylim[1]
            mask = (y >= ymin) & (y <= ymax)
            y    = y[mask]

        # Create the pixel bins
        x_bins = np.linspace(xmin-0.5, xmax+0.5, xnbins + 1)
        y_bins = np.linspace(ymin-0.5, ymax+0.5, ynbins + 1)
        
        # Compute the 2D histogram
        H, xedges, yedges = np.histogram2d(x, y, bins=[x_bins, y_bins])

        return H, xedges, yedges
    
    def plot(self, 
             nbins=(600,600), 
             binsize=None,
             squarepixels=True,
             RAlim=None,
             DEClim=None,
             center=None,
             ax=None, 
             title=None,
             vmin=None,
             vmax=None,):
        """
        Bins the projected sky pixels (X and Y) into a 2D array.
        """
        
        is_new_ax = False
        if ax is None:
            # Create a new axes with the WCS projection if none was provided
            ax = plt.subplot(projection=self.wcs, slices=(0, 0, 'x', 'y'))
            is_new_ax = True

        # Create 2D histogram
        H, xedges, yedges = self._create_2dhist_from_data(nbins=nbins)

        # Plot the image.
        if squarepixels:
            # Define the extent so imshow knows where these pixels are in the WCS
            extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
            im = ax.imshow(H.T, origin='lower', norm='log', vmin=vmin, vmax=vmax, extent=extent)
        else:
            X, Y = np.meshgrid(xedges, yedges)
            ax.pcolormesh(X, Y, H, origin='lower', norm='log', vmin=vmin, vmax=vmax)

        # Formatting
        ax.set_xlabel('RA')
        ax.set_ylabel('DEC')
        if title is None:
            ax.set_title(f'{self.instrument} Image')
        else:
            ax.set_title(title)
        ax.set_facecolor("black")
        ax.grid(color='blue', ls='solid')#, alpha=0.5)
        plt.colorbar(im, ax=ax)

        if is_new_ax:
            plt.show()

        return ax

    def _get_sky_coords(self,RA,DEC):
        """
        Converts celestial coordinates (RA,DEC) to XMM sky coordinates (X,Y).

        Parameters
        ----------
        RA : int | list
            RA to convert, by default None
        DEC : int | list
            DEC to convert, by default None

        Returns
        -------
        tuple
            XMM sky coordinates (X,Y).
        """

        if isinstance(RA, (int,float)): RA  = list(RA)
        if isinstance(DEC,(int,float)): DEC = list(DEC)

        if len(RA) != len(DEC):
            raise ValueError('RA and DEC must be the same size.')

        nevnts = len(RA)
        zeros  = np.zeros(nevnts)
        coords = np.column_stack((zeros,zeros,RA,DEC))
        sky_coords = self.wcs.all_world2pix(coords, 1)
        X = [int(round(row[2])) for row in sky_coords]
        Y = [int(round(row[3])) for row in sky_coords]

        return (X,Y)
    
    def _get_celestial_coords(self,X=None,Y=None):
        """
        Converts XMM sky coordinates (X,Y) to celestial coordinates (RA,DEC).

        If nothing is passed in then all X and Y sky coordinates in the data
        will be converted to RA and DEC.

        Parameters
        ----------
        X : int | list, optional
            XMM X sky coordinates to convert, by default None
        Y : int | list, optional
            XMM Y sky coordinates to convert, by default None

        Returns
        -------
        SkyCoord
            Astropy SkyCoord object containing the RA and DEC.
        """
        
        if X is None: X = self.data['X']
        if Y is None: Y = self.data['Y']

        if len(X) != len(Y):
            raise ValueError('X and Y must be the same size.')

        nevnts = len(X)
        zeros  = np.zeros(nevnts)
        coords = np.column_stack((zeros,zeros,X,Y))
        world_coords = self.wcs.all_pix2world(coords, 1)
        ra = set_unit(np.array(world_coords[:,2]), u.deg)
        dec = set_unit(np.array(world_coords[:,3]), u.deg)
        evt_coords = SkyCoord(ra=ra, dec=dec, frame='icrs')

        return evt_coords

    def _read_xmm_gti(self,gti_file: str, ext_name: str = None) -> list:
        """
        Reads an XMM-Newton Good Time Interval (GTI) file.
        It attempts to read the file as a FITS file first; if that fails, 
        it assumes the file is an ASCII text file.
        
        Parameters:
        - gti_file: str, path to the GTI file.
        - ext_name: str, optional specific FITS extension name to read (e.g., 'STDGTI04').
                    If None, auto-detects the first extension with START/STOP columns.
                    
        Returns:
        - list of tuples: [(start_1, stop_1), (start_2, stop_2), ...]
        """
        if not os.path.exists(gti_file):
            raise FileNotFoundError(f"File not found: {gti_file}")

        # FITS file
        try:
            with fits.open(gti_file) as hdul:
                if ext_name:
                    if ext_name not in hdul:
                        raise KeyError(f"Extension '{ext_name}' not found in FITS file.")
                    data = hdul[ext_name].data
                    return list(zip(data['START'], data['STOP']))

                # Auto-detect the GTI extension
                for hdu in hdul:
                    # Check if this HDU is a table containing START and STOP columns
                    if hasattr(hdu, 'columns'):
                        col_names = [col.name.upper() for col in hdu.columns]
                        if 'START' in col_names and 'STOP' in col_names:
                            data = hdu.data
                            return list(zip(data['START'], data['STOP']))
                
                raise ValueError(f"No GTI extension with START/STOP columns found in {gti_file}.")
        except Exception:
            # fits.open fails on non-FITS files (e.g., ASCII files)
            pass

        # ASCII
        try:
            # np.loadtxt ignores lines starting with '#' and handles varying whitespaces
            data = np.loadtxt(gti_file)
            
            # If the file is completely empty
            if data.size == 0:
                return []
                
            # If there is only one single row/interval, numpy makes it 1D. Reshape to 2D.
            if data.ndim == 1 and len(data) >= 2:
                data = data.reshape(1, len(data))
            elif data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("ASCII file must have at least two columns for START and STOP.")
            
            # Extract the first two columns as start and stop
            starts = data[:, 0]
            stops = data[:, 1]
            
            return list(zip(starts, stops))
            
        except Exception as e:
            raise IOError(f"Failed to read file {gti_file} as either FITS or ASCII: {e}")

    def _compute_data_mask(self,keyword,):

        return
    
    def _compute_gti_mask(self,gti):
        """
        Creates a boolean mask for time bins falling within GTIs.

        Input must be list of tuples: 
            [(start_1, stop_1), (start_2, stop_2), ...]
        
        """
        mask = np.zeros_like(self.data['TIME'], dtype=bool)
        for sgti in gti:
            start, stop = sgti
            # Check if the bin center falls within the GTI
            in_gti = (self.data['TIME'] >= start) & (self.data['TIME'] <= stop)
            mask |= in_gti
        return mask

    def _is_valid_gti_format(self,gti_var) -> bool:
        """
        Checks if a variable matches the output format of read_xmm_gti:
        A list of tuples, where each tuple contains exactly two numeric values (start, stop).
        
        Parameters:
        - gti_var: The variable to test.
        
        Returns:
        - bool: True if valid, False otherwise.
        """
        # 1. It must be a list
        if not isinstance(gti_var, list):
            return False
            
        # 2. An empty list is a valid return from read_xmm_gti
        if len(gti_var) == 0:
            return True
            
        # Allowed numeric types (standard python int/float, and any numpy number)
        valid_types = (int, float, np.number)

        if len(gti_var) == 2 and isinstance(gti_var[0], valid_types) and \
            isinstance(gti_var[1], valid_types):
            gti_var = [gti_var]
            
        # 3. Check the structure and types of every item in the list
        for item in gti_var:
            # Must be a tuple
            if not isinstance(item, (tuple,list)):
                return False
                
            # Must contain exactly two elements (start, stop)
            if len(item) != 2:
                return False
                
            start, stop = item
            
            # Elements must be numeric
            if not isinstance(start, valid_types) or not isinstance(stop, valid_types):
                return False

        # If it passes all checks, it's valid
        return True

    def _add_history(self,hist=None,slctexpr=None):

        from pysas import __version__ as version
        iso_time = datetime.now().isoformat()
        pri_hist = f'Modified by {version} at {iso_time}'

        if hist is not None:
            self.primary_header.add_history(hist)

        self.primary_header.add_history(pri_hist)

        if slctexpr is not None:
            if isinstance(slctexpr,list):
                slctexpr = ' && '.join(slctexpr)
            self.data_header['SLCTEXPR'] = (slctexpr, 'Filtering expression used by pySAS')





