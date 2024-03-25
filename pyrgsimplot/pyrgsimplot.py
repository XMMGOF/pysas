# ESA (C) 2000-2021
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

# pyrgsimplot.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pyrgsimplot (pyrgsimplot-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 


import logging
import pysas.pyutils.pyutils as pyutils
import os
import numpy as np
import sys
import pysas.pysasplot_utils.pysasplot_utils as sasplt
from astropy.io import fits
import matplotlib.pyplot as plt
from astropy import units as u
import warnings
warnings.filterwarnings('ignore')
from matplotlib.colors import LogNorm
from matplotlib.colors import PowerNorm
import glob
import time
import matplotlib.transforms as tr
from astropy.wcs import WCS
from astropy.coordinates import Angle
from pysas.logger import TaskLogger as TL
PI = u.def_unit('PI', 1 * u.eV)
u.add_enabled_units([PI])

logger = TL('pyrgsimplot')


def set_xlabel(xlabel):
    """
    Defines the value for the x label depending on the data taken from the fits'
    header.

    Args:
        xlabel: the original value taken from the fits file.

    Output:
        xlabel: the new value for the x label.
    """

    if xlabel == 'M_TIMES_LAMBDA':
        xlabel = r"$\lambda$" + ' (nm)'
    elif xlabel == 'DETX':
        xlabel = 'DETX (mm)'
    elif xlabel == 'BETA_CORR':
        xlabel = 'DISPERSION ANGLE (rad)'
    elif xlabel == 'LAMBDA':
        xlabel = r"$\lambda$" + r"($\AA$)"
    else:
        pass

    return xlabel


def getobservationdetails(in_dataset):
    """
    Uses pyutils to return the keywords corresponding to the given fits file.

    Args:
        in_dataset: the fits file to evaluate.

    Output:
        fits_info: list containing the exposure, telescope, obs_id, exp_id, instr,
    date_obs, date_end
    """

    logger.log('debug', 'Running getobservationdetails...')

    exposure = pyutils.get_key_word(in_dataset, 'EXPOSURE', 0)
    telescope = pyutils.get_key_word(in_dataset, 'TELESCOP', 0)
    obs_id = pyutils.get_key_word(in_dataset, 'OBS_ID', 0)
    exp_id = str(pyutils.get_key_word(in_dataset, 'EXP_ID', 0))[-3:]
    instr = pyutils.get_key_word(in_dataset, 'INSTRUME', 0)
    date_obs = pyutils.get_key_word(in_dataset, 'DATE-OBS', 0)
    date_end = pyutils.get_key_word(in_dataset, 'DATE-END', 0)

    fits_info = [exposure, telescope, obs_id, exp_id, instr, date_obs, date_end]
    
    return fits_info


def set_ylabel(ylabel):
    """
    Defines the value for the y label depending on the data taken from the fits
    header.

    Args:
        ylabel: the original value taken from the fits file.

    Output:
        ylabel: the new value for the y label.
    """

    if ylabel == 'XDSP_CORR':
        ylabel = 'CROSS DISPERSION ANGLE (radians)'
    elif ylabel == 'PHA':
        ylabel = 'PHA (Channel)'
    elif ylabel == 'PI':
        ylabel = 'PI (Channel)'
    elif ylabel == 'PIFUDGE':
        ylabel = 'PI (Channel)'
    elif ylabel == 'DETY':
        ylabel = 'DETY (mm)'
    else:
        pass

    return ylabel


