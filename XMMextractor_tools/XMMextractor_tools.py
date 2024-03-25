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

# XMMextractor_tools



import os
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from astropy.io import fits
import subprocess
from pysas.pyutils import pyutils
from pysas.logger import TaskLogger as TL
tool_log = TL('aux.log')
import glob
import shutil
from pysas.wrapper import Wrapper as W
import warnings
import tarfile
import urllib.request
from astroquery.esa.xmm_newton import XMMNewton 

def ODF_times(SAS_file = ''):
    '''
    Searches for the start time and the end time of the observation.
    
    Args:
        SAS_file: (optional) a SAS file. By default it will search for one 
        in the main directory for XMMExtractor.
    
    Output:
        (start time, end time, duration)
    '''

    if SAS_file == '':
        SAS_file = glob.glob(XMMExtractor.main_dir + '/*.SAS')[0]

    t_start = 0
    t_end = 0
    duration = 0

    with open(SAS_file, 'r') as f:
        for line in f:
            if 'Observation Start Time' in line:
                t_start = line.replace(' / Observation Start Time', '')
                t_start = Time(t_start)
            if 'Observation End Time' in line:
                t_end = line.replace(' / Observation End Time', '')
                t_end = Time(t_end)
            if t_start != 0 and t_end != 0:
                break # There is no interested in the rest of the file.
        duration = t_end - t_start

    return (t_start, t_end, duration.value*86400)


def ra(source_name):
    '''
    '''

    cmd = ned_coord_directory + ned_coord_script + source_name
    ps = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    out = ps.communicate()[0]

    out = out.split()

    if out[0] == 'Target':
        ra = 0.
    else:
        ra = out[0]

    return ra


def dec(source_name):
    '''
    '''

    cmd = ned_coord_directory + ned_coord_script + source_name
    ps = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    out = ps.communicate()[0]

    out = out.split()

    if out[0] == 'Target':
        dec = 0.
    else:
        dec = out[1]

    return dec


def angular_distance(ra1, ra2, dec1, dec2):
    '''
    Returns the angular distance between two objectives in degrees.

    Args:
        ra1: RA of the first item.
        ra2: RA of the second item.
        dec1: DEC of the first item.
        dec2: DEC of the second item.
    
    Output: 
        angular_distance: The angular distance between the objectives, in AstroPy degree units format.
    '''

    # TODO: dheck units (and add them)
    coord1 = SkyCoord(ra1 * u.deg, dec1 * u.deg)
    coord2 = SkyCoord(ra2 * u.deg, dec2 * u.deg)

    angular_distance = coord1.separation(coord2)

    return angular_distance


def add_source_to_region_file(region_file, x, y, r1, r2, color, text, region_type, coord_type):
    '''
    Creates a region file that can be read with ds9.

    Args:
        region_file: the name of the region file.
        x: x coordinate.
        y: y coordinate.
        r1: radius 1 (use r1 = 0 for circle)
        r2: radius 2.
        color: desired colour.
        text: added text.
        region_type: region type.
        coord_type: type of coordinates.

    Output:
        0: if finished; 1 if the region could not be read.
    '''

    with open(region_file, 'w+') as rg_file:
        if region_type == 'circle':
            rg_file.write('{};circle({},{},{}) # color={} text=\"{}\" \n'.format(coord_type, x, y, r2, color, text))
        elif region_type == 'annulus':
            rg_file.write('{};annulus({},{},{},{}) # color={} text=\"{}\" \n'.format(coord_type, x, y, r1, r2, color, text))
        elif region_type == 'box':
            rg_file.write('{};box({},{},{},{}) # color={} text=\"{}\" \n'.format(coord_type, x, y, r1, r2, color, text))
        else:
            warnings.warn('Shape not accepted. Only circle, annulus and box.')
            return 1

    return 0


