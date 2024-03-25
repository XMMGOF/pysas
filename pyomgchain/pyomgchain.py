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

# pyomgchain.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'pyomgchain (pyomgchain-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

# The Python code for pyomgchain should go inside run

# iparsdic is a dictionary with all the task parameters, where their
# respective values are either those entered from the command line 
# or those taken from par file defaults.

import os
import datetime
import sys
import glob
import pysas.pyutils.pyutils as pyutils
import logging
import subprocess
import re
import fnmatch
import time



def process_orbit(orbit_key, has_ff, ff_name):
    """
    Process the orbit.
    
    Args:
        orbit_key: the orbit to process.
        has_ff: the flat field flag.
        ff_name: the name of the flat field flag.
    """

    highlighted_message('*', '    Processing orbit {}'.format(orbit_key))

    global flat_field_filename
    for obs in obs_list.keys():
        Message('     Observation {}'.format(obs))
        if has_ff:
            Message('Using flatfield (hasff = {})'.format(has_ff))
            Message('ff_name = {}'.format(ff_name))
            flat_field_filename = ff_name
        else:
            flat_field_filename = ''

        for exp_key in sorted(exp_list.keys()):
            process_exposure(orbit_key, obs, exp_key)


def process_exposure(orb_key, obs_key, exp_key):
    """
    Processes a single exposure.

    Args:

        orb_key: orbit key
        obs_key: the observation key
        exp_key: the exposure.
    """

    vis_win = dict()
    vis_wx0 = dict()
    vis_wy0 = dict()
    vis_wdx = dict()
    vis_wdy = dict()
    vis_proc = dict()

    uv_win = dict()
    uv_wx0 = dict()
    uv_wy0 = dict()
    uv_wdx = dict()
    uv_wdy = dict()
    uv_proc = dict()

    message = '     Exposure: {}'.format(exp_key)
    highlighted_message('*', message)

    tracking_history_flag = 0
    window_file_flag =0

    if fnmatch.filter(list_of_files, orb_key + obs_key + exp_key + '*00THX*'):
        tracking_history_flag = 1
        tracking_history_filename = fnmatch.filter(list_of_files, orb_key + obs_key + exp_key + '*00THX*')[0]
    else:
        tracking_history_flag = 0

    if tracking_history_flag:
        Message('Tracking hisotry flag: Ok')
    else:
        Message('Tracking history filename file for {} is missing.'.format(exp_key))

        SAS_dir = os.environ['SAS_DIR']
        Message('Creating a dummy file for tracking history.')
        tracking_history_filename = 'DUMMYTHX.FIT'

    global window_data_filename
    if fnmatch.filter(list_of_files, orb_key + obs_key + exp_key + '*00WDX*'):
        window_file_flag = 1
        window_data_filename = fnmatch.filter(list_of_files, orb_key + obs_key + exp_key + '*00WDX*')[0]
    else:
        window_data_flag = 0
    if window_file_flag:
        Message('Window data file: o.k')
    else:
        Message('Window data file for the exposure {} is missing.'.format(exp_key))

    f1 = '*' + orb_key + '*' + obs_key + '*' + exp_key + '*00WDX*'
    f2 = '*' + orb_key + '*' + obs_key + '*OM*00000NPH*'
    f3 = '*' + orb_key + '*' + obs_key + '*OM*00000PEH*'

    if fnmatch.filter(list_of_files, f1) and fnmatch.filter(list_of_files, f2) and fnmatch.filter(list_of_files, f3):
        global periodic_hk_filename, non_periodic_hk_filename
        periodic_hk_filename = fnmatch.filter(list_of_files, f3)[0]
        non_periodic_hk_filename = fnmatch.filter(list_of_files, f2)[0]
        window_data_filename = fnmatch.filter(list_of_files, f1)[0]

        s = window_data_filename[18] # takes the letter for the mode
        tracking_history_plot_filename = 'P' + obs_key + 'OM' + s + exp_key + 'TSHPLT' + '0000.PS'
        Message('Tracking history plot file: {}'.format(tracking_history_plot_filename))

        s = non_periodic_hk_filename[18] # takes the letter for the mode
        tracking_history_timeseries_filename = 'P' + obs_key + 'OM' + s + exp_key + 'TSTRTS0000.FIT'
        Message('Tracking history timeseries file: {}'.format(tracking_history_timeseries_filename))

        number_of_grisms = 0
        vis_index = 0
        uv_index = 0

        for i in sorted(win_list.keys()):
            win_key = i
            if fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + win_key + '*IMI*')[0]:
                image_file = inp_dir + '/' + fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + win_key + '*IMI*')[0]
                if os.path.isfile(image_file):
                    Message('Image found: {}'.format(image_file))

                filter_id = pyutils.get_key_word(image_file, 'FILTER')
                wx0 = pyutils.get_key_word(image_file, 'WINDOWX0')
                wy0 = pyutils.get_key_word(image_file, 'WINDOWY0')
                wdx = pyutils.get_key_word(image_file, 'WINDOWDX')
                wdy = pyutils.get_key_word(image_file, 'WINDOWDY')

                if filter_id == 200:
                    vis_win.update({vis_index : win_key})
                    vis_wx0.update({vis_index : wx0})
                    vis_wy0.update({vis_index : wy0})
                    vis_wdx.update({vis_index : wdx})
                    vis_wdy.update({vis_index : wdy})
                    vis_proc.update({vis_index : 1})
                    vis_index = vis_index + 1

                if filter_id == 1000:
                    uv_win.update({uv_index : win_key})
                    uv_wx0.update({uv_index : wx0})
                    uv_wy0.update({uv_index : wy0})
                    uv_wdx.update({uv_index : wdx})
                    uv_wdy.update({uv_index : wdy})
                    uv_proc.update({uv_index : 1})
                    uv_index = uv_index + 1

        if vis_index > 0:
            process_windows(orb_key, obs_key, exp_key, filter_id, vis_index, vis_win, vis_wx0, vis_wy0, vis_wdx, vis_wdy, vis_proc)

        if uv_index > 0:
            process_windows(orb_key, obs_key, exp_key, filter_id, uv_index, uv_win, uv_wx0, uv_wy0, uv_wdx, uv_wdy, uv_proc)

    else:
        Message('*** Warning ***')
        Message('Exposure {} in observation {} is missing a file'.format(exp_key, obs_key))

        thx_file = orb_key + "_" + obs_key + "_OMS" + exp_key + "00THX.FIT"
        Message('Please check if the file {} is in the ODF'.format(thx_file))

        nph_file = orb_key + "_" + obs_key + "_OMS" + exp_key + "00NPH.FIT"
        Message('Please check if the file {} is in the ODF'.format(nph_file))

        peh_file = orb_key + "_" + obs_key + "_OMS" + exp_key + "00PEH.FIT"
        Message('Please check if the file {} is in the ODF'.format(peh_file))

        wdx_file = orb_key + "_" + obs_key + "_OMS" + exp_key + "00WDX.FIT"
        Message('Please check if the file {} is in the ODF'.format(wdx_file))


