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

# omdrifthist.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'omdrifthist (omdrifthist-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'


import numpy as np
from matplotlib.patches import ConnectionPatch
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import warnings
import sys
import re
import os
import glob
import math
import pysas.pyutils.pyutils as pyutils
from astropy.io import fits
from astropy.table import Table
import time
import pysas.pysasplot_utils.pysasplot_utils as sasplt
from pysas.logger import TaskLogger as TL

logger = TL('omdrifthist')

########################################
############ CALC FUNCTIONS ############
########################################

def euclid_modulus(point):
    """
    Returns the modulus of two given points.

    Args:
        point: the coordinates of a point in a 2D space.

    Output:
        modulus: the calculated modulus.
    """

    a, b = point
    modulus = np.sqrt(a**2 + b**2)

    return modulus


def incremental_drift(history, x0, y0, rpixel):
    """
    Calculates the incremental drift roll and the incremental drift coordinates.

    Args:
        history: the 2D matrix containing the x data and y data in separate
    columns.
        x0: original x coordinate from the file.
        y0: original y coordinate from the file.
        rpixel: the radius for the pixel adapted from trackradius.

    Output:
        incdrift: the list containing the incremental drift size.
        increments: the array of increments in the drift roll
        n_out: the number of pixels outside the original radius.
        n_out_0: the number of pixels outside the original radius at x0, y0
    """

    logger.log('debug', 'Calculating incremental drift arrays...')

    n_out = 0
    incdrift = [euclid_modulus(history[0])]
    increments = [history[0]]
    n_out_0 = 0

    for i in range(1, len(history)):
        incdrift.append(euclid_modulus(history[i] - history[i - 1]))
        increments.append(history[i] - history[i - 1])
        r0 = np.sqrt((x0 - history[i][0]) ** 2 + (y0 - history[i][1]) ** 2)
        r = euclid_modulus(history[i])
        if r > rpixel:
            n_out = n_out + 1
        if r0 > rpixel:
            n_out_0 = n_out_0 + 1

    increments = np.vstack(increments)
    logger.log('debug', 'Incremental drift arrays calculated.')

    return incdrift, increments, n_out, n_out_0


def get_more_recent_ccf(abspaths):
    """
    Returns the absolute path of the most recent CCF file.

    Args:
        abspaths: the absolute path of the files to evaluate.

    Output:
        the absolute path of the most recent file.
    """

    maxn = 0
    for f in abspaths:
        f_aux = os.path.basename(f)
        num = int(re.search(r'\d+', f_aux).group(0))
        if num > maxn:
            maxn = num
            maxf = f
            
    return maxf


def get_platescale(filt):
    """
    Searches in the optical monitor calibration file for the value of the plate
    scale for the given filter.

    Args:
        filt: the filter used in the observation.

    Output:
        platescale: the value for the plate scale as float.
    """

    logger.log('debug', 'Looking for platescale...')

    try:
        ccfpath = os.environ['SAS_CCFPATH']
    except KeyError:
        logger.log('error', 'Could not locate variable SAS_CCFPATH. Quitting...')
        sys.exit(0)


    folders = ccfpath.split(':')
    if len(folders) == 1:
        om_ccf_file = glob.glob(os.environ['SAS_CCFPATH'] + '/OM_ASTR*')
        om_ccf_file = get_more_recent_ccf(om_ccf_file)
        logger.log('debug', 'CCF file used: {0}.'.format(om_ccf_file))
        search_extension = 'FILTER-' + filt.upper()
        platescale = pyutils.get_key_word(om_ccf_file, 'PLTSCALE', search_extension)
    else:
        om_ccf_list = []
        logger.log('debug', 'List of folders found in CCF path: {0}'.format(folders))
        for folder in folders:
            try:
                om_ccf_file = os.path.abspath(glob.glob(folder + '/OM_ASTR*')[0])
            except IndexError:
                logger.log('debug', '{} does not contain OM astronometry calibration file.'.format(folder))
                continue
            om_ccf_list.append(om_ccf_file)
        logger.log('debug', 'Found the following OM CCF compatible files: {0}'.format(om_ccf_list))
        latest_ccf = get_more_recent_ccf(om_ccf_list)
        logger.log('debug', 'CCF file used: {0}.'.format(latest_ccf))
        search_extension = 'FILTER-' + filt.upper()
        platescale = pyutils.get_key_word(latest_ccf, 'PLTSCALE', search_extension)


    if platescale == 'unknown':
        logger.log('warning', 'Could not find the platescale keyword in the CCF. Will use the most frequen value.')
        platescale = 0.476513
    else:
        logger.log('info', 'Platescale retrieved from ccf file. Value: {}.'.format(platescale))
    return float(platescale)