def produce_ps_file(fits_file, region_file, title, ps_file):
    '''
    Produces a PS file.
    
    Args:
        fits_file: the given FITS file.
        region_file: the name of the region file.
        title: the title of the PS.
        ps_file: the name of the PS file.

    Output:
        0 if run successfully, 1 otherwise.
    '''

    args = 'ds9 -cmap invert yes -cmap b -cmap value 1.15 .13 -fits {} '.format(fits_file) +\
        '-region {} -zoom to fit -title {} -print destination file '.format(region_file, title)+\
        '-print filename {} -print palette rgb -print level 1 -print resolution 300 -print -exit'.format(ps_file)

    if os.system(args):
        return 1

    return 0


def deg_to_hours(deg):
    '''
    Moves from degrees to hours.
    
    Args:
        deg: degrees.
    
    Output: 
        hour: the equivalent in hours.
    '''

    if hasattr(deg, 'unit'):
        if deg.unit == 'hourangle':
            print('Already in hours')
            hour = deg
        else:
            hour = deg.to(u.hourangle)
    else:
        deg = deg * u.deg
        hour = deg.to(u.hourangle)

    return hour


def deg_to_sexagesimal(deg):
    '''
    Moves from degrees to sexagesimal degrees.
    
    Args:
        deg: degrees.
    
    Output:
        dms: the equivalent in dms as a tuple.
    '''

    if hasattr(deg, 'unit'):
        if deg.unit == 'deg':
            dms = Angle(deg.value, deg.unit)
            dms = dms.dms
    else:
        deg = Angle(deg, u.deg)
        dms = deg.dms

    return dms


def event_file_spectral_info(event_file, instr):
    '''
    Writes into the log file some basic information regarding the given event list.
    
    Args:
        event_file: the event list.
        instr: the instrument.

    Output: 
        (exposure live time, backscale, areascale).
    '''

    #instr = PythonUtils.normalize_instrument(instrument)

    #live_time = PythonUtils.get_key_word(event_file, 'EXPOSURE', 1)
    live_time = pyutils.get_key_word(event_file, 'EXPOSURE', 1)
    
    if live_time == 'EXPOSURE' or live_time == '' or live_time == 0:
        live_time = 'unknown'

    backscale = get_back_scale(event_file, 1)
    areascale = get_area_scale(event_file, 1)

    tool_log.log('info', '   #> Information from Spectra file: {}'.format(event_file))
    tool_log.log('info', '   {} live time : {} (Weighted live time of CCDs in extraction region)'.format(instr, live_time))
    tool_log.log('info', '   {} Backscale : {}'.format(instr, backscale))
    tool_log.log('info', '   {} Areascale : {}'.format(instr, areascale))

    return (live_time, backscale, areascale)


def get_back_scale(event_file, extension):
    '''
    Checks for the BACKSCAL in a given event file and extension.
    
    Args:
        event_file: the event file.
        extension: the extension of that event file.
    
    Output: 
        backscale: the backscale.
    '''

    backscale = pyutils.get_key_word(event_file, 'BACKSCAL', extension)
    if backscale == 'BACKSCAL' or backscale == '':
        backscale = 'unknown'
    
    return backscale


def get_area_scale(event_file, extension):
    '''
    Checks for the AREASCAL in a given event file and extension.

    Args:
        event_file: the event file.
        extension: the extension of that event file.
    
    Output: 
        areascale: the areascale.
    '''

    areascale = pyutils.get_key_word(event_file, 'AREASCAL', extension)
    if areascale == 'AREASCAL' or areascale == '':
        areascale = 'unknown'
    
    return areascale


def get_entries(event_file, extension):
    '''
    Checks for the number of entries in a given event file and extension.
    
    Args:
        event_file: the event file.
        extension: the extension of that event file.

    Output:
        n_entries: the number of entries found in the FITS file.
    '''
    
    n_entries = pyutils.get_key_word(event_file, 'NAXIS2', extension)
    return n_entries


def print_SAS_setup():
    '''
    Prints the SAS information regarding env variables into the XMMextractor
    log file.
    '''

    list_var = os.environ
    SAS_info = ''
    for i in list_var:
        if 'SAS' in i:
            SAS_info = SAS_info + i + '=' + os.environ.get(i) + '\n'

    tool_log.log('debug', '   #> This is the current SAS set-up: ')
    tool_log.log('info', SAS_info)