def Message(message):
    """
    Prints a message directly to the screen and sends it to a log file.
    
    Args:
        message: the message to send to the log and screen.
    """

    logging.basicConfig(filename = 'pyomgchain.log', level = logging.DEBUG)

    print(message)
    logging.info(message)


def highlighted_message(character, message):
    """
    Delivers a clearier, easier to read, and probably more important
    message.

    Args
        character: character preceding the message used to 'highlight'.
        message: the proper message.
    """

    message = message.split('\n')
    num_lines = len(message)
    max_lenght = len(message[0])

    if num_lines > 1:
        for i in range(1, num_lines):
            if len(message[i]) > max_lenght:
                max_lenght == len(message[i])

    text = ''
    for i in range(0, max_lenght):
        text = text + character
    Message(text)

    for i in range(0, num_lines):
        Message(message[i])

    Message(text)


def get_ODF_directory(SASfile):
    """
    Returns the ODF directory.

    Args:
        SAS_file: the .SAS summary file.
    
    Output: 
        directory: the ODF directory as a string.
    """

    with open (SASfile, 'r') as SAS_file:
        for line in SAS_file:
            if 'PATH' in line:
                directory = line[5:]

    return directory


def check_for_house_keeping_files(list_of_files):
    """
    Raises exceptions if there are missing periodic or non periodic files.

    Args:
        list_of_files: the total list of the files from the input directory.
    
    Output:
        (periodic_hk_filename, non_periodic_hk_filename): the house keeping files as a tuple of strings.
    """

    print('Checking for house keeping files...')
    periodic_file_flag = 0
    non_periodic_file_flag = 0

    for file in list_of_files:
        if file.endswith('PEH.FIT') and 'OM' in file:
            periodic_hk_filename  = file
            periodic_file_flag = 1
        if file.endswith('NPH.FIT') and 'OM' in file:
            non_periodic_file_flag = 1
            non_periodic_hk_filename = file

    if periodic_file_flag == 0:
        message = "The ODF does NOT contain a Periodic Housekeeping file. Please insert into the ODF."
        Message(message)
        raise OSError('Task Failure. Incomplete ODF.')
    else:
        Message(    "ODF contains a Periodic Housekeeping file.")

    if non_periodic_file_flag == 0:
        message = "The ODF does NOT contain a Non Periodic Housekeeping file. Please insert into the ODF."
        Message(message)
        raise OSError('Task Failure. Incomplete ODF.')
    else:
        Message('ODF contains a non periodic housekeeping file.')

    return (periodic_hk_filename, non_periodic_hk_filename)


