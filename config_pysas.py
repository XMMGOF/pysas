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

# Standard library imports
import os, glob, time, subprocess

# Third party imports

# Local application imports
# from pysas import sas_cfg
from pysas.init_sas import initializesas
from configparser import ConfigParser
from pathlib import Path

# Config class
class sas_config:
    """
    Class for interacting with the pySAS configuration file.

    Parameters
    ----------
    config_file : str, optional
        Path to config file, by default 'XDG_CONFIG_HOME (usually the user's 
        HOME directory).
    """

    def __init__(self, config_file: str = None):

        self.config = ConfigParser()

        # Raw defaults
        self.sas_cfg_defaults = {
            "suppress_warning" : 1,
            "verbosity"        : 4,
            "pysas_verbosity"  : "WARNING",
            "repo"             : "ESA",
            "work_dir_name"    : "work"
        }
        
        # Resolve the full path to the configuration file
        if config_file is None:
            home_dir = Path.home()
            # For SciServer
            if str(home_dir) == '/home/idies':
                user = os.environ.get('SCISERVER_USER_NAME')
                home_dir = home_dir / "workspace" / "Storage" / user / "persistent"
                if not home_dir.exists(): home_dir = Path.home()
            CONFIG_ROOT = os.environ.get("XDG_CONFIG_HOME", home_dir / ".config")
            CONFIG_ROOT = Path(CONFIG_ROOT).resolve()
            CONFIG_ROOT  = CONFIG_ROOT / 'sas'
            if not CONFIG_ROOT.exists():
                try:
                    os.makedirs(CONFIG_ROOT)
                except OSError:
                    #print(f'Unable to create config directory {CONFIG_ROOT}')
                    pass    
            config_file = CONFIG_ROOT / 'sas.cfg'
        else:
            config_file = Path(config_file).resolve()

        self.absolute_config_path = config_file

        if self.absolute_config_path.exists():
            # Read the configuration file
            self.config.read(self.absolute_config_path)
        else:
            self.config = ConfigParser(self.sas_cfg_defaults)
            if not self.config.has_section('sas'): self.config.add_section('sas')
            self.save_config()

    def get_setting(self, option: str, section: str = 'sas'):
        """
        Retrieves a setting from the current session configuration (not from 
        the config file).

        Parameters
        ----------
        option : str
            Which setting to retrieve.
        section : str, optional
            Which section in the config file, by default 'sas'.

        Returns
        -------
        str
            The returned setting.
        """
        return self.config.get(section, option)

    def set_setting(self, option: str, value: str, section: str = 'sas'):
        """
        Sets a setting in the current session configuration (does not change 
        the config file).

        Parameters
        ----------
        option : str
            Which setting to set.
        value : str
            Value to be set.
        section : str, optional
            Which section in the configuration has the option, by default 'sas'.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)

    def set_setting_and_save(self, option: str, value: str, section: str = 'sas'):
        """
        Sets a setting in the current session configuration AND saves the 
        setting to the config file.

        Parameters
        ----------
        option : str
            Which setting to set.
        value : str
            Value to be set.
        section : str, optional
            Which section in the configuration has the option, by default 'sas'.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.save_config()

    def save_config(self, config_file_path: str = None):
        """
        Saves the current session configuration to the config file. Does not 
        modify any configuration options.

        Parameters
        ----------
        config_file_path : str, optional
            Path to config file, by default None.
        """
        if config_file_path is None:
            absolute_config_path = self.absolute_config_path
        else:
            absolute_config_path = Path(config_file_path).resolve()
        try:
            with open(absolute_config_path, 'w') as file:
                self.config.write(file)
        except IOError:
            print(f'Unable to write config file to {absolute_config_path}')
            pass

    def show_current_config(self):
        """
        Prints the current session configuration settings to the terminal. 
        
        Note: The current session configuration settings are usually the same 
        as the contents of the config file, but they can be different.
        """
        defaults = self.config.defaults()
        print(f'[{self.config.default_section}]')
        for k,v in defaults.items():
            print(f'{k} = {v}')
        
        for section in self.config.sections():
            print(f'\n[{section}]')
            for k,v in self.config.items(section):
                if k in defaults.keys():
                    if defaults[k] == v:
                        continue
                print(f'{k} = {v}')

    def show_config_file(self):
        """
        Prints the contents of the configuration file to the terminal.
        """
        with open(self.absolute_config_path, 'r') as file:
            content = file.read()
            print(content)

    def reset_to_defaults(self):
        """
        Resets configuration file to the defaults.
        """
        self.config = ConfigParser(self.sas_cfg_defaults)
        if not self.config.has_section('sas'): self.config.add_section('sas')
        self.save_config()

    def simple_config(self, 
                      sas_dir: str = None, 
                      sas_ccfpath: str = None, 
                      data_dir: str = None,
                      repo: str = None):
        """
        For quick, simple configuration of pySAS.

        Parameters
        ----------
        sas_dir : str, optional
            Directory where SAS is installed, by default None.
        sas_ccfpath : str, optional
            Directory with calibration files, by default None.
        data_dir : str, optional
            User data directory, by default None.
        repo : str, optional
            Default repository for downloading data, by default None.
            Accepted values are,

            'ESA' (data from the XSA)

            'NASA' (data from the HEASARC)

            'AWS' (data from AWS s3 bucket (NASA))

            'Fornax' (if user is on Fornax)

            'SciServer' (if user is on SciServer)
        """
        home_dir = Path.home()
        if sas_dir is None: sas_dir = os.environ.get('SAS_DIR')
        if sas_ccfpath is None: sas_ccfpath = os.environ.get('SAS_CCFPATH')
        
        # For Fornax
        if str(sas_ccfpath) == '/opt/support-data/xmm_ccf':
            if repo is None:
                repo = 'fornax'
        
        # For SciServer
        if str(home_dir) == '/home/idies':
            if data_dir is None:
                user = os.environ.get('SCISERVER_USER_NAME')
                data_dir = os.path.join('/home/idies/workspace/Temporary/',user,'scratch/xmm_data')
            if repo is None:
                repo = 'sciserver'
        
        if data_dir is None: 
            data_dir = home_dir / 'xmm_data'
            data_dir = data_dir.resolve()

        if sas_dir: self.set_setting('sas_dir', sas_dir)
        if sas_ccfpath: self.set_setting('sas_ccfpath', sas_ccfpath)
        if repo: self.set_setting('repo', repo)
        self.set_setting('data_dir', str(data_dir))
        self.save_config()