def set_coordinates(obs, ra = '', dec = ''):
    '''
    For a given observation object, modifies the RA and DEC of it's attributes
    and in the XML file.
    #TODO: check consistency with the GUI.
    
    Args:
        obs: the observation object.
        ra:: the new RA.
        dec: the new DEC.

    Output:
        obs: the observation object with the applied changes.
    '''


    test_odfingest = run_cifbuild.test_odfingest()
    odfingest_file = test_odfingest[1]

    if not test_odfingest[0]:
        tool_log.log('error','    Run odfingest first')
        RunCifbuild.run_odfingest()

    if ra != '' or dec != '':
        tool_log.log('info', '   #> Using user defined coordinates')
        if ra != '':
            obs.set_coord(ra = str(ra))
        if dec != '':
            obs.set_coord(dec = str(ra))

        # obs.writeXML()
        # filename = glob.glob('*.xml')[0]
        # obs = XMMXMLextractor_classes.Observation(filename)

    else:
        tool_log.log('info', "   #> Not user defined coordinates found. Using the SUM.SAS RA_OBJ and DE_OBJ coordinates.")
        tool_log.log('info','   #> RA_OBJ = {}'.format(obs.ra))
        tool_log.log('info','   #> DEC_OBJ = {}'.format(obs.dec))

    return obs


def produce_image(event_file, image_file, instr, mode):
    '''
    Generates an image for an EPN or EMOS1, EMOS2 event list.

    Args:
        event_file: the event file.
        image_file: the name for the image file.
        instr: the instrument (will be normalized)
        mode: the mode

    Output:
        0 if run successfully; 1 otherwise.
    '''

    tool_log.log('info', '   #> Producing image from {} .... '.format(event_file))
    if instr == 'EPN':
        expr = '#XMMEA_EP'
    if instr == 'EMOS1':
        expr = '#XMMEA_EM'
    if instr == 'EMOS2':
        expr = '#XMMEA_EM'

    if mode == 'IMAGING' or mode == 'imaging':
        xbin = 80
        ybin = 80
        xval = 'X'
        yval = 'Y'

    elif instr == 'EPN' and (mode == 'TIMING' or mode == 'timing'):
        xbin = 1
        ybin = 1
        xval = 'RAWX'
        yval = 'RAWY'
    elif (mode == 'TIMING' or mode == 'timing') and (instr == 'EMOS1' or instr == 'EMOS2'):
        xval = 'RAWX'
        yval = 'TIME'
    else:
        tool_log.log('error', 'ERROR producing image: {}'.format(image_file))
        return 1

    args = ['table=\"{}\"'.format(event_file), 'expression=\"{}\"'.format(expr), ' withimageset=yes', +\
        'imageset=\"{}\"'.format(image_file), 'imagebinning=binSize', 'ximagebinsize={}'.format(xbin), 'yimagebinsize={}'.format(ybin), 'xcolumn=\"{}\"'.format(xval), 'ycolumn=\"{}\"'.format(yval)]

    t = W('evselect', args)

    t.run()

    tool_log.log('info', 'Image: done: {}'.format(image_file))
    
    return 0


def produce_image_4GUI(event_file, image_file, instr, mode):
    '''
    Generates an image for the XMMextractor GUI for an EPN or EMOS1, EMOS2 event list.

    Args:
        event_file: the path to the event file.
        image_file: the name for the image file.
        instr: the instrument (will be normalized)
        mode: the mode

    Output:
        0 if run successfully; 1 otherwise.
    '''

    tool_log.log('info', ' Producing image from {} .... '.format(event_file))

    if instr == 'EPN':
        expr = '#XMMEA_EP'
    if instr == 'EMOS1':
        expr = '#XMMEA_EM'
    if instr == 'EMOS2':
        expr = '#XMMEA_EM'

    if mode == 'IMAGING' or mode == 'imaging':
        xbin = 80
        ybin = 80
        xval = 'X'
        yval = 'Y'
        extra_params = []
    elif instr == 'EPN' and (mode == 'TIMING' or mode == 'timing'):
        xbin = 1
        ybin = 1
        xval = 'RAWX'
        yval = 'RAWY'
        extra_params = ["imagebinning=binSize", "ximagebinsize={}".format(xbin), "yimagebinsize={}".format(ybin)]
    elif (mode == 'TIMING' or mode == 'timing') and (instr == 'EMOS1' or instr == 'EMOS2'):
        xval = 'RAWX'
        yval = 'TIME'
        extra_params = []
    else:
        tool_log.log('error', 'ERROR producing image for GUI: {}'.format(image_file))
        return 1

    #image_file = image_file[image_file.rfind('/') + 1:]

    inargs = ['table={}'.format(event_file), 'expression={}'.format(expr),  'withimageset=yes', \
        'imageset={}'.format(image_file), 'xcolumn={}'.format(xval), 'ycolumn={}'.format(yval)] + extra_params

    t = W('evselect', inargs)
    t.run()

    tool_log.log('info', 'Image: done')

    return 0


