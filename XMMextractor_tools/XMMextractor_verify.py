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

# XMMextractor_verify


import numpy as np
import os
import sys
import glob
from pysas.logger import TaskLogger as TL
from pysas.pyutils import pyutils



############################################
############## EPIC images ################
###########################################
def test_existance_epic_clean_image(obs, expo,type=None):
    '''
    Checks and retunr EPIC gti filetered full image
    Args:
       obs: observation objects
       exposure: exposure identifier
    '''
    
    EPNlog = TL(os.path.join(obs.working_dir, 'EPNlog'))
    wd = os.getcwd()
    try:
        os.chdir(obs.images_dir)
    except FileNotFoundError:
        return (0, 'No images directory')
    
    if type == 'full':
        inst = None
        if  expo[0:2].lower() == 'pn':
            inst = 'EPN'
        elif expo[0:2].lower() == 'm1':
            inst = 'EMOS1'
        elif expo[0:2].lower() == 'm2':
            inst = 'EMOS2'

        image_file =  glob.glob('*'+inst + '_' + expo[2:6] + '_Imaging_Image.ds')
    else:
        image_file =  glob.glob( expo[0:2].lower() + '_' + expo[2:6] + '_IMAGING_image_full.fits')

    os.chdir(wd)
    if len(image_file) != 1:
        EPNlog.log('info', '#>  Image file not found')
        return(0, 'No file')
    else:
        return(True, obs.images_dir + '/' + image_file[0])

############################################
################ EPN files #################
############################################

def test_existance_pn_eventfiles(obs, exposure =None,type='EVT'):
    '''
    Checks if for a given expid exist event lists.
    
    Args:
        obs: the observation object.
        exposure: an exposure.
    
    Output:
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''

    EPNlog = TL(os.path.join(obs.working_dir, 'EPNlog'))

    wd = os.getcwd()

    expid = ''
    if exposure is not None:
        if isinstance(exposure, str):
            expid = exposure[-4:]
        else:
            expid = exposure.expid[-4:]

    
    EPIC_evlist = ""
    if type == 'EVT':
        if not os.getcwd().endswith('EPN'):
            try:
                os.chdir(obs.EPN_dir)
            except FileNotFoundError:
                return (0, 'No EPN directory')

        EPIC_evlist = glob.glob('*EPN*' + expid + '*ImagingEvts.ds')

    elif type == 'CLEAN':
        if not os.getcwd().endswith('GTI'):
            try:
                os.chdir(obs.GTI_dir)
            except FileNotFoundError:
                return (0, 'No EPN directory')
        EPIC_evlist = glob.glob('*pn*' + expid + '*ImagingEvts_events_gtifiltered.fits')


    if len(EPIC_evlist) > 0:
        index = 0
        duration = []
        EPNlog.log('info', 'PN Image Event List found: {}'.format(EPIC_evlist))
        for i in EPIC_evlist:
            obj_duration = pyutils.get_key_word(i, 'DURATION', 1)
            duration.append(obj_duration)

        max_index = np.argmax(duration)
        pn_list = EPIC_evlist[max_index]
        EPNlog.log('info', 'Using event file with longest Observation Duration: {}'.format(pn_list))
        os.chdir(wd)
        if type == 'EVT':
            return(True, obs.EPN_dir + '/' + pn_list)
        else:
            return(True, obs.GTI_dir + '/' + pn_list)
    else:
        EPNlog.log('info', '#> PN Imaging Event List not found')
        os.chdir(wd)
        return(0, 'No file')


def test_existance_pn_timing_eventfiles(obs,exposure = None,type='EVT'):
    '''
    Checks if for a given expid exist timing event lists.
    
    Args:
        obs: the observation object.
        exposure: an exposure.
    
    Output: 
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''

    EPNlog = TL(os.path.join(obs.working_dir, 'EPNlog'))

    wd = os.getcwd()

    if exposure is not None:
        if isinstance(exposure, str):
            expid = exposure[-4:]
        else:
            expid = exposure.expid[-4:]

    
    EPIC_evlist = ""
    if type == 'EVT':
        if not os.getcwd().endswith('EPN'):
            try:
                os.chdir(obs.EPN_dir)
            except FileNotFoundError:
                return (0, 'No EPN directory')
            
        EPIC_evlist = glob.glob('*EPN*' + expid + '*TimingEvts.ds')

    elif type == 'CLEAN':
        if not os.getcwd().endswith('GTI'):
            try:
                os.chdir(obs.GTI_dir)
            except FileNotFoundError:
                return (0, 'No directory')
        EPIC_evlist = glob.glob(exposure+'*_events_gti*Filtered.fits')


    if len(EPIC_evlist) > 0:
        EPNlog.log('info', 'PN Timing Event List found: {}'.format(EPIC_evlist))
        
        print(EPIC_evlist[0])
        
        EPNlog.log('info', 'Using event file with longest Observation Duration: {}'.format(EPIC_evlist[0]))
        os.chdir(wd)
        if type == 'EVT':
            return(True, obs.EPN_dir + '/' + EPIC_evlist[0])
        else:
            return(True, obs.GTI_dir + '/' + EPIC_evlist[0])

    else:
        EPNlog.log('info', '#> PN Timing List not found')
        os.chdir(wd)
        return(0, 'No file')


    