def plot_image(data, hdu, fits_info, xlabel, ylabel, norm, colourmap, region_list, plot_title, kind, srclist):
    """
    Plots an image. Depending on the input, on top of the image the regions from the
    sources might be added.

    Args:
        data: the array to plot.
        hdu: the header from the FITS file to get the WCS reference.
        fits_info: information regarding the file that is being plotted.
        xlabel: name of the xlabel.
        ylabel: name of the ylabel.
        norm: normalization to use.
        colourmap: the colour map of the image.
        region_list: the dictionary containing the regions to be plotted.
        plot_title: the title for the plot.
        kind: the two types of plot to use.
        srclist: file corresponding to the source list to plot the RA and DEC.
    """

    exposure, telescope, obs_id, exp_id, instr, date_obs, date_end, typing = fits_info
   
    if dark_mode:
        plt.style.use('dark_background')

    if norm.upper() == 'LOG':
        norm = LogNorm()
        # Uncomment the following lines to change empty pixels with the minimum value.
        #second_minimum = sorted(set(data.flatten()))[1]
        #data[data == 0] = second_minimum
        norm_name = 'log'
    elif norm.upper() == 'POW':
        norm = PowerNorm(gamma = gamma)
        norm_name = 'power'
    else:
        norm = ''
        norm_name = 'linear'
    
    logger.log('info', 'Plotting {0}.'.format(plot_title))

    wcs = WCS(hdu)
    fig, ax1 = plt.subplots(subplot_kw = {'projection': wcs})

    try:
        with u.add_enabled_units([PI]):
            if inverted:
                colour_map_parsed = plt.cm.get_cmap(colourmap)
                im = ax1.imshow(data,interpolation = None, origin = 'lower', aspect = 'auto', norm = norm, cmap = colour_map_parsed.reversed())
            else:
                im = ax1.imshow(data,interpolation = None, origin = 'lower', aspect = 'auto', norm = norm, cmap = colourmap)
    except ValueError:
        logger.log('warning', 'The input colourmap is not available for matplotlib. Using \'plasma\' by default.')
        colourmap = 'plasma'
        with u.add_enabled_units([PI]):
            if inverted:
                colour_map_parsed = plt.cm.get_cmap(colourmap)
                im = ax1.imshow(data,interpolation = None, origin = 'lower', aspect = 'auto', norm = norm, cmap = colour_map_parsed.reversed())
            else:
                im = ax1.imshow(data,interpolation = None, origin = 'lower', aspect = 'auto', norm = norm, cmap = colourmap)

    # if the plot is reduced to the PI detection even if the sources extend it:
    #ylims = ax1.get_ylim()
    #xlims = ax1.get_xlim()

    if region_list:
        for key in region_list.keys():
            # masking out the non-value coordinates marked as 0:
            filt_valuex = region_list[key][0]
            filt_valuex[filt_valuex == 0] = np.nan
            filt_valuey = region_list[key][1]
            filt_valuey[filt_valuey == 0] = np.nan
            with u.add_enabled_units([PI]):
                if kind == 'endisp':
                    order_key = key[key.upper().find('ORDER') + 6]
                    if not order_key.isnumeric():
                        logger.log('warning', 'Could not identify the order in the source key.')
                        colour_plot = 'C0'
                    else:
                        colour_plot = 'C{0}'.format(order_key)
                else:
                    colour_plot = 'C0'
                if 'ext' in key:
                    ax1.plot(filt_valuex, filt_valuey,'--', color = colour_plot, transform = ax1.get_transform('world'))
                else:
                    ax1.plot(filt_valuex, filt_valuey, color = colour_plot, transform = ax1.get_transform('world'))
    
    if srclist:
        text = ''
        s_ra, s_dec, s_label = get_source_details(srclist)
        for i in range(0, len(s_label)):
            aux_text = r"$\bf{Label: }$ " + s_label[i] + r" $\bf{RA: }$ " + s_ra[i] + r" $\bf{DEC: }$ " + s_dec[i] + '\n'
            text = text + aux_text

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    cbar = fig.colorbar(im)

    if norm_name != 'power':
        cbar.ax.set_ylabel('Counts per binned pixel ({} intensity).'.format(norm_name))
    else:
        cbar.ax.set_ylabel('Counts per binned pixel (power (gamma = {}) intensity).'.format(gamma))
    plt.figtext(0.5, 0.01, text)
    #ax1.set_xlim(xlims)
    #ax1.set_ylim(ylims)
    fig.set_size_inches(12, 9)
    ax1.set_title('Date-OBS: {0}  Date-END: {1}\nOBS-ID: {2}  EXP-No: {3}'.format(date_obs, date_end, obs_id, exp_id))
    fig.suptitle('XMM Newton {0} {1} Image'.format(instr, typing), fontsize = 16)
    
    # since more than one file is going to be written, the names must be changed
    if withendispset and withspatialset:
        plot_title = plot_title + kind
    
    try:
        logger.log('debug', 'Saving {} {}.'.format(plot_title, out_format))
        plt.savefig(plot_title + '.' + out_format)
    except FileNotFoundError:
        try:
            dirs, rfile = os.path.split(plot_title + '.' + out_format)
            os.makedirs(dirs)
            plt.savefig(plot_title + '.' + out_format)
        except:
            logger.log('error', 'Could not create {}. Could not resolve the given path.'.format(plot_title + '.' + out_format))

    
    if device:
        if os.getenv['DISPLAY']:
            plt.show()
        else:
            logger.log('warning', 'Display not available.')

    logger.log('info', 'Created {}.'.format(plot_title))


