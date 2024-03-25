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

# pyutils.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pyutils (pyutils-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 


import numpy as np
import subprocess
import os
from astropy.io import fits
import re
import datetime
import sys
from astropy.table import Table


def pyadd(images, outfile):
    """
    Adds several images into a single outfile.
    
    Args:
        images: a tuple or list with the images.
        outfile: the name of the outfile.
    """

    with fits.open(images[0]) as image:
        primary_hdu = image[0]
        sum_im = primary_hdu.data

    for im in range(1, len(images)):
        with fits.open(images[im]) as image1:
            sum_im = sum_im + image1[0].data

    primary_hdu.data = sum_im
    primary_hdu.writeto(outfile, overwrite = True)


def date_time():
    """
    Returns the current date.

    Output:
        the current date time in as string.
    """

    now = datetime.datetime.now()
    return('Current time: {}'.format(now.strftime('%Y - %m - %d -- %H:%M:%s')))


def pyselect(filename, outfile, extension, column, lim_up = ' ', lim_down = ' ',
    return_data = False, exact_match = ''):
    """
    Returns the rows corresponding to a series of conditions imposed by
    given limits for a given fits file. Creates a second fits file with the
    selected rows (second extension, first is the primary extension of the
    original fits file).

    Args:
        filename: the name of the fits file.
        outfile: the name of the output fits file.
        extension: the extension you want to check.
        column: the name of the column to verify.
        lim_up: upper limit.
        lim_down: lower limit.
        return_data: (optional, False by default) returns the selected data as an recarray
        exact_match: whether or not an exact match is required.

    Output:
       selection: creates the file, and depending on return_data, returns the recarray.
    """

    with fits.open(filename) as fits_file:
        hdu_primary = fits_file[0]
        selected_extension = fits_file[extension]

        data_fits = fits_file[extension].data
        if exact_match != '':
            selection = data_fits[data_fits[column] == exact_match]
        else:
            if lim_up != ' ' and lim_down != ' ':
                if lim_down > lim_up:
                    raise ValueError('Upper limit is lower than the lower limit!')
                selection = data_fits[(data_fits[column] > lim_down) & (data_fits[column] < lim_up)]
            elif lim_up != ' ' and lim_down == ' ':
                selection = data_fits[data_fits[column] < lim_up]
            elif lim_up == ' ' and lim_down != ' ':
                selection = data_fits[data_fits[column] > lim_down]
            else:
                raise ValueError('Something went wrong. Check your limits.')

        hdu_primary.writeto(outfile, overwrite = True)

        with fits.open(outfile, 'update') as out_file:
            out_file.append(selected_extension)
            out_file[1].data = selection
            out_file.flush()

    if return_data:
        return selection


def pymodhdu(filename, extension, card, value, comment = ''):
    """
    Modifies the header of a fits file.
    No need for temporary files.
    
    Args:
        filename: name of the file.
        extension: the extension. 0 for primary...
        card: the 'card' that has to be edited.
        value: the value.
        comment: the comment, if any.
    """

    with fits.open(filename, 'update') as fits_file:
        hdr = fits_file[extension].header
        hdr.set(card, value, comment)
        fits_file.flush()


def get_key_word(filename, keyword, extension = '', not_found_output = 'unknown'):
    """
    Search a fits file for a given keyword and returns it.
    
    Args:
        filename: the path of the file to search.
        keyword: the keyword.
        extension (optional): the extension. If none is given it will return the first keyword found that matches.
        not_found_output: the value of the keyword if it couldn't be found in the FITS file.

    Output:
        the value of that given keyword. 'unknown' if not matches were found.
    """

    if isinstance(filename, str):
        if extension == '':
            try:
                with fits.open(filename) as event:
                    for i in range(0, len(event)):
                        if keyword in event[i].header:
                            return event[i].header[keyword]
            except FileNotFoundError:
                return(not_found_output)
        else:
            try:
                with fits.open(filename) as event:
                    hdr = event[extension].header
                    if keyword in hdr:
                        return hdr[keyword]
            except FileNotFoundError:
                return(not_found_output)
    elif isinstance(filename, fits.hdu.hdulist.HDUList):
        if extension == '':
            try:
                for i in range(0, len(filename)):
                    if keyword in filename[i].header:
                        return filename[i].header[keyword]
            except FileNotFoundError:
                return(not_found_output)
        else:
            try:
                hdr = filename[extension].header
                if keyword in hdr:
                    return hdr[keyword]
            except FileNotFoundError:
                return(not_found_output)
    else:
        raise FileNotFoundError('Could not determine the type of the file.')

    return not_found_output


