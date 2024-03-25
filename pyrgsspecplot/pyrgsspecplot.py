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

# pyrgsspecplot.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pyrgsspecplot (pyrgsspecplot-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

# pyrgsspecplot


import numpy as np
import pysas.pyutils.pyutils as pyutils
import pysas.pysasplot_utils.pysasplot_utils as sasplt
import sys
import pickle
from astropy.io import fits
from astropy.table import Table
import time
import os
import warnings
#warnings.filterwarnings("error")
import glob
import re
from pysas.logger import TaskLogger as TL
from astropy import units as u
import matplotlib.pyplot as plt
from astropy import constants as const
from astropy.coordinates import Angle


logger = TL('pyrgsspecplot')


##################################
######### PLOTTING UTILS #########
##################################

def plot_spectrum(spec_data, axisunits, fits_info, t_labels, output, plot_info, beta_calc_info):
    """
    Plots the given spectrum passed as a table object.

    Args:
        spec_data: the table containing the data to be plotted.
        axisunits: the units to plot for the x-axis.
        fits_info: a list containing information to add to the plot.
        t_labels: the labels from the table, related to spec_data.
        output: the name of the plot file.
        plot_info: list or tuple containing basic information to show in the plots.
        beta_calc_info: information needed for the operations between Channel and wavelength.

    Output:
        1 when finished.
    """
    
    logger.log('debug', 'Starting graph processing...')
   
    if dark_mode:
        plt.style.use('dark_background')
    else:
        plt.style.use('default')

    fig, ax1 = plt.subplots()
    t_xlabel, t_ylabel, t_elabel = t_labels

    logger.log('debug', 'Getting passed data.')
    
    try:
        spec_data, errors_t = spec_data
        logger.log('debug', 'Rebinned - separated tables for error and data.')
    except ValueError:
        logger.log('debug', 'Only one table for error and data.')
        errors_t = spec_data

    spec_pix, original_min_channel, original_channel_range, spec_val, spec_delta = beta_calc_info
    spec_data[t_elabel][np.isnan(spec_data[t_elabel])] = 0
    ax1.set_ylabel('COUNTS/CHANNEL')
    ax1.plot(spec_data[t_xlabel], spec_data[t_ylabel], label = 'Counts/channel')

    ax1.plot(errors_t[t_xlabel], errors_t[t_elabel], label = 'Error')
    ax1.legend()

    obs_id, exp_id, telescope, instr, date_obs, date_end, object_fits, ra, dec, exp_idstr, order, exposuret, src_label, spectrumtype, srcid = fits_info

    text = 'XMM. {0}. OBJECT: {1} RA: {2}. DEC: {3}\n'.format(instr, object_fits, ra, dec)
    text = text + 'OBS-ID: {0}. EXP-ID: {1}. Exp. Time: {2}.\nSource label: {3}. Source ID: {4}.'.format(obs_id, exp_id, exposuret, src_label, srcid)
    text = text + '\n\n'
    
    rebin_tag, alpha0, d, offaxis = plot_info

    fig.text(0.5, 0.8, text)
    ax1.set_position([0.1, 0.1, 0.8, 0.6])
    text_l = 'DATE-OBS: {0}. \nDATE-END: {1}.\n{2}.\n\n'.format(date_obs, date_end, rebin_tag)
    fig.text(0.1, 0.8, text_l)
    
    logger.log('debug', '{} {}'.format(np.nanmin(spec_data[t_xlabel].data), np.nanmax(spec_data[t_xlabel].data)))
    ax1.set_xlim(np.nanmin(spec_data[t_xlabel].data), np.nanmax(spec_data[t_xlabel].data))

    if axisunits == 'rad':
        ax1.set_xlabel('BETA CHANNEL')
        ax1.set_xlim((0, 3000))
        # draws an horizontal linee at x = 0
        if dark_mode:
            ax1.axhline(y = 0, color = 'white')
        else:
            ax1.axhline(y = 0, color = 'black')

        ax2 = ax1.twiny()
        ax2.set_position([0.1, 0.1, 0.8, 0.6])
        ax2.spines['top'].set_position(('axes', 1))
        ticks = ax1.get_xticks()
        ticks[np.where(ticks == 0)] = 1
        lambda_val = beta2lambda(d, alpha0, ticks, order * (-1), offaxis[0])
        
        print('lambda_val', lambda_val)
        lamb_array = np.arange(39) + 1
        lamb_major = np.array((5, 10, 15, 20, 25, 30, 35, 40))
        lamb_array_beta = lambda2beta(d, alpha0, lamb_array, order * (-1), offaxis[0])
        lamb_major_beta = lambda2beta(d, alpha0, lamb_major, order * (-1), offaxis[0])
        betamin = betaref + 0.5 * betawid + original_min_channel * betawid
        print('lambda_major:', lamb_major_beta)
        betarange = betawid * original_channel_range
        majorpos =(lamb_major_beta - betamin) / betarange
        labelpos = (lamb_array_beta - betamin) / betarange
        print('betamin', betamin, 'betarange', betarange)

        print('amjorpos', majorpos)
        #ax2.set_xticks(majorpos)
        ax2.xaxis.set_ticks(majorpos)
        ax2.xaxis.set_ticklabels(lamb_major)
        ax2.xaxis.set_ticks(labelpos, minor = True)
        #ax2.set_xlim(min(lambda_val), max(lambda_val))
        ax2.set_xlabel(r"$\lambda / \AA$")

        # energy position in the plot
        energy_major = np.array((5, 3.5, 2.5, 2, 1.5, 1, 0.5))
        lambda_energy_major = 12.3985 / energy_major
        energy_values = np.linspace(4.7, 0.4, 100)
        lambda_energy_values = 12.3985 / energy_values
        energy_major_pos = (lambda_energy_major - betamin) / betarange
        energy_values_pos = (lambda_energy_values - betamin) / betarange
        ax3 = ax1.twiny()
        ax3.set_position([0.1, 0.1, 0.8, 0.6])
        print('energy major pos:', energy_major_pos)
        ax3.spines['top'].set_position(('axes', 1.1))
        ax3.xaxis.set_ticks(energy_major_pos)
        ax3.xaxis.set_ticklabels(energy_major)
        ax3.xaxis.set_ticks(energy_values_pos, minor = True)
        ax3.set_xlabel('Energy / KeV')

    elif axisunits == 'angstrom':
        ax1.set_xlabel(r"$\lambda / \AA$")
        if dark_mode:
            ax1.axhline(y = 0, color = 'white')
        else:
            ax1.axhline(y = 0, color = 'black')
        #ax2.set_position([0.1, 0.1, 0.8, 0.6])
        ticks = ax1.get_xticks()
        lamb_marks = (5, 10, 15, 20, 25, 30, 35, 40)
        lamb_values = betaref + ticks * betawid
        lambda_values = np.arange(39) + 1
        lambda_pos = []
        for lamb_tick in lambda_values:
            lambda_pos.append(min(lamb_values, key=lambda x:abs(x - lamb_tick)))
        ax1.xaxis.set_ticklabels(np.around(lamb_values, 2))
        ticks[np.where(ticks == 0)] = 1
        energy_val = 12.3985 / lamb_values
        #ax2.xaxis.set_ticks(ticks)
        #ticks = ax1.get_xticks()
        #ticks[np.where(ticks == 0)] = 1
        #lambda_val = beta2lambda(d, alpha0, ticks, order * (-1), offaxis[0])

        #lamb_array = np.arange(39) + 1
        #lamb_major = np.array((5, 10, 15, 20, 25, 30, 35, 40))
        #lamb_array_beta = lambda2beta(d, alpha0, lamb_array, order * (-1), offaxis[0])
        #lamb_major_beta = lambda2beta(d, alpha0, lamb_major, order * (-1), offaxis[0])
        #lambda_pos = []
        #lambda_pos_minor = []

        #for lamb_tick in lamb_major_beta:
        #    lambda_pos.append(min(spec_data[t_xlabel], key=lambda x:abs(x - lamb_tick)))
        #for lamb_tick in lamb_array_beta:
        #    lambda_pos_minor.append(min(spec_data[t_xlabel], key=lambda x:abs(x - lamb_tick)))

        #lambda_pos = np.array(lambda_pos)
        #lambda_pos_minor = np.array(lambda_pos_minor)
        #betamin = betaref + 0.5 * betawid + original_min_channel * betawid
        #betarange = betawid * original_channel_range
        #majorpos = (lambda_pos - betamin) / betarange
        #minorpos = (lambda_pos_minor - betamin) / betarange
        #ax1.set_xticks(majorpos)
        #ax1.xaxis.set_ticks(majorpos)
        #ax1.xaxis.set_ticklabels(lamb_major)
        #ax1.xaxis.set_ticks(minorpos, minor = True)
        #ax2 = ax1.twiny()

        #ax2.set_xlim(min(lambda_val), max(lambda_val))
        #ax2.set_xlabel('Energy / KeV')

    fig.set_size_inches(12, 9)
    
    fig.suptitle('pyrgsspecplot -- {0} SPECTRUM; ORDER {1}'.format(spectrumtype, order))
    
    if out_format.upper() == 'XS':
        if os.getenv['DISPLAY']:
            plt.show()
        else:
            logger.log('warning', 'Display not available.') 
    else:
        try:
            logger.log('debug', 'Saving {}.{}.'.format(output, out_format))
            plt.savefig(output + '.' + out_format)
        except FileNotFoundError:
            try:
                dirs, rfile = os.path.split(output + '.' + out_format)
                os.makedirs(dirs)
                plt.savefig(output + '.' + out_format)
            except:
                logger.log('error', 'Could not create {}. Could not resolve the given path.'.format(output + '.' + out_format))


