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

# pysasplot_utils.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pysasplot_utils (pysasplot_utils-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 


import pysas.pyutils.pyutils as pyutils
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import os
from astropy.table import Table
import sys
import re
import warnings
import matplotlib.backends.backend_pdf
import pickle
from pypdf import PdfMerger
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

def text_plot(fits_file, extra_text = ''):
    """
    Prepares the text for the plot reading Keywords from the given FITS file.

    Args:
        fits_file: the path to the FITS file.
        extra_text: additional text to add to the plot. Empty by default.

    Output:
        text_plot: the text as a string to be added to the plot.
    """

    obs = pyutils.get_key_word(fits_file, 'OBS_ID')
    expo = pyutils.get_key_word(fits_file, 'EXPIDSTR')
    inst = pyutils.get_key_word(fits_file, 'INSTRUME')
    revolut = pyutils.get_key_word(fits_file, 'REVOLUT')
    ra = pyutils.get_key_word(fits_file, 'RA_OBJ')
    dec = pyutils.get_key_word(fits_file, 'DEC_OBJ')
    obj = pyutils.get_key_word(fits_file, 'OBJECT')
    date_obs = pyutils.get_key_word(fits_file, 'DATE-OBS')

    text_plot = 'OBS ID: {}\nInstrument: {}\nExposure: {}\nRevolution: {}\nDate: {}\nRA & DEC: ({} {})\n\n{}'.format(obs, inst, expo, revolut, date_obs, ra, dec, extra_text)

    return text_plot


def ingest_data(fits_file, in_data, label = 'label'):
    """
    Prepares the data from the input in a key-value, ready to plot with the
    other functions.

    Args:
        fits_file: the path or the HDU mobject for the fits file.
        in_data: the data to use. Can by an ndarray object or string-like, as in extension:card.
        label: the label to address the data.

    Output:
        data: the adapted dictionary with the {label:data}
    """

    if isinstance(fits_file, str):
        try:
            f = fits.open(fits_file)
        except (FileNotFoundError, ValueError) as e:
            warnings.warn('Could not locate file {}. Quitting...'.format(fits_file))
            sys.exit(0)
    elif isinstance(fits_file, fits.hdu.hdulist.HDUList):
        f = fits_file
    else:
        warnings.warn('Cannot open the FITS file. Checking the card for array instead of extensions...')

    data = dict()

    if isinstance(in_data, np.ndarray):
        print('Input data: numpy array.')
        data.update({label : in_data})
    elif isinstance(in_data, str):
        in_data = in_data.strip()
        ext, card = in_data.split(':')
        try:
            data.update({ext + ':' + card : f[ext].data[card]})
        except KeyError:
            print('Could not find the combination of extension-key {} in the current FITS file.'.format(ext + ':' + card))
            f.close()
            return None
    elif is_iterable(in_data):
        for comb in range(0, len(in_data)):
            if isinstance(in_data[comb], np.ndarray):
                if is_iterable(label):
                    try:
                        data.update({label[comb] : in_data[comb]})
                    except IndexError:
                        data.update({'{0}_{1}'.format(label[-1], comb) : in_data[comb]})
                else:
                    data.update({'{0}_{1}'.format(label, comb) : in_data[comb]})
            else:
                try:
                    in_data[comb] = in_data[comb].strip()
                    ext, card = in_data[comb].split(':')
                    try:
                        data.update({ext + ':' + card : f[ext].data[card]})
                    except KeyError:
                        print('Could not find the following combination key: {}.'.format(ext + ':' + card))
                        continue
                except KeyError:
                    print('Could not find combination {} in the given FITS file.'.format(ext + ':' + card))
                    continue
    else:
        print('Format unrecognised for x data. Quitting...')
        f.close()
        return None
    
    f.close()

    return data