def getarrayattributes(data_header):
    """
    From the header of an array, gets the basic information needed.

    Args:
        data_header: the header to extract the data.

    Output:
        (xlabel, ylabel, xref, yref, xbinwidth, ybinwidth, xmin, ymin): tuple
    containing the data extracted.
    """

    logger.log('debug', 'Running getarrayattributes...')

    xlabel = data_header['CTYPE1']
    if xlabel == 'M_LAMBDA':
        xlabel = 'LAMBDA'

    ylabel = data_header['CTYPE2']
    xref = float(data_header['CRPIX1'])
    yref = float(data_header['CRPIX2'])
    xbinwidth = float(data_header['CDELT1'])
    ybinwidth = float(data_header['CDELT2'])

    xmin = float(data_header['CRVAL1']) + (1 - xref) * xbinwidth
    ymin = float(data_header['CRVAL2']) + (1 - yref) * ybinwidth
    
    return (xlabel, ylabel, xref, yref, xbinwidth, ybinwidth, xmin, ymin)


def run(iparsdic):
    print(f'Executing {__file__} {iparsdic}')

    t_start = time.time()

    global withspatialset, withendispset

    withspatialset = iparsdic['withspatialset']
    if 'Y' in withspatialset.upper() or 'T' in withspatialset.upper():
        withspatialset = True
    else:
        withspatialset = False

    withendispset = iparsdic['withendispset']
    if 'Y' in withendispset.upper() or 'T' in withendispset.upper():
        withendispset = True
    else:
        withendispset = False
    
    withspatialregionsets = iparsdic['withspatialregionsets']
    if 'Y' in withspatialregionsets.upper() or 'T' in withspatialregionsets.upper():
        withspatialregionsets = True
    else:
        withspatialregionsets = False

    order_list = iparsdic['orderlist']
    order_list = order_list.replace(' ','').split(',')

    global inverted
    inverted = iparsdic['inverted']
    if 'Y' in inverted.upper() or 'T' in inverted.upper():
        inverted = True
    else:
        inverted = False

    global out_format

    withendispregionsets = iparsdic['withendispregionsets']
    if 'Y' in withendispregionsets.upper() or 'T' in withendispregionsets.upper():
        withendispregionsets = True
    else:
        withendispregionsets = False

    global device
    device = iparsdic['device']
    if 'Y' in device.upper() or 'T' in device.upper():
        device = True
    else:
        device = False

    endispset = iparsdic['endispset']
    spatialset = iparsdic['spatialset']

    srclistset = iparsdic['srclistset']
    if not os.path.isfile(srclistset):
        srclistset = None

    plot_title = iparsdic['plotfile']
    plot_title = os.path.abspath(plot_title)
    plot_title, out_format = os.path.splitext(plot_title)
    
    if out_format == '':
        out_format = 'pdf'
        logger.log('warning', 'Could not find format. Using {0}.{1} as default.'.format(plot_title, out_format))
    else:
        out_format = out_format.replace('.', '')
        if not out_format.upper() in ('PDF', 'PNG'):
            logger.log('error', 'Format {} not supported. Please use pdf or png.'.format(out_format))
    
    
    colourmap = iparsdic['colour']
    norm = iparsdic['colourmap']
    n_sources = int(iparsdic['srcidlist'])
    
    global gamma
    gamma = float(iparsdic['gamma'])
    
    global dark_mode
    dark_mode = iparsdic['dark_mode']
    if 'Y' in dark_mode.upper() or 'T' in dark_mode.upper():
        dark_mode = True
    else:
        dark_mode = False

    if not withspatialset and not withendispset:
        logger.log('error', 'Nothing to plot.')
        sys.exit(0)
    if withspatialset:
        spatialset = iparsdic['spatialset']
    if withendispset:
        endispset = iparsdic['endispset']
        if not os.path.isfile(endispset):
            logger.log('error', 'No energy dispersion set provided.')


    ################################
    ######## SPATIAL IMAGE #########
    ################################
    
    logger.log('info', 'Starting processing the spatial energy block...')

    if withspatialset:
        try:
            with fits.open(spatialset) as in_dataset:
                fits_info = getobservationdetails(in_dataset)
                fits_info.append('Spatial')
                in_array = in_dataset[0].data
                array_header = in_dataset[0].header
        except FileNotFoundError:
            logger.log('error', 'Could not open spatial set file.')
            sys.exit(0)

        dim = in_array.shape
        xlabel, ylabel, xref, yref, xbinwidth, ybinwidth, xmin, ymin = getarrayattributes(array_header)
        xlabel = set_xlabel(xlabel)
        ylabel = set_ylabel(ylabel)
        ymax = ymin + dim[1] * ybinwidth
        xmax = xmin + dim[0] * xbinwidth
        limits = [xmin, ymin, xmax, ymax]

        if withspatialregionsets:
            region_list = collect_regions_spatial(srclistset, n_sources)
        else:
            region_list = None
        
        plot_image(in_array, array_header, fits_info, xlabel, ylabel, norm, colourmap, region_list, plot_title, 'spatial', srclistset)


    ###############################
    ######## ORDERS IMAGE #########
    ###############################

    logger.log('info', 'Starting energy dispersion block...')

    if withendispset:
        try:
            with fits.open(endispset) as in_dataset:
                in_array = in_dataset[0].data
                fits_info = getobservationdetails(in_dataset)
                fits_info.append('Energy dispersion')
                array_header = in_dataset[0].header
        except FileNotFoundError:
            logger.log('error', 'Could not open the energy dispersion dataset.')
            sys.exit(0)

        dim = in_array.shape
        xlabel, ylabel, xref, yref, xbinwidth, ybinwidth, xmin, ymin = getarrayattributes(array_header)
        xlabel = set_xlabel(xlabel)
        ylabel = set_ylabel(ylabel)
        ymax = ymin + dim[1] * ybinwidth
        xmax = xmin + dim[0] * xbinwidth
        limits = [xmin, xmax, ymin, ymax]

        if withendispregionsets:
            region_list = collect_region_order(srclistset, n_sources, order_list)
        else:
            region_list = None
        plot_image(in_array, array_header, fits_info, xlabel, ylabel, norm, colourmap, region_list, plot_title, 'endisp', srclistset)


    if out_format.upper() == 'PDF' and withendispset and withspatialset:
        pdf_files = glob.glob(plot_title + '*.{}'.format(out_format))
        logger.log('debug', 'Merging PDFs... ({}).'.format(pdf_files))
        status = sasplt.merge_pdf(pdf_files, plot_title + '.{}'.format(out_format))
        if status == 0:
            logger.log('warning', 'Error while merging the PDFs.')
        else:
            for i in pdf_files:
                os.remove(i)

    t_stop = time.time()
    logger.log('info', 'All blocks completed in time {}.'.format(round(t_stop - t_start, 2)))