##################################
########### MISC UTILS ###########
##################################

def rebin_min_counts(table, min_counts, xcol, ycol, errcol = None):
    """
    Easy tool for 2D rebinning.
    
    Args:
        table: teh table to be rebinned.
        min_counts: the minimum counts per bin.
        xcol: name of the column with the x data.
        ycol: name of the column with the y counts.
        errcol: none by default. The name of the column with the errors.
    
    Output:
        t: the rebinned table.
    """

    logger.log('debug', 'Running rebbin_min_counts.')
    t = table
    newcounts = [0] * len(t)
    newchannel = [0] * len(t)
    newyerror = [0] * len(t)
    low_bin = [t[0][xcol]]
    high_bin = []

    howfar = 0 # how much of the table has been processed so far
    k = 0 # positions in the new tabble
    looped = 0 # number of rows a single new bin has needed to reach min_counts

    while howfar < len(t):
        howfar = howfar + looped
        used_bins = 0 # numbins
        runtotal = 0
        looped = 0

        for i in range(howfar, len(t)):
            if runtotal > min_counts:
                low_bin.append(i)
                high_bin.append(i)
                break
            used_bins = used_bins + 1
            if np.isnan(t[i][ycol]):
                t[i][ycol] = 0
                t[i][errcol] = 0
            runtotal = runtotal + t[i][ycol]
            newchannel[k] = newchannel[k] + t[i][xcol]
            newcounts[k] = newcounts[k] + t[i][ycol]
            looped = looped + 1
       
        if k < len(t) - 1:
            try:
                newchannel[k] = newchannel[k] / used_bins
                newcounts[k] = newcounts[k] / used_bins
            except ZeroDivisionError:
                newchannel[k] = newchannel[k] / 1
                newcounts[k] = newcounts[k] / 1
            newyerror[k] = np.sqrt(abs(newcounts[k]))
            k = k + 1

    #if axisunits == 'angstrom':
     #   for j in range(0, len(newchannel)):
      #      logger.log('debug', 'angs values: {} {} {}'.format(j, newchannel[j], (betaref + betawid * newchannel[j]) / order))
       #     newchannel[j] = (betaref + betawid * newchannel[j]) / order
        