#############################################
################# MOS files #################
#############################################

def test_existance_EMOS(obs, exposure,type='EVT'):
    ''' 
    Checks if for a given expid exist event lists (EMOS1).
    
    Args:
        obs: an observation object.
        exposure: an exposure.
    
    Output: 
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''

    EMOSlog = TL(os.path.join(obs.working_dir, 'EMOSlog'))

    wd = os.getcwd()
    instrument = ""
    if(exposure[0:2] == 'M1'):
        instrument = 'EMOS1'
    elif(exposure[0:2] == 'M2'):
        instrument = 'EMOS2'
    else:
        EMOSlog.log('error','Instrument not found')
        
    exp_id = exposure[2:6]
    EMOS_evlist=""
    dir=''
    if type == 'EVT':
        if not os.getcwd().endswith('EMOS'):
            try:
                os.chdir(obs.MOS_dir)
            except FileNotFoundError:
                return (0, 'No directory')
        EMOS_evlist = glob.glob('*'+instrument+'*' + exp_id + '*ImagingEvts.ds')
        dir = obs.MOS_dir
        
    if type == 'CLEAN':
        if not os.getcwd().endswith('GTI'):
            try:
                os.chdir(obs.GTI_dir)
            except FileNotFoundError:
                return (0, 'No directory')

        EMOS_evlist = glob.glob('*'+exposure[0:2].lower() + '*'+ exp_id + '*_events_gti*Filtered.fits')
        dir = obs.GTI_dir        
        

        
    if len(EMOS_evlist) > 0:
        index = 0
        duration = []
        EMOSlog.log('info', '#> {} Image Event List found: {}'.format(instrument,EMOS_evlist))
        for i in EMOS_evlist:
            obj_duration = pyutils.get_key_word(i, 'DURATION', 1)
            duration.append(obj_duration)

        max_index = np.argmax(duration)
        EMOS_list = EMOS_evlist[max_index]

        EMOSlog.log('info', '      Using event file with longest Observation Duration: {}'.format(EMOS_list))
        os.chdir(wd)
        return(1, dir + '/' + EMOS_list)
    else:
        EMOSlog.log('info', '#> EMOS1 Imaging Event List not found')
        os.chdir(wd)
        return(0, 'No file')


def test_existance_EMOS_timing(obs, exposure,type='EVT'):
    ''' 
    Checks if for a given expid exist timing event lists (EMOS)
    
    Args:
        obs: an observation object.
        exposure: an exposure.
    
    Output: 
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''
    
    EMOSlog = TL(os.path.join(obs.working_dir, 'EMOSlog'))
    
    wd = os.getcwd()

    instrument = ""
    if(exposure[0:2] == 'M1'):
        instrument = 'EMOS1'
    elif(exposure[0:2] == 'M2'):
        instrument = 'EMOS2'
    else:
        EMOSlog.log('error','Instrument not found')
        
    exp_id = exposure[2:6]
    EMOS_timeevlist=""
    dir=''
    if type == 'EVT':
        if not os.getcwd().endswith('EMOS'):
            try:
                os.chdir(obs.MOS_dir)
            except FileNotFoundError:
                return (0, 'No directory')
        EMOS_timeevlist = glob.glob('*'+instrument+'*' + exp_id + '*TimingEvts.ds')
        dir = obs.MOS_dir

    if type == 'CLEAN':   
        if not os.getcwd().endswith('GTI'):
            try:
                os.chdir(obs.GTI_dir)
            except FileNotFoundError:
                return (0, 'No directory')
        EMOS_timeevlist = glob.glob(exposure+ '*_events_gti*Filtered.fits')
        dir = obs.GTI_dir

    if len(EMOS_timeevlist) > 0:
        index = 0
        duration = []
        EMOSlog.log('info', '#> {} timing Event List found: {}'.format(instrument,EMOS_timeevlist))
        for i in EMOS_timeevlist:
            obj_duration = pyutils.get_key_word(i, 'DURATION', 1)
            duration.append(obj_duration)

        max_index = np.argmax(duration)

        EMOS_timelist = EMOS_timeevlist[max_index]

        EMOSlog.log('info', '      Using event file with longest Observation Duration: {}'.format(EMOS_timelist))
        os.chdir(wd)
        return(1, dir + '/' + EMOS_timelist)
    else:
        EMOSlog.log('info', '#> EMOS1 Timing Event List not found')
        os.chdir(wd)
        return(0, 'No file')