def is_iterable(py_obj):
    """
    Given a Python object, will return True or False if it's and iterable object aside
    from string.

    Args:
        py_obj: the object that has to be evaluated.

    Output:
        bool: whether or not is iterable.
    """

    from collections.abc import Iterable

    if isinstance(py_obj, Iterable) and not isinstance(py_obj, str):
        return True
    else:
        return False


def get_time_deltas(fits_file, extension = 1, points = 512, x_data = 'TIME', card = 'TIMEDEL'):
    """
    Finds the proper Delta intervals for a FITS file.

    Args:
        fits_file: the fits file: either the path or one already opened.
        extension: the extension for the time sereis to be evaluated. 0 by
    default (primary HDU).
        points: the final number of points wanted. Default: 512.
        x_data: the data to evaluate the x-axis delta. TIME by default.
        card: the card to search in the extension's header. TIMEDEL by default.

    Ouput:
        (DTin, DTout): the initial and final delta time intervals.
        Will return (1, 1) if the file could not be opened or if the extension
    does not contain a proper TIME data column (implying no rebinning).
    """
    
    if not isinstance(fits_file, Table):
        timedel = pyutils.get_key_word(fits_file, card, extension)
    else:
        timedel = 'unknown'

    if isinstance(fits_file, str):
        try:
            with fits.open(fits_file) as f:
                t0 = f[extension].data[x_data][0]
                tf = f[extension].data[x_data][-1]
                fsize = f[extension].data.size
        except FileNotFoundError:
            print('Could not locate file.')
            return (1,1)
    elif isinstance(fits_file, fits.hdu.hdulist.HDUList):
        try:
            t0 = fits_file[extension].data[x_data][0]
            tf = fits_file[extension].data[x_data][-1]
            fsize = fits_file[extension].data.size
        except KeyError:
            print('Could not locate TIME column in data at [{0}].'.format(extension))
            return (1, 1)
    elif isinstance(fits_file, Table):
        t0 = fits_file[x_data][0]
        tf = fits_file[x_data][-1]
        fsize = len(fits_file)

    if timedel == 'unknown':
        DTin = int(np.round(abs(tf - t0) / fsize))
    else:
        DTin = timedel

    DTout = int(np.round((tf - t0) / points))

    return DTin, DTout


