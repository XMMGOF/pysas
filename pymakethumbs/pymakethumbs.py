# ESA (C) 2000-2022
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

# pymakethumbs.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pymakethumbs (pymakethumbs-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'



import matplotlib.pyplot as plt
import os
import sys
from pysas.pyutils import pyutils as pyutils
from pysas.logger import TaskLogger as TL
thumb_log = TL('makethumb')
from astropy.wcs import WCS
from astropy.io import fits
import numpy as np
from matplotlib.colors import LogNorm



def str_to_bool(string_param):
    '''
    Returns True or False depending on the strings found in parameters that are supposed 
    to be booleans.

    Args:
        string_param: the given parameter.
    
    Output:
        bool
    '''

    if 'Y' in string_param.upper() or 'T' in string_param.upper():
        return True
    else:
        return False


def prepare_text(hdu, manual_parameters, n_image, srcindexstyle, iau = ''):
    '''
    Creates the text for the upper part of the thumbnail.

    Args:
        hdu: the header of the FITS image.
        manual_parameters: tuple containing the information that can be passed via the command line:
         - obsstr
         - inststr
         - erangestr
        n_image: the index number of the image.
        srcindexstyle: the preffix for the index.
        iau: the name from the IAU catalogue. Might be left empty.
    
    Output:
        (plot_text, plot_comments): the text prepared for the plot, and the comments.
    '''

    obsidstr, inststr, erange, commupper, commlower = manual_parameters

    if obsidstr == '' or obsidstr.upper() == 'DEFAULT':
        try:
            obs_id = hdu['OBSID']
        except KeyError:
            obs_id = hdu['OBS_ID']
    else:
        obs_id = obsidstr

    if inststr == '' or inststr.upper() == 'DEFAULT':
        try:
            instr = hdu['INSTRUME']
        except KeyError:
            thumb_log.log('warning', 'Could not find the INSTRUME keyword in the given FITS image.')
            instr = 'unknown'
    else:
        instr = inststr

    id_image = int(n_image) + 1
    
    if iau != '':
        id_image = ''
        srcindexstyle = ''

    plot_text = '{0}{1} {2}\n'.format(srcindexstyle, id_image, iau) + \
            '{0} {1} {2}'.format(obs_id, instr, erange)

    plot_comments = commupper + '\n' + commlower

    return (plot_text, plot_comments)