def pydump(fits_file, extension, column):
    """
    Returns the value or values of a wanted column for a fits file.

    Args:
        file: the file name.
        extension: the extension.
        column: the name of the column.

    Output:
        values: values obtained as a float or list of floats. Will be empty if
    there were no matches.
    """

    values = []

    if isinstance(fits_file, str):
        try:
            with fits.open(fits_file) as ev:
                data_table = Table(ev[extension].data)
                data_ev = data_table[column]
                #for i in range(0, len(data_ev)):
                #values.append(data_ev[i].item())
        except KeyError:
            print('Returning empty list. The given file does not contain either the extension or the column.')
            return []
    elif isinstance(fits_file, fits.hdu.hdulist.HDUList):
        try:
            data_table = Table(fits_file[extension].data)
            data_ev = data_table[column]
            #for i in range(0, len(data_ev)):
                #values.append(data_ev[i].item())
        except KeyError:
            print('Returning empty list. The given file does not contain either the extension or the column')
            return []
    else:
        raise TypeError('Unrecognised format for the fits file.')
    return data_ev


def is_notebook():
    """
    Checks whether or not the user is running a Python terminal or a Notebook environment.

    Output:
        True if running on a Jupyter Notebook.
        False if running from terminal, iPython or other systems.
    """

    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type
    except NameError:
        return False      # Probably standard Python interpreter


def delete_data(fits_file, extension, to_delete, direction):
    """
    Deletes a row or column (or sets of rows or columns) from a given fits file.

    Args:
        fits_file: the fits file. Either the path or an opened fits object.
        extension: the extension to evaluate the data.
        to_delete: the list, string or number of column/row that has to be
    removed.
        direction: 'R' for row, 'C' for column.

    Output:
        None if run into errors.
        If the fits file is a string, will return the string again.
        If the fits file is a HDU object, will return the given HDU object
    modified. You may want to load it again.
    """

    if isinstance(fits_file, str):
        with fits.open(fits_file, 'update') as f:
            try:
                data_in = Table(f[extension].data)
            except KeyError:
                print('Could not open extension.')
                return None
            if direction.upper() == 'R':
                try:
                    if isinstance(to_delete, int):
                        data_in.remove_row(to_delete)
                    elif isinstance(to_delete, list):
                        data_in.remove_rows(to_delete)
                except IndexError:
                    print('Index error while deleting rows. Check the limits.')
                    return None
            elif direction.upper() == 'C':
                if isinstance(to_delete, int) or isinstance(to_delete, str):
                    try:
                        data_in.remove_column(to_delete)
                    except KeyError:
                        print('Could not remove the column {}. It does not exist.'.format(to_delete))
                        return None
                elif isinstance(to_delete, list):
                    try:
                        data_in.remove_columns(to_delete)
                    except KeyError:
                        print('Could not remove the given columns.')
                        return None
            else:
                print('Invalid argument. Please insert C for column(s) or R for row(s)')
                return None
            f[extension].data = None
            f[extension].data = data_in.as_array()
            f.flush()
        return fits_file

    elif isinstance(fits_file, fits.hdu.hdulist.HDUList):
        f = fits_file
        try:
            data_in = Table(f[extension].data)
        except KeyError:
            print('Could not open extension.')
            return None
        if direction.upper() == 'R':
            try:
                if isinstance(to_delete, int):
                    data_in.remove_row(to_delete)
                elif isinstance(to_delete, list):
                    data_in.remove_rows(to_delete)
            except IndexError:
                print('Index error while deleting rows. Check the limits.')
                return None
        elif direction.upper() == 'C':
            if isinstance(to_delete, int) or isinstance(to_delete, str):
                try:
                    data_in.remove_column(to_delete)
                except KeyError:
                    print('Could not remove the column {}. It does not exist.'.format(to_delete))
                    return None
            elif isinstance(to_delete, list):
                try:
                    data_in.remove_columns(to_delete)
                except KeyError:
                    print('Could not remove the given columns. Matches could not be found.')
                    return None
        else:
            print('Invalid argument. Please insert C for column(s) or R for row(s)')
            return None
        f[extension].data = None
        f[extension].data = data_in.as_array()
        return f
    else:
        print('invalid type for the FITS file. Entered {}.'.format(type(fits_file)))
        return None