def set_up_directory_paths():
    """
    Prepares some basic directories into global variables, if not already present.
    
    
    Output:
        (has_ff, ff_name, inp_dir, out_dir): tuple containing the flat field flag and filename and the paths of the input and output directories.
    """

    global inp_dir, out_dir
    has_ff = 0
    ff_dir = os.environ['SAS_DIR'] + '/packages'
    working_dir = os.getcwd()
    if os.path.isdir(ff_dir):
        ff_name = ff_dir + "/omgchain/test/superflat_withoutLED.fit"
        if os.path.isdir(ff_name):
            print('Flat field file found.')
            has_ff = 1
    else:
        ff_name = ''

    if inpdirectory == '':
        if not 'SAS_ODF' in os.environ or os.environ['SAS_ODF'] == '':
            inp_dir = os.getcwd()
            os.environ['SAS_ODF'] = inp_dir
            SAS_file = glob.glob('*.SAS')[0]

        else:
            pos = os.environ['SAS_ODF'].index('SAS')
            if pos > 0:
                SAS_file = os.environ['SAS_ODF']
                inp_dir = get_ODF_directory(SAS_file).rstrip()
            else:
                inp_dir = os.environ['SAS_ODF'].rstrip()
                SAS_file = glob.glob(inp_dir + '*.SAS')[0]
    else:
        if os.path.isdir(inpdirectory):
            inp_dir = inpdirectory
        else:
            os.mkdir(inpdirectory)
            inp_dir = inpdirectory

    if outdirectory != '':
        if os.path.isdir(outdirectory):
            out_dir = outdirectory
        else:
            os.mkdir(outdirectory)
            out_dir = outdirectory
    else:
        out_dir = os.getcwd()


    return(has_ff, ff_name, inp_dir, out_dir)


def process_windows(orb_key, obs_key, exp_key, filter_id, index, mixed_win, mixed_wx0, mixed_wy0, mixed_wdx, mixed_wdy, mixed_proc):
    """
    Don't mistake this with process_window. Evaluates the windows that are in each exposure.
    Args:
        orb_key: current orbital key.
        obs_key: current orbit key.
        exp_key: current exposure key.
        filter_id: the id of the filter for the exposure.'
        index: value for index taken from the exposure.
        mixed_win: the mixed value for the window.
        mixed_wx0, mixed_wy0, mixed_wdx, mixed_wdy, mixed_proc: mixed values taken from the fits from the exposure.
    """

    win = mixed_win
    wx0 = mixed_wx0
    wy0 = mixed_wy0
    wdx = mixed_wdx
    wdy = mixed_wdy
    proc = mixed_proc
    comb_list = dict()

    message_filter = 'filter value does not correspond to a grism'

    if filter_id == 200:
        grism_id = "Grism 2 (visual)"
        message_filter = "Filter value corresponds to {}".format(grism_id)

    if filter_id == 1000:
        grism_id = "Grism 1 (UV)"
        message_filter = "Filter value corresponds to {}".format(grism_id)

    Message(message_filter)

    i = 0
    while i < index:
        if proc[i] >= 0:
            wx_edge = wx0[i]
            dx_edge = wdx[i]
            wy_edge = wy0[i]
            dy_edge = wdy[i]
            message_window = "Window {} will be processed".format(win[i])
            Message(message_window)

            icomb = 0
            comb_list = list(win.values())

            # Combine images only if the parameter $combine is yes
            if combine:
                j = i
                Message('Combine = yes')
                while j < (index - 1):
                    j = j + 1
                    if wx0[j] == (wx_edge + dx_edge) and wy0[j] == wy_edge and wdy[j] == dy_edge:
                        icomb = icomb + 1
                        comb_list[icomb] = win[j]
                        wx_edge = wx_edge + dx_edge
                        dx_edge = wdx[j]
                        wy_edge = wy0[j]
                        dy_edge = wdy[j]
                        proc[j] = -1

                k = 0
                # Check if the input files exist:
                while k <= icomb:
                    f = orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[k] + "*IMI*"
                    if fnmatch.filter(list_of_files, f):
                        input_image_filename = fnmatch.filter(list_of_files, f)[0]
                    k = k + 1

            k = len(comb_list)
            process_window(orb_key, obs_key, exp_key, comb_list)

        else:
            Message("The window {} is in the combined list and will not be processed ".format(win[i]))
        i = i + 1