def info_from_catalogue(cat_file, cat_ext, srcnum):
    '''
    Returns the source info from the given catalogue. 

    Args:
        cat_file: the name of the file containing the catalogue.
        cat_ext: the extension in the catalogue in which the data can be found.
        srcnum: the number that identifies the source in the catalogue data.

    Output:
        src_nums: the sources numbers.
        srcids: a list of sources ids.
        detids: the DETID column information.
        numhex: the hexagesimal number for the source number.
        iau_vals: an array containing the IAUNAME data.
    '''

    thumb_log.log('debug', 'Getting source info from source catalogue.')

    if srcnum == 0:
        with fits.open(cat_file) as cat_f:
            data_cat = cat_f[cat_ext].data
            try:
                iau_vals = data_cat['IAUNAME']
            except KeyError:
                thumb_log.log('warning', 'Could not locate IAUNAME column in the source data catalogue.')
                iau_vals = [''] * len(data_cat)
            try:
                detids = data_cat['detid']
            except KeyError:
                try:
                    detids = data_cat['DETID']
                except KeyError:
                    thumb_log.log('warning', 'Could not locate DETID column in catalogue data.')
                    detids = [''] * len(data_cat)
            try:
                srcids = data_cat['srcid']
            except KeyError:
                srcids = [''] * len(data_cat)
            try:
                src_nums = data_cat['src_num']
            except KeyError:
                src_nums = [''] * len(data_cat)
            numhex = []
            for i in src_nums:
                try:
                    n_hex = int(i)
                    numhex.append(hex(n_hex))
                except TypeError:
                    numhex.append('')
    else:
        with fits.open(cat_file) as cat_f:
            data_cat = cat_f[cat_ext].data
            if 'SRC_NUM' in data_cat.names or 'src_num' in data_cat.names:
                iau_vals = data_cat[data_cat['SRC_NUM'] == srcnum]['IAUNAME'][0]
                detids = data_cat[data_cat['SRC_NUM'] == srcnum]['detid'][0]
                srcids = data_cat[data_cat['SRC_NUM'] == srcnum]['SRCID'][0]
                src_nums = data_cat[data_cat['SRC_NUM'] == srcnum]['SRC_NUM'][0]
                try:
                    numhex = hex(int(srcnum))
                except TypeError:
                    thumb_log.log('warning', 'Could not convert the given src number to hexagesimal.')
                    numhex = ''
            else:
                try:
                    src_nums = np.array((data_cat['SRC_NUM'][srcnum]))[0]
                except (IndexError, KeyError) as e:
                    thumb_log.log('warning', 'Could not find SRC_NUM in the given catalogue table: {}:{}.'.format(cat_file, cat_ext))
                    src_nums = srcnum
                try:
                    iau_vals = np.array((data_cat['IAUNAME'][srcnum]))[0]
                except (IndexError, KeyError) as e:
                    thumb_log.log('warning', 'Could not find IAUNAME in the given catalogue table: {}:{}.'.format(cat_file, cat_ext))
                    iau_vals = ''
                try:
                    detids = np.array((data_cat['detid'][srcnum]))[0]
                except (IndexError, KeyError) as e:
                    thumb_log.log('warning', 'Could not find DETID in the given catalogue table: {}:{}.'.format(cat_file, cat_ext))
                    detids = ''
                    try:
                        numhex = hex(int(src_num))
                    except TypeError:
                        numhex = ''
                try:
                    srcids = np.array((data_cat['SRCID'][srcnum]))[0]
                except (IndexError, KeyError) as e:
                    thumb_log.log('warning', 'Could not find SRCID in the given catalogue table: {}:{}.'.format(cat_file, cat_ext))
                    srcids = ''
                    numhex = ''

    return (src_nums, srcids, detids, numhex, iau_vals)


def source_from_table(src_file, src_ext, srcnum):
    '''
    Returns the coordinates (RA, DEC) and the number of images ethat will be 
    produced by checking the source list.

    Args:
        src_file: the file containing the source list.
        src_ext: the extension in the file in which the data can be found.
        srcnum: the number/index of the source. 0 indicates all the sources available.

    Output:
        coords: a list containing all the values from RA, DEC fund.
        n_images: the number of images that will be produced.
    '''

    thumb_log.log('debug', 'Getting source info from source table.')
    
    if srcnum == 0:
        thumb_log.log('info', 'Selecting all sources available in file {}:{}.'.format(src_file, src_ext))
        with fits.open(src_file) as src_f:
            try:
                ra_coords = src_f[src_ext].data['RA']
                dec_coords = src_f[src_ext].data['DEC']
                try:
                    src_nums = src_f[src_ext].data['SRC_NUM']
                except KeyError:
                    thumb_log.log('debug', 'Could not locate SRC_NUM in file {}. Will try with SRCNUM.'.format(src_file))
                    try:
                        src_nums = src_f[src_ext].data['SRCNUM']
                    except KeyError:
                        src_nums = np.arange(len(ra_coords))
                        thumb_log('warning', 'Could not locate srcnum info. Using a ordered list instead.')
            except (IndexError, KeyError) as e:
                thumb_log.log('error', 'Could not find RA/DEC info in the given source file: {}:{}.'.format(src_file, src_ext))
                sys.exit(0)
    else:
        with fits.open(src_file) as src_f:
            if 'SRC_NUM' in src_f[src_ext].data.names:
                ra_coords = src_f[src_ext].data[src_f[src_ext].data['SRC_NUM'] == srcnum]['RA']
                dec_coords = src_f[src_ext].data[src_f[src_ext].data['SRC_NUM'] == srcnum]['DEC']
                src_nums = srcnum
            else:
                thumb_log.log('warning', 'Could not find SRC_NUM in the sourcelist data columns. Selecting the srcnum element in list.')
                try:
                    ra_coords = np.array((src_f[src_ext].data['RA'][srcnum]))
                    dec_coords = np.array((src_f[src_ext].data['DEC'][srcnum]))
                    src_nums = srcnum
                except (IndexError, KeyError) as e:
                    thumb_log.log('error', 'Could not find RA/DEC info in the given source file: {}:{}.'.format(src_file, src_ext))
                    sys.exit(0)

    n_images = len(ra_coords)
    if n_images == 0:
        thumb_log.log('error', 'No RA/DEC coordinates were found in the SourceList.')
        sys.exit(0)

    coords = []

    for c in range(0, n_images):
        coords.append((ra_coords[c], dec_coords[c]))

    return coords, n_images, src_nums