def get_source_details(srclistset):
    """
    Gets information regarding the SRCLIST extension from the given source list.

    Args:
        srclistset: the path to the source list fits file.

    Output:
        tuple containing the list of RA, DEC and labels of the sources.
    """
    
    logger.log('debug', 'Evaluating the coordinates of the source list...')

    try:
        with fits.open(srclistset) as f:
            source_table = f[1].data
    except FileNotFoundError:
        logger.log('error', 'Could not open the soure list set.')
        sys.exit(0)

    source_ra = []
    source_dec = []
    source_name = []

    for row in source_table:
        source_name.append(row['LABEL'])
        source_ra.append(transform_to_hms(row['RA']))
        source_dec.append(transform_to_dms(row['DEC']))

    return (source_ra, source_dec, source_name)


def transform_to_hms(value):
    """
    Transforms the input degree value into a hour-minute-second tuple format 
    using astropy's angle utility.

    Args:
        value: the raw angle in numeric form.

    Ouput:
        transformed: the tuple with the new data.
    """

    logger.log('debug', 'Transforming unit...')
    
    value = str(value)
    transformed = Angle(value + 'd').hms
    str_trans = '{0}H:{1}M:{2}S'.format(int(transformed[0]), int(transformed[1]), round(int(transformed[2]),2))
    
    return str_trans