def process_window(orb_key, obs_key, exp_key, comb_list):
    """
    Processes a single window of the observation.

    Args:
        orb_key: the current orbital key.
        obs_key: the current observation key.
        exp_key: the current exposition key.
        comb_list: the combination list for windoes.
    """

    exposure_image_list = []
    n_win = len(comb_list)
    combined_file_name = "g" + obs_key + "OMS" + exp_key + "CIMAGE0000.FIT"
    mode_symbol = 'S'
    combined_image_was_produced = 0

    Message('Number of sub-windows found: {}'.format(n_win))

    if combine and n_win == 4:
        k = 0
        while k <= n_win:
            f = orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[k] + "*IMI*"
            if fnmatch.filter(list_of_files, f):
                exposure_image_list.append(inp_dir + '/' + fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[k] + '*IMI*')[0])
                mode_symbol = fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[k] + '*IMI*')[0][18]
                combined_filename = 'g' + obs_key + 'OM' + mode_symbol + exp_key + 'CIMAGE0000.FIT'
                k = k + 1
        
        #parsing the list into a string...:
        exposure_image_list = str(exposure_image_list).strip('[]')
        exposure_image_list.replace(',', ' ')

        Message("... Combining sub-windows (Engineering-2 Mode data) ... ")
        highlighted_message("*", "... omcomb ...")

        cmd = "imagesets=\"" + exposure_image_list + "\"" + " outset=\"" + out_directory + '/' + combined_filename + "\""
        print('omcomb arguments: {}'.format(cmd))

        if subprocess.Popen('omcomb {}'.format(cmd), shell = True).wait():
            raise OSError('Failed while running omcomb.')

        Message('... Produced a combined image {}'.format(combined_filename))
        combined_image_was_produced = 1

    Message('... Running Tracking tasks ... ')
    i_win = 0


    while i_win < len(comb_list):
        if fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[i_win] + '*IMI*'):
            print(comb_list)
            highlighted_message('-', 'Window {}'.format(comb_list[i_win]))

            if combine and combined_image_was_produced:
                input_image_filename = out_directory + '/' + combined_filename
            else:
                input_image_filename = inp_dir + '/' + fnmatch.filter(list_of_files, orb_key + '*' + obs_key + '*' + exp_key + '*' + comb_list[i_win] + '*IMI*')[0]

            Message('Image file name: {}'.format(input_image_filename))

            filter_id = pyutils.get_key_word(input_image_filename, 'FILTER')

            if filter_id == 200 or filter_id == 1000:
                if filter_id == 200:
                    grism_id = 'Grism 2 (visual)'
                    Message('Filter value corresponds to {}'.format(grism_id))
                elif filter_id == 1000:
                    grism_id = 'Grism 1 (UV)'
                    Message('Filter value corresponds to {}'.format(grism_id))
                else:
                    Message('Filter value does not correspond to a grism.')


                raw_image = 'g' + input_image_filename
                s = mode_symbol

                out_flat_filename = "g" + obs_key + "OM" + s + exp_key + "FLAFLD" + comb_list[i_win][1] + "000.FIT"
                osw_list_intermediary_detect_filename = "p" + obs_key + "OM" + s + exp_key + "SWSRLI" + comb_list[i_win][1] + "000.FIT"
                second_osw_list_intermediary_detect_filename = "p" + obs_key + "OM" + s + exp_key + "SWSRLI" + comb_list[i_win][1] + "001.FIT"
                image_pps_product_filename = "p" + obs_key + "OM" + s + exp_key + "IMAGE_" + comb_list[i_win][1] + "000.FIT"
                intermediate_image_filename = "g" + obs_key + "OM" + s + exp_key + "IMAGEI" + comb_list[i_win][1] + "000.FIT"
                detectorCoordImageFileName = "g" + obs_key + "OM" + s + exp_key + "IMAGE_" + comb_list[i_win][1] + "000.FIT"
                skyCoordImageFileName = "g" + obs_key + "OM" + s + exp_key + "SIMAGE" + comb_list[i_win][1] + "000.FIT"
                rotatedImageFileName = "p" + obs_key + "OM" + s + exp_key + "RIMAGE" + comb_list[i_win][1] + "000.FIT"
                smoothRotatedImageFileName = "s" + obs_key + "OM" + s + exp_key + "IMAGE_" + comb_list[i_win][1] + "000.FIT"
                undistImageFileName = "u" + obs_key + "OM" + s + exp_key + "IMAGE_" + comb_list[i_win][1] + "000.FIT"

                unscatteredImageFileName = "g" + obs_key + "OM" + s + exp_key + "RIMNSC" + comb_list[i_win][1] + "000.FIT"
                bkgImageFileName = "g" + obs_key + "OM" + s + exp_key + "RIMBKG" + comb_list[i_win][1] + "000.FIT"

                modulo_8_product_filename = "g" + obs_key + "OM" + s + exp_key + "MOD8MP" + comb_list[i_win][1] + "000.FIT"
                sky_coord_pps_product_filename = "p" + obs_key + "OM" + s + exp_key + "SIMAGE" + comb_list[i_win][1] + "000.FIT"
                region_file = "p" + obs_key + "OM" + s + exp_key + "REGION" + comb_list[i_win][1] + "000.ASC"
                second_region_file = "p" + obs_key + "OM" + s + exp_key + "REGION" + comb_list[i_win][1] + "001.ASC"
                spectraRegionFileName = "p" + obs_key + "OM" + s + exp_key + "SPCREG" + comb_list[i_win][1] + "001.ASC"
                PPS_eventlist_file = "g" + obs_key + "OM" + s + exp_key + "EVLIST" + comb_list[i_win][1] + "000.FIT"

                spectraRegionPlotName = "p" + obs_key + "OM" + s + exp_key + "SPCREG" + comb_list[i_win][1] + "001.PS"
                spectraRegionPDF = "p" + obs_key + "OM" + s + exp_key + "SPCREG" + comb_list[i_win][1] + "001.PDF"
                # temporary files for testing purposes
                background_output = "tmp_background" + obs_key + "OM" + s + exp_key + "BACKGR" + comb_list[i_win][1] + ".FIT"
                signifimage_output = "tmp_signifimage" + obs_key + "OM" + s + exp_key + "SIGNIF" + comb_list[i_win][1] + ".FIT"
                grismOutFileName="p" + obs_key + "OM" + s + exp_key + "SPECTR" + comb_list[i_win][1] + "000.FIT"

                if extract_field_spectra:
                    Message("Available spectra of the field objects will be extracted (by request)")
                    out_spectra_list_filename = "p" + obs_key + "OM" + s + exp_key + "SPECLI" + comb_list[i_win][1] + "000.FIT"
                else:
                    Message('Extraction of the target object spectrum (no field spectra will be extracted)')
                    out_spectra_list_filename = "p" + obs_key + "OM" + s + exp_key + "SPECLI" + comb_list[i_win][1] + "000.FIT"

                Message('Running grism mode tasks...')

                highlighted_message('*', 'omgprep')

                arg_list = "set={}".format(input_image_filename) + " nphset={}/{}".format(inp_dir, non_periodic_hk_filename) +\
                    " pehset={}/{}".format(inp_dir, periodic_hk_filename) +\
                    " wdxset={}/{}".format(inp_dir, window_data_filename) +\
                    " modeset=4" + " outset={}/{}".format(out_dir, intermediate_image_filename)

                Message("omprep {}".format(arg_list))

                if os.system('omprep {}'.format(arg_list)):
                    highlighted_message('*', 'omprep has detected an error- this observation will not be processed')
                    return 'Error in omprep'

                highlighted_message('*', ' ... ommodmap ...')
                arg_list = "set={}/{}".format(out_dir, intermediate_image_filename) +\
                    " flatset={}".format(flat_field_filename) + " mod8product=yes" +\
                    " mod8set={}/{}".format(out_dir, modulo_8_product_filename) +\
                    " outset={}/{}".format(out_dir, detectorCoordImageFileName) +\
                    " outflatset={}/{}".format(out_dir, out_flat_filename) +\
                    " nsig={}".format(ommodmap_nsig) + " nbox={}".format(ommodmap_nbox) +\
                    " mod8correction={}".format(mod8correction)

                Message('ommodmap {}'.format(arg_list))
                if subprocess.Popen('ommodmap {}'.format(arg_list), shell = True).wait():
                    return 'Error while running ommodmap'


                highlighted_message('*', '... omgprep ...')
                omgprep_usecat = 'F'

                print("removeScatteredLight= {}\n".format(removeScatteredLight))
                if removeScatteredLight:
                    arg_list = "set={}/{}".format(out_dir, detectorCoordImageFileName) +\
                        " outset={}/{}".format(out_dir, rotatedImageFileName) +\
                        " undistset={}/{}".format(out_dir, undistImageFileName) +\
                        " removescatteredlight={}".format(removeScatteredLight) +\
                        " backgroundset={}/{}".format(out_dir, bkgImageFileName)
                else:
                    arg_list = "set={}/{}".format(out_dir, detectorCoordImageFileName) +\
                        " outset={}/{}".format(out_dir, rotatedImageFileName) +\
                        " undistset={}/{}".format(out_dir, undistImageFileName)

                Message('omgprep {}'.format(arg_list))
                if subprocess.Popen('omgprep {}'.format(arg_list), shell = True).wait():
                    highlighted_message('*', 'omgprep has found an error.')
                    return 'Error'

                level_image_file = 'LEVEL.FIT'

                highlighted_message('*', '... omdetect ...')
                arg_list = "nsigma={}".format(nsigma) +\
                    " set={}/{}".format(out_dir, rotatedImageFileName) +\
                    " regionfile={}/{}".format(out_dir, second_region_file) +\
                    " outset={}/{}".format(out_dir, second_osw_list_intermediary_detect_filename)

                Message('omdetect {}'.format(arg_list))
                if subprocess.Popen('omdetect {}'.format(arg_list), shell = True).wait():
                    return 'Error while running omdetect.'

                n_source = 0

                with open(out_dir + '/' + second_region_file) as region_file:
                    for line in region_file:
                        n_source = n_source + 1

                Message('Number of detected sources: {}'.format(n_source))

                highlighted_message('*', '... omatt ...')

                arg_list = "set=" +  out_dir + '/' + rotatedImageFileName +\
                    " sourcelistset=" +  out_dir + '/' + second_osw_list_intermediary_detect_filename +\
                    " ppsoswset=" + out_dir + '/' + skyCoordImageFileName + " usecat=F"

                Message('omatt {}'.format(arg_list))
                if subprocess.Popen('omatt {}'.format(arg_list), shell = True).wait():
                    return 'Error while running omatt'

                highlighted_message('*', '... omgrism ...')

                arg_list = "set={}/{}".format(out_dir, rotatedImageFileName) +\
                    " sourcelistset={}/{}".format(out_dir, second_osw_list_intermediary_detect_filename) +\
                    " outset={}/{}".format(out_dir, grismOutFileName) +\
                    " bkgoffsetleft={}".format(bkgOffsetLeft) +\
                    " bkgwidthleft={}".format(bkgWidthLeft) + " bkgoffsetright={}".format(bkgOffsetRight) +\
                    " bkgwidthright={}".format(bkgWidthRight) + " spectrumhalfwidth={}".format(spectrumHalfWidth) +\
                    " spectrumsmoothlength={}".format(spectrumsmoothlength) +\
                    " extractionmode={}".format(extractionmode) + " extractfieldspectra={}".format(extract_field_spectra) +\
                    " regionfile={}/{}".format(out_dir, second_region_file) + " spectraregionfile={}/{}".format(out_dir, spectraRegionFileName) +\
                    " outspectralistset={}".format(out_spectra_list_filename) + " addedregionfile={}".format(addedRegionFile)

                Message('omgrism {}'.format(arg_list))

                if subprocess.Popen('omgrism {}'.format(arg_list), shell = True).wait():
                    return 'Error while running omgrism.'

                spectrum_plot_file0 = "g" + obs_key + "OM" + s + exp_key + "SPECTR" + comb_list[i_win][1] + "000.PS"
                spectrum_PDF_file0 = "p" + obs_key + "OM" + s + exp_key + "SPECTR" + comb_list[i_win][1] + "000.PDF"

                highlighted_message('*', '... omgrismplot ...')
                Message('OMGRISM spectrum pps file: {}'.format(grismOutFileName))

                if os.path.exists(out_dir + '/' + grismOutFileName):
                    plotBinSize = 1
                    os.environ['PGPLOT_TYPE'] = 'ps'

                    arg_list = "set=" + out_dir + '/' + grismOutFileName +\
                        " scalebkgplot={}".format(scaleBkgPlot) + " binsize={}".format(plotBinSize) +\
                        " plotflux={}".format(plotFlux) +\
                        " plotfile=t.ps" + " spectraregionfile=" + out_dir + '/' + spectraRegionFileName +\
                        " regionplotfile=r.ps" + " rotatedimageset=" + out_dir + '/' + rotatedImageFileName

                    Message('omgrismplot {}'.format(arg_list))

                    if subprocess.Popen('omgrismplot {}'.format(arg_list), shell = True).wait():
                        return 'Error in omgrismplot'

                    os.rename('t.ps', out_dir + '/' + spectrum_plot_file0)
                    os.rename('r.ps', out_dir + '/' + spectraRegionPlotName)

                    print("spectraRegionFileName={}/{} \n".format(out_dir, spectraRegionFileName))
                    if os.path.isfile(out_dir + '/' + spectrum_plot_file0):
                        Message('Converting the spectrum PostScript file to PDF')
                        if subprocess.Popen('ps2pdf {}/{} {}/{}'.format(out_dir, spectrum_plot_file0, out_dir, spectraRegionPDF), shell = True).wait():
                            return 'Error while converting to pdf.'

                    else:
                        Message("The required spectrum PostScript file is missing")

                    if os.path.exists(out_dir + '/' + spectraRegionPlotName):
                        Message("Converting the spectrum region PostScript file to PDF")
                        if subprocess.Popen('ps2pdf {}/{} {}/{}'.format(out_dir, spectraRegionPlotName, out_dir, spectraRegionPDF), shell = True).wait():
                            return 'Error while converting to pdf.'
                    else:
                        Message("The spectrum region PostScript file is missing")
                else:
                    Message("File {} does not exist: no plot produced".format(grismOutFileName))
        else:
            Message('Image file for this window does not exist.')

        i_win = i_win + 1