def TSrebin(tstable, DTin, DTout, t_xlabel = 'TIME', t_ylabel = 'RATE', t_elabel = 'ERROR', fracexp = 'FRACEXP'):
    """
    Re-binning function.

    Input:
        tstable: time series with TIME, RATE and ERROR columns.
        DTin: the input bin size.
        DTout: the output bin size.
        t_xlabel: the label to search for the x value. TIME by default.
        t_ylabel: the label to search for the y value. RATE by default.
        t_elabel: the label to search for the error values. ERROR by default.
        fracexp: the label to search for the FRACEXP. FRACEXP by default.

    Output:
        ntstable: a Table object with the corrected bin size.
    """

    #
    # Check input Table Columns, in case it's been loaded as a rec array (as in ext.data)
    #

    if isinstance(tstable, fits.fitsrec.FITS_rec):
        tstable = Table(tstable)

    colNames = tstable.keys() # Input ColumnNames
    mandatoryColumns = [t_xlabel, t_ylabel, t_elabel, fracexp] # Mandatory ColumnNames
    diff = set(mandatoryColumns) - set(colNames)

    fracexp_chk = 0
    if diff == {fracexp}:
        print('FRACEXP is missing. fracexp = 1')
        fracexp_chk = 1
    elif len(diff) != 0:
        print('Missing Columns in input Table : ', diff, '\n Exiting.')
        sys.exit(1)

    #
    # Re-Binning of the Table 'tstable'
    #

    tstable.sort(t_xlabel)
    ntime = tstable[t_xlabel]
    nrate = np.nan_to_num(tstable[t_ylabel])
    nerror = np.nan_to_num(tstable[t_elabel])

    if fracexp_chk == 1:
        fracexp = np.linspace(1, 1, len(ntime))
    else:
        fracexp = np.nan_to_num(tstable[fracexp])

    tcum = np.nancumsum(tstable[t_xlabel])
    rcum = np.nancumsum(nrate * fracexp) # Errors propagation are weighted by the FRACEXP from the TS
    ecum = np.nancumsum(nerror**2 * fracexp)
    fcum = np.nancumsum(fracexp)

    nin = len(rcum) # Number of In points

    t_bin_frac = int(np.round(DTout / DTin))

    if t_bin_frac <= 1: # No re-binning
        ntstable = tstable
        new_time_bin = t_bin_frac
        print('    No re-binning needed for this Light Curve. Input / Output time bins ratio : ', t_bin_frac)
    else:
        nout = int(nin/t_bin_frac) # Number of Out points. t_bin_frac == DTout / DTin ('TIMEDEL'). Re-binning factor

        #print('    Input / Output time bins / ratio : ', DTin, 'sec', ' / ',DTout, 'sec', ' / ', t_bin_frac)

        #print('    Input / Output dots number       : ', nin, ' / ',nout)

        i1 = np.arange(nout) * t_bin_frac
        i2 = np.concatenate((i1[1:] - 1, np.array([nin - 1])))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category = RuntimeWarning) #
            if fracexp_chk == 0: # TS has FRACEXP column => rate and error are weighted by FRACEXP
                nrate  = ((rcum[i2] - rcum[i1]) / (fcum[i2] - fcum[i1])    )
                nerror = (np.sqrt(np.nan_to_num(ecum[i2] - ecum[i1])) / (fcum[i2] - fcum[i1]))
                ntime = (tstable[t_xlabel][i2] + tstable[t_xlabel][i1]) / 2.
                nfrac = (fcum[i2] - fcum[i1]) / (i2 - i1)
                ntstable = Table([ntime, nrate, nerror, nfrac], names = [t_xlabel, t_ylabel, t_elabel, fracexp])
            else: # TS has NOT FRACEXP column => fracexp = 1
                nrate  = ((rcum[i2]-rcum[i1]) / (fcum[i2] - fcum[i1])    )
                nerror = (np.sqrt(np.nan_to_num(ecum[i2] - ecum[i1]))/(fcum[i2]-fcum[i1]))
                ntime = (tstable[t_xlabel][i2] + tstable[t_xlabel][i1])/2.
                ntstable = Table([ntime, nrate, nerror], names = [t_xlabel, t_ylabel, t_elabel])

    return ntstable


def load_figures(list_of_saved_figs):
    """
    Loads a list of pickled figures (passed as a list of paths) and returns a list of figure objects.

    Args:
        list_of_saved_figs: a list containing the paths of the pickled figures.

    Output:
        saved_figs: a list of figures.
    """

    saved_figs = []

    for i in list_of_saved_figs:
        with open(i, 'rb') as f:
            try:
                unpickled = pickle.load(f)
                saved_figs.append(unpickled)
            except AttributeError:
                warnings.warn('Could not open the pickled file: callbacks error.')
                saved_figs.append(None)

    return saved_figs


def saves_in_pdf(fig_list, output_name = 'output', papertype = 'a4'):
    """
    Saves the given figures into a single pdf file.

    Args:
        fig_list: a list or tuple containing the Matplotlib elements to be
    saved into a pdf. Recommended: matplotlib.figure.Figure.
        output_name: the name for the pdf file.
        papertype: the paper type for the output. A4 by default.

    Output:
        the absolute path of the created pdf.
        None if the list is empty or the type of fig_list is not correct.
    """

    from matplotlib.backends.backend_pdf import PdfPages

    try:
        if len(fig_list) == 0:
            warnings.warn('The given list is empty.')
            return None
    except TypeError:
        warnings.warn('The input fig_list is not iterable. Quitting...')
        return None

    missed_fig = 0

    with PdfPages('{}'.format(output_name)) as pdf:
        for i in range(0, len(fig_list)):
            try:
                pdf.savefig(fig_list[i], papertype = papertype)
            except ValueError:
                warnings.warn('Index {0} cannot be saved as it is not recognised as a Figure. Skipping...'.format(i))
                missed_fig = missed_fig + 1
                continue

    if missed_fig == len(fig_list):
        warnings.warn('The pdf is empty due to all figures being non-compatible.')

    return os.path.abspath('{}'.format(output_name))