def return_expid(filename):
    """
    Returns the EXPIDSTR keyword in a fashion INXEXPID, being X the mode and
    IN the prefix for the instrument.
    
    Args:
        filename: the file.
    
    Output:
        the EXPIDSTR.
    """

    prefix = ''
    instr = pyutils.get_key_word(filename, 'INSTRUME')

    if instr == 'OM':
        prefix = 'OM'
    if instr == 'EMOS1':
        prefix = 'M1'
    if instr == 'EMOS2':
        prefix = 'M2'
    if instr == 'RGS1':
        prefix = 'R1'
    if instr == 'RGS2':
        prefix = 'R2'
    if instr == 'EPN':
        prefix = 'PN'

    EXPIDSTR = 'unknown'

    try:
        with fits.open(filename) as ev:
            for i in range(0, len(ev)):
                if 'EXPIDSTR' in ev[i].header:
                    EXPIDSTR = ev[i].header['EXPIDSTR']
                    return prefix + EXPIDSTR

            if EXPIDSTR == 'unknown':
                for i in range(0, len(ev)):
                    if 'EXP_ID' in ev[i].header:
                        EXPIDSTR = 'X' + ev[i].header['EXP_ID'][-3:]
                        return prefix + EXPIDSTR
    except FileNotFoundError:
        warnings.warn('Could not open file {}.'.format(filename))
        return None

    return EXPIDSTR


def produce_smooth_image(event_file, image_file, smooth_file, instr, mode):
    '''
    Produces a smooth image.

    Args:
        event_file: the event file.
        immage_file: the image_file.
        smooth_file: name of the output file.
        instr: name of the instrument.
        mode: the mode of the observation.
    
    Output: 
        0 (success) or 1 (error).
    '''

    tool_log.log('info', '   #> Producing smooth image from {} .... '.format(event_file))

    if instr == 'EPN':
        expr = '#XMMEA_EP'
    if instr == 'EMOS1':
        expr = '#XMMEA_EM'
    if instr == 'EMOS2':
        expr = '#XMMEA_EM'

    if mode == 'IMAGING' or mode == 'imaging':
        xbin = 80
        ybin = 80
        xval = 'X'
        yval = 'Y'

    elif instr == 'EPN' and (mode == 'TIMING' or mode == 'timing'):
        xbin = 1
        ybin = 1
        xval = 'RAWX'
        yval = 'RAWY'
    elif (mode == 'TIMING' or mode == 'timing') and (instr == 'EMOS1' or instr == 'EMOS2'):
        xbin = 1
        ybin = 1
        xval = 'RAWX'
        yval = 'TIME'
    else:
        tool_log.log('error', 'ERROR producing smooth image.')
        return 1

    inargs = ['table=\"{}\"'.format(event_file), 'expression=\"{}\"'.format(exptr), 'withimageset=yes', + \
        'imageset=\"{}\"'.format(image_file), 'imagebinning=binSize', 'ximagebinsize={}'.format(xbin), 'yimagebinsize={}'.format(ybin), 'xcolumn=\"{}\"'.format(xval), 'ycolumn=\"{}\"'.format(yval)]

    t = W('evselect', inargs)
    t.run()


    cmd = "(asmooth inset=\"{}\" outset=\"{}\" smoothstyle=simple convolverstyle=gaussian width=2.5)".format(image_file, smooth_file)
    if os.system(cmd):
        warnings.warn('Could not run asmooth')
        tool_log.log('error', 'Could not run asmooth.')
        return 1

    shutil.copy(smooth_file, obs.image_dir)

    tool_log.log('info', 'Smooth image created. Ok')
    return 0