def evaluate_zerodrift(tracking_header):
    """
    Checks if the header contains the ZERODRIFT keyword, which implies that
    the file is not suitable for working with omdrifthist.

    Args:
        tracking_header: a copy of the header for the tracking history file.

    Output:
        1 when finished; will exit if ZERODRIFT is found.
    """

    zerodrift_flag = True

    try:
        zerodrift = tracking_header['ZERODRIFT']
    except KeyError:
        zerodrift_flag = False

    if zerodrift_flag:
        logger.log('error', 'The file was marked as inadequate to work with omdrifthist.')
        sys.exit(0)

    return 1


########################################
########## PLOTTING FUNCTIONS ##########
########################################

def omdrifthist1(datax, datay, x0, y0, r0, scale = '', nbins = 50, added_text ='', output = 'plot', fig_title = 'OM tracking plot'):
    """
    Creates a tracking plot form the input points, with count histograms for the
    x - y axis.This task provides graphical and statistical information on the OM tracking history.

    Args:
        datax: the array of x-coordinates.
        datay: the array of y-coordinates.
        x0: the x coordinate for the center of the circle.
        y0: the y coordinate for the center of the circle.
        r0: the radius of the circle.
        nbins: number of bins. 50 by default.
        scale: the y scale.
        added_text: text to be added.
        output: the name of the final file. plot1.png by default
        fig_title: the name of the main figure..

    Output:
        1 when finished, 0 if could not finish the plot.
    """

    logger.log('info', 'Working on plot 1.')
    # evaluating data

    if len(datax) != len(datay):
        logger.log('warning', 'The coordinate length is not the same for bot axes. Plot 1 will not be produced...')
        return 0

    ####################################
    # definitions for the axes
    left, width = 0.1, 0.55
    bottom, height = 0.1, 0.55
    spacing = 0.005

    coordsA = "data"
    coordsB = "data"

    rect_scatter = [left, bottom, width, height]
    rect_histx = [left, bottom + height + spacing, width, 0.2]
    rect_histy = [left + width + spacing, bottom, 0.2, height]

    # start with a rectangular Figure
    f = plt.figure(figsize=(11, 11))

    ax_scatter = plt.axes(rect_scatter)
    ax_scatter.tick_params(direction='in', top=True, right=True)
    ax_histx = plt.axes(rect_histx)
    ax_histx.set_ylabel('Freq.')
    ax_histx.tick_params(direction='in', labelbottom=False)
    ax_histy = plt.axes(rect_histy)
    ax_histy.tick_params(direction='in', labelleft=False)
    ax_histy.set_xlabel('Freq.')
    # the scatter plot:
    t = np.arange(len(datax))
    ax_scatter.scatter(datax, datay, marker = 'o', label = 'Scattered points', c=t, cmap=plt.get_cmap('summer'))
    
    #drawing arrows...
    for i in range(0, len(datay) - 1):
        if i == 0:
            minx = datax[i]
            miny = datay[i]
            maxx = datax[i]
            maxy = datay[i]
        xyA = (datax[i], datay[i])
        xyB = (datax[i + 1], datay[i + 1])
        r = np.sqrt((x0 - datax[i]) ** 2 + (y0 - datay[i]) ** 2)
        if r < r0:
            con = ConnectionPatch(xyA, xyB, coordsA, coordsB,
                    arrowstyle = "-|>", shrinkA = 5, shrinkB = 5,
                      mutation_scale = 20, fc = "w")
        else:
            con = ConnectionPatch(xyA, xyB, coordsA, coordsB,
                    arrowstyle = "->", shrinkA = 5, shrinkB = 5,
                        mutation_scale = 20, fc = "w")
        ax_scatter.add_artist(con)
        
        if datax[i + 1] > maxx:
            maxx = datax[i + 1]
        if datax[i + 1] < minx:
            minx = datax[i + 1]
        if datay[i + 1] < miny:
            miny = datay[i + 1]
        if datay[i + 1] > maxy:
            maxy = datay[i + 1]

    #### more testing code
    if (r0 + x0) > maxx:
        maxx = r0 + x0
    if (x0 - r0) < minx:
        minx = x0 - r0
    if (r0 + y0) > maxy:
        maxy = r0 + y0
    if (y0 - r0) < miny:
        miny = y0 - r0

    if maxx > maxy:
        absmax = maxx
    else:
        absmax = maxy
    if minx > miny:
        absmin = miny
    else:
        absmin = minx

    binwidth = 0.25
    lim = np.ceil(np.abs([datax, datay]).max() / binwidth) * binwidth
   
    ax_scatter.set_xlim((absmin, absmax))
    ax_scatter.set_ylim((absmin, absmax))

    bins = np.arange(-lim, lim + binwidth, binwidth)
    ax_histx.hist(datax, bins = nbins, color = 'forestgreen', alpha = 0.2, label='x counts')
    ax_histy.hist(datay, bins = nbins, orientation = u'horizontal', color = 'forestgreen', alpha = 0.2,label='y counts')

    ax_histx.set_xlim(ax_scatter.get_xlim())
    ax_histy.set_ylim(ax_scatter.get_ylim())

    circle_region = plt.Circle((x0, y0), r0, color = 'b', fill=False, label = 'Nominal tracking circle')
    ax_scatter.add_patch(circle_region)

    ax_scatter.set_xlabel('x (pixels)')
    ax_scatter.set_ylabel('y (pixels)')

    #ax_histy.text(0.5, 1.5, added_text, fontsize = 9)
    plt.text(1.01, 0.6, added_text, ha='left', va = 'top', transform = ax_histx.transAxes)

    if scale != '':
        try:
            plt.yscale(scale)
        except ValueError:
            warnings.warn('The given scale is not supported. Using linear scale instead.')
            plt.yscale('linear')

    f.suptitle(fig_title, fontsize=19)

    if '2' in pages:
        if out_format.upper() == 'PDF':
            out1 = os.path.splitext(output)[0] + '_1{}.{}'.format('DRIFT_TEMP', out_format)
        else:
            out1 = os.path.splitext(output)[0] + '_{}.{}'.format('1', out_format)
    else:
        out1 = output + '.' + out_format

    logger.log('debug', 'Saving plot 1: {}.{} ({})'.format(output, out_format, out1))

    try:
        plt.savefig(out1)
    except FileNotFoundError:
        try:
            dirs, rfile = os.path.split(out1)
            os.makedirs(dirs)
            plt.savefig(out1)
        except:
            logger.log('error', 'Could not create {}. Could not resolve the given path.'.format(out1))

    if pyutils.is_notebook():
        plt.show()
    
    logger.log('info', 'Plot produced: {}'.format(out1))
    
    return 1