def omgchain():
    """
    Main process for pyomgchain. Will start the whole chain.
    """

    py_version = 0.1

    if 'SAS_VERBOSITY' in os.environ:
        SAS_verbosity = os.environ['SAS_VERBOSITY']
    else:
        SAS_verbosity = '5'
        os.environ['SAS_VERBOSITY'] = '5'

    if int(SAS_verbosity) > 7:
        os.environ['SAS_VERBOSITY'] = '5'

    has_ff, ff_name, inp_dir, out_dir = set_up_directory_paths()

    inp_dir = inp_dir.rstrip()
    out_dir = out_dir.rstrip()

    periodic_file_flag = 0
    non_periodic_file_flag = 0
    flat_field_file_flag = 0

    task_name = 'OMGCHAIN'
    date = pyutils.date_time()
    Message(date)

    global ommodmap_nbox, ommodmap_nsig, spectrum_length_U
    global spectrum_length_V, src2_spectrum_U, src2_spectrum_V
    global image_smooth_box_idth, image_smooth_box_height
    ommodmap_nsig = 6
    ommodmap_nbox = 16

    spectrum_length_U = 1000.0
    spectrum_length_V = 400.0
    spectrumHalfWidth = -8.0

    src2_spectrum_U = 1100.0
    src2_spectrum_V = 800.0
    image_smooth_box_idth = 10.0
    image_smooth_box_height = 10.0

    create = 'Running SAS task {} V{} {}'.format(task_name, py_version, date)
    text1 = ' Input directory: {}'.format(inp_dir)
    text2 = ' Output directory: {}'.format(out_dir)
    highlighted_message('*', create + '  ' + comment + '  ' + text1 + ' ' + text2)

    if combine:
        Message("Engineering-2 Mode sub-windows (if they exist) will be combined")
    else:
        Message("Engineering-2 Mode windows will not be combined")

    global list_of_files

    list_of_files = glob.glob(inp_dir + '/*FIT')
    for i in range(0, len(list_of_files)):
        list_of_files[i] = list_of_files[i].replace(inp_dir + '/', '')

    global periodic_hk_filename
    global non_periodic_hk_filename

    periodic_hk_filename, non_periodic_hk_filename = check_for_house_keeping_files(list_of_files)

    global orb_list
    global obs_list
    global exp_list
    global win_list

    orb_list, obs_list, exp_list, win_list = fill_orb_obs_exp_dict(list_of_files)

    for orb_key in orb_list.keys():
        process_orbit(orb_key, has_ff, ff_name)