#    logger.log('debug', 'i data: {} {}'.format(len(low_bin), low_bin))
    newchannel = newchannel[0:k-3]
    newcounts = newcounts[0:k-3]
    newyerror = newyerror[0:k-3]
    ts = Table((newchannel, newcounts, newyerror), names = (xcol, ycol, errcol))
    
    #if axisunits == 'rad':
    #    for j in range(0, len(newchannel)):
    #        newchannel[j] = (spec_val - spec_pix * spec_delta - 0.5 * spec_delta) + newchannel[j] * spec_delta
    
#    logger.log('debug', 'total K: {}'.format(ts))
    
    
    copy_newe = []
    for i in newyerror:
        copy_newe.extend([i, i])

    low_bin.append(high_bin[-1])

    copy_newy = []
    for i in newcounts:
        copy_newy.extend([i, i])

    #creating a 'binning' grid for the x-axis of the plots
    pos = [item for sublist in zip(low_bin, high_bin) for item in sublist]
    
    #if axisunits == 'angstrom':
     #   for j in range(0, len(pos)):
      #      pos[j] = (betaref + betawid * pos[j]) / order


    new_t = Table([pos[:-2], copy_newy, copy_newe], names = (xcol, ycol, errcol))

    return new_t, ts


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


def check_xmm_misc(spec_header):
    """
    Checks the XMM miscellanous data CCF file to search for RGS values.

    Args:
        spec_header: the header of the spectrum.
        instr: the name of the instrument.

    Output:
        (d, alpha0): the line separation and the main angle.
    """

    logger.log('debug', 'Looking for XMM misc data...')
    
    instr = spec_header['INSTRUME']

    d = 0
    alpha0 = 0

    try:
        alpha0 = spec_header['RGSALPHA']
    except KeyError:
        alpha0 = 0
    try:
        d = spec_header['LINE_SEP']
    except KeyError:
        d = 0

    if d != 0 and alpha0 != 0:
        return d, alpha0

    try:
        ccfpath = os.environ['SAS_CCFPATH']
    except KeyError:
        logger.log('error', 'Could not locate variable SAS_CCFPATH. Quitting...')
        sys.exit(0)

    folders = ccfpath.split(':')

    if len(folders) == 1:
        xmm_ccf_file = glob.glob(os.environ['SAS_CCFPATH'] + '/XMM_MISCDATA*')
        xmm_ccf_file = get_more_recent_ccf(xmm_ccf_file)
        logger.log('debug', 'CCF file used: {0}.'.format(xmm_ccf_file))
        with fits.open(xmm_ccf_file) as xmm:
            try:
                alpha0_data = xmm[1].data[xmm[1].data['PARM_ID'] == 'INCIDENCE_ANGLE'] 
                alpha0 = alpha0_data[alpha0_data['INSTRUMENT_ID'] == instr.upper()]['PARM_VAL'][0]
                alpha0_unit = alpha0_data[alpha0_data['INSTRUMENT_ID'] == instr.upper()]['PARM_UNIT'][0]
                if alpha0_unit.lower() == 'deg':
                    alpha0 = alpha0 * 180 / np.pi
                d_data = xmm[1].data[xmm[1].data['PARM_ID'] == 'GRAT_LINE_DENS']
                d = d_data[d_data['INSTRUMENT_ID'] == instr.upper()]['PARM_VAL'][0]
            except (KeyError, IndexError) as e:
                logger.log('warning', 'Could not locate alpha0 and d in the XMM CCF file.')
    else:
        xmm_ccf_list = []
        logger.log('debug', 'List of folders found in CCF path: {0}'.format(folders))
        for folder in folders:
            try:
                xmm_ccf_file = os.path.abspath(glob.glob(folder + '/XMM_MISCDATA*')[0])
            except IndexError:
                logger.log('debug', '{} does not contain XMM misc. data calibration file.'.format(folder))
                continue
            xmm_ccf_list.append(xmm_ccf_file)
        logger.log('debug', 'Found the following XMM misc. data CCF compatible files: {0}'.format(xmm_ccf_list))
        latest_ccf = get_more_recent_ccf(xmm_ccf_list)
        logger.log('debug', 'CCF file used: {0}.'.format(latest_ccf))

        with fits.open(latest_ccf) as xmm:
            try:
                alpha0_data = xmm[1].data[xmm[1].data['PARM_ID'] == 'INCIDENCE_ANGLE']
                alpha0 = alpha0_data[alpha0_data['INSTRUMENT_ID'] == instr.upper()]['PARM_VAL'][0]
                alpha0_unit = alpha0_data[alpha0_data['INSTRUMENT_ID'] == instr.upper()]['PARM_UNIT'][0]
                if alpha0_unit.lower() == 'deg':
                    logger.log('debug', 'Original alpha in degrees')
                    alpha0 = alpha0 * np.pi / 180
                d_data = xmm[1].data[xmm[1].data['PARM_ID'] == 'GRAT_LINE_DENS']
                d = d_data[d_data['INSTRUMENT_ID'] == instr.upper()]['PARM_VAL'][0]
            except (KeyError, IndexError) as e:
                logger.log('warning', 'Could not locate d and alpha0 in the XMM CCF file.')

    if alpha0 == 0 or d == 0:
        logger.log('error', 'Could not locate d or alpha0 neither in the Spectrum file or the XMM CCF file.')
        sys.exit(0)

    logger.log('info', 'Line separation and alpha angle retrieved from ccf file. Values: {}, {}.'.format(alpha0, d))
    return(float(d), float(alpha0))
    