def simple_1d_hist(y_data, x_label = 'x', y_label = 'y', add_text = '', scale = '', nbins = 20, sharebins = False, \
    fits_file = '', fits_info = True, plot_title = '', outformat = 'pdf'):
    """
    Utility for simple 1 dimention histogram.

    Args:
        y_data: the data for the histogram. Uses the inputs from ingest_data. For example, if fits_file has an input: y_data = ['RATE:RATE', array1, array2...].
        x_label: the label for the x-axis.
        y_label: the label for the y-axis.
        add_text: additional text to add alongside the histogram.
        scale: the desired scale to adapt the y-data.
        nbins: the number of bins for the histogram. 20 by default.
        sharebins: whether or not force all the data to have the same bins distribution.
        fits_file = the fits file to use (if any).
        fits_info: Bool. Whether or not show basic info from the FITS file.
        plot_title: the title of the plot.
        outformat: the format (according to matplotlib. PDF by default.
    """

    plt.style.use('ggplot')
    y_data = ingest_data(fits_file, y_data, y_label)

#    if y_data_errors != '':
#        y_data_errors = ingest_data(fits_file, y_data_errors, y_label)

    fig = plt.figure(figsize = (16, 9), facecolor = 'white')

    if fits_info or add_text != '':
        ax = fig.add_axes([0.3, 0.3, 0.6, 0.4])
    else:
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])

    if sharebins:
        y_data_list = list(y_data.values())
        nbins = np.histogram(np.hstack(y_data_list), bins = nbins)[1]

    for key in y_data.keys():
        try:
            #y_key_error = y_data_errors[key]
            y_error_flag = True
        except (KeyError, TypeError) as e:
            y_error_flag = False
        if not y_error_flag:
            heights, bins, _ = ax.hist(y_data[key], label = str(key), histtype = 'step', fill = True, alpha = 0.2, bins = nbins)
        else:
            heights, bins, _ = ax.hist(y_data[key], label = str(key), histtype = 'step', fill = True, alpha = 0.2, bins = nbins)
            #TODO add errors as separate plotting

    ax.legend(bbox_to_anchor = (1.05, 1), loc = 'upper left', borderaxespad = 0.)

    if fits_file != '' and fits_info:
        add_text = text_plot(fits_file, add_text)

    if add_text != '':
        plt.gcf().text(0.02, 0.5, add_text, fontsize = 14)
    plt.subplots_adjust(top = 0.3)

    if scale != '':
        try:
            plt.yscale(scale)
        except ValueError:
            warnings.warn('The given scale is not supported. Using linear scale instead.')
            plt.yscale('linear')

    if is_iterable(x_label):
        x_label = x_label[0]
    if is_iterable(y_label):
        y_label = y_label[0]

    if plot_title == '':
        plot_title = '{0}_{1}_hist'.format(x_label, y_label)

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(plot_title)

    # writes the filename filtering out non_alphabetical characters
    file_name = re.sub(r'\W+', '', plot_title)

    # will save the plot. If the program is running in a Notebook environment, will show the plot.
    if pyutils.is_notebook():
        plt.show()
        if outformat.upper() == 'PDF':
            saves_in_pdf([fig], file_name)
        elif outformat.upper() == 'PNG':
            plt.savefig(file_name + '.png')
        else:
            warnings.warn('Unrecognised format, will not be saved.')
    else:
        if outformat.upper() == 'PDF':
            saves_in_pdf([fig], file_name)
        else:
            try:
                plt.savefig(file_name + '.{}'.format(outformat))
            except ValueError:
                warnings.warn('Unrecognised format, will not be saved.')

    return fig