def GTI_file_info(event_file):
    '''
    Reads a GTI event file and returns the ONTIME as a float. Also updates
    the proper GTI log file.
    
    Args:
        event_file: the GTI event file.
    
    Output: 
        GTI_time as string*.

    * To avoid exceptions if the timing is unknown.
    '''

    instr = pyutils.get_key_word(event_file, 'INSTRUME')
    GTI_time = pyutils.get_key_word('ONTIME')

    tool_log.log('info', '#> Information from GTI file: {}'.format(event_file))
    tool_log.log('info', '{} Sum of all Good Time Intervals: {}'.format(instr, GTI_time))

    return GTI_time


def get_OM_science_modes(obs):
    '''
    Returns as a tuple the modes available for a given observation for the OM
    instrument.
    
    Args:
        obs: the observation as an object.
    
    Output: 
        the tuple. 0 indicates that the mode is not available. 1 indicates
    the oposite.

    The order is: omichain, omfchain, omgchain.
    '''

    omichain = False
    omfchain = False
    omgchain = False

    for expo in obs.get_instrument('OM').get_exposures():
        for p in obs.get_instrument('OM').get_exposure(expo).get_products():
            for task in p.get_tasks():                
                if task.task_name == 'omichain':
                    omichain = True
                if task.task_name == 'omfchain':
                    omfchain = True
                if task.task_name == 'omgchain':
                    omgchain = True


    return (omichain, omfchain, omgchain)



def get_region_SP_creation(exposure,t):
    '''
    Returns the source information for a given exposure object.
    
    Args:
        exposure: the exposure as an object from XMMextractor_classes.
    
    Output: 
        returns as a tuple (shape, x, y, L1, L2 and the radius). If one of
    them is 0, then that implies that that value is not used in that geometry.
    '''

    shape = ''
    src_xc = 0
    src_yc = 0
    src_L1 = 0
    src_L2 = 0
    src_r = 0

    region = ''
    prod = exposure.get_product('spectra')
    val = ""
    if t == 'SRC':
        val = 'srcexp'
    else:
        val = 'backexp'
        
    region = ''

    task = prod.get_task('especget','sp_creation')
    expr = task.get_param(val).param_value
    if expr == '':
        return ('no shape', 0, 0, 0 ,0, 0)
    expr = expr.replace(expr[0:expr.index(')') + 2], '')

    shape = ''
    if 'box' in expr:
        shape = 'box'
    if 'annulus' in expr:
        shape = 'annulus'
    if 'circle' in expr:
        shape = 'circle'
    if 'point' in expr:
        shape = 'point'
    if 'line' in expr:
        shape = 'line'

    coords = expr[expr.index('(') + 1:expr.index(')')]
    coords = coords.split(',')
    src_xc = coords[0]
    src_yc = coords[1]

    if shape == 'box' or shape == 'annulus':
        src_L1 = coords[2]
        src_L2 = coords[3]

    if shape == 'circle':
        src_r = coords[2]
    else:
        src_r = 0.0

    return (shape, src_xc, src_yc, src_L1, src_L2, src_r)