#############################################
################# RGS files #################
#############################################

def test_existance_RGS(obs,expo):
    '''
    Checks if exist event lists (RGS1).

    Args:
        obs: the observation object.
        expo: RGS instrument and exposures

    Output:
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''

    RGSlog = TL(os.path.join(obs.working_dir, 'RGSlog'))

        
    if not os.getcwd().endswith('RGS'):
        try:
            os.chdir(obs.RGS_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    RGS_evlist = glob.glob('*'+expo+'*EVENLI0000.FIT')
    if len(RGS_evlist) > 0:
        RGSlog.log('debug', '   #> RGS1 Event List found')
        RGSlog.log('info', RGS_evlist)
        return (1, os.getcwd() + '/' + RGS_evlist[0])
    else:
        RGSlog.log('info', '#> RGS1 Event List not found')
        return(0, 'No file')


def test_existance_SRC_RGS(obs,expo):
    '''
    Checks if exist source files (RGS1).

    Args:
        obs: an observation object.
        expo: instrument plus exposure id
    
    Output:
        tuple. First element one (file) or zero (no file). Second element,
    a string with the file or 'No file'.
    '''

    RGSlog = TL(os.path.join(obs.working_dir, 'RGSlog'))

    if not os.getcwd().endswith('RGS'):
        try:
            os.chdir(obs.RGS_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    RGS_srclist = glob.glob('*'+expo+'*SRCLI_0000.FIT')
    if len(RGS_srclist) > 0:
        RGSlog.log('info', '   #> RGS1 Source List found')
        RGSlog.log('info', RGS_srclist)
        return (1, os.getcwd() + '/' + RGS_srclist[0])
    else:
        RGSlog.log('info', '#> RGS Source List not found')
        return(0, 'No file')




#############################################
################# OM  files #################
#############################################

def test_OM_event_files(obs):
    '''
    Checks for event list produced by omichain.

    Output:
        a tuple, with 0 or 1 (not found, found) and 'No file' or the name
    of the file.
    '''

    omlog = TL(os.path.join(obs.working_dir, 'OMlog'))

    if not os.getcwd().endswith('OM'):
        try:
            os.chdir(obs.OM_dir)
        except FileNotFoundError:
            return (0, 'No OM directory')

    OM_event_list = glob.glob('P*OM*SIMAGE*.FIT')
    if len(OM_event_list) > 0:
        omlog.log('info', '#> OM Event List found [omichain]')
        omlog.log('info', OM_event_list)
        return (1, os.path.join(obs.OM_dir, OM_event_list[0]))
        #if len(OM_event_list) > 1:
        #    omlog.log('info', 'Using only {}'.format(OM_event_list[0]))
        #    OM_event = OM_event_list[0]
        #    return (1, os.getcwd() + '/' + OM_event)
    else:
        omlog.log('info', '#> OM Event List not found for omichain processing.')
        return (0, 'No file')


def test_OMF_event_files(obs):
    '''
    Checks for event list produced by omfchain.

    Output:
        a tuple, with 0 or 1 (not found, found) and 'No file' or the name
    of the file.
    '''

    omlog = TL(os.path.join(obs.working_dir, 'OMlog'))

    if not os.getcwd().endswith('OM'):
        try:
            os.chdir(obs.OM_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    OM_event_list = glob.glob('*OM*EVLIST*.FIT')
    if len(OM_event_list) > 0:
        omlog.log('info', '#> OM Event List found [omfchain]')
        omlog.log('info', OM_event_list)
        return (1, os.path.join(obs.OM_dir, OM_event_list[0]))
        #if len(OM_event_list) > 1:
        #    mlog.log('info', 'Using only {}'.format(OM_event_list[0]))
        #    OM_event = OM_event_list[0]
        #    return (1, os.getcwd() + '/' + OM_event)
    else:
        omlog.log('info', '#> OM Event List not found for omfchain processing.')
        return (0, 'No file')


def test_OMG_event_files(obs):
    '''
    Checks for event list produced by omgchain.

    Output:
        a tuple, with 0 or 1 (not found, found) and 'No file' or the name
    of the file.
    '''

    omlog = TL(os.path.join(obs.working_dir, 'OMlog'))

    if not os.getcwd().endswith('OM'):
        try:
            os.chdir(obs.OM_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    OM_event_list = glob.glob('p*OM*RIMAGE*.FIT')
    if len(OM_event_list) > 0:
        omlog.log('info', '#> OM Event List found [omgchain]')
        omlog.log('info', OM_event_list)
        return (1, os.path.join(obs.OM_dir, OM_event_list[0]))
        #if len(OM_event_list) > 1:
        #    xmmlog.info('    Using only {}'.format(OM_event_list[0]))
        #    OM_event = OM_event_list[0]
        #    return (1, os.getcwd() + '/' + OM_event)
    else:
        omlog.log('info','  #> OM Event List not found for omgchain processing.')
        return (0, 'No file')


def test_OMSRC_files(obs):
    '''
    Checks for Source files.

    Output:
        a tuple, with 0 or 1 (not found, found) and 'No file' or the name
    of the file.
    '''

    omlog = TL(os.path.join(obs.working_dir, 'OMlog'))

    if not os.getcwd().endswith('OM'):
        try:
            os.chdir(obs.OM_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    OM_event_list = glob.glob('*P*OM*SRLI*.FIT')
    if len(OM_event_list) > 0:
        omlog.log('info', '#> OM Source List found')
        omlog.log('info', OM_event_list)
        return (1, os.path.join(obs.OM_dir, OM_event_list[0]))
        #if len(OM_event_list) > 1:
        #    omlog.log('    Using only {}'.format(OM_event_list[0]))
        #    OM_event = OM_event_list[0]
        #return (1, os.getcwd() + '/' + OM_event)
    else:
        omlog.log('info', '   #> OM Source List not found.')
        return (0, 'No file')


def test_OMSRCCombo_files(obs):
    '''
    Checks for Source combo files.

    Output:
        a tuple, with 0 or 1 (not found, found) and 'No file' or the name
    of the file.
    '''
    omlog = TL(os.path.join(obs.working_dir, 'OMlog'))

    if not os.getcwd().endswith('OM'):
        try:
            os.chdir(obs.OM_dir)
        except FileNotFoundError:
            return (0, 'No directory')

    OM_event_list = glob.glob('*P*OMCOMBOBSMLI*.FIT')
    if len(OM_event_list) > 0:
        omlog.log('info', '#> OM Source Combo List found')
        omlog.log('info', OM_event_list)

        if len(OM_event_list) > 1:
            omlog.log('info', 'Using only {}'.format(OM_event_list[0]))
            OM_event = OM_event_list[0]
            return (1, os.path.join(obs.OM_dir, OM_event))
            #return (1, os.getcwd() + '/' + OM_event)
        else:
            OM_event = OM_event_list[0]
            omlog.log('info', 'Using {}'.format(OM_event))
            return (1, os.path.join(obs.OM_dir, OM_event))
            #return (1, os.getcwd() + '/' + OM_event)
    else:
        omlog.log('info', '#> OM Source Combo List not found.')
        return (0, 'No file')



#############################################
############## Spectra   files ##############
#############################################


def check_spectra_files(dir,expo):
    '''
    Check for the existence of EPIC spectra files.
    
    Args:
        dir: spectra directory
        expo: exposure object

    Output: 
        1 if EPIC file is found, 0 otherwise.
    '''
    
    inst = None
    if  expo[0:2].lower() == 'pn':
        inst = 'EPN'
    elif expo[0:2].lower() == 'm1':
        inst = 'EMOS1'
    elif expo[0:2].lower() == 'm2':
        inst = 'EMOS2'

    srcfile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*source_spectrum.fits')
    bkgfile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*background_spectrum.fits')
    arffile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*.arf')    
    rmffile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*.rmf')
    
    if len(srcfile) != 0 and  len(bkgfile) != 0 and len(arffile) != 0 and len(rmffile) != 0 :
        return (1,[srcfile[0],bkgfile[0],arffile[0],rmffile[0]])
    else:
        return  (0, 'No file')


################################################
############## Lightcurve   files ##############
################################################


def check_lightcurve_files(dir,expo):
    '''
    Check for the existence of EPIC spectra files.
    
    Args:
        dir: lightcurve directory
        expo: exposure object

    Output: 
        1 if EPIC files are found, 0 otherwise.
    '''
    
    inst = None
    if  expo[0:2].lower() == 'pn':
        inst = 'EPN'
    elif expo[0:2].lower() == 'm1':
        inst = 'EMOS1'
    elif expo[0:2].lower() == 'm2':
        inst = 'EMOS2'

    srcFile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*source.lc')
    bkgFile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*bkg.lc')
    bkgSubstractedFile = glob.glob(dir + '/*'+inst+'*'+expo[2:6]+'*sourcebkgsubtracted.lc')    

    
    if len(srcFile) != 0 and  len(bkgFile) != 0 and len(bkgSubstractedFile) != 0 :
        return (1,[srcFile[0],bkgFile[0],bkgSubstractedFile[0]])
    else:
        return  (0, 'No file')


################################################
############## Lightcurve   files ##############
################################################


def check_edetect_images(dir,expo):
    '''
    Check for the existence of EPIC spectra files.
    
    Args:
        dir: lightcurve directory
        expo: exposure object

    Output: 
        1 if EPIC files are found, 0 otherwise.
    '''
    
    fullFile = glob.glob(dir + '/*'+expo[0:2].lower()+'*'+expo[2:6]+'*full.fits')
    enerFiles = glob.glob(dir + '/*'+expo[0:2].lower()+'*'+expo[2:6]+'*image_b?.fits')

    
    if len(fullFile) != 0 and  len(enerFiles) != 0  :
        return (1,[fullFile[0],enerFiles])
    else:
        return  (0, 'No file')


def check_edetect_files(dir,expo):
    '''
    Check for the existence of EPIC spectra files.
    
    Args:
        dir: lightcurve directory
        expo: exposure object

    Output: 
        1 if EPIC files are found, 0 otherwise.
    '''
    

    ebox_l_file = glob.glob(dir + '/*'+expo[0:2].lower()+'*'+expo[2:6]+'*eboxlist_l.fits')
    ebox_m_file = glob.glob(dir + '/*'+expo[0:2].lower()+'*'+expo[2:6]+'*eboxlist_m.fits')
    emllist_file = glob.glob(dir + '/*'+expo[0:2].lower()+'*'+expo[2:6]+'*emllist.fits')

    
    if len(ebox_l_file) != 0 and  len(ebox_m_file) != 0 and len(emllist_file) != 0 :
        return (1,[ebox_l_file[0],ebox_m_file[0],emllist_file[0]])
    else:
        return  (0, 'No file')
    




    
#############################################
################# GTI files #################
#############################################

def check_GTI_files(gti_dir, expo):
    '''
    Check for the existance of EPIC timing event files (non-filtered).
    
    Args:
        gti_dir: GTI directory
        instr: the instrument.
        exposure: the exposure.

    Output:
        1 if found, 0 otherwise.
        filename
    '''
    
    files = glob.glob(gti_dir + '/'+expo+'_*_*_gti*.fits')

    if len(files) != 0:
        return (1,files)
    else:
        return  (0, 'No file')

    
def check_flaring_event_files(dir,expo):
    '''
    Check for the existance of EPIC events files cleaned by flaring bkg (filtered).
    
    Args:
        dir: GTI directory
        expo: exposure identifier.

    Output:
        1 if found, 0 otherwise.
        filename
    '''
    files=  glob.glob(dir+'/'+ expo[0:2].lower() + '_' + expo[2:6] + '_ImagingEvts_events_gtiFlaringFiltered.fits')


    if len(files) != 0:
        return (1,files)
    else:
        return  (0, 'No file')
    