def create_fits_from_data(data, labels, filename = '', ext_name = None):
    """
    Creates a table object containing the data and the labels passed to its
    arguments. May also create the FITS file if so is specified.

    Args:
        data: list of all the arrays to be included in the table.
        labels: a list of the labels. This list must be of the same lenght as
    the data list.
        filename: empty by default. If the user wants to save the table, this
    argument must contain the name of the file.
        ext_name: the name of the extension. If not provided, the extension name will be empty.

    Output:
        None if the lenght of the lists differ.
        t: the table object.
    """

    if len(data) != len(labels):
        print('Mismatching lenght for the labels and the data columns.')
        return None

    t = Table(data, names = labels)

    if filename != '':
        t.write('{}'.format(str(filename)), format = 'fits', overwrite = True)
    
    if ext_name:
        with fits.open(filename, 'update') as ef:
            ef[1].name = ext_name
            ef.flush()

    return 0


def filter_data(data, nan_values = -999, upper_limit = None, lower_limit = None):
    """
    Allows for easily filter 2D numpy arrays or astropy.Table objects.

    Args:
        data: the data to filter: either a numpy.ndarray or a Table.
        nan_values: the value (or list of values) to be considered nan. NaN
    values will always be considered as such.
        upper_limit: the tolerated upper limit.
        lower_limit: the tolerated lower limit.

    Output:
        data: the filtered data in the same input format. If the input format is not supported, will simply return 1.
    """

    try:
        nan_length = len(nan_values)
    except TypeError:
        nan_length = 0

    if isinstance(data, np.ndarray):
        data = data[~np.isnan(data).any(axis=1)]
        if nan_length == 0:
            data = np.delete(data, np.where(data == nan_values)[0], 0)
        else:
            for i in nan_values:
                data = np.delete(data, np.where(data == i)[0], 0)

        if type(upper_limit) == int or type(upper_limit) == float:
            data = data[data[:,0] < upper_limit, :]

        if type(lower_limit) == int or type(lower_limit) == float:
            data = data[data[:,0] > lower_limit, :]

    elif isinstance(data, Table):
        has_nan = np.zeros(len(data), dtype = bool)
        for col in data.itercols():
            if col.info.dtype.kind == 'f':
                has_nan |= np.isnan(col)
        data = data[~has_nan]
        if nan_length == 0:
            mask = np.logical_or.reduce([c == nan_values for c in data.columns.values()])
            data = data[~mask]
        else:
            for i in nan_values:
                mask = np.logical_or.reduce([c == i for c in data.columns.values()])
                data = data[~mask]

        if type(upper_limit) == int or type(upper_limit) == float:
            mask = np.logical_or.reduce([c > upper_limit for c in data.columns.values()])
            data = data[~mask]
        if type(lower_limit) == int or type(lower_limit) == float:
            mask = np.logical_or.reduce([c < lower_limit for c in table.columns.values()])
            data = data[~mask]

    else:
        print('Format not supported.')
        return 1

    return data