def get_region_LC(exposure,t):
    '''
    Returns the source information for a given exposure object.
    
    Args:
        exposure: the exposure as an object from pyOAL.
    
    Output: returns as a tuple (shape, x, y, L1, L2 and the radius). If one of
    them is 0, then that implies that that value is not used in that geometry.
    '''

    shape = ''
    src_xc = 0
    src_yc = 0
    src_L1 = 0
    src_L2 = 0
    src_r = 0

    region = ''
    prod = exposure.get_product('lightcurve')
    exp = ""
    if t == 'SRC':
        exp = 'src_filtering'
    else:
        exp = 'bkg_filtering'
        
    
    task = prod.get_task('evselect','src_filtering')        
    expr = task.get_param('expression').param_value
    if expr == '':
        return ('no shape', 0, 0, 0 ,0, 0)
    expr = expr.replace(expr[0:expr.index(')') + 2], '')

    shape = ''
    if 'box' in expr:
        shape = 'box'
    if 'annulus' in expr:
        shape = 'annulus'
    if 'circle' in expr:
        shape = 'circle'
    if 'point' in expr:
        shape = 'point'
    if 'line' in expr:
        shape = 'line'

    coords = expr[expr.index('(') + 1:expr.index(')')]
    coords = coords.split(',')
    src_xc = coords[0]
    src_yc = coords[1]

    if shape == 'box' or shape == 'annulus':
        src_L1 = coords[2]
        src_L2 = coords[3]

    if shape == 'circle':
        src_r = coords[2]
    else:
        src_r = 0.0

    return (shape, src_xc, src_yc, src_L1, src_L2, src_r)


def build_expression(instr, mode, shape, values, current_log = ''):
    '''
    Writes an expression for the source or the background.
    
    Args:
        instr: the instrument.
        mode: the observation mode (timing or imaging).
        shape: the shape wanted for the expression.
        values: the values wanted.
    
    Output: 
        the expression as a string or empty string if the condiitons were
    not fit.
    '''

    if obsmode.upper() == 'IMAGING':
        xval = 'X'
        yval = 'Y'
    elif obsmode.upper() == 'TIMING' and instr == 'EPN':
        xval = 'RAWX'
        yval = 'RAWY'
    elif obsmode.upper() == 'TIMING' and (instr == 'EMOS1' or instr == 'EMOS2'):
        xval = 'RAWX'
        yval = 'TIME'

    expr = ''

    if shape == 'circle' and len(values) == 3:
        xc = values[0]
        yc = values[1]
        rc = values[2]
        expr = '(({},{}) in {}({},{},{}))'.format(xval, yval, shape, xc, yc, rc)
    elif shape == 'circle' and len(values) == 4:
        xc = values[0]
        yc = values[1]
        if values[2] > values[3]:
            rc = values[2]
        else:
            rc = values[3]
        expr = '(({},{}) in {}({},{},{}))'.format(xval, yval, shape, xc, yc, rc)

    if shape == 'annulus' and len(values) == 4:
        xc = values[0]
        yc = values[1]
        r1 = values[2]
        r2 = values[3]
        expr = '(({},{}) in {}({},{},{},{}))'.format(xval, yval, shape, xc, yc, r1, r2)

    if shape == 'box' and len(values) == 4:
        xc = values[0]
        yc = values[1]
        L1 = values[2]
        L2 = values[3]
        expr = '(({},{}) in {}({},{},{},{}))'.format(xval, yval, shape, xc, yc, L1, L2)

    if expr == '':
        tool_log.log('warning', '\n Something wrong happened while writting an expression.')
    if current_log != '':
        tool_log.log('info', 'Expression for the given parameters: {}'.format(expr))

    return expr