def beta2lambda(d, alpha0, beta_values, order, offaxis):
    """
    Return the lambda equivalence to the beta channel array in the input.

    Args:
        d: the line separation of the spectrometer.
        alpha0: the angle of the spectrometer.
        lambda_values: the array containing the channel values.
        order: the order of the spectrum.
        offaxis: the value from the axis.

    Output:
        lamb_values: the lambda equivalence to the beta channel input.
    """

    if order == 0:
        logger.log('warning', 'Cannot obtain lambda values with order 0')
        return np.zeros(len(beta_values))

    lamb_values = (np.cos(beta_values) - np.cos(alpha0 + offaxis)) * (d / order)

    return lamb_values


def lambda2beta(d, alpha0, lambda_values, order, offaxis):
    """
    Transforms the beta channel values into wavelength measurements.

    Args:
        d: the line separation of the spectrometer.
        alpha0: the angle of the spectrometer.
        lambda_values: the array containing the channel values.
        order: the order of the spectrum.
        offaxis: the value from the axis.

    Output:
        beta: the beta conversion.
    """
    
    cosbeta = np.cos(alpha0 + offaxis) + order * lambda_values / d
    
    print('    cosbeta = np.cos(alpha0 + offaxis) + order * lambda_values / d', alpha0, offaxis, order, lambda_values, d)
    if sasplt.is_iterable(cosbeta):
        for i in range(0, len(cosbeta)):
            if cosbeta[i] > 1:
                cosbeta[i] = 0
    else:
        if cosbeta > 1:
            cosbeta = 0

    beta = np.arccos(cosbeta)

    return beta