#################################
############# PLOT ##############
#################################

def plot_thumb(data, hdu, plot_config, plot_text):
    '''
    Makes both the image plot and the corresponding cross.

    Args:
        data: the data to plot as an array.
        hdu: the hdu of the data file.
        plot_config: a tuple containing the parameters that define the plot.
        plot_text: the text to add to the plot.

    Output:
        None
    '''

    thumb_log.log('info', 'Running plot_thumb...')

    plt.style.use('dark_background')

    plot_title, colourmap, imagesize, coords, lwidth, sizeratiocross = plot_config
    ra, dec = coords

    wcs = WCS(hdu)
    
    imagesize = imagesize * 3
    
    thumb_log.log('info', 'Making plot with center coordinates RA: {0} DEC:{1}.'.format(ra, dec))

    # defining center and corners
    xc, yc = wcs.wcs_world2pix(ra, dec, 0)
    dx_high, dy_high = wcs.wcs_world2pix(ra + imagesize / 2, dec + imagesize / 6, 0)
    dx_low, dy_low = wcs.wcs_world2pix(ra - imagesize / 2, dec - imagesize / 6, 0)
     
    x_diff = abs(dx_high - dx_low)
    y_diff = abs(dy_high - dy_low)
    
    x_lims = np.array((dx_low, dx_high))
    y_lims = np.array((dy_low, dy_high))


    if x_diff < y_diff:
        dif_lim = x_diff
    else:
        dif_lim = y_diff

    # plotting thumb image

    fig, axs = plt.subplots(2, 1, subplot_kw = {'projection' : wcs})
    fig.set_figheight(10)
    fig.set_figwidth(10)

    axs[1].imshow(data, cmap = colourmap, norm = LogNorm())
    axs[0].axis('off')
    axs[1].axis('off')
    axs[1].set_xlim(x_lims)
    axs[1].set_ylim(y_lims)
    

    # plotting cross
    # getting the center reference
    xlims = axs[1].get_xlim()
    ylims = axs[1].get_ylim()
    
    # set limits to the axis containing the text to match the one from the image
    #axs[0].set_xlim(xlims)
    #axs[0].set_ylim(ylims)

    # invert image:
    axs[1].invert_xaxis()

    # plotting the cross in the image:
    x_diff = abs(x_lims[1] - x_lims[0])
    y_diff = abs(y_lims[1] - y_lims[0])

    # horizontal points
    x = [x_lims[0] - x_diff * 0.25, x_lims[0] - x_diff * (0.45 - sizeratiocross)] 
    y = [yc] * len(x) 
    axs[1].plot(x, y, transform = axs[1].get_transform('pixel'), color = 'C0', linewidth = lwidth)

    x = [x_lims[0] - x_diff * (0.55 + sizeratiocross), x_lims[0] - x_diff * 0.75] 
    y = [yc] * len(x)
    axs[1].plot(x, y, transform = axs[1].get_transform('pixel'), color = 'C0', linewidth = lwidth)

    # vertical points
    y = [y_lims[0] + y_diff * (0.45 - sizeratiocross), y_lims[0] + y_diff * 0.25]  
    x = [xc] * len(y) 
    axs[1].plot(x, y, transform = axs[1].get_transform('pixel'), color = 'C0', linewidth = lwidth)

    y = [y_lims[0] + y_diff * (0.55 + sizeratiocross), y_lims[0] + y_diff * 0.75] 
    x = [xc] * len(y) 
    axs[1].plot(x, y, transform = axs[1].get_transform('pixel'), color = 'C0', linewidth = lwidth)

    # adding text
    plot_text, plot_comments = plot_text # unpacking the text
    axs[0].text(0, 0, plot_text, fontsize = 9)
    axs[0].text(1, 0, plot_comments, fontsize = 9, ha = 'right')


    # fix aspect
    axs[0].set_aspect('equal', adjustable = 'box')
    plt.savefig(plot_title)


    return None