def prepare_region_log_file(instr, exposure, current_product, current_log, src_info = '', \
    bkg_info = ''):
    '''
    Writes into a log file regarding a region.
    
    Args:
        instr: the instrument.
        exposure:: an exposure object.
        current_product: the type of the product as string.
        current_log,: a log file.
        src_info (optional): info regarding region if the one read from the expression
    is not good (src).
        bkg_info (optional): info regarding region if the one read from the expression
    is not good (bkg).
    '''

    if src_info == '' and bkg_info == '':
        src_shape, src_xc, src_yc, src_L1, src_L2, src_R = get_region(exposure,'SRC')
        bkg_shape, bkg_xc, bkg_yc, bkg_L1, bkg_L2, bkg_R = get_region(exposure,'BKG')
    elif src_info != '' and bkg_info == '':
        bkg_shape, bkg_xc, bkg_yc, bkg_L1, bkg_L2, bkg_R = get_region(exposure,'BKG')
        src_shape, src_xc, src_yc, src_L1, src_L2 = src_info
    elif src_info == '' and bkg_info != '':
        src_shape, src_xc, src_yc, src_L1, src_L2, src_R = get_region(exposure,'SRC')
        bkg_shape, bkg_xc, bkg_yc, bkg_L1, bkg_L2 = bkg_info
    elif src_info != '' and bkg_info != '':
        bkg_shape, bkg_xc, bkg_yc, bkg_L1, bkg_L2 = bkg_info
        src_shape, src_xc, src_yc, src_L1, src_L2 = src_info

    if current_product == 'LC':
        product = 'lightcurve'
    else:
        product = 'spectra'

    tool_log.log('debug', "   #> {} processing...".format(product))
    tool_log.log('debug', "   #> Centroid of source to analyze (Physical Units)")
    tool_log.log('debug', "   #> INSTRUMENT: {} EXPOSURE: {}".format(instr, exposure.expid))
    tool_log.log('debug', "         SRC Region : {}".format(src_shape))
    tool_log.log('debug', "         SRC XC     : {}".format(src_xc))
    tool_log.log('debug'"         SRC YC     : {}".format(src_yc))

    if src_shape == "circle":
        if src_L1 == 0:
            if src_L2 != 0:
                src_r = src_L2
        else:
            if src_L2 == 0:
                src_r = src_L1
        tool_log.log('info', '         SRC R    : {}'.format(src_r))
    if src_shape == "annulus":
        tool_log.log('info', '         SRC R1 - SRC R2    : {} - {}'.format(src_L1, src_L2))
        if src_L1 > src_L2:
            tool_log.log('warning',' source inner radius is bigger than outer radius')
    if src_shape == "box":
        tool_log.log('info', "         SRC BOX    : {} {}".format(src_L1, src_L2))

    # BKG
    tool_log.log('debug', "         BKG Region : {}".format(bkg_shape))
    tool_log.log('info', "         BKG XC     : {}".format(bkg_xc))
    tool_log.log('info', "         BKG YC     : {}".format(bkg_yc))
    
    if bkg_shape == "circle":
        if bkg_L1 == 0:
            if bkg_L2 != 0:
                bkg_r = bkg_L2
        else:
            if bkg_L2 == 0:
                bkg_r = bkg_L1
        tool_log.log('info', '         BKG R    : {}'.format(bkg_r))
    if bkg_shape == "annulus":
        tool_log.log('info','         BKG R1 - BKG R2    : {} - {}'.format(bkg_L1, bkg_L2))
        if bkg_L1 > bkg_L2:
            tool_log.log('warning', 'WARNING: bkg inner radius is bigger than outer radius')
    if bkg_shape == "box":
        tool_log.log('info', "         BKG BOX    : {} {}".format(bkg_L1, bkg_L2))
        area_factor = exposure.get_products(product)[0].get_tasks("xmmextractor","details")[0].get_params("areafactor")[0].param['default']
        tool_log.log('info', "         BKG AREA SCALE FACTOR : {} (Only area taken into account)".format(area_factor))
        if bkg_L1 == 6000 or bkg_L2 == 6000 or src_L1 == 6000 or src_L2 == 6000:
            tool_log.log('warning', "         WARNING : PN regions : Maximum allowed radius reached")

    tool_log.log('info', 'Finished writing region log.')
    return 0


