# config_pysas.py
#
# Written by: Ryan Tanner
# email: ryan.tanner@nasa.gov
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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SAS. If not, see <http://www.gnu.org/licenses/>.

# config_pysas.py

"""
    The purpose of this script is so that the user can set the pySAS
    defaults 
    
        sas_dir (required)
        sas_ccfpath (required)
        data_dir (optional)
        
    Once the defaults are set by the user, SAS will automatically be 
    initialized when pySAS is imported (import pysas).

    The user can also optionally set a default data directory (data_dir)
    where observation data files (odf) will be downloaded. A separate 
    subdirectory will be made for each observation ID (obsID).
    
    The default data directory can be set or change later using the 
    function set_sas_config_option().

    For example:

        from pysas import sas_cfg
        data_path = '/path/to/data/dir/'
        sas_cfg.set_setting_and_save('data_dir', data_path)
        
    The default values for the SAS directory (sas_dir), the path to the
    calibration files (sas_ccfpath), along with 'verbosity' and 
    'suppress_warning', can also be set in the same way.

    At any time the user can reset the config file to the defaults,

        from pysas import sas_cfg
        sas_cfg.reset_to_defaults()
"""

# Standard library imports
import os, glob

# Third party imports

# Local application imports
from pysas import sas_cfg
from pysas.init_sas import initializesas
from pysas.sasutils import update_calibration_files

__version__ = 'config_pysas (config_pysas-1.1)'

verbosity        = sas_cfg.get_setting('verbosity')
suppress_warning = sas_cfg.get_setting('suppress_warning')