def run(iparsdic):
    print(f'Executing {__file__} {iparsdic}')
    t_start = time.time()

    group = iparsdic['group']
    if 'T' in group.upper() or 'Y' in group.upper():
        group = True
    else:
        group = False

    global dark_mode
    dark_mode = iparsdic['dark_mode']
    if 'Y' in dark_mode.upper() or 'T' in dark_mode.upper():
        dark_mode = True
    else:
        dark_mode = False

    global out_format

    device = iparsdic['device']
    device = device.replace('/', '')

    srclist = iparsdic['sourcelistset']
    sourceid = int(iparsdic['sourceid'])
    
    plotfile = iparsdic['plotfile']
    plotfile = os.path.abspath(plotfile)
    plotfile, out_format = os.path.splitext(plotfile)


    if out_format == '':
        out_format = device
    else:
        if out_format.upper() != device.upper():
            logger.log('warning', 'Mismatch between device parameter and the extension given in the plotfile parameter. {} will be used.'.format(device))
        out_format = device

#    if out_format == '':
#        out_format = 'pdf'
#        logger.log('warning', 'Could not find format. Using {0}.{1} as default.'.format(plotfile, out_format))
#    else:
#        out_format = out_format.replace('.', '')
#        if not out_format.upper() in ('PDF', 'PNG'):
#            logger.log('error', 'Format {} not supported. Please use pdf or png.'.format(out_format))

    if out_format.upper() == 'PS':
        out_format = 'pdf'
        logger.log('warning', 'PostScript format devaluated. Using PDF instead.')

    format_flag = sasplt.check_format_compatibility(out_format)
    if format_flag:
        pass
    else:
        logger.log('warning', 'Format ({0}) not supported. Using PDF...'.format(out_format))
        out_format = 'pdf'

    global rebin
    rebin = iparsdic['rebin']

    spectrumsets = iparsdic['spectrumsets']
    if ',' in spectrumsets:
        spectrumsets = spectrumsets.replace(' ', '')
        spectrumsets = spectrumsets.split(',')
    else:
        spectrumsets = spectrumsets.split(' ')

    nspectrumsets = len(spectrumsets)
    if nspectrumsets == 0:
        logger.log('error', 'Empty list of spectra..')
        sys.exit(0)

    if 'T' in rebin.upper() or 'Y' in rebin.upper():
        rebin = True
    else:
        rebin = False

    global mincounts
    mincounts = int(iparsdic['mincounts'])
    if mincounts < 0:
        logger.log('error', 'mincounts must be greater than zero.')
        sys.exit(0)

    nspec = 0

    for spectrum in spectrumsets:
        if nspectrumsets == 1:
            pass
        else:
            nspec = nspec + 1
            
        logger.log('info', 'Evaluating file {}.'.format(spectrum))
        with fits.open(spectrum) as f:
            spec_data = f[1].data
            logger.log('debug', 'Filtering data using pyutils...')
            spec_data = Table(spec_data)
            # commented out in order to use nan in the binning
            #spec_data = pyutils.filter_data(spec_data) 
            spec_header = f[1].header

        try:
            hduclas2 = spec_header['HDUCLAS2']
        except KeyError:
            logger.log('warning', 'Keyword HDUCLAS2 missing in the spectrum file {}. Selecting BACKGROUND as default.'.format(spectrum))
            spectrumtype = 'BACKGROUND'
        if hduclas2 == 'TOTAL':
            spectrumtype = 'SRC+BKG'
        elif hduclas2 == 'NET':
            spectrumtype = 'NET'
        else:
            spectrumtype = 'BACKGROUND'

        global axisunits
        try:
            tcuni = spec_header['TCUNI']
        except KeyError:
            try:
                tcuni = spec_header['TCUNI1']
            except KeyError:
                logger.log('warning', 'Keyword TCUNI missing in the spectrum file {}. Selecting rad as default.'.format(spectrum))
                tcuni = 'rad'
                axisunits = 'BACKGROUND'
        
        if tcuni == 'Angstrom':
            axisunits = 'angstrom'
        elif tcuni == 'rad':
            axisunits = 'rad'
        else:
            axisunits = 'rad'

        src_label, offaxis = get_src_label_and_offaxes(srclist, sourceid)
        exposuret = float(pyutils.get_key_word(spectrum, 'Exposure'))
        global order
        order = spec_header['RFLORDER']

        global spec_delta
        try:
            spec_delta = spec_header['SPECDELT']
        except KeyError:
            logger.log('warning', 'SPECDELT not found')
            spec_delta = 1
        global spec_pix
        try:
            spec_pix = spec_header['SPECPIX']
        except KeyError:
            logger.log('warning', 'SPECPIX not found')
            spec_pix = 0
        global spec_val
        try:
            spec_val = spec_header['SPECVAL']
        except KeyError:
            logger.log('warning', 'SPECVAL not found')
            spec_val = 0

        detchans = spec_header['DETCHANS']
        nbins = len(spec_data)

        global betaref
        try:
            betaref = spec_header['TCRVL']
        except KeyError:
            try:
                betaref = spec_header['TCRVL1']
            except KeyError:
                logger.log('error', 'Could not locate reference in the input file.')
                sys.exit(0)
        global betawid
        try:
            betawid = spec_header['TCDLT']
        except KeyError:
            try:
                betawid = spec_header['TCDLT1']
            except KeyError:
                logger.log('error', 'Could not locate width reference in the input file.')
                sys.exit(0)

        channel_p = spec_data['CHANNEL']
        xmin = sorted(channel_p)[0] - (sorted(channel_p)[2] - sorted(channel_p)[1]) / 2.0
        xmax = sorted(channel_p)[-1] + (sorted(channel_p)[-1] - sorted(channel_p)[-2]) / 2.0

        try:
            counts_error_p = spec_data['STAT_ERR']
        except KeyError:
            pass

        t_elabel = 'STAT_ERR'
        t_xlabel = 'CHANNEL'

        try:
            counts_p = spec_data['COUNTS']
            t_ylabel = 'COUNTS'
            try:
                yerror = spec_data['STAT_ERR']
            except KeyError:
                yerror = np.sqrt(abs(counts_p))
        except KeyError:
            logger.log('debug', 'RATE-like spectrum...')
            try:
                rate_p = spec_data['RATE']
                try:
                    counts_p = exposuret * rate_p
                except RuntimeError:
                    logger.log('error', '{} {}'.format(exposuret, rate_p))
                    raise RuntimeError
                try:
                    yerror = np.sqrt(abs(counts_p))
                except KeyError:
                    yerror = np.sqrt(abs(spec_data['RATE'] * exposuret))
                t_ylabel = 'RATE'
            except KeyError:
                logger.log('error', 'Could not detect either COUNTS or RATE columns in spectrum data.')
                sys.exit(0)
        
        yerror = np.sqrt(abs(counts_p))

        data_table = Table((channel_p, counts_p, yerror), names = (t_xlabel, t_ylabel, t_elabel))
        
        # Grouping analysis...
        if group:
            try:
                grouping = spec_data['GROUPING']
                grouping_flag = True
            except KeyError:
                logger.log('warning', 'Could not locate the GROUPING column in file {}.'.format(spectrum))
                grouping_flag = False

            if grouping_flag:
                logger.log('info', 'Working on grouped spectrum.')
                total_new_bins = 0
                bin_c = 0
                
                for i in range(0, nbins):
                    if grouping[i] == 1:
                        total_new_bins = total_new_bins + 1

                summed_counts = [0] * total_new_bins
                n_channels = [0] * total_new_bins
                summed_channels = [0] * total_new_bins
                
                for i in range(1, nbins):
                    if t_ylabel == 'COUNTS':
                        summed_counts[bin_c] = summed_counts[bin_c] + counts_p[i - 1]
                    elif t_ylabel == 'RATE':
                        summed_counts[bin_c] = summed_counts[bin_c] + counts_p[i - 1]
                    try:
                        summed_channels[bin_c] = summed_channels[bin_c] + channel_p[i - 1]
                        n_channels[bin_c] = n_channels[bin_c] + 1
                    except IndexError:
                        logger.log('error', 'An error has ocurred while trying to form the grouped channels.')
                        sys.exit(0)

                    if grouping[i] == 1:
                        bin_c = bin_c + 1
                
                channel = []
                counts = []
               
                channel = np.divide(summed_channels, n_channels)
                if np.isnan(channel[-1]):
                    channel[-1] = nbins
                counts = summed_counts
                y_error = np.sqrt(counts)
                data_table = Table((channel, counts, y_error), names = (t_xlabel, t_ylabel, t_elabel))

        # Rebinning...
        if rebin:
            logger.log('info', 'Rebinning for file {}.'.format(spectrum))
            original_min_channel = xmin
            original_channel_range = xmax
            #DTin, DTout = sasplt.get_time_deltas(spectrum, 1, mincounts, 'CHANNEL')
            rebin_tag = 'Rebin: Minimum counts per bin: {0}'.format(mincounts)
            tstable = rebin_min_counts(data_table, mincounts, t_xlabel, t_ylabel, t_elabel)
        else:
            original_channel_range = spec_delta * detchans
            original_min_channel = spec_val - spec_pix * spec_delta - 0.5 * spec_delta
            DTin, DTout = 1, 1
            rebin_tag = 'No rebinning'
            tstable = sasplt.TSrebin(data_table, DTin, DTout, t_xlabel, t_ylabel, t_elabel)

        fits_info = collect_fits_info(spectrum)

        d, alpha0 = check_xmm_misc(spec_header)
        plot_info = (rebin_tag, alpha0, d, offaxis)
        fits_info.append(order)
        fits_info.append(exposuret)
        fits_info.append(src_label)
        fits_info.append(spectrumtype)
        fits_info.append(sourceid)
        t_labels = (t_xlabel, t_ylabel, t_elabel)

        beta_calc_info = spec_pix, original_min_channel, original_channel_range, spec_val, spec_delta
        
        if nspec != 0:
            if out_format.upper() == 'PDF':
                save_as = plotfile + '_{0}_TEMP_SPECPLOT'.format(nspec)
            else:
                save_as = plotfile + '_{0}'.format(nspec)
        else:
            save_as = plotfile
        
        plot_spectrum(tstable, axisunits, fits_info, t_labels, save_as, plot_info, beta_calc_info)


    if nspec > 1 and out_format.upper() == 'PDF':
        logger.log('info', 'Merging existing PDFs...')
        pdf_files = glob.glob(plotfile + '*_TEMP_SPECPLOT.{}'.format(out_format))
        status = sasplt.merge_pdf(pdf_files, plotfile + '.{}'.format(out_format))

        if status:
            for pdf_f in pdf_files:
                os.remove(pdf_f)
        else:
            logger.log('warning', 'Failed to merge the PDFs.')

    t_stop = time.time()

    logger.log('info', 'Finished running pyrgsspecplot in {} seconds.'.format(round(t_stop - t_start, 2)))