def simple_2d_plot(x_data, y_data, x_data_errors = '', y_data_errors = '', plot_title = '', x_label = 'x', y_label = 'y', fits_file = '', fits_info = True, \
    add_text = '', scale = '', points = 512, outformat = 'png'):
    """
    Utility for simple 2 dimentional plots. The data can be:
        from FITS files, written as in EXT:CARD.
        iterable types, including numpy arrays.
        Iterable types with a mix of the above.

    If using a FITS file, always use the phrasing EXT:CARD to refer to an
    extension and card data. Introduce first this information and leave the
    other type of arrays for last.

    Args:
        x_data: the x coordiantes of the data.
        y_data: the y coordinates of the data.
        x_data_errors: errors for the x axis.
        y_data_errors: errors for the y axis.
        plot_title: title for the plot. Will be used also when writting the file.
        x_label: label for the x axis. x by default.
        y_label: label for the y axis. y by default.
        fits_file: only needed if requesting an extension:card in one of the data inputs.
        add_text: additional text to add. None by default.
        scale: the scale to apply.
        points: the number of points. Required in case of rebinning.
        outformat: the format for the output.
    """

    plt.style.use('ggplot')


    if isinstance(fits_file, Table):
        x_data, y_data, x_data_errors, y_data_errors = ingest_table(fits_file, points, x_data, y_data, x_error_label = x_data_errors, y_errors_label = y_data_errors)
        fits_info = False # it's impossible to extract those values from a table object
    else:
        x_data = ingest_data(fits_file, x_data, x_label)
        y_data = ingest_data(fits_file, y_data, y_label)

        if y_data_errors != '':
            y_data_errors = ingest_data(fits_file, y_data_errors, y_label)
        if x_data_errors != '':
            x_data_errors = ingest_data(fits_file, x_data_errors, x_label)

    fig = plt.figure(figsize = (16, 9), facecolor = 'white')
    if fits_info or add_text != '':
        ax = fig.add_axes([0.3, 0.3, 0.6, 0.4])
    else:
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])

    if len(list(x_data.keys())) == 1:
        x_data_key = list(x_data.keys())[0]
        x_data = list(x_data.values())[0]

        for key in y_data.keys():
            try:
                y_key_error = y_data_errors[key]
                y_error_flag = True
            except (KeyError, TypeError) as e:
                y_error_flag = False
            try:
                x_key_error = x_data_errors[key]
                x_error_flag = True
            except (KeyError, TypeError) as e:
                x_error_flag = False
            if not y_error_flag and not x_error_flag:
                try:
                    ax.plot(x_data, y_data[key], marker='.', label = str(key), linewidth = 0.8)
                    ax.legend(bbox_to_anchor = (1.05, 1), loc = 'upper left', borderaxespad=0.)
                except ValueError:
                    print('Mismatching sizes for x and y: {} and {}. Omitting this curve.'.format(len(x_data), y_data[key].size))
                    continue
            elif x_error_flag and not y_error_flag:
                try:
                    ax.errorbar(x_data, y_data[key], xerr = x_key_error, marker='.', label = str(key), linewidth = 0.8)
                except ValueError:
                    print('Mismatching between the given arrays. Key: {}.'.format(key))
                    continue
            elif y_error_flag and not x_error_flag:
                try:
                    ax.errorbar(x_data, y_data[key], yerr = y_key_error, marker='.', label = str(key), linewidth = 0.8)
                except ValueError:
                    print('Mismatching between the given arrays. Key: {}.'.format(key))
                    continue
            elif y_error_flag and x_error_flag:
                try:
                    ax.errorbar(x_data, y_data[key], xerr = x_key_error, yerr = y_key_error, marker='.', label = str(key), linewidth = 0.8)
                except ValueError:
                    print('Mismatching between the given arrays. Key: {}.'.format(key))
                    continue

    if fits_info and (isinstance(fits_file, str) or isinstance(fits_file, fits.hdu.hdulist.HDUList)):
        add_text = text_plot(fits_file, add_text)

    plt.gcf().text(0.02, 0.5, add_text, fontsize=14)
    #plt.subplots_adjust(top=0.3)

    if scale != '':
        try:
            plt.yscale(scale)
        except ValueError:
            warnings.warn('The given scale is not supported. Using linear scale instead.')
            plt.yscale('linear')

    if is_iterable(x_label):
        x_label = x_label[0]
    if is_iterable(y_label):
        y_label = y_label[0]

    if plot_title == '':
        plot_title = '{0}_{1}_plot'.format(x_label, y_label)

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(plot_title)

    file_name = re.sub(r'\W+', '', plot_title)
    # will save the plot. If the program is running in a Notebook environment, will show the plot.
    if pyutils.is_notebook():
        plt.show()
        if outformat.upper() == 'pdf':
            saves_in_pdf([fig], file_name)
        else:
            plt.savefig(file_name + '.{}'.format(outformat))
    else:
        if outformat.upper() == 'pdf':
            saves_in_pdf([fig], file_name)
        else:
            try:
                plt.savefig(file_name + '.{}'.format(outformat))
            except ValueError:
                warnings.warn('Unrecognised format. Will not save plot.')

    return fig