def run_config():
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
    subdirectory will be made for each observation ID (Obs ID).
    
    The default data directory can be set or change later using functions in 
    the 'sas_cfg' object.

    For example::

        import pysas
        data_path = '/path/to/data/dir/'
        pysas.sas_cfg.set_setting_and_save('data_dir', data_path)
        
    The default values for the SAS directory (sas_dir), the path to the
    calibration files (sas_ccfpath), along with 'verbosity' and 
    'suppress_warning', can also be set in the same way.

    At any time the user can reset the config file to the defaults,::

        import pysas
        pysas.sas_cfg.reset_to_defaults()
    """

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

            import pysas
            data_path = '/path/to/data/dir/'
            pysas.sas_cfg.set_setting_and_save('data_dir', data_path)
            
        The default values for the SAS directory (sas_dir), the path to the
        calibration files (sas_ccfpath), along with 'verbosity' and 
        'suppress_warning', can also be set in the same way.

        At any time the user can reset the config file to the defaults,

            import pysas
            pysas.sas_cfg.reset_to_defaults()

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    """

    print(outcomment)

    positive = ['y','yes','ye','yeah','yea','ys','aye','yup','totally','si','oui']
    negative = ['n','no','not','nay','no way','nine','non']
    esa = ['esa','e','es','europe']
    nasa = ['nasa','n','na','nas','ns','nsa','us','usa','heasarc','hea']

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
        initializesas(sas_dir, sas_ccfpath)

    if not os.path.exists(sas_dir):
        print(f'There is a problem with SAS_DIR {sas_dir}. Please check and try again.')
        raise Exception(f'There is a problem with SAS_DIR {sas_dir}. Please check and try again.')

    if not os.path.exists(sas_ccfpath) and not download_calibration:
        print(f'SAS_CCFPATH ({sas_ccfpath}) does not exist! Make sure you create it and download the calibration files!')
        
    # Create config object
    sas_cfg = sas_config()

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
        if esa_or_nasa in esa:
            cmd = f'rsync -v -a --delete --delete-after --force --include=\'*.CCF\' --exclude=\'*/\' sasdev-xmm.esac.esa.int::XMM_VALID_CCF {sas_ccfpath}'
        elif esa_or_nasa in nasa:
            cmd = f'wget -nH --no-remove-listing -N -np -r --cut-dirs=4 -e robots=off -l 1 -R "index.html*" https://heasarc.gsfc.nasa.gov/FTP/xmm/data/CCF/ -P {sas_ccfpath}'
        print(f'Downloading calibration data using the command:\n{cmd}')
        print('This may take a while...')
        time.sleep(3)
        result = subprocess.run(cmd, shell=True)

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