def get_src_label_and_offaxes(srclist, sourceid):
    """
    Returns the label and the offaxis values matching the source id from the source list.

    Args:
        srclist: the FITS file containing the source list info.
        sourceid: the source id that is being evaluated.

    Output:
        src_label: the label taken from the source file.
        offaxis: tuple with the DELTA_DISP and the DELTA_XDSP values.
    """
    
    logger.log('debug', 'Getting source label and offaxis values from {} with id {}.'.format(srclist, sourceid))

    with fits.open(srclist) as f:
        try:
            src_label = f['SRCLIST'].data['LABEL'][sourceid - 1]
        except (KeyError, IndexError) as e:
            logger.log('warning', 'Could not locate label with the current source id ({0}) and source list ({1}). Switching to sourceid = 1.'.format(sourceid, srclist))
            src_label = 'Indef'
            sourceid = 1
        try:
            src_delta_disp = f['SRCLIST'].data['DELTA_DISP'][sourceid - 1]
            src_delta_xdsp = f['SRCLIST'].data['DELTA_XDSP'][sourceid - 1]
            src_delta_disp = Angle(src_delta_disp, u.arcminute)
            src_delta_xdsp = Angle(src_delta_xdsp, u.arcminute)

            offaxis = (src_delta_disp.radian, src_delta_xdsp.radian)
            offaxis = (src_delta_disp.value * np.pi / 180 / 60, src_delta_xdsp.value * np.pi / 180 / 60)
        except (KeyError, IndexError) as e:
            logger.log('warning', 'Could not locate the offaxis values within the current source list and source id.')
            offaxis = (0,0)

    return src_label, offaxis