def event_file_info(event_file, instr):
    '''
    Gathers the information of a given event file.

    Args:
        event_file: the event file.
        instr: the instrument.

    Output: 
        tuple with (dmode, filter, submode, utc_obsdate, obs_duration, ontime, livetime, t_start, t_end).
    '''

    ext = 1
    if instr == 'OM':
        ext = 0

    dmode = pyutils.get_key_word(event_file, 'DATAMODE', ext)
    submode = pyutils.get_key_word(event_file, 'SUBMODE', ext)
    filter_info = pyutils.get_key_word(event_file, 'FILTER', ext)
    utc_obsdate = pyutils.get_key_word(event_file, 'DATE-OBS', ext)
    obs_duration = pyutils.get_key_word(event_file, 'DURATION', ext)
    ontime = pyutils.get_key_word(event_file, 'ONTIME', ext)
    livetime = pyutils.get_key_word(event_file, 'LIVETIME', ext)
    exposure = return_expid(event_file)
    t_start = pyutils.get_key_word(event_file, 'TSTART', ext)
    t_end = pyutils.get_key_word(event_file, 'TSTOP', ext)

    # if tstart or tend are not defined, the values will be taken from the
    # data. Same for duration.
    if t_start =='unknown' or t_end == 'unknown':
        with fits.open(event_file) as ev:
            data_time = ev[ext].data['TIME']
            t_start = data_time[0]
            t_end = data_time[-1]

    if obs_duration == 'unknown':
        obs_duration = t_end - t_start

    # Writting to the given log...

    tool_log.log('info', '    #> Information from Event File: {}'.format(event_file))
    tool_log.log('info',"       {} OBS DATE          : {}".format(instr, utc_obsdate))
    tool_log.log('info',"       {} OBS STARTING TIME : {} (1st Event)".format(instr, t_start))
    tool_log.log('info', "       {} OBS ENDING TIME   : {} (Last Event)".format(instr, t_end))
    tool_log.log('info', "       {} EXPOSURE ID  : {} ".format(instr, exposure))
    tool_log.log('info', "       {} OBS DURATION : {}   ".format(instr, obs_duration))
    tool_log.log('info', "       {} OBS ONTIME   : {}".format(instr, ontime))
    tool_log.log('info', "       {} OBS LIVETIME : {}".format(instr, livetime))
    tool_log.log('info', "       {} D MODE       : {}  ".format(instr, dmode))
    tool_log.log('info', "       {} SUBMODE      : {}   ".format(instr, submode))
    tool_log.log('info', "       {} FILTER       : {} ".format(instr, filter_info))

    return (dmode, filter_info, submode, utc_obsdate, obs_duration, ontime, livetime, t_start, t_end)


def postcard_from_XSA(obsid, filename = None):
    '''
    Downloads an images given the observation id using the postcard format from astroquery.

    Args:
        obsid: the observation id.
        filename: the name of the image. None by default - will use the name from XSA.

    Ouput:
        img_name: the name of the downloaded image.
        1 if run into errors.
    '''

    try:
        img_name = XMMNewton.get_postcard(str(obsid), filename = None)
    except:
        return 1

    return img_name


def unpackODF(obs_file):
    '''
    Unpacks the OBS file tar.gz file.

    Args:
        obs_file: the path to the .tar.gz file.

    Output:
        0 when finished, 1 if any errors were found.
    '''

    try:
        targz_file = tarfile.open(obs_file, 'r:gz')
    except FileNotFoundError:
        return 1

    targz_file.extractall()
    targz_file.close()
    os.remove(os.path.basename(obs_file))


    tar_file = glob.glob('*.TAR')

    if len(tar_file) != 0:
        tar_file = tar_file[0]
        tar = tarfile.open(tar_file, 'r:')
        tar.extractall()
        tar.close()
        os.remove(os.path.basename(tar_file))

    return 0


def check_for_connection():
    '''
    Checks if there's internet connection available.

    Args:
        none

    Output: bool.
    '''

    host = 'http://google.com'

    try:
        urllib.request.urlopen(host)
        return True
    except:
        return False


def xsaRequest_image(input_obs):
    '''
    Downloads a PPS-level image from the XSA using astroquery.

    Args:
        input_obs: the OBSID for the download.

    Output:
        0 when finished, 1 if an exception is found.
    '''

    fileName = input_obs+'.FTZ'

    try:
        XMMNewton.download_data(input_obs, filename=fileName,level = 'PPS', extension='FTZ',name='OIMAGE', verbose = True)
    except:
        return 1

    return 0


def download_ODF_from_XSA(input_obs, level, username = '', password = ''):
    '''
    Download the product data for an input file.

    Args:
        input_obs: the obsid.
        level: either 'ODF', 'PPS'.

    Output:
        0 when finished, 1 if any errors occurred.
    '''
    
    try:
        XMMNewton.download_data(str(input_obs), level = level)
    except:
        return 1
    
    return 0