def merge_fits(fits_list, extensions, output_file, columns, new_ext = None):
    """
    Merges the values from a series of given FITS files.

    Args:
        fits_list: the list of fits files to merge.
        extensions: the list of extensions on 1:1 correspondency to the fits file
    list.
        output_file: the name for the output file.
        columns = the columns to take from the data as string (if one) or as a
    list or a tuple (if more than one).
        new_ext: the name of the new extension. If None, the name from the first
    extension of the first file will be used.

    Output:
        0 or 1, depending on whether or not any errors were found.
    """

    data_dict = dict()
    # evaluating columns:
    if isinstance(columns, str):
        data_dict.update({columns : np.array(())})
    elif isinstance(columns, list) or isinstance(columns, tuple):
        for i in columns:
            data_dict.update({i : np.array(())})
    elif columns is None:
        with fits.open(fits_list[0]) as ff:
            names = ff[extensions[0]].data.names
            for i in names:
                data_dict.update({i : np.array(())})
    else:
        print('Unrecognised format.')
        return 1

    size_diff = len(fits_list) - len(extensions)

    for i in range(0, len(fits_list)):
        fits_file = fits_list[i]
        try:
            with fits.open(fits_file) as ffile:
                if i == 0:
                    new_primary = ffile[0]
                    new_base_header = ffile[1]
                    if new_ext == None:
                        new_ext = ffile[1].name
                for key in data_dict.keys():
                    try:
                        if len(extensions) == 1:
                            extension = extensions[0]
                        else:
                            extension = extensions[i]
                        
                        if len(ffile[extension].data) == 0:
                            continue
                        data_key = ffile[extension].data[key]
                        data_in_dict = data_dict[key]
                        data_dict.update({key : np.concatenate((data_in_dict, data_key))})
                    except (IndexError, AttributeError) as e:
                        print('Could not locate {0} in {1}:{2}.'.format(key, fits_file, extension))

        except FileNotFoundError:
            print('Could not open {}.'.format(fits_file))
            return 1

    names = []
    dict_to_values = []

    # Seems like Table does not support dict_keys as a proper list. Converting in a loop:
    for key in data_dict:
        dict_to_values.append(data_dict[key])
        names.append(key)

    new_table = Table(dict_to_values, names = names)
   
    new_table.write(output_file, overwrite = True)

    with fits.open(output_file, 'update') as ff:
        ff[1].name = new_ext
        ff[1].header = new_base_header.header
        #new_hdul = fits.HDUList([new_primary, new_base_header])
        ff.flush()

    return 0


def imgstat(fits_file, lower_limit = None, upper_limit = None, output = None):
    """
    Similar to fimgstat, the function return the statistical information from the image
    in the fits file. Can also be dumped into a txt file.

    Args:
        fits_file:
        lower_limit: the lower value to consider in the statistics.
        upper_limit: the upper value to consider in the statistics.
        output: if specified, will dump the information into the specified file.

    Output:
        mean_image: the mean value of the image.
        std_dev_image: the standard deviation of the image.
        min_val: the minimum value found.
        max_val: the maximum value found.
        sum_val: the total sum of all the values used.
        used_val: the number of values used.
        max_index: the indexes of the maxima.
        min_index: the indexes for the minima.
    """

    if isinstance(fits_file, str):
        try:
            with fits.open(fits_file) as f:
                if f[0].is_image:
                    fits_image = f[0].data
                else:
                    raise AttributeError('The PRIMARY extension of the fits file does not correspond to an image.')
                    sys.exit(0)
        except FileNotFoundError:
            print('Could not open {}.'.format(fits_file))
            sys.exit(0)
    elif isinstance(fits_file, fits.hdu.hdulist.HDUList):
        if fits_file[0].is_image:
            fits_image = fits_file[0].data
        else:
            raise AttributeError('The PRIMARY extension of the fits file does not correspond to an image.')
            sys.exit(0)

    flattened_image = fits_image.flatten()

    # filtering...
    flattened_image = flattened_image[~np.isnan(flattened_image)]
    if lower_limit != None:
        flattened_image = flattened_image[flattened_image >= lower_limit]
    if upper_limit != None:
        flattened_image = flattened_image[flattened_image <= upper_limit]

    mean_image = np.mean(flattened_image)
    std_dev_image = np.std(flattened_image)
    min_val = np.min(flattened_image)
    max_val = np.max(flattened_image)
    used_val = len(flattened_image)
    sum_val = sum(flattened_image)
    max_index = np.asarray(np.where(fits_image == max_val)).T
    min_index = np.asarray(np.where(fits_image == min_val)).T

    if output != None:
        with open(str(output), 'w') as f:
            f.write('Mean value: {}\n'.format(mean_image))
            f.write('Standard deviation: {}\n'.format(std_dev_image))
            f.write('Max value: {}\n'.format(max_val))
            f.write('Min value: {}\n'.format(min_val))
            f.write('Values used in the calculation: {}\n'.format(used_val))
            f.write('Total sum of the values used: {}\n'.format(sum_val))
            f.write('Location of maxima: {}\n'.format(max_index))
            f.write('Location of minima: {}\n'.format(min_index))


    return(mean_image, std_dev_image, min_val, max_val, sum_val, used_val, max_index, min_index)