def omdrifthist2(roll, nframes, datax, datay, incremental_drift, scale = '', nbins = 50, added_text = '', output = 'plot', fig_title = 'OM tracking'):
    """
    Presents plots with data related to the drift for the tracking histogram:
     - the histogram with the incremental drift sizes.
     - the roll drift according to each frame.
     - the incremental drift spots coordinates.

    Args:
        roll: the roll frames data.
        nframes: an array with the frames for the roll drift plot.
        datax: an array with the x coordinates of the incremental drift spots.
        datay: an array with the y coordinates of the incremental drift spots.
        incremental_drift: the incremental drift array.
        scale: the wanted scale for the y axis.
        nbins: the number of bins for the histogram.
        added_text: extra text to be added to the figure.
        output: the output file.
        fig_title: name of the main figure.

    Output:
        1 when finished.
    """

    logger.log('info', 'Working on plot 2.')

    roll = np.array(roll) * 180 / math.pi
    f, ax = plt.subplots(2, 2, figsize = (8, 10), sharey=False, sharex=False)

    ax1 = ax[1,0]
    ax[1,0].plot(nframes, roll, marker = '.')
    high, bins, _ = ax[0,1].hist(incremental_drift, color = 'forestgreen', fill = True, bins = nbins, alpha = 0.2, density = False)

    # plot titles...
    ax[1,1].title.set_text('Incremental drift spot diagram')
    ax[1,0].title.set_text('Roll drift plot')
    ax[0,1].title.set_text('Drift size histogram')

    # left empty to add text
    ax[0,0].axis('off')
    ax[0,0].text(-0.1,0.3, added_text, fontsize=10)

    t = np.arange(len(datax))
    cs = ax[1,1].scatter(datax, datay, marker = 'o', c=t, cmap=plt.get_cmap('summer'), label = 'Scattered points')
    cbar = f.colorbar(cs, orientation = 'vertical')
    cbar.ax.set_ylabel('Frame number')

    ax[0,1].set_xlabel('Incremental drift size (pixels)')
    ax[0,1].set_ylabel('Counts')
    # lowering histogram plot:
    ax[0,1]
    ax[1,0].set_xlabel('Frame number')
    ax[1,0].set_ylabel('Roll drift (degrees)')
    ax[1,1].set_xlabel('x (pixels)')
    ax[1,1].set_ylabel('y (pixels)')
    skip_pos = fig_title.find(':') + 1
    fig_title = fig_title[:skip_pos] + "\n" + fig_title[skip_pos:]
    f.suptitle(fig_title, x = 0.3, fontsize = 16)
    f.tight_layout()
    
    # to add in future?
    if scale != '':
        try:
            plt.yscale(scale)
        except ValueError:
            warnings.warn('The given scale is not supported. Using linear scale instead.')
            plt.yscale('linear')

    if '1' in pages:
        if out_format.upper() == 'PDF':
            out2 = os.path.splitext(output)[0] + '_2{}.{}'.format('DRIFT_TEMP', out_format)
        else:
            out2 = os.path.splitext(output)[0] + '_{}.{}'.format('2', out_format)
    else:
        out2 = output + '.' + out_format

    logger.log('debug', 'Saving plot 2: {}.{} ({})'.format(output, out_format, out2))

    try:
        plt.savefig(out2)
    except FileNotFoundError:
        try:
            dirs, rfile = os.path.split(out2)
            os.makedirs(dirs)
            plt.savefig(out2)
        except:
            logger.log('error', 'Could not create {}. Could not resolve the path.'.format(out2))

    if pyutils.is_notebook():
        plt.show()
    logger.log('info', 'Plot produced: {}'.format(out2))

    return 1


