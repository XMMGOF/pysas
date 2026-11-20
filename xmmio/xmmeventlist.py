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
from astropy.coordinates import Angle, SkyCoord
from astropy.utils.exceptions import AstropyWarning

# Local application imports
from pysas.sasutils import (parse_value, 
                            set_unit,
                            get_region,)
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

    def plot(self, 
             nbins=(600,600), 
             binsize=None,
             squarepixels=True,
             xlim=None,
             ylim=None,
             center=None,
             ax=None, 
             title=None,
             vmin=None,
             vmax=None,
             data=None):
        """
        Bins the projected sky pixels (X and Y) into a 2D array.
        """

        if data is None: data = self.data
        x = data['X']
        y = data['Y']

        # Get the actual pixel boundaries of the data
        skyx,skyy = self._get_skyxy_maxmin()
        xmin, xmax = skyx.min(), skyx.max()
        ymin, ymax = skyy.min(), skyy.max()

        # Override the span if xlim/ylim are provided
        if xlim is not None:
            xmin, xmax = xlim[0], xlim[1]
        if ylim is not None:
            ymin, ymax = ylim[0], ylim[1]

        # Shift the box to the requested center
        if center is not None:
            import astropy.units as u
            
            # Parse the input (handles both pure floats and astropy Quantities)
            ra_val, dec_val = center[0], center[1]
            ra_deg = set_unit(ra_val,u.deg) 
            dec_deg = set_unit(dec_val,u.deg)
            
            # Safely extract the 2D celestial WCS to calculate the center in X/Y pixels
            cwcs = getattr(self.wcs, 'celestial', self.wcs)
            center_x, center_y = cwcs.world_to_pixel_values(ra_deg, dec_deg)
            
            # Calculate current span and shift the min/max to perfectly center it
            x_span = xmax - xmin
            y_span = ymax - ymin
            xmin = center_x - (x_span / 2.0)
            xmax = center_x + (x_span / 2.0)
            ymin = center_y - (y_span / 2.0)
            ymax = center_y + (y_span / 2.0)

        # Mask the data to the final view window
        mask = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
        x = x[mask]
        y = y[mask]
        
        xlim = [int(xmin), int(xmax)]
        ylim = [int(ymin), int(ymax)]
        
        # Handle binsize
        if binsize is not None:
            if isinstance(binsize,(float,int)):
                binsize = [int(binsize),int(binsize)]
            elif isinstance(binsize,(list,tuple)) and len(binsize) != 2:
                _logger.critical('binsize should be a list of size 2.')
                return
            xdiff = xmax - xmin
            ydiff = ymax - ymin
            xnbins = np.ceil(xdiff/binsize[0])
            ynbins = np.ceil(ydiff/binsize[1])
            nbins = (int(xnbins),int(ynbins))

        # Get WCS and set nbins
        wcs = self.wcs.copy()
        wcs.pixel_shape = nbins
        
        # Get current axes
        is_new_ax = False
        if ax is None:
            # Create a new axes with the WCS projection if none was provided
            ax = plt.subplot(projection=wcs)
            is_new_ax = True

        # Create 2D histogram
        H, xedges, yedges = self._create_2dhist_from_data(nbins=nbins,x=x,y=y,xlim=xlim,ylim=ylim)

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
        ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax))
        ax.set_facecolor("black")
        ax.grid(color='blue', ls='solid')#, alpha=0.5)
        plt.colorbar(im, ax=ax)

        if is_new_ax:
            plt.show()

        return ax
    
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
            from pysas.xmmio import XMMLightCurve
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
    
    def filter_on_expression(self, 
                             expr: str,
                             return_mask: bool = False,
                             apply_mask: bool = True):

        expr_tree = self._parse_filter_string(expr)
        filt_mask = self._apply_filter_tree(expr_tree)
        filt_expr = self._rebuild_expression_string(expr_tree)

        if apply_mask:
            self._applied_filters.append(filt_expr)
            self._apply_mask_to_data(filt_mask)

        if return_mask:
            return filt_mask

        return
    
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
    
    def filter_on_region(self,expression,return_mask=False,apply_mask=True,return_region=False):

        from regions import PixCoord, PixelRegion, SkyRegion

        if isinstance(expression,PixelRegion):
            data_coords = PixCoord(self.data['X'], self.data['Y'])
            mask = expression.contains(data_coords)
            return_region = False
        elif isinstance(expression,SkyRegion):
            data_coords = self._get_celestial_coords()
            mask = expression.contains(data_coords, self.wcs)
            return_region = False
        else:
            expr_tree = self._parse_filter_string(expression)
            mask = self._filter_on_region(expr_tree)
            filt_expr = self._rebuild_expression_string(expr_tree)

        if apply_mask:
            self._applied_filters.append(filt_expr)
            self._apply_mask_to_data(mask)

        if return_region:
            coords = expr_tree['coords']
            shape = expr_tree['shape']
            values = expr_tree['values']
            if 'X' in coords[0] and 'Y' in coords[1]:
                pixels = True
            else:
                pixels = False
            sky_region = get_region(shape,values,pixels)
            if return_mask:
                return mask, sky_region
            else:
                return sky_region
        
        if return_mask:
            return mask
        else:
            return
    
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
                                 x,
                                 y,
                                 xlim,
                                 ylim):
        """
        Generates a 2D histogram from the event list.

        Parameters
        ----------
        nbins : tuple
            The number of bins in the x and y directions.
        x : list
            List of x values.
        y : list
            List of y values.

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

        xmin = xlim[0]
        xmax = xlim[1]
        ymin = ylim[0]
        ymax = ylim[1]
        xnbins = nbins[0]
        ynbins = nbins[1]

        # Create the pixel bins
        x_bins = np.linspace(xmin-0.5, xmax+0.5, xnbins + 1)
        y_bins = np.linspace(ymin-0.5, ymax+0.5, ynbins + 1)
        
        # Compute the 2D histogram
        H, xedges, yedges = np.histogram2d(x, y, bins=[x_bins, y_bins])

        return H, xedges, yedges
    
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

        if isinstance(RA, (int,float)): RA  = [RA]
        if isinstance(DEC,(int,float)): DEC = [DEC]

        if len(RA) != len(DEC):
            raise ValueError('RA and DEC must be the same size.')

        coords = np.column_stack((RA,DEC))
        sky_coords = self.wcs.all_world2pix(coords, 1)
        X = [int(round(row[0])) for row in sky_coords]
        Y = [int(round(row[1])) for row in sky_coords]

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

        coords = np.column_stack((X,Y))
        world_coords = self.wcs.all_pix2world(coords, 1)
        sky_coords = SkyCoord(ra=world_coords[:, 0] * u.deg,
                              dec=world_coords[:, 1] * u.deg, 
                              frame='icrs')

        return sky_coords

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

        return

    #### Begin expression parsing functions.
    def _parse_filter_string(self, expr: str, force_negate: bool = False):
        """Recursively parses a boolean filtering string.
        
        Warning: This will most likely fail if you try to get too fancy with 
                 the expression str. Just save everyone some grief and keep
                 it simple.

        """
        expr = expr.strip()
        if not expr: return None
            
        while expr.startswith('(') and expr.endswith(')'):
            depth = 0; is_matched = True
            for i, char in enumerate(expr):
                if char in '([': depth += 1
                elif char in ')]': depth -= 1
                if depth == 0 and i < len(expr) - 1:
                    is_matched = False; break
            if is_matched: expr = expr[1:-1].strip()
            else: break
                
        tokens, current, depth, i = [], [], 0, 0
        while i < len(expr):
            char = expr[i]
            if char in '([':
                depth += 1; current.append(char); i += 1
            elif char in ')]':
                depth -= 1; current.append(char); i += 1
            elif depth == 0 and expr[i:i+3] in ('!&&', '!||'):
                if current: tokens.append(''.join(current).strip()); current = []
                tokens.append(expr[i:i+3]); i += 3
            elif depth == 0 and expr[i:i+2] in ('&&', '||'):
                if current: tokens.append(''.join(current).strip()); current = []
                tokens.append(expr[i:i+2]); i += 2
            else:
                current.append(char); i += 1
                
        if current: tokens.append(''.join(current).strip())
            
        if len(tokens) > 1:
            parsed_tree = []
            negate_next = force_negate
            
            for t in tokens:
                if t in ('!&&', '!||'):
                    parsed_tree.append(t[1:]) 
                    negate_next = True
                elif t in ('&&', '||'):
                    parsed_tree.append(t)
                    negate_next = force_negate
                else:
                    parsed_tree.append(self._parse_filter_string(t, force_negate=negate_next))
                    negate_next = force_negate
                    
            return parsed_tree
            
        return self._classify_node(expr, force_negate)
    
    def _apply_filter_tree(self, tree: list | dict) -> np.ndarray:
        """
        Recursively navigates the parsed syntax tree, routes nodes to their 
        respective filtering functions, and combines them using boolean logic.
        """
        # BASE CASE: It's a single Node (a dictionary)
        if isinstance(tree, dict):
            node_type = tree.get('type')
            
            # Route to the correct function based on type
            if node_type == 'relational':
                mask = self._filter_on_relational(tree)
            elif node_type == 'range':
                mask = self._filter_on_range(tree)
            elif node_type == 'region':
                mask = self._filter_on_region(tree)
            elif node_type == 'other':
                mask = self._filter_on_other(tree)
            else:
                raise ValueError(f"Unknown node type: {node_type}")
                
            # Automatically handle the negation if '!&&' or '!||' was used upstream
            if tree.get('negated', False):
                mask = ~mask
                
            return mask
            
        # RECURSIVE CASE: It's a list containing sub-trees and string operators
        if isinstance(tree, list):
            if not tree:
                return None
                
            # 1. Evaluate the very first node in the list
            current_mask = self._apply_filter_tree(tree[0])
            
            # 2. Iterate through the rest of the list in pairs (Operator, Next_Node)
            for i in range(1, len(tree), 2):
                operator_str = tree[i]
                next_node = tree[i+1]
                
                # Evaluate the next node
                next_mask = self._apply_filter_tree(next_node)
                
                # 3. Combine the masks using bitwise array logic
                if operator_str == '&&':
                    current_mask = current_mask & next_mask
                elif operator_str == '||':
                    current_mask = current_mask | next_mask
                else:
                    raise ValueError(f"Unknown logical operator: {operator_str}")
                    
            return current_mask
    
    def _evaluate_range_node(self, range_str: str):
        """Validates and evaluates a single range string."""
        OPS = {'==': operator.eq, '!=': operator.ne,
               '<=': operator.le, '>=': operator.ge,
               '<':  operator.lt, '>':  operator.gt}
        
        pat_str = re.sub(r'\s+', '', range_str)
        F = r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?"

        if re.match(r'^[\(\[]?:[\)\]]?$', pat_str):
            return ()

        m_exact = re.match(rf'^[\(\[]?({F})[\)\]]?$', pat_str)
        if m_exact:
            val = float(m_exact.group(1))
            val = int(val) if val.is_integer() else val
            return ((operator.eq, val),)

        m_lo_open = re.match(rf'^([\[\(]?)({F}):([\]\)]?)$', pat_str)
        if m_lo_open:
            left_b, val_str, right_b = m_lo_open.groups()
            val = float(val_str)
            val = int(val) if val.is_integer() else val
            op = OPS['>'] if left_b == '(' else OPS['>=']
            return ((op, val),)
        
        m_hi_open = re.match(rf'^([\[\(]?):({F})([\]\)]?)$', pat_str)
        if m_hi_open:
            left_b, val_str, right_b = m_hi_open.groups()
            val = float(val_str)
            val = int(val) if val.is_integer() else val
            op = OPS['<'] if right_b == ')' else OPS['<=']
            return ((op, val),)

        m_range = re.match(rf'^([\[\(]?)({F}):({F})([\]\)]?)$', pat_str)
        if m_range:
            left_b, lo_str, hi_str, right_b = m_range.groups()
            lo = float(lo_str)
            lo = int(lo) if lo.is_integer() else lo
            hi = float(hi_str)
            hi = int(hi) if hi.is_integer() else hi
            
            if lo >= hi:
                raise ValueError(f'Invalid interval range ({lo}:{hi}).')
            
            op_lo = OPS['>='] if left_b in ('[', '') else OPS['>']
            op_hi = OPS['<='] if right_b in (']', '') else OPS['<']
            return ((op_lo, lo), (op_hi, hi))

        raise SyntaxError(f'Invalid range string: {range_str}')

    def _classify_node(self, node_str: str, force_negate: bool = False) -> dict:
        """Classifies nodes into Region, Relational, Range, or Other."""
        KEYWORDS = ['TIME', 'RAWX', 'RAWY', 'DETX', 'DETY', 'X', 'Y', 'PHA', 'PI', 'FLAG',
                    'PATTERN', 'PAT_ID', 'PAT_SEQ', 'CCDNR', 'TIME_RAW', 'ENERGY', 'GTI',
                    'TELX', 'TELY', 'RA', 'DEC']
        OPS = {'==': operator.eq, '!=': operator.ne,
               '<=': operator.le, '>=': operator.ge,
               '<':  operator.lt, '>':  operator.gt}
        node_str = node_str.strip()
        is_negated = force_negate
        
        # Handle Unary Negation safely
        if node_str.startswith('!'):
            is_negated = not is_negated 
            node_str = node_str[1:].strip()
            
            while node_str.startswith('(') and node_str.endswith(')'):
                depth = 0; is_matched = True
                for i, char in enumerate(node_str):
                    if char in '([': depth += 1
                    elif char in ')]': depth -= 1
                    if depth == 0 and i < len(node_str) - 1:
                        is_matched = False; break
                if is_matched: node_str = node_str[1:-1].strip()
                else: break

        # -------------------------------------------------------------
        # 3a. Check for Region Node (Strictly using commas)
        # Format: (X,Y) in TYPE(val1, val2, val3...) 
        # -------------------------------------------------------------
        region_pattern = r"^\s*\(\s*(RAWX|DETX|X|TELX|RA)\s*,\s*(RAWY|DETY|Y|TELY|DEC)\s*\)\s+IN\s+(CIRCLE|ELLIPSE|ANNULUS|BOX|POLYGON)\s*\(([^)]+)\)\s*$"
        m_region = re.match(region_pattern, node_str, re.IGNORECASE)
        
        if m_region:
            coord1 = m_region.group(1).upper()
            coord2 = m_region.group(2).upper()
            shape = m_region.group(3).upper()
            values_str = m_region.group(4)
            
            # Validate that it's a correct pair (preventing accidental 'RAWX,DEC' typos)
            valid_pairs = [('RAWX','RAWY'), ('DETX','DETY'), ('X','Y'), ('TELX','TELY'), ('RA','DEC')]
            if (coord1, coord2) in valid_pairs:
                try:
                    # Convert comma-separated string to a list of floats
                    values = [float(v.strip()) for v in values_str.split(',')]
                    
                    # Must have 3 or more values to define a region
                    if len(values) >= 3:
                        return {
                            'type': 'region',
                            'coords': (coord1, coord2),
                            'shape': shape,
                            'values': values,
                            'negated': is_negated
                        }
                except ValueError:
                    # If values couldn't be parsed as floats, fall through to 'other'
                    pass

        kw_group = r"(" + "|".join(KEYWORDS) + r")"
        
        # -------------------------------------------------------------
        # 3b. Check for Relational Node
        # -------------------------------------------------------------
        rel_pattern = rf"^\s*{kw_group}\s*(==|!=|<=|>=|<|>)\s*(.+)\s*$"
        m_rel = re.match(rel_pattern, node_str, re.IGNORECASE)
        if m_rel:
            val = float(m_rel.group(3).strip())
            val = int(val) if val.is_integer() else val
            return {
                'type': 'relational',
                'keyword': m_rel.group(1).upper(),
                'operator': OPS[m_rel.group(2)],
                'value': val,
                'negated': is_negated
            }
            
        # -------------------------------------------------------------
        # 3c. Check for Range Node 
        # -------------------------------------------------------------
        range_pattern = rf"^\s*{kw_group}\s+in\s+(.+)\s*$"
        m_range = re.match(range_pattern, node_str, re.IGNORECASE)
        if m_range:
            keyword = m_range.group(1).upper()
            intervals_str = m_range.group(2).strip()
            
            intervals = [i.strip() for i in intervals_str.split(',')]
            evaluated_intervals = []
            for interval in intervals:
                ops_tuple = self._evaluate_range_node(interval)
                if len(ops_tuple) == 1:
                    return {
                        'type': 'relational',
                        'keyword': keyword,
                        'operator': ops_tuple[0][0],
                        'value': ops_tuple[0][1],
                        'negated': is_negated
                    }
                evaluated_intervals.append({
                    'interval_string': interval,
                    'operations': ops_tuple
                })
                
            return {
                'type': 'range',
                'keyword': keyword,
                'evaluated_intervals': evaluated_intervals,
                'negated': is_negated
            }
            
        # -------------------------------------------------------------
        # 3d. Fallback ('other')
        # -------------------------------------------------------------
        return {
            'type': 'other',
            'content': node_str,
            'negated': is_negated
        }
    
    #### The following functions ONLY calculate and return a filtering mask.####
    #
    #       _filter_on_relational
    #       _filter_on_range
    #       _filter_on_region
    #       _filter_on_other
    #       _filter_on_flag
    #       _compute_gti_mask
    # 
    ############################################################################
    def _filter_on_relational(self, node: dict) -> np.ndarray:
        """
        Handles relational filtering (e.g., PATTERN == 0, PI <= 3000).
        """
        keyword = node['keyword']
        op = node['operator']
        value = node['value']
        
        mask = op(self.data[keyword],value)

        return mask

    def _filter_on_range(self, node: dict) -> np.ndarray:
        """
        Handles range filtering (e.g., PI in [500:2000]).
        """
        keyword = node['keyword']
        intervals = node['evaluated_intervals']
        mask = np.zeros(len(self.data), dtype=bool)
        for interval in intervals:
            ops_tups = interval['operations']
            next_mask = ops_tups[0][0](self.data[keyword],ops_tups[0][1]) & ops_tups[1][0](self.data[keyword],ops_tups[1][1])
            mask = mask | next_mask

        return mask

    def _filter_on_region(self, node: dict) -> np.ndarray:

        from regions import PixCoord

        coords = node['coords']
        shape = node['shape']
        values = node['values']
        # The "do nothing" mask in case an error was made.
        mask = np.ones(len(self.data), dtype=bool)

        if coords[0] == 'X' and coords[1] == 'Y':
            data_coords = PixCoord(self.data['X'], self.data['Y'])
            pixels = True
        elif coords[0] == 'RA' and coords[1] == 'DEC':
            data_coords = self._get_celestial_coords()
            pixels = False
        elif coords[0] == 'DETX' and coords[1] == 'DETY':
            data_coords = PixCoord(self.data['DETX'], self.data['DETY'])
            pixels = True
        elif coords[0] == 'RAWX' and coords[1] == 'RAWY':
            data_coords = PixCoord(self.data['RAWX'], self.data['RAWY'])
            pixels = True
        
        sky_region = get_region(shape,values,pixels)
            
        if pixels:
            mask = sky_region.contains(data_coords)
        else:
            mask = sky_region.contains(data_coords, self.wcs)

        return mask
    
    def _filter_on_other(self, node: dict) -> np.ndarray:
        """
        Handles specialized fallback filtering (e.g., bitwise flags: (FLAG & 0x766ba000) == 0).
        """
        content = node['content']

        # The "do nothing" mask in case an error was made.
        mask = np.ones(len(self.data), dtype=bool)

        if 'FLAG' in content or 'XMMEA_' in content:
            mask = self._filter_on_flag(content)
        
        return mask
    
    def _filter_on_flag(self, expression: str) -> np.ndarray:
    
        flag = None
        operator = ''
        bitwise = False
        
        # Strip whitespace
        clean_str = expression.replace(' ','')
        # First, check if general flag
        pattern = re.compile(r"^.*(XMMEA_(\d{1,2}|EP|EM|SM)).*$")
        match = pattern.match(clean_str)
        if match:
            try:
                clean_str = self.data_header[match.group(1)]
                clean_str = clean_str.replace(' ','')
            except KeyError:
                try:
                    val = int(match.group(2))
                    flag = 2**(val)
                    operator = '!='
                except ValueError:
                    pass
        # Pattern match for standard SAS FLAG expression
        pattern = re.compile(r"^\(*FLAG&(0x[0-9a-fA-F]+)\)(==|!=)0\)*$")
        match = pattern.match(clean_str)
        pattern2 = re.compile(r"^\(*FLAG(==|!=)(\d+|0x[0-9a-fA-F]+)\)*$")
        match2 = pattern2.match(clean_str)
        if match:
            hex_val_str = match.group(1)
            flag = int(hex_val_str, 16)
            operator = match.group(2)
            bitwise = True
        elif match2:
            hex_val_str = match2.group(2)
            flag = int(hex_val_str, 16)
            operator = match2.group(1)
        # Check for Hexadecimal
        elif clean_str.startswith('0x'):
            flag =  int(clean_str, 16)
            operator = '=='
        # Check for Binary 
        elif clean_str.startswith('0b'):
            flag =  int(clean_str, 2)
            operator = '=='

        if flag is None:
            if 'EMOS' in self.instrument and 'XMMEA_EP' in expression:
                print(f'The flag {expression} cannot be used with the instrument {self.instrument}.')
                print(f'Use #XMMEA_EM instead.')
            elif 'EPN' in self.instrument and 'XMMEA_EM' in expression:
                print(f'The flag {expression} cannot be used with the instrument {self.instrument}.')
                print(f'Use #XMMEA_EP instead.')
            else:
                print( '-----------------------------')
                print(f'Flag {expression} not recognized.')
                print( '-----------------------------')
            print('')
            return

        # Set mask to True
        mask = self.data['FLAG'] != -1
        
        if operator == '==' and bitwise:
            mask = (self.data['FLAG'] & flag) == 0
        elif operator == '==' and not bitwise:
            mask = self.data['FLAG'] == flag
        elif operator == '!=' and bitwise:
            mask = (self.data['FLAG'] & flag) != 0
        elif operator == '!=' and not bitwise:
            mask = self.data['FLAG'] != flag

        return mask

    def _compute_gti_mask(self, gti: list) -> np.ndarray:
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
    
    def _rebuild_expression_string(self, tree) -> str:
        """
        Recursively navigates the parsed syntax tree and rebuilds it into 
        a clean, standardized boolean expression string.
        """
        op_to_str = {operator.lt: "<",
                     operator.le: "<=",
                     operator.eq: "==",
                     operator.ne: "!=",
                     operator.ge: ">=",
                     operator.gt: ">"
                    }
        # ---------------------------------------------------------
        # BASE CASE: It's a single Leaf Node (Dictionary)
        # ---------------------------------------------------------
        if isinstance(tree, dict):
            node_type = tree.get('type')
            node_str = ""
            
            # 1. Rebuild Relational Nodes
            if node_type == 'relational':
                keyword = tree['keyword']
                op = op_to_str[tree['operator']]
                value = tree['value']
                node_str = f"({keyword} {op} {value})"
                
            # 2. Rebuild Range Nodes
            elif node_type == 'range':
                keyword = tree['keyword']
                intervals = tree['evaluated_intervals']
                
                # Extract just the raw strings (e.g. "100:200") from the evaluated dicts
                interval_strings = [i['interval_string'] for i in intervals]
                
                # Join multiple intervals with commas
                joined_intervals = ", ".join(interval_strings)
                node_str = f"({keyword} in {joined_intervals})"
                
            # 3. Rebuild Region Nodes
            elif node_type == 'region':
                coords = tree['coords']
                shape = tree['shape']
                values = tree['values']
                
                # Universal Comma Spacing
                coord_str = f"{coords[0]},{coords[1]}"
                    
                # Convert the list of float values back to a comma-separated string
                val_str = ", ".join(str(v) for v in values)
                
                # Formats beautifully as: ((X,Y) in CIRCLE(100.5, 200.2, 50.0))
                node_str = f"(({coord_str}) in {shape}({val_str}))"

            # 4. Rebuild Other Nodes
            elif node_type == 'other':
                content = tree['content']
                # Only wrap in parens if it isn't already perfectly wrapped
                if content.startswith('(') and content.endswith(')'):
                    node_str = content
                else:
                    node_str = f"({content})"
                    
            else:
                raise ValueError(f"Unknown node type: {node_type}")
                
            # 5. Apply Unary Negation if the node was flagged as negated
            if tree.get('negated', False):
                node_str = f"!{node_str}"
                
            return node_str

        # ---------------------------------------------------------
        # RECURSIVE CASE: It's a list containing sub-trees and operators
        # ---------------------------------------------------------
        if isinstance(tree, list):
            if not tree:
                return ""
                
            rebuilt_parts = []
            
            for item in tree:
                if item in ('&&', '||'):
                    # It's an operator, just add it with standard spacing
                    rebuilt_parts.append(item)
                else:
                    # It's a sub-tree or node, recurse into it
                    rebuilt_parts.append(self._rebuild_expression_string(item))
                    
            # Join the parts of this level together
            level_str = " ".join(rebuilt_parts)
            
            # Wrap the resolved level in parentheses to preserve order of operations
            return f"({level_str})"

        return ""
    #### END expression parsing functions. ####