def ingest_table(table, points, x_label, y_labels, x_error_label = None, y_errors_label = None):
    """
    Ingest the data from a given table and returns the data using Python
    dictionaries with labels. Only labels from the table are supported.

    Args:
        table: the table object.
        points: the number of points wanted. A rebinning will be applied to the table.
        x_label: the label for the x axis.
        y_labels: the label (or array of labels) for the y data.
        x_error_label: the label for the error for the x-coordinates.
        y_error_labels: the label (or array of labels) for the error of the
    y-coordinates.

    Output:
        (x_data, y_data, x_error, y_data_errors): set of dictionaries containing
    the information from the table.
    """

    DTin, DTout = get_time_deltas(table, 1, points)
    t_bin_frac = int(np.round(DTout / DTin))
    if t_bin_frac <= 1:
        print('No rebinning.')
    else:
        table = TSrebin(table, DTin, DTout)

    x_data = {x_label : table[x_label]}
    y_data = dict()

    if is_iterable(y_labels):
        for label in y_labels:
            y_data.update({label : table[label]})
    elif isinstance(y_labels, str):
        y_data.update({y_labels : table[y_labels]})

    nrows = len(table)
    x_error = dict()

    try:
        if x_error_label:
            x_error = x_error.update({x_error_label : table[x_error_label]})
    except KeyError:
        print('Could not find errors for the x axis in {0}.'.format(x_error_label))

    y_error = dict()

    if y_errors_label:
        if is_iterable(y_errors_label):
            for label in y_errors_label:
                try:
                    y_error.update({label : table[label]})
                except KeyError:
                    print('Could not find {0} in the given table.'.format(label))
                    continue
        elif isinstance(y_errors_label, str):
            try:
                y_error.update({y_labels : table[y_labels]})
            except KeyError:
                print('Could not find {0} in the given table.'.format(y_labels))

    return(x_data, y_data, x_error, y_error)


def merge_pdf(pdf_files, output_file):
    """
    Merges several PDF files passed as the arguments. 
    
    Args:
        pdf_files: list or tuple containing the paths to the pdfs.
        output_file: the name of output file.

    Output:
        1 depending on whether or not the process has been completed; 0 if not.
    """

    merger = PdfMerger()
    total_files = len(pdf_files)
    e_count = 0

    for pdf in pdf_files:
        try:
            merger.append(pdf)
        except:
            print('Could not append {}.'.format(pdf))
            e_count = e_count + 1

    with open(output_file, 'wb') as out:
        merger.write(out)

    if e_count == total_files:
        print('ERROR: No pdf was merged')
        return 0

    #merger.write(output_file)
    
    merger.close()

    return 1


