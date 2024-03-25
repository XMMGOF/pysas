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

# pyeslewsearch.py

import os
import sys
import time
import pysas.pyutils.pyutils as pyutils
from pysas.logger import TaskLogger as TL
from astropy.io import fits
from astropy.io import ascii
from astropy.table import Table, unique, QTable
from astropy import units as u
import numpy as np
import re
import glob


logger = TL('pyeslewsearch')

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pyeslewsearch (pyeslewchain-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'


def pyeslewsearch():
    """
    Main program of the task. The function will be called when from the
    command line.
    """

    t_start = time.time()

    coldesc = ['DSSNAME', 'SRCNAME', 'XIMNAME']

    expmaps = []

    for i in os.listdir(os.getcwd()):
        if 'EXPMAP8' in i:
            expmaps.append(i)

    if len(expmaps) == 0:
        print('Empty exposure map list.')
        sys.exit(0)

    expmaps = sorted(expmaps)

    for expmap in expmaps:
        for band_code in ('6', '7', '8'):
            expin = expmap[0:23] + band_code + expmap[24:30]
            imin = expmap[0:17] + 'IMAGE_' + band_code + expmap[24:30]
            srclst = expmap[0:17] + 'SRCLST' + band_code + expmap[24:30]

            ecf = get_ECF(band_code)
            n_events = num_events(imin)

            if n_events > 0:
                eslewsearch_guts(imin, expin, srclst, ecf)
            else:
                print('Empty image ({0}).'.format(imin))
    
    b6list = expmaps[0][0:17] + 'OMSRLI6000.FIT'
    b7list = expmaps[0][0:17] + 'OMSRLI7000.FIT'
    b8list = expmaps[0][0:17] + 'OMSRLI8000.FIT'
   
    srclst6_files = glob.glob('*SRCLST6*')

    if len(srclst6_files) != 0:
        logger.log('info', 'Working on source list files for band 6.')

        status = pyutils.merge_fits(srclst6_files, [1], b6list, columns = None, new_ext = None)
        if status:
            logger.log("error","Failed to merge band 6 lists")

    srclst7_files = glob.glob('*SRCLST7*')
    
    if len(srclst7_files) != 0:
        status = pyutils.merge_fits(srclst7_files, [1], b7list, columns = None, new_ext = None)
        if status:
            logger.log("error","Failed to merge band 7 lists")

    srclst8_files = glob.glob('*SRCLST8*')

    if len(srclst8_files) != 0:
        status = pyutils.merge_fits(srclst8_files, [1], b8list, columns = None, new_ext = None)
        if status:
            logger.log("error","Failed to merge band 8 lists")

    logger.log('info', 'Sizes of each band: B6: {}, B7: {} B8: {}.'.format(len(srclst6_files), len(srclst7_files), len(srclst8_files)))
    # cleaning up...
    logger.log('info', 'Cleaning up...')
    srclistrm = glob.glob('*SRCLST*')

    for file_rm in srclistrm:
        os.remove(file_rm)

    # Append the different band lists into a single list (no source merging)
    create_single_list(b6list, b7list, b8list)
    
    del_list = glob.glob('box*.ds')
    if os.path.isfile('detmask.fits'):
        del_list.append('detmask.fits')
    if os.path.isfile('splinemap.ds'):
        del_list.append('splinemap.ds')

    for f in del_list:
        os.remove(f)

    t_stop = time.time()

    logger.log('info', 'eslewsearch completed in {0} seconds.'.format(round(t_stop - t_start, 2)))


def add_name_cols(mlist, image):
    """
    Adds a column into the source list.

    Args:
        mlist: the original list.
        image: the image file.
    """

    logger.log('debug', 'Running add_name_cols with source list {0} and image {1}.'.format(mlist, image))
    
    coord_string = make_coord_strings(mlist)

    fstrings = make_file_string(image, coord_string)
    # Write strings to data file

    temp_col_fits = 'temp_col_data.fits'

    # Convert name strings into FITS format

    logger.log('debug', 'Running create_fits_from_data.')
    coldesc = ['DSSNAME', 'SRCNAME', 'XIMNAME']
    
    coldata = fstrings
    coldata = np.array(coldata).T.tolist()
    status = pyutils.create_fits_from_data(coldata, coldesc, temp_col_fits)
    
    if status:
        logger.log('error', 'Error while running create_fits_from_data')
    
    status = pyutils.add_column_to_fits(mlist, 1, coldesc, coldata)
    
    if status:
        logger.log('error', 'Error while running add_column.')
        sys.exit(0)
   

def make_file_string(image, coords):
    """
    Creates a string containing basic information from the file.

    Args: 
        image: the name of the image file.
        coords: the coordinates corresponding to the file.

    Output:
        fstring: the formatted string.
    """

    logger.log('debug', 'Running make_file_string with image {0}.'.format(image))

    obsid = image[1:11]
    rev = image[2:6]
    fstrings = []
    
 # Loop over each coordinate string and create a string for import
    for coord in coords:
        dsstring = "ds" + obsid + "_" + coord[0] + coord[1] + ".ds"
        srcname = "xs" + rev + "_" + obsid + "_" + coord[0] + coord[1] + ""
        fstring = (dsstring, srcname, "" + image + "")
        fstrings.append(fstring)
    
    return fstrings


def convert_name(srcin):
    """
    Adds the individual band list into one list.

    Args:
        srcin: the information from the source string.

    Output:
        srcout: the name for the source.
    """

    srcin = srcin.replace("'", '')
    srcout = "XMMSL_J" + srcin[18:].replace(':', '')
    return srcout


def create_single_list(b6list, b7list, b8list):
    """
    Creates a single list containing information from each energy bband.

    Args:
        b6list: the list of the sources in the 6 band.
        b7list: the list of the sources in the 7 band.
        b8list: the list of the sources in the 8 band.
    """

    logger.log('debug', 'Running create_single_list...')

    b6temp = 'temp_b6.dat'
    b7temp = 'temp_b7.dat'
    b8temp = 'temp_b8.dat'
    tempmerge = 'temp_merged.dat'
    mergedlist = b8list[0:19] + 'SSLI0000.FIT'

    # Combine into a single text file with separate columns for each band

    if os.path.isfile(b6list):
        # Dump files into ascii
        with fits.open(b6list) as ff6:
            t = Table(ff6[1].data) 
            t = t['SRCNAME', 'RA', 'DEC', 'RADEC_ERR', 'SCTS', 'SCTS_ERR', 'EXT', 'EXT_ERR', 'DET_ML', 'BG_MAP', 'RATE', 'RATE_ERR','FLUX', 'FLUX_ERR',
            'XIMNAME', 'ID_INST']
            t.write(b6temp, format = 'ascii')

        logger.log('info', 'Working with B6...')

        with open(b6temp) as b6_tf:
            rows_b6 = []

            for line in b6_tf.readlines():
                aux_list = line.split(" ")
                # Add useful records (non-titles and with inst!=0) to output text file
                ii = len(aux_list)
                
                if ii > 0:
                    #for k in range(0, ii):
                        #try:
                            #aux_list[k] = str(np.float32(aux_list[k]))
                        #except:
                            #continue
                    if 'xs' in aux_list[0] and aux_list[15] != 0:
                        # Convert source name to XMMSL format
                        cname = convert_name(aux_list[0])
                        # Write output record\
                        row = [cname, aux_list[1], aux_list[2], aux_list[3], aux_list[4], aux_list[5], np.nan, np.nan, np.nan, np.nan,\
                            aux_list[6], aux_list[7], np.nan, np.nan, np.nan, np.nan, aux_list[8], \
                            np.nan, np.nan, aux_list[9], np.nan, np.nan, aux_list[10], aux_list[11], \
                            np.nan, np.nan, np.nan, np.nan, aux_list[12], aux_list[13], \
                            np.nan, np.nan, np.nan, np.nan, aux_list[14]]

                        rows_b6.append(row)

    else:
        logger.log('error', 'Could not open the B6 list.')

    logger.log('info', 'Working with B7...')
    
    if os.path.isfile(b7list):
        with fits.open(b7list) as ff:
            t = Table(ff[1].data)
            t = t['SRCNAME', 'RA', 'DEC', 'RADEC_ERR', 'SCTS', 'SCTS_ERR', 'EXT' , 'EXT_ERR' ,'DET_ML', 'BG_MAP', 'RATE', 'RATE_ERR','FLUX', 'FLUX_ERR', 'XIMNAME', 'ID_INST']
            ascii.write(t, b7temp, overwrite = True)

        with open(b7temp) as b7_tf:
            rows_b7 = []
            for line in b7_tf.readlines():
                aux_list = line.split(' ')
                # Add useful records to output text file
                ii = len(aux_list)
                if ii > 0:
                    #for k in range(0, ii):
                        #try:
                            #aux_list[k] = str(np.float32(aux_list[k]))
                        #except:
                            #continue
                    if 'xs' in aux_list[0] and aux_list[15] != 0:
                        # Convert source name to XMMSL format
                        cname = convert_name(aux_list[0])
                        # Write output record
                        row = [cname, aux_list[1], aux_list[2], aux_list[3], np.nan, np.nan, aux_list[4], aux_list[5], np.nan, np.nan, \
                            np.nan, np.nan, aux_list[6], aux_list[7], np.nan, np.nan, np.nan, aux_list[8], \
                            np.nan, np.nan, aux_list[9], np.nan, np.nan, np.nan, aux_list[10], aux_list[11], \
                            np.nan, np.nan, np.nan, np.nan, aux_list[12], aux_list[13], \
                            np.nan, np.nan, aux_list[14]]

                        rows_b7.append(row)


    else:
        logger.log('error', 'Could not open the B7 list.')

    logger.log('info', 'Working with B8...')

    if os.path.isfile(b8list):
        with fits.open(b8list) as ff:
            t = Table(ff[1].data)
            t = t['SRCNAME', 'RA', 'DEC', 'RADEC_ERR', 'SCTS', 'SCTS_ERR', 'EXT' , 'EXT_ERR' ,'DET_ML', 'BG_MAP', 'RATE', 'RATE_ERR','FLUX', 'FLUX_ERR', 'XIMNAME', 'ID_INST']
            ascii.write(t, b8temp, overwrite = True)

        with open(b8temp) as b8_tf:
            rows_b8 = []
            for line in b8_tf.readlines():
                aux_list = line.split(" ")
                # Add useful records to output text file
                ii = len(aux_list)
                if ii > 0:
                    #for k in range(0, ii):
                        #try:
                            #aux_list[k] = str(np.float32(aux_list[k]))
                        #except:
                            #continue
                    if 'xs' in aux_list[0] and aux_list[15] != 0:
                        # Convert source name to XMMSL format
                        cname = convert_name(aux_list[0])
                        # Write output record
                        row = [cname, aux_list[1], aux_list[2], aux_list[3], np.nan, np.nan, np.nan, np.nan, aux_list[4], aux_list[5], np.nan, np.nan, \
                            np.nan, np.nan, aux_list[6], aux_list[7], np.nan, np.nan,  aux_list[8], \
                            np.nan, np.nan, aux_list[9], np.nan, np.nan, np.nan, np.nan, aux_list[10], aux_list[11], \
                            np.nan, np.nan, np.nan, np.nan, aux_list[12], aux_list[13], aux_list[14]]

                        rows_b8.append(row)

    else:
        logger.log('error', 'Could not open the B8 list.')

    logger.log('info', 'Write the merged text file into a FITS file.')
    
    labels = make_final_cols()

    logger.log('info', 'Joining band files...')

    start_b6_data = np.array(rows_b6).T.tolist()
    status = pyutils.create_fits_from_data(start_b6_data, labels, 'b6band.temp', 'SRCLIST')
    
    logger.log('debug', 'Creating temp 6')
    start_b7_data = np.array(rows_b7).T.tolist()
    status = pyutils.create_fits_from_data(start_b7_data, labels, 'b7band.temp', 'SRCLIST')
    start_b8_data = np.array(rows_b8).T.tolist()
    status = pyutils.create_fits_from_data(start_b8_data, labels, 'b8band.temp', 'SRCLIST')

    temp_band_files = ('b6band.temp', 'b7band.temp', 'b8band.temp')
    status = pyutils.merge_fits(temp_band_files, [1], mergedlist, columns = None, new_ext = None)

    for f in temp_band_files:
        if os.path.isfile(f):
            os.remove(f)

    #status = pyutils.add_row_to_fits(mergedlist, 'SRCLIST', rows_b7)
    #if status:
    #    logger.log('error', 'Error while running add_rows_to_fits.')
    
    #status = pyutils.add_row_to_fits(mergedlist, 'SRCLIST', rows_b8)
    
    #if status:
    #    logger.log('error', 'Error while running add_row_to_fits.')

    # Finally sort the list on RA, deleting additional entries.

    with fits.open(mergedlist) as ff:
        t = QTable(ff[1].data)
        t = unique(t, 'RA')
        t['RA'] = t['RA'].astype('float')
        t['DEC'] = t['DEC'].astype('float')
        t.sort('RA')

    qt = add_custom_format(t)
    qt = add_units_table(qt)

    try:
        qt.write(mergedlist, format = 'fits', overwrite = True)
    except:
        logger.log('error', 'Could not save the file.')
        sys.exit(0)

    # Change the extension
    with fits.open(mergedlist, 'update') as ef:        
        ef[1].name = 'SRCLIST'
        ef.flush()
   

    add_comments(mergedlist)
    add_units_band(b6list)
    add_units_band(b7list)
    add_units_band(b8list)

    # Clean up but do not throw error if no files to clean
    if os.path.isfile(b6temp):
        os.remove(b6temp)
    if os.path.isfile(b7temp):
        os.remove(b7temp)
    if os.path.isfile(b8temp):
        os.remove(b8temp)
    if os.path.isfile('temp_col_data.fits'):
        os.remove('temp_col_data.fits')


def add_custom_format(t):
    """
    Changes the type of the values for the input data.

    Args:
        t: the input table.
    Output:
        t (corrected).
    """

    aux_srcname = np.chararray(len(t['SRCNAME']), itemsize = 40, unicode = False)
    aux_srcname[:] = t['SRCNAME']
    t['SRCNAME'] = aux_srcname
    t['RA'] = np.array(t['RA'], dtype = 'float64')
    t['DEC'] =  np.array(t['DEC'], dtype = 'float64')
    t['RADEC_ERR'] = np.array(t['RADEC_ERR'], dtype =  'float64')
    t['SCTS_B6'] = np.array(t['SCTS_B6'], dtype = 'float32')
    t['SCTS_B6_ERR'] = np.array(t['SCTS_B6_ERR'], dtype = 'float32')
    t['SCTS_B7'] = np.array(t['SCTS_B7'],dtype = 'float32')
    t['SCTS_B7_ERR'] = np.array(t['SCTS_B7_ERR'], dtype = 'float32')
    t['SCTS_B8'] = np.array(t['SCTS_B8'], dtype = 'float32')
    t['SCTS_B8_ERR'] = np.array(t['SCTS_B8_ERR'], dtype = 'float32')
    t['EXT_B6'] = np.array(t['EXT_B6'], dtype = 'float32')
    t['EXT_B6_ERR'] = np.array(t['EXT_B6_ERR'], dtype = 'float32')
    t['EXT_B7'] = np.array(t['EXT_B7'], dtype = 'float32')
    t['EXT_B7_ERR'] = np.array(t['EXT_B7_ERR'], dtype = 'float32')
    t['EXT_B8'] = np.array(t['EXT_B8'], dtype = 'float32')
    t['EXT_B8_ERR'] = np.array(t['EXT_B8_ERR'], dtype = 'float32')
    t['DET_ML_B6'] = np.array(t['DET_ML_B6'], dtype = 'float32')
    t['DET_ML_B7'] = np.array(t['DET_ML_B7'], dtype = 'float32')
    t['DET_ML_B8'] = np.array(t['DET_ML_B8'], dtype = 'float32')
    t['BG_MAP_B6'] = np.array(t['BG_MAP_B6'], dtype = 'float32')
    t['BG_MAP_B7'] = np.array(t['BG_MAP_B7'], dtype = 'float32')
    t['BG_MAP_B8'] = np.array(t['BG_MAP_B8'], dtype = 'float32')
    t['RATE_B6'] = np.array(t['RATE_B6'], dtype = 'float32')
    t['RATE_B6_ERR'] = np.array(t['RATE_B6_ERR'], dtype = 'float32')
    t['RATE_B7'] = np.array(t['RATE_B7'], dtype = 'float32')
    t['RATE_B7_ERR'] = np.array(t['RATE_B7_ERR'], dtype = 'float32')    
    t['RATE_B8'] = np.array(t['RATE_B8'], dtype = 'float32')
    t['RATE_B8_ERR'] = np.array(t['RATE_B8_ERR'], dtype = 'float32')
    t['FLUX_B6'] = np.array(t['FLUX_B6'], dtype = 'float32')
    t['FLUX_B6_ERR'] = np.array(t['FLUX_B6_ERR'], dtype = 'float32') 
    t['FLUX_B7'] = np.array(t['FLUX_B7'], dtype = 'float32')
    t['FLUX_B7_ERR'] = np.array(t['FLUX_B7_ERR'], dtype = 'float32')
    t['FLUX_B8'] = np.array(t['FLUX_B8'], dtype = 'float32')
    t['FLUX_B8_ERR'] = np.array(t['FLUX_B8_ERR'], dtype = 'float32')
    aux_ximname = np.chararray(len(t['XIMNAME']), itemsize = 40, unicode = False)
    aux_ximname[:] = t['XIMNAME']
    t['XIMNAME'] = aux_ximname

    return t


def add_units_band(blist):
    """
    Moves the input table into a Quantity table object and gets the proper units for each column. Applied to band fits files.

    Args:
        blist: the FITS file of the band.

    Output:
        1 when finished.
    """

    logger.log('debug', 'Running add_units_band with {}.'.format(blist))

    with fits.open(blist) as bl:
        qt = QTable(bl[1].data)

    qt = add_custom_format_band(qt)

    try:
        qt['SCTS'].unit = u.ct
        qt['SCTS_ERR'].unit = u.ct
        qt['X_IMA'].unit = u.pix
        qt['X_IMA_ERR'].unit = u.pix
        qt['Y_IMA'].unit = u.pix
        qt['Y_IMA_ERR'].unit = u.pix
        qt['EXT'].unit = u.pix
        qt['EXT_ERR'].unit = u.pix
        qt['BG_MAP'].unit = u.ct / u.pix
        qt['EXP_MAP'].unit = u.s
        qt['FLUX'].unit = u.erg / u.s / (u.cm * u.cm) 
        qt['FLUX_ERR'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['RATE'].unit = u.ct / u.s
        qt['RATE_ERR'].unit = u.ct / u.s
        qt['RA'].unit = u.deg
        qt['DEC'].unit = u.deg
        qt['RADEC_ERR'].unit = u.arcsec
        qt['LII'].unit = u.deg
        qt['BII'].unit = u.deg
        qt['RAWX'].unit = u.pix
        qt['RAWY'].unit = u.pix
        qt['OFFAX'].unit = u.arcmin
        qt['CUTRAD'].unit = u.pix
        qt['DIST_NN'].unit = u.arcsec
    except:
        logger.log('warning', 'Could not fit all the data in {}.'.format(blist))
    

    qt.write(blist, format = 'fits', overwrite = True)

    return 1


def add_custom_format_band(t):
    """
    Corrects the format of the input data table.

    Args:
        t: the data table for bands B6, B7 and B8.

    Output:
        t (corrected)
    """

    logger.log('debug', 'Running add_custom_format...')
    
    t['ML_ID_SRC'] = np.array(t['ML_ID_SRC'], dtype = 'int32')
    t['BOX_ID_SRC'] = np.array(t['BOX_ID_SRC'], dtype = 'int32')
    t['ID_INST'] = np.array(t['ID_INST'], dtype = 'int32')
    t['ID_BAND'] = np.array(t['ID_BAND'], dtype = 'int32')
    t['ID_CLUSTER'] = np.array(t['ID_CLUSTER'], dtype = 'int32')
    t['SCTS'] = np.array(t['SCTS'], dtype = 'float32')
    t['SCTS_ERR'] = np.array(t['SCTS_ERR'], dtype = 'float32')
    t['X_IMA'] = np.array(t['X_IMA'], dtype = 'float32')
    t['X_IMA_ERR'] = np.array(t['X_IMA_ERR'], dtype = 'float32')
    t['Y_IMA'] = np.array(t['Y_IMA'], dtype = 'float32')
    t['Y_IMA_ERR'] = np.array(t['Y_IMA_ERR'], dtype = 'float32')
    t['EXT'] = np.array(t['EXT'], dtype = 'float32')
    t['EXT_ERR'] = np.array(t['EXT_ERR'], dtype = 'float32')
    t['DET_ML'] = np.array(t['DET_ML'], dtype = 'float32')
    t['EXT_ML'] = np.array(t['EXT_ML'], dtype = 'float32')
    t['BG_MAP'] = np.array(t['BG_MAP'], dtype = 'float32')
    t['EXP_MAP'] = np.array(t['EXP_MAP'], dtype = 'float32')
    t['FLUX'] = np.array(t['FLUX'], dtype = 'float32')
    t['FLUX_ERR'] = np.array(t['FLUX_ERR'], dtype = 'float32')
    t['RATE'] = np.array(t['RATE'], dtype = 'float32')
    t['RATE_ERR'] = np.array(t['RATE_ERR'], dtype = 'float32')
    t['RA'] = np.array(t['RA'], dtype = 'float64')
    t['DEC'] = np.array(t['DEC'], dtype = 'float64')
    t['RADEC_ERR'] = np.array(t['RADEC_ERR'], dtype = 'float32')
    t['LII'] = np.array(t['LII'], dtype = 'float64')
    t['BII'] = np.array(t['BII'], dtype = 'float64')
    t['RAWX'] = np.array(t['RAWX'], dtype = 'int32')
    t['RAWY'] = np.array(t['RAWY'], dtype = 'int32')
    t['OFFAX'] = np.array(t['OFFAX'], dtype = 'float32')
    t['CCDNR'] = np.array(t['CCDNR'] , dtype = 'int32')
    t['HR1'] = np.array(t['HR1'], dtype = 'float32')
    t['HR1_ERR'] = np.array(t['HR1_ERR'], dtype = 'float32')
    t['HR2'] = np.array(t['HR2'], dtype = 'float32')
    t['HR2_ERR'] = np.array(t['HR2_ERR'], dtype = 'float32')
    t['HR3'] = np.array(t['HR3'], dtype = 'float32')
    t['HR3_ERR'] = np.array(t['HR3_ERR'], dtype = 'float32')
    t['HR4'] = np.array(t['HR4'], dtype =  'float32')
    t['HR4_ERR'] = np.array(t['HR4_ERR'], dtype = 'float32')
    t['CUTRAD'] = np.array(t['CUTRAD'], dtype = 'float32')
    t['MASKFRAC'] = np.array(t['MASKFRAC'], dtype = 'float32')
    t['EEF'] = np.array(t['EEF'], dtype = 'float32')
    t['VIGNETTING'] = np.array(t['VIGNETTING'], dtype = 'float32')
    t['ONTIME'] = np.array(t['ONTIME'], dtype = 'float32')
    t['PILEUP'] = np.array(t['PILEUP'], dtype = 'float32')
    t['DIST_NN'] = np.array(t['DIST_NN'], dtype = 'float32')
    aux_flag = np.chararray(len(t['FLAG']), itemsize = 12, unicode = False)
    aux_flag[:] = t['FLAG']
    t['FLAG'] = aux_flag
    aux_DSSNAME = np.chararray(len(t['DSSNAME']), itemsize = 40, unicode = False)
    aux_DSSNAME[:] = t['DSSNAME']
    t['DSSNAME'] = aux_DSSNAME
    aux_srcname = np.chararray(len(t['SRCNAME']), itemsize = 40, unicode = False)
    aux_srcname[:] = t['SRCNAME']
    t['SRCNAME'] = aux_srcname
    aux_ximname = np.chararray(len(t['XIMNAME']), itemsize = 40, unicode = False)
    aux_ximname[:] = t['XIMNAME']
    t['XIMNAME'] = aux_ximname
    #DSSNAME   str40
    #SRCNAME   str40
    #XIMNAME   str40

    return t


def add_units_table(qt):
    """
    Moves the input table into a Quantity table object and gets the proper units for each column.

    Args:
        qt: the input table without units.

    Output:
        qt: the Quantity Table with proper units.
    """
    
    logger.log('debug', 'Adding units to main table...')
    
    try:
        qt['RA'] = qt['RA'] * u.deg
        qt['DEC'].unit = u.deg
        qt['RADEC_ERR'].unit = u.arcsec
        qt['EXT_B6'].unit = u.pix
        qt['EXT_B6_ERR'].unit = u.pix
        qt['EXT_B7'].unit = u.pix
        qt['EXT_B7_ERR'].unit = u.pix
        qt['EXT_B8'].unit = u.pix
        qt['EXT_B8_ERR'].unit = u.pix
        qt['BG_MAP_B6'].unit = u.ct / u.pix
        qt['BG_MAP_B7'].unit = u.ct / u.pix
        qt['BG_MAP_B8'].unit = u.ct / u.pix
        qt['RATE_B6'].unit = u.ct / u.s
        qt['RATE_B6_ERR'].unit = u.ct / u.s
        qt['RATE_B7'].unit = u.ct / u.s
        qt['RATE_B7_ERR'].unit = u.ct / u.s
        qt['RATE_B8'].unit = u.ct / u.s
        qt['RATE_B8_ERR'].unit = u.ct / u.s
        qt['FLUX_B6'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['FLUX_B6_ERR'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['FLUX_B7'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['FLUX_B7_ERR'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['FLUX_B8'].unit = u.erg / u.s / (u.cm * u.cm)
        qt['FLUX_B8_ERR'].unit = u.erg / u.s / (u.cm * u.cm)
    except:
        logger.log('warning', 'An error ocurred while adding the units to the final source list. It may be incomplete.')

    return qt


def num_events(image):
    """
    Gets the total number of events in a given image.

    Args:
        image: the path or FITS image to be evaluated.
    Output:
        sum: the total sum returned by imgstat.
    """

    stat_image = pyutils.imgstat(image, 0, None)

    return stat_image[4]


def make_coord_strings(mlist):
    """
    Reads coordinates and converts them into HMS,dms.

    Args:
        mlist: list to check coordinates.

    Output:
        new_coords: a list of the tuples of the new coordinates.
    """

    new_coords = []
    coords = pyutils.pydump(mlist, 1, ['RA', 'DEC'])

    for row in coords:
        ra_o = float(row[0])
        dec_o = float(row[1])
        values_coords = (convert_RA(ra_o), convert_DEC(dec_o))
        new_coords.append(values_coords)
    return new_coords


def make_final_cols():
    """
    Returns the main labels to use in the column to be formatted.

    Output:
        labels: the labels to be used.
    """
    
    labels = ['SRCNAME',
 'RA',
 'DEC',
 'RADEC_ERR',
 'SCTS_B6',
 'SCTS_B6_ERR',
 'SCTS_B7',
 'SCTS_B7_ERR',
 'SCTS_B8',
 'SCTS_B8_ERR',
 'EXT_B6',
 'EXT_B6_ERR',
 'EXT_B7',
 'EXT_B7_ERR',
 'EXT_B8',
 'EXT_B8_ERR',
 'DET_ML_B6',
 'DET_ML_B7',
 'DET_ML_B8',
 'BG_MAP_B6',
 'BG_MAP_B7',
 'BG_MAP_B8',
 'RATE_B6',
 'RATE_B6_ERR',
 'RATE_B7',
 'RATE_B7_ERR',
 'RATE_B8',
 'RATE_B8_ERR',
 'FLUX_B6',
 'FLUX_B6_ERR',
 'FLUX_B7',
 'FLUX_B7_ERR',
 'FLUX_B8',
 'FLUX_B8_ERR',
 'XIMNAME']

    return labels


def eslewsearch_guts(image, expmap, mlist, ecf):
    """
    Runs several SAS' tasks to create additional files. Will quit if the aforementioned taasks run into any error (check the log file).

    Args:
        image: the image to manipulate.
        expmap: the exposure map for the image.
        mlist:
        ecf: the energy correction factor.
    """

    logger.log('debug', 'Running eslewsearch_guts with {0}, {1}, {2}.'.format(image, expmap, mlist))

    # Set constants and thresholds
    pimin = 1499 # USe 1.5 keV for the PSF in all energy-band images!!
    pimax = 1501
    eboxlthr = 8
    eboxmthr = 10
    emlthr = 8
    mask = 'detmask.fits'
    boxlist_l = 'boxlist_l.ds'
    boxlist_m = 'boxlist_m.ds'
    bckgnd = 'splinemap.ds'

    # Run emask
    status_code = os.system("emask expimageset={0} detmaskset={1} threshold1=1e-5 threshold2=0.5".format(expmap, mask))
    
    if status_code:
        logger.log('error', 'Could not run emask.')
        sys.exit(0)

    # Run eboxdetect (local mode)
    status_code = os.system("eboxdetect boxlistset={0} boxsize=5 expimagesets={1} imagesets={2} likemin={3} nruns=3 pimax={4} pimin={5} usemap=no usematchedfilter=no withdetmask=yes detmasksets={6} withexpimage=yes withoffsets=no obsmode='slew'".format(boxlist_l, expmap, image, eboxlthr, pimax, pimin, mask))
    
    if status_code:
        logger.log("error","Failure in eboxdetect (local) on {0}".format(image))
        sys.exit(0)

    # Create background map
    status_code = os.system("esplinemap bkgimageset={0} boxlistset={1} withcheese=no withdetmask=yes detmaskset={2} excesssigma=3 idband=1 imageset={3} mlmin=1 nfitrun=3 nsplinenodes=10 scut=0.005 withexpimage=no".format(bckgnd, boxlist_l, mask, image))
    if status_code:
        logger.log("error","Failure in esplinemap on {0}.".format(image))
        sys.exit(0)

    # Run eboxdetect (map mode)
    status_code = os.system("eboxdetect bkgimagesets={0} boxlistset={1} boxsize=5 withexpimage=yes expimagesets={2} imagesets={3} likemin={4} nruns=3 pimax={5} pimin={6} usemap=yes usematchedfilter=no withdetmask=yes detmasksets={7} withoffsets=no obsmode='slew'".format(bckgnd, boxlist_m, expmap, image, eboxmthr, pimax, pimin, mask))
    
    if status_code:
        logger.log("error","Failure in eboxdetect (map) on {0}".format(image));
        sys.exit(0)

    # Run emldetect
    status_code = os.system("emldetect bkgimagesets={0} boxlistset={1} determineerrors=yes dmlextmin=2 ecf={2} ecut=36 withexpimage=yes expimagesets={3} fitcounts=yes fitextent=yes fitposition=yes imagesets={4} mllistset={5} mlmin={6} pimax={7} pimin={8} scut=0.9 usecalpsf=yes useevents=no withhotpixelfilter=no withoffsets=no withxidband=no nmaxfit=1 nmulsou=1 psfmodel='slew'".format(bckgnd, boxlist_m, ecf, expmap, image, mlist, emlthr, pimax, pimin))
    
    if status_code:
        logging.log("error","Failure in emldetect on {0}".format(image))
        sys.exit(0)

    if os.path.isfile(mlist):
        add_name_cols(mlist, image)


def convert_RA(ra):
    """
    Change the format of the RA parameter and returns it as a formatted string.

    Args:
        ra: the numerical value of RA.

    Output:
        hms: the formatted RA string.
    """

    hrs = int(ra / 15)
    mins = int((ra - hrs * 15.0) * 60.0 / 15.0)
    secs = (ra - (hrs * 15.0 + mins * 15.0 / 60.0)) * 3600.0 / 15.0

    if secs > 59.95:
        secs = 0
        mins = mins + 1

    if mins == 60:
        mins = 0
        hrs = hrs + 1

    if hrs == 24:
        hrs = 0

    #hms = '{0}:{1}:{2}'.format(str(round(hrs, 2)).zfill(2), str(round(mins, 2)).zfill(2), round(secs, 4))

    hms = '{0}:{1}:{2}'.format(str(round(hrs, 2)).zfill(2), str(round(mins, 2)), round(secs, 1))

    return hms


def convert_DEC(dec):
    """
    Converts the dec into a formatted string.

    Args:
        dec: the dec value as a real number.

    Output:
        degstring:
    """

    deg = int(dec)
    mins = int((dec - deg) * 60.0)
    secs = int(abs(dec - (deg + mins / 60.0)) * 3600.0 + 0.5)
    amins = abs(mins)

    # Sign
    sign = "+"

    if (dec < 0.0):
        sign = "-"

    # Sort out ranges
    if (secs > 59.95):
        secs = 0.0
        amins = amins + 1

    if amins == 60:
        amins = 0.0
        if dec < 0.0:
            deg = deg - 1
        else:
            deg = deg + 1

    degstring = '{0}{1}:{2}:{3}'.format(sign, str(round(abs(deg), 2)).zfill(2), str(round(amins, 2)).zfill(2), str(round(secs, 2)).zfill(2))

    return degstring;


def get_ECF(band):
    """
    Returns the energy conversion factor for the corresponding energy band.

    Args:
        band: the energy band (6, 7, 8).

    Output:
        ecf: the energy conversion factor (as a real).
    """

    band = int(band)

    if band == 6:
        ecf = 1.436 # soft energy band (0.2 - 2 keV)
    elif band == 7:
        ecf = 9.144 # hard energy band (2 - 12 keV)
    elif band == 8:
        ecf = 3.159 # total energy band (0.2 - 12 keV)
    else:
        logger.log('error', 'The input energy band is not supported ({0})'.format(band))
        sys.exit(0)

    ecf = 10 / ecf # for EMLDETECT

    return ecf


def add_comments(mlist):
    """
    Adds the comment info to the first header of the source list.

    Args:
        mlist: the final source list.
    """

    with fits.open(mlist, 'update') as ff:
        for j in ff[1].header:
            field_n = re.findall(r'\d+', j)
            if len(field_n) > 0:
                field_n = field_n[0]
            if ff[1].header[j] == 'RA':
                ff[1].header[j] = ('RA', 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'DEC':
                ff[1].header[j] = ("DEC", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RADEC_ERR':
                ff[1].header[j] = ("RADEC_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == "EXT_B6":
                ff[1].header[j] = ("EXT_B6", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'EXT_B6_ERR':
                ff[1].header[j] = ("EXT_B6_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'EXT_B7':
                ff[1].header[j] = ("EXT_B7", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'EXT_B7_ERR':
                ff[1].header[j] = ("EXT_B7_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'EXT_B8':
                ff[1].header[j] = ("EXT_B8", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'EXT_B8_ERR':
                ff[1].header[j] = ("EXT_B8_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'BG_MAP_B6':
                ff[1].header[j] = ("BG_MAP_B6", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'BG_MAP_B7':
                ff[1].header[j] = ("BG_MAP_B7", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'BG_MAP_B8':
                ff[1].header[j] = ("BG_MAP_B8", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B6':
                ff[1].header[j] = ("RATE_B6", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B6_ERR':
                ff[1].header[j] = ("RATE_B6_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B7':
                ff[1].header[j] = ("RATE_B7", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B7_ERR':
                ff[1].header[j] = ("RATE_B7_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B8':
                ff[1].header[j] = ("RATE_B8", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'RATE_B8_ERR':
                ff[1].header[j] = ("RATE_B8_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B6':
                ff[1].header[j] = ("FLUX_B6", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B6_ERR':
                ff[1].header[j] = ("FLUX_B6_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B7':
                ff[1].header[j] = ("FLUX_B7", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B7_ERR':
                ff[1].header[j] = ("FLUX_B7_ERR", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B8':
                ff[1].header[j] = ("FLUX_B8", 'label for field {}'.format(field_n))
            if ff[1].header[j] == 'FLUX_B8_ERR':
                ff[1].header[j] = ("FLUX_B8_ERR", 'label for field {}'.format(field_n))
        ff.flush()


def run(iparsdic):
    print('Executing {}.'.format(__file__))
    pyeslewsearch()