def get_plot_title(gifroot, fnamestyle, gifsuffix, fnameseparator, cat_info = ''):
    '''
    Returns the title for the plot given the values of the parameters.
    
    Args:
        gifroot: the start of the filename.
        fnamestyle: the style of the nomenclature.
        gifsuffix: the final suffix of the filename.
        fnameseparator: the separator to use in the nomenclature.
        cat_info: the information to add to the title from the catalogue. 
    
    Output:
        plot_title: the name of the output file.
    '''
    
    separators = get_separators(fnameseparator)
    use_srcid, use_srcnum, use_detid, use_numhex = get_namestyles(fnamestyle)
    full_str_l = [''] * 4
    full_str = ''

    if not isinstance(cat_info, str):
        src_num, srcid, detid, num_hex = cat_info 
        thumb_log.log('debug', 'Catalogue info gathered: {}.'.format(cat_info))
        if use_srcid != -1:
            full_str_l[use_srcid] = use_srcid
        else:
            full_str_l.remove('')
        if use_srcnum != -1:
            full_str_l[use_srcnum] = src_num
        else:
            full_str_l.remove('')
        if use_detid != -1:
            full_str_l[use_detid] = detid
        else:
            full_str_l.remove('')
        if use_numhex != -1:
            full_str_l[use_numhex] = num_hex
        else:
            full_str_l.remove('')
            
    thumb_log.log('debug', 'Full string iteration: {}. Separators: {}. full_str: {}'.format(full_str_l, separators, full_str))

    if len(full_str_l) == 0:
        full_str = ''
    elif len(full_str_l) == 1:
        full_str = '{0}{1}'.format(full_str, full_str_l[0])
    else:
        for j in range(0, len(full_str_l)):
            if j == len(full_str_l) - 1: # no need to add separator for the last item
                full_str = full_str + '{0}'.format(full_str_l[j])
            else:
                full_str = full_str + '{0}{1}'.format(full_str_l[j], separators[j])
    
    plot_title = gifroot + full_str + gifsuffix
    
    return plot_title


def get_separators(nameseparators):
    '''
    Returns a list of the characters to be used as separators.

    Args:
        nameseparators: a string parsed from fnameseparators

    Output:
        char_list: a list of four elements containing the characters to be used.
    '''
    
    nameseparators = nameseparators.strip().rstrip()
    char_list = list(nameseparators)

    if len(char_list) == 0:
        thumb_log.log('warning', 'Could not find separators. Using _ by default.')
        char_list = ['_'] * 4
    
    while len(char_list) < 4:
        char_list = char_list + [char_list[-1]]

    return char_list