# end of omgchain


def fill_orb_obs_exp_dict(list_of_files):
    """
    Fill several dictionaries containing info of the orbit, the observation,
    the exposure and the window.
    Args:
        list_of_files: the list of FIT files to evaluate.
    
    Ouput: 
        orb_list, obs_list, exp_list, win_list: (orbit dictionary, obsid dictionary, exposure dicitonary, window dictionary).
    """

    orb_list = dict()
    obs_list = dict()
    exp_list = dict()
    win_list = dict()

    for i in list_of_files:

        if i.endswith('IMI.FIT'):
            print(i)
            orbit = i[0:4]
            obs = i[5:15]
            expo = i[19:22]
            win = i[22:24]

            orb_list.update({i[0:4] : i[0:4]})
            if obs in obs_list:
                if orbit not in obs_list[obs]:
                    obs_list[obs].append(orbit)
            else:
                obs_list.update({obs : [orbit]})
            if expo in exp_list:
                if obs not in exp_list[expo]:
                    exp_list[expo].append(obs)
            else:
                exp_list.update({expo : [obs]})
            if win in win_list:
                if expo not in win_list[win]:
                    win_list[win].append(expo)
            else:
                win_list.update({win : [expo]})

    return (orb_list, obs_list, exp_list, win_list)


def run(iparsdic):
    
    print(f'Executing {__file__} {iparsdic}')

    start = time.time()
    # gather params...
    global combine
    
    if iparsdic['combine'] == 'yes':
        combine = True
    else:
        combine = False

    global mod8correction, spectrumHalfWidth, spectrumsmoothlength, plot_bin_size, extract_field_spectra, extractionmode
    
    extractionmode = iparsdic['extractionmode']
    mod8correction = iparsdic['mod8correction']
    spectrumHalfWidth = iparsdic['spectrumhalfwidth']
    plot_bin_size = iparsdic['plotbinsize']
    extract_field_spectra = iparsdic['extractfieldspectra']

    global bkgOffsetLeft, bkgWidthLeft, bkgWidthRight, bkgOffsetRight
    spectrumsmoothlength = iparsdic['spectrumsmoothlength']
    bkgOffsetLeft = iparsdic['bkgoffsetleft']
    bkgWidthLeft = iparsdic['bkgwidthleft']
    bkgWidthRight = iparsdic['bkgwidthright']
    bkgOffsetRight = iparsdic['bkgoffsetright']
    
    global addedRegionFile, scaleBkgPlot, plotFlux, removeScatteredLight, nsigma
    plotFlux = iparsdic['plotflux']
    scaleBkgPlot = iparsdic['scalebkgplot']
    addedRegionFile = iparsdic['addedregionfile']
    removeScatteredLight = iparsdic['removescatteredlight']
    
    if removeScatteredLight == 'yes' or removeScatteredLight == 1:
        removeScatteredLight = True
    else:
        removeScatteredLight = False

    nsigma = iparsdic['nsigma']

    global comment, inpdirectory, outdirectory
    inpdirectory = iparsdic['inpdirectory']
    outdirectory = iparsdic['outdirectory']
    comment = iparsdic['comment']


    omgchain()

    stop = time.time()

    highlighted_message('*', 'pyomgchain ended. Total time: {} seconds.'.format(stop - start))