def add_column_to_fits(fits_file, extension, colname, coldata):
    """
    Adds a column and its data to the given FITS file.

    Args:
        fits_file: the path to the FITS file to be modified.
        extension: in which extension is the data located.
        colname: the name of the column.
        coldata: the data of the column.

    Output:
        0 when finished. 1 otherwise.
    """

    with fits.open(fits_file, 'update') as ff:
        data_t = Table(ff[extension].data)
        primary_head = ff[0].header 
        if isinstance(colname, str):
            try:
                data_t[colname] = coldata
            except:
                try: #insert empty column
                    if len(data_t) == 0 or len(coldata) == 0:
                        data_t[colname] = []
                except:
                    print('Warning: Mismatching sizes in add_column_to_fits.')
                    return 1
        else:
            for i in range(0, len(colname)):
                try:
                    data_t[colname[i]] = coldata[i]
                except:
                    if len(data_t) == 0:
                        try:
                            data_t[colname[i]] = []
                        except:
                            print('Warning: Mismatching size in the {} element (add_column_to_table).'.format(i))
        
        # new file
        data_t.write(fits_file, format = 'fits', overwrite = True)
        with fits.open(fits_file, 'update') as ff2:
            ff2[0].header = primary_head
            ff2.flush()

    return 0


def add_row_to_fits(fits_file, extension, rows):
    """
    Adds a row to the given FITS file in the provided extension.

    Args:
        fits_file: the FITS file to be edited.
        extension: the extension in which the data is found.
        rows: the rows (list format) to add.

    Output:
        0 if completed. 1 otherwise.
    """

    if isinstance(fits_file, str):
        try:
            with fits.open(fits_file, 'update') as ff:
                data = ff[extension].data
                t = Table(data)
                for row in range(0, len(rows)):
                    try:
                        t.add_row(rows[row])
                    except IndexError:
                        print('Could not add row {}.'.format(row))
                        continue
                ff[extension].data = None
                ff[extension].data = t.as_array()
                ff.flush()
        except FileNotFoundError:
            print('Could not open file {0}.'.format(fits_file))
            return 1

    return 0


def sort_fits(fits_file, extension, label, desc = True):
    """
    Rewrites the data of a FITS file after sorting the data of a given extension.

    Args:
        fits_file: the path to the FITS file that has to be modified.
        extension: the extension in which the data is located.
        label: the label of the column to be used. If more than one is provided, use a list of strings.
        desc: bool - if desc(endant) order is wanted.

    Output:
        0 if done correctly; 1 otherwise.
    """
    
    try:
        with fits.open(fits_file, 'update') as ff:
            t = Table(ff[extension].data)
            t.sort(label)
            if not desc:
                t.reverse()
            ff[extension].data = None
            ff[extension].data = t.as_array()
            ff.flush()

    except FileNotFoundError:
        print('Could not open file {}.'.format(fits_file))
        return 1

    return 0