def collect_fits_info(specfits):
    """
    Returns the needed information from a spectrum fits file.

    Args:
        specfits: the spectrum fits file, either the path or an already opened
    astropy object.

    Output:
        obs_id, exp_id, telescope, instr, date_obs, date_end, object_fits, ra, dec,
    exp_idstr
    """

    obs_id = pyutils.get_key_word(specfits, 'OBS_ID')
    exp_id = pyutils.get_key_word(specfits, 'EXP_ID')
    telescope = pyutils.get_key_word(specfits, 'TELESCOP')
    instr = pyutils.get_key_word(specfits, 'INSTRUME')
    date_obs = pyutils.get_key_word(specfits, 'DATE-OBS')
    date_end = pyutils.get_key_word(specfits, 'DATE-END')
    object_fits = pyutils.get_key_word(specfits, 'OBJECT')

    if object_fits == 'unknown':
        object_fits = 'Indef'

    ra = pyutils.get_key_word(specfits, 'RA_OBJ')
    if ra == 'unknown':
        ra = pyutils.get_key_word(specfits, 'RA')
        if ra == 'unknown':
            ra = 'Indef'
    try:
        ra = round(ra, 3)
    except TypeError:
        pass

    dec = pyutils.get_key_word(specfits, 'DEC_OBJ')
    
    if dec == 'unknown':
        dec = pyutils.get_key_word(specfits, 'DEC')
        if dec == 'unknown':
            dec = 'Indef'
    
    try:
        dec = round(dec, 3)
    except TypeError:
        pass

    exp_idstr = pyutils.get_key_word(specfits, 'EXPIDSTR')

    return[obs_id, exp_id, telescope, instr, date_obs, date_end, object_fits, ra, dec, exp_idstr]