def get_namestyles(fnamestyle):
    '''
    Returns a set of booleans that incorporate info on which information should 
    be used in the naming of the files.

    Args:
        fnamestyle: the line parameter fnamestyle.

    Output:
        use_<param>: a set of four booleans.
    '''

    use_srcid, use_srcnum, use_detid, use_numhex = -1, -1, -1, -1
    fnamestyle = fnamestyle.upper()

    name_styles = fnamestyle.split('_')

    if 'SRCID' in name_styles:
        use_srcid = name_styles.index('SRCID')
    if 'SRCNUM' in name_styles:
        use_srcnum = name_styles.index('SRCNUM')
    if 'DETID' in name_styles:
        use_detid = name_styles.index('DETID')
    if 'NUMHEX' in name_styles:
        use_numhex = name_styles.index('NUMHEX')
   
    return(use_srcid, use_srcnum, use_detid, use_numhex)


################################
########### makethumb ##########
################################

def run(iparsdic):
    '''
    Main function of the script. Will change for 'run'.
    '''

    print(f'Executing {__file__} {iparsdic}')

    # gets the parameters...
    # running parameters
    printparams = iparsdic['printparams']
    printparams = str_to_bool(printparams)
    
    if printparams:
        thumb_log.log('info', 'Full parameter info: {}'.format(iparsdic))

    dryrun = iparsdic['dryrun']
    dryrun = str_to_bool(dryrun)
    
    # main data parameters
    imageset = iparsdic['imageset']
    
    if not os.path.isfile(imageset):
        thumb_log.log('error', 'The given imageset cannot be found.')
        sys.exit(0)
    else:
        with fits.open(imageset) as imset:
            hdu = imset[0].header
            data = imset[0].data

    # source detection
    withsrclist = iparsdic['withsrclist']
    withsrclist = str_to_bool(withsrclist)
   
    withcoords = iparsdic['withcoords']
    withcoords = str_to_bool(withcoords)

    if not withcoords:
        withsrclist = True

    if not withsrclist and not withcoords:
        thumb_log.log('error', 'Either withcoords or withsrclist must be true.')
        sys.exit(0)


    # catalogue
    withcat = iparsdic['withcat']
    withcat = str_to_bool(withcat)

    # source number selection
    if withcat or withsrclist:
        withsrcnum = iparsdic['withsrcnum']
        srcnum = int(iparsdic['srcnum'])


    if withsrclist:
        srclisttab = iparsdic['srclisttab']
        try:
            src_file, src_ext = srclisttab.split(':')
        except ValueError:
            thumb_log.log('warning', 'Could not split srclisttab. Will use The first non-primary extension.')
            src_file = srclisttab
            src_ext = 1
        coords, n_images, srcnums = source_from_table(src_file, src_ext, srcnum)
        thumb_log.log('debug', 'Info from srclisttab: coords: {}. source numbers: {}.'.format(coords, srcnums))
    else:
        # manual coordinates selection
        if withcoords:
            ra = float(iparsdic['ra'])
            dec = float(iparsdic['dec'])
            n_images = 1
            coords = [(ra, dec)]

    if withcat and not withcoords:
        cattab = iparsdic['cattab']
        try:
            cat_file, cat_ext = cattab.split(':')
        except ValueError:
            thumb_log.log('warning', 'Could not split cattab. Will use The first non-primary extension.')
            cat_file = cattab
            cat_ext = 1
        if isinstance(srcnums, int):
            src_nums, srcids, detids, numhex, iau_vals = info_from_catalogue(cat_file, cat_ext, srcnums)
        else:
            src_nums = []
            srcids = []
            detids = []
            numhex = []
            iau_vals = []
            for src in srcnums:
                src_nums_i, srcids_i, detids_i, numhex_i, iau_vals_i = info_from_catalogue(cat_file, cat_ext, src)
                src_nums.append(src_nums_i)
                srcids.append(srcids_i)
                detids.append(detids_i)
                numhex.append(numhex_i)
                iau_vals.append(iau_vals_i)


        thumb_log.log('debug', 'Catalogue overall info: src_nums: {0}, srcids: {1}, detids: {2}. Num.Hex: {3}.'.format(src_nums, srcids, detids, numhex))

    
    # formatting parameters:
    autofname = iparsdic['autofname']
    autofname = str_to_bool(autofname)
   
    if not autofname:
        outfilename = iparsdic['outfilename']
        plot_title = outfilename
        if n_images != 1:
            thumb_log.log('warning', 'Since a fixed filename was passed but more than one images were expected only the first one will be created.')
            n_images = 1
    else:
        gifroot = iparsdic['gifroot']
        fnamestyle = iparsdic['fnamestyle']
        gifsuffix = iparsdic['gifsuffix']
        if '.GIF' in gifsuffix.upper():
            thumb_log.log('warning', 'matplotlib does not support GIF format. Changing to png.')
            gifsuffix = '.png'
        fnameseparator = iparsdic['fnameseparator']
        

    srcindexstyle = iparsdic['srcindexstyle']
        
    if srcindexstyle.upper() == 'DEFAULT':
        if withcat:
            srcindexstyle = 'detid'
        elif withsrclist:
            srcindexstyle = 'srcnum'
        else:
            srcindexstyle = 'none'

    if srcindexstyle.upper() == 'NONE':
        srcindexstyle = ''
    elif srcindexstyle.upper() == 'SRCNUM':
        srcindexstyle = '/'
    elif srcindexstyle.upper() == 'HEXSRCNUM':
        srcindexstyle == ''
        thumb_log.log('warning', 'srcindexstyle=hexsrcnum is not yet supported. Switched to none')
    elif srcindexstyle.upper() == 'DETID':
        srcindexstyle = ':'
    elif srcindexstyle.upper() == 'SRCID':
        srcindexstyle = '/'
    else:
        srcindexstyle = ''
        thumb_log.log('warning', 'Unrecognised format. Using none.')

    # plotting options
    iaunameprefix = iparsdic['iaunameprefix']
    obsidstr = iparsdic['obsidstr']
    erangestr = iparsdic['erangestr']
    inststr = iparsdic['inststr']
    lwidth = iparsdic['lwidth']
    commupper = iparsdic['commupper']
    commlower = iparsdic['commlower']
    imagesize = float(iparsdic['imagesize']) # arcmin
    imagesize = imagesize / 60
    sizeratiocross = float(iparsdic['sizeratiocross'])
    sizeratiocross = sizeratiocross / 100 # the ratio is in %
    colourmap = iparsdic['colourmapid'] # refined for matplotlib
    manual_parameters = (obsidstr, inststr, erangestr, commupper, commlower)

    try:
        colourmap = plt.cm.get_cmap(colourmap)
    except ValueError:
        thumb_log.log('warning', "The selected colourmap is not present in the matplotlib cmap list. Using 'plasma' by default.")
        colourmap = plt.cm.get_cmap('plasma')

    for i in range(0, n_images):
        if autofname:
            if withcat and not withcoords:
                src_num = srcnums[i]
                srcid = srcids[i]
                detid = detids[i]
                num_hex = numhex[i]
                iau = iaunameprefix + iau_vals[i]
                cat_info = src_num, srcid, detid, num_hex
                thumb_log.log('debug', 'Plot info for image {}'.format(i))
                plot_title = get_plot_title(gifroot, fnamestyle, gifsuffix, fnameseparator, cat_info)
            else:
                plot_title = gifroot + str(1 + i) + gifsuffix
                thumb_log.log('debug', 'Plot title: {}.'.format(plot_title))
        else:
            thumb_log.log('debug', 'Plot title: {}.'.format(plot_title))
        
        ra_dec = coords[i]
        
        plot_text = prepare_text(hdu, manual_parameters, i, srcindexstyle)
        plot_parameters = (plot_title, colourmap, imagesize, ra_dec, lwidth, \
                sizeratiocross)
        plot_thumb(data, hdu, plot_parameters, plot_text)
    

    return None