########################################


def run(iparsdic):
    logger.log('warning', f'Executing {__file__} {iparsdic}')

    t_start = time.time()
    fits_file = iparsdic['set']
    trackradius = float(iparsdic['trackradius'])
    global pages
    pages = str(iparsdic['pages'])
    output = str(iparsdic['plotfile'])
    plot_abs_path = os.path.abspath(output)
    output_base = os.path.basename(plot_abs_path)
    output_base = os.path.splitext(plot_abs_path) # splits the format and the plotfile
    
    global out_format
    
    if output_base[1] == '':
        output = plot_abs_path
        out_format = 'pdf'
        logger.log('warning', 'Format not found in the plotfile parameter. Using {0}.{1} as default.'.format(plot_abs_path, out_format))
    else:
        output_base, out_format = output_base
        out_format = out_format.replace('.', '')
        output = output_base
        logger.log('debug', 'Using {}.{}'.format(output, out_format))

    logger.log('debug', 'Working with {}.{}'.format(output, out_format))
    nbins = int(iparsdic['nbins'])
    verbosity = int(os.environ['SAS_VERBOSITY'])

    if not out_format.upper() in ('PNG', 'PDF'):
        logger.log('error', 'Format {} not understood. Please use only pdf or png formats.'.format(out_format))
        sys.exit(0)

    TBD = 10

    if not os.path.isfile(fits_file):
        logger.log('error', 'The input file does not exist.')
        sys.exit(0)

    datamode = pyutils.get_key_word(fits_file, 'DATAMODE')
    if datamode != 'TRACKING':
        logger.log('error', 'Invalid datamode ({0}) for tracking history.'.format(datamode))
        sys.exit(0)

    try:
        binbpe = pyutils.get_key_word(fits_file, 'BINBPE')
        exp_id = pyutils.get_key_word(fits_file, 'EXP_ID')
        obj = pyutils.get_key_word(fits_file, 'OBJECT')
        obs_id = pyutils.get_key_word(fits_file, 'OBS_ID')
        filt = pyutils.get_key_word(fits_file, 'FILTER')
        frametime = pyutils.get_key_word(fits_file, 'FRMTIME')
    except FileNotFoundError:
        logger.log('error', 'Could not open the fits file. Quitting...')
        sys.exit(0)

    platescale = get_platescale(filt)
    trackradius = trackradius / platescale

    if os.path.isfile(fits_file):
        with fits.open(fits_file) as f:
            prim_h = f[0].header
            tracking_header = f[1].header
            t = Table(f[1].data)
    else:
        logger.log('error', 'Could not find the fits file. Quitting...')
        sys.exit(0)

    evaluate_zerodrift(tracking_header)

    logger.log('debug', 'File {0} read.'.format(fits_file))
    rpixel = trackradius

    try:
        nframes = t['FRAME']
        dx = t['DX']
        dy = t['DY']
        t_roll = t['ROLL']
        quality = t['QUALITY']
        nggs = t['NGGS']
    except KeyError:
        pyutils.pymodhdu(fits_file, 1, 'ZERODRIFT', 1, comment = 'File not suitable for working with omdrifthist.')
        logger.log('error', 'At least one column could not be loaded.')
        sys.exit(0)

    if len(nframes) == 0:
        pyutils.pymodhdu(fits_file, 1, 'ZERODRIFT', 1, comment = 'File not suitable for working with omdrifthist.')
        logger.log('warning', 'Not a valid tracking history file. Will write extension to notify.')
        sys.exit(0)

    nrows = len(t)

    # create an array with the calculated quality
    quality_array = quality / 1000000
    quality_array = np.sqrt(quality_array / (2 * nggs - 1))

    # verify the data (bad tracking files)
    nbad = 0
    nhist = 0

    x = []
    y = []
    roll = []

    for i in range(0, nrows):
        if quality_array[i] < TBD and nggs[i] > 3:
            nhist = nhist + 1
            x.append(dx[i] / 1000)
            y.append(dy[i] / 1000)
            roll.append(math.asin(t_roll[i] / 1000000))
        else:
            nbad = nbad + 1

    x0 = x[0]
    y0 = y[0]

    # creates the history of appearance of the filtered x,y points
    history = np.array([x, y])
    history = np.matrix.transpose(history)

    incdrift, increments, nout, n_out_0 = incremental_drift(history, x0, y0, rpixel)

    inc_x = increments[:,0]
    inc_y = increments[:,1]
    
    meandrift = sum(incdrift) / (len(nframes) - 1)
    del(increments)

    fig_title = 'OM tracking history plot: object {0}.'.format(obj)
    if '1' in str(pages):
        text = "Observation ID: {0}. \nExposure ID: {1}.\nFilter: {2}. Plate-scale: {3} \narcsecs/pixel.\n".format(obs_id, exp_id, filt, platescale)
        text = text + "Tracking frame time: {0} s.\nNumber of good tracking frames: {1}.\nTracking radius: {2}.\n".format(round(float(frametime)/1024, 2), nhist, round(trackradius))
        text = text + "Number of bad tracking frames: {0}.\n".format(nbad)
        omdrifthist1(x, y, x0, y0, rpixel, scale = '', nbins = nbins, added_text = text, output = output, fig_title = fig_title)
    
    if '2' in str(pages):
        text = "Observation ID: {0}. \nExposure ID: {1}.\nFilter: {2}. Plate-scale: {3} arcsecs/pixel.\n".format(obs_id, exp_id, filt, platescale)
        text = text + "Tracking frame time: {0} s.\nNumber of good tracking frames: {1}.\n".format(round(float(frametime)/1024, 2), nhist)
        text = text + "Tracking radius: {:.2f}.\n".format(trackradius)
        text = text + "Number of bad tracking frames: {0}.\n\n".format(nbad)
        text = text + "Percentage of pixels outside radius: {:.2f}%.\n\n".format(nout/len(nframes) * 100)
        #text = text + "Percentage of excursion outside initial\ncircle coordinates: {} %.\n\n".format(n_out_0/len(nframes) * 100)
        text = text + "Mean drift per tracking frame (pixels): {:.2f}.".format(meandrift)
        omdrifthist2(roll, nframes, inc_x, inc_y, incdrift, nbins = nbins, added_text = text, output = output, fig_title = fig_title)

    if '1' in str(pages) and '2' in str(pages) and out_format.upper() == 'PDF':
        logger.log('debug', 'More than one PDF created. Merging...')
        pdf_files_found = glob.glob(os.path.splitext(output)[0] + '*DRIFT_TEMP*')
        pdf_files_found.sort()
        logger.log('debug', 'sorted list: {}'.format(pdf_files_found))
        output = output.replace('DRIFT_TEMP', '')
        status = sasplt.merge_pdf(pdf_files_found, os.path.splitext(output)[0] + '.{}'.format(out_format))

        if status == 0:
            logger.log('warning', 'Could not merge the two PDFs')
        else:
            logger.log('debug', 'PDF merged. Cleaning up...')
            for pdffile in pdf_files_found:
                if pdffile == output + '.{}'.format(out_format):
                    pass
                else:
                    os.remove(pdffile)

    t_stop = time.time()
    logger.log('info', 'Finished running omdrifthist in {:.2f} seconds.'.format(t_stop - t_start))
    print('Finished running omdrifthist in {:.2f} seconds.'.format(t_stop - t_start))