def transform_to_dms(value):
    """
    Transforms the input degree value into a degree-minute-second tuple format
    using astropy's angle utility.

    Args:
        value: the raw angle in numeric form.

    Ouput:
        transformed: the tuple with the new data.
    """

    logger.log('debug', 'Transforming unit...')

    value = str(value)
    transformed = Angle(value + 'd').dms
    str_trans = '{0}D:{1}M:{2}S'.format(int(transformed[0]), int(transformed[1]), round(int(transformed[2]),2))

    return str_trans


def collect_regions_spatial(srclist, n_sources):
    """
    Collects the spatial regions present in the source list, under the source id 
    passed.

    Args:
        srclist: the source list fits file.
        n_sources: the source number that has to be checked.

    Output:
        region_list: a dictionary containing the regions ready to plot.
    """
    
    logger.log('debug', 'Collecting the spatial regions...')

    if n_sources == 0:
        return None

    region_list = dict()
    ext = ''
    sp_regions = []
    
    try:
        with fits.open(srclist) as f:
            for h in f:
                if 'SPATIAL' in h.name:
                    sp_regions.append(h.name)
            if len(sp_regions) == 1:
                ext = sp_regions[0]
            elif len(sp_regions) >= 1:
                for i in sp_regions:
                    if '_SRC{}'.format(n_sources) in i:
                        ext = i
            if ext == '':
                logger.log('warning', 'Could not locate spatial regions in the source list.')
                return None
            else:
                dimen, xtag, ytag, component = f[ext].data.names
                for i in range(0, len(f[ext].data)):
                    if '!' in f[ext].data[dimen][i]:
                        region_list.update({'ext{}'.format(i) : (f[ext].data[i][xtag], f[ext].data[i][ytag])})
                    else:
                        region_list.update({'inc{}'.format(i) : (f[ext].data[i][xtag], f[ext].data[i][ytag])})
    except FileNotFoundError:
        logger.log('error', 'Could not open the source list file.')
        sys.exit(0)

    logger.log('debug', 'Spatial regions collected.')

    return region_list


def collect_region_order(srclist, n_sources, order_list):
    """
    Returns a dictionary containing all the region plots for the given source list, the 
    specified order/orders and the specified source.

    Args:
        srclist: the path to the file for the source list.
        n_sources: the source id to find in the source list.
        order_list: the energy orders to be evaluated.

    Output:
        region_list: the dictionary containing the regions.
    """

    logger.log('debug', 'Selecting regions for energy dispersion plot...')

    if n_sources == 0:
        return None

    region_list = dict()
    ext = []
    en_regions = []

    try:
        with fits.open(srclist) as f:
            for h in f:
                if 'ORDER' in h.name:
                    en_regions.append(h.name)
            if len(en_regions) == 1:
                ext = en_regions[0]
            elif len(en_regions) >= 1:
                for i in en_regions:
                    if '_SRC{}'.format(n_sources) in i:
                        for order in order_list:
                            if '_{}'.format(order) in i:
                                ext.append(i)
            if len(ext) == 0:
                logger.log('warning', 'WARNING: no regions were matched for the srcidlist.')
                return None
            else:
                for e in ext:
                    dimen, xtag, ytag, component = f[e].data.names
                    for i in range(0, len(f[e].data)):
                        if '!' in f[e].data[dimen][i]:
                            region_list.update({'ext{}'.format(e + ':' + str(i)) : (f[e].data[i][xtag], f[e].data[i][ytag])})
                        else:
                            region_list.update({'inc{}'.format(e + ':' + str(i)) : (f[e].data[i][xtag], f[e].data[i][ytag])})
    except FileNotFoundError:
        logger.log('error', 'Could not open the source list file.')
        sys.exit(0)

    logger.log('debug', 'Energy dispersion regions collected.')

    return region_list