def run_config():

    outcomment = """

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        The purpose of this script is so the user can set the pySAS defaults 
        
            sas_dir (required)
            sas_ccfpath (required)
            data_dir (optional, recommended)
            
        Once the defaults are set by the user, SAS will automatically be 
        initialized when pySAS is imported (import pysas).

        The user can also optionally set a default data directory (data_dir)
        where observation data files (odf) will be downloaded. A separate 
        subdirectory will be made for each observation ID (obsID).
        
        The default data directory can be set or changed later using the 
        function set_setting_and_save().

        For example:

            from pysas import sas_cfg
            data_path = '/path/to/data/dir/'
            sas_cfg.set_setting_and_save('data_dir', data_path)
            
        The default values for the SAS directory (sas_dir), the path to the
        calibration files (sas_ccfpath), along with 'verbosity' and 
        'suppress_warning', can also be set in the same way.

        At any time the user can reset the config file to the defaults,

            from pysas import sas_cfg
            sas_cfg.reset_to_defaults()

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    """

    print(outcomment)

    positive = ['y','yes','ye','yeah','yea','ys','aye','yup','totally','si','oui']
    negative = ['n','no','not','nay','no way','nine','non']
    esa = ['esa','e','es','europe']
    nasa = ['nasa','n','na','nas','ns','nsa','us','usa']

    ############## Getting sas_dir ##############
    
    # If sas_dir is already set
    psas_dir = os.environ.get('SAS_DIR')

    if psas_dir:
        print('Is this the correct SAS directory?')
        print('\n    {0}\n'.format(psas_dir))
        response = input('y/n: ')
        response = response.lower()
        if response in positive:
            sas_dir = psas_dir
            print(f'Setting SAS_DIR = {sas_dir}')
        elif response in negative:
            # Ask for SAS_DIR path
            scomment = '\nPlease provide the full path to the SAS install directory (SAS_DIR).\n'
            print(scomment)
            sas_dir = input('Full path to SAS: ')
        else:
            print(f'Your response, {response}, is not recognized.')
            print(f'Try any of these: {positive}')
            print(f'-or any of these: {negative}')
            raise Exception('Input not recognized!')
    else:
        # Ask for SAS_DIR path
        scomment = '\nPlease provide the full path to the SAS install directory (SAS_DIR).\n'
        print(scomment)
        sas_dir = input('Full path to SAS: ')

    if not sas_dir.startswith('/'): sas_dir = os.path.abspath(sas_dir)
    if sas_dir.endswith('/'): sas_dir = sas_dir[:-1]
    if not os.path.exists(sas_dir):
        print(f'SAS path {sas_dir} does not exist! Check path or SAS install!')
        raise Exception(f'SAS path {sas_dir} does not exist!')

    print('\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    ############## Getting sas_ccfpath ##############

    psas_ccfpath = os.environ.get('SAS_CCFPATH')

    if psas_ccfpath:
        print('Is this the correct directory for the calibration files?')
        print('\n    {0}\n'.format(psas_ccfpath))
        response = input('y/n: ')
        response = response.lower()
        if response in positive:
            sas_ccfpath = psas_ccfpath
            print(f'Setting SAS_CCFPATH = {sas_ccfpath}')
        elif response in negative:
            # Ask for SAS_CCFPATH path
            scomment = '\nPlease provide the full path to the calibration files (SAS_CCFPATH).\n'
            print(scomment)
            sas_ccfpath = input('Full path to the calibration files: ')
        else:
            print(f'Your response, {response}, is not recognized.')
            print(f'Try any of these: {positive}')
            print(f'-or any of these: {negative}')
            raise Exception('Input not recognized!')
    else:
        scomment = """
            SAS_CCFPATH not set.

            Please provide the full path to the SAS calibration directory (SAS_CCFPATH).

        """
        print(scomment)
        sas_ccfpath = input('Full path to calibration files: ')
        if not sas_ccfpath.startswith('/'): sas_ccfpath = os.path.abspath(sas_ccfpath)
        if sas_ccfpath.endswith('/'): sas_ccfpath = sas_ccfpath[:-1]

    if not os.path.exists(sas_ccfpath):
        print(f'The directory {sas_ccfpath} was not found!')
        response = input('Should I create it? (y/n): ')
        response = response.lower()
        if response in positive:
            print(f'Creating: {sas_ccfpath}')
            os.mkdir(sas_ccfpath)
        elif response in negative:
            print('\nPlease create the directory for the calibration files!\n')
        else:
            print(f'Your response, {response}, is not recognized.')
            print(f'Try any of these: {positive}')
            print(f'-or any of these: {negative}')
            raise Exception('Input not recognized!')
            
    download_calibration = False
    esa_or_nasa = ''
    print('Would you like to download the current valid set of calibration files?\nWill download at the end of this script.')
    response2 = input('(y/n): ')
    response2 = response2.lower()
    if response2 in positive:
        download_calibration = True
        print('Which repository do you want to use to download the calibration files?')
        esa_or_nasa = input('ESA or NASA: ')
        esa_or_nasa = esa_or_nasa.lower()
        if esa_or_nasa in esa+nasa:
            pass
        else:
            print(f'Your response, {esa_or_nasa}, is not recognized.')
            print(f'Try any of these: {esa}')
            print(f'-or any of these: {nasa}')
            raise Exception('Input not recognized!')
    elif response2 in negative:
        print('Please make sure you download the calibration data!')
    else:
        print(f'Your response, {response2}, is not recognized.')
        print(f'Try any of these: {positive}')
        print(f'-or any of these: {negative}')
        raise Exception('Input not recognized!')
        
    print('\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    ############## Getting data_dir ##############

    scomment = """
        No default data directory.

        Please provide the full path to the user data directory.
        (OPTIONAL, but recommended)

    """
    print(scomment)
    data_dir = input('Full path to user data directory: ')
    if not data_dir.startswith('/'): data_dir = os.path.abspath(data_dir)
    if data_dir.endswith('/'): data_dir = data_dir[:-1]
    print('\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    # Check if data_dir exists. If not then create it.
    if not os.path.isdir(data_dir):
        print(f'{data_dir} does not exist. Creating it!')
        os.mkdir(data_dir)
        print(f'{data_dir} has been created!')
    else:
        print(f'\nData directory exists. Will use {data_dir} to download data.')

    # Check if paths for SAS_DIR and SAS_CCFPATH exist.
    if os.path.exists(sas_dir) and os.path.exists(sas_ccfpath):
        print('SAS_DIR and SAS_CCFPATH exist. Will use the following to initialize SAS:')
        print(f'     SAS_DIR = {sas_dir}')
        print(f'     SAS_CCFPATH = {sas_ccfpath}')
        initializesas(sas_dir, sas_ccfpath, verbosity=verbosity,suppress_warning=suppress_warning)

    if not os.path.exists(sas_dir):
        print(f'There is a problem with SAS_DIR {sas_dir}. Please check and try again.')
        raise Exception(f'There is a problem with SAS_DIR {sas_dir}. Please check and try again.')

    if not os.path.exists(sas_ccfpath) and not download_calibration:
        print(f'SAS_CCFPATH ({sas_ccfpath}) does not exist! Make sure you create it and download the calibration files!')
        

    # Set sas_dir in configuration settings
    sas_cfg.set_setting('sas_dir', sas_dir)

    # Set sas_ccfpath in configuration settings
    sas_cfg.set_setting('sas_ccfpath', sas_ccfpath)

    # Set data_dir in configuration settings
    sas_cfg.set_setting('data_dir', data_dir)

    # Save configuration settings to file
    sas_cfg.save_config()

    # Putting calibration file download in its own function since it is used in multiple locations.
    if download_calibration:
        result = update_calibration_files(repo=esa_or_nasa)

    scomment = f"""
        Success!

        SAS_DIR set to {sas_dir}
        SAS_CCFPATH set to {sas_ccfpath}
        data_dir set to {data_dir}

        Upon running the command 'import pysas' SAS will 
        automatically be initialized.

        The defaults can be changed at any time using the commands:

            from pysas import sas_cfg
            sas_cfg.set_setting_and_save('value_to_set',value)

        At any time the user can reset the config file to the defaults,

            from pysas import sas_cfg
            sas_cfg.reset_to_defaults()

    """
    print(scomment)