def plot_image(path_to_image, ext = 0, output = None):
    """
    Plots and saves an image corresponding to a FITS image.

    Args:
        path_to_image: the path to the FITS file.
        ext: the extension of the image in the FITS file. 0 by default.
        output: None by default. Whethere or not save the image.

    Output:
        0 when finished.
    """

    with fits.open(path_to_image) as img:
        img_data = img[ext].data

    plt.imshow(img_data)

    if output is None:
        if os.getenv('DISPLAU'):
            plt.show()
        else:
            warnings.warn('Nothing was found in DISPLAY -- nothing was produced')
        return 0
    else:
        plt.savefig(output)

    return 0


def check_format_compatibility(out_format):
    """
    Checks if the input format is available as a matplotlib backend format.

    Args:
        out_format: the format to be checkec.

    Output:
        bool: whether or not the format can be used.
    """

    format_list = ('PNG', 'PDF', 'PGF', 'EPS', 'SVG2', 'RGBA', 'RAW', 'PS', 'SVG')

    if out_format.upper() in format_list:
        return True
    else:
        return False


def plot_region_box(ax, x1, y1, width, height, angle = 0, fill = False, colour = 'green', text = None, transform = None):
    '''
    Returns an axis object with with a box region printed on it.

    Args:
        ax: the original axis to use for the plot.
        x1: the starting x coordinate for the box.
        y1: the starting y coordinate for the box.
        width: the width of the box.
        height: the heigth of the box.
        angle: the angle of the box (if any). 0 by default.
        fill: boolean. Whether or not fill the box.
        colour: the colour of the box and the fill (if fill = True).
        text: None by default. Text to add at the (x1, y1) coordinates.
        transform: None by default. The transformation for the axis. Must be comatible with matplotlib standards.

    Output:
        f_ax: the axis after plotting the box.
    '''
     
    rec = Rectangle((x1, y1), width, height, angle, fill = fill, transform = transform, color = colour)
    
    pc = PatchCollection([rec], match_original = True)
    

    if text is None:
        pass
    else:
        ax.annotate(text, (x1, y1), color = colour, fontsize = 10)
        
    ax.add_collection(pc)
    
    return None


def reg_to_list(reg):
    ''' 
    Gets the information from a region based on the input string (based on ds9 formatting).

    So far, only tested for BOX regions.

    Args:
        reg: the region string in ds9 standards.

    Output:
        TODO: must be useful for all shapes. 
    ''' 
    
    shape_info, shape_details = reg.split('#') 
    shape_info = shape_info.strip().rstrip() 
    
    if 'BOX' in shape_info.upper(): 
        polygon = 'BOX' 
        x1, y1, width, heigth, angle = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", shape_info)
        shape_info = (polygon, x1, y1, width, heigth, angle)
        
    # text details 
    if shape_details.find('COLOR') == -1: 
        colour = 'green' 
    else: 
        c_letters = shape_details[shape_details.find('COLOR') + 6 : shape_details.find('COLOR') + 9]
        if c_letters.upper() in 'RED': 
            colour = 'red' 
        elif c_letters.upper() in 'GREEN': 
            colour = 'green' 
        elif c_letters.upper() in 'BLUE': 
            ccolour = 'blue' 
        elif c_letters.upper() in 'CYAN': 
            colour = 'cyan' 
        elif c_letters.upper() in 'WHITE':  
            ccolour = 'white' 
        elif c_letters.upper() in 'MAGENTA': 
            colour = 'magenta' 
        elif c_letters.upper() in 'YELLOW': 
            ccolour = 'yellow' 
        else: 
            warnings.warn('Colour not recognised. Using green by default') 
            colour = 'green' 

    if not 'TEXT' in shape_details.upper(): 
        text = None
    else: 
        text = shape_details[shape_details.find('TEXT') + 6: shape_details.find('}')]
            
            
    return (polygon, float(x1), float(y1), float(width), float(heigth), float(angle), colour, text)
