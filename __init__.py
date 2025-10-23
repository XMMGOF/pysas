# __init__.py for pysas
#
#

import os

# Check if SAS_DIR, SAS_PATH, and SAS_CCFPATH are already set.
sas_initialize = True
sas_ready      = False 
sas_dir        = os.environ.get('SAS_DIR')
sas_path       = os.environ.get('SAS_PATH')
sas_ccfpath    = os.environ.get('SAS_CCFPATH')

value = None

if sas_dir and \
   sas_ccfpath and \
   sas_path:
    if os.path.exists(sas_dir) and \
       os.path.exists(sas_ccfpath) and \
       os.path.exists(sas_path):
        # SAS_DIR, SAS_PATH, and SAS_CCFPATH enviroment variables already set.
        # SAS already initialized.
        sas_initialize = False
        sas_ready      = True
        # Check for SAS_VERBOSITY and SAS_SUPPRESS_WARNING
        # Set to default values if not present
        value = os.environ.get("SAS_VERBOSITY")
        if value is None:
            os.environ['SAS_VERBOSITY'] = '4'
        value = os.environ.get("SAS_SUPPRESS_WARNING")
        if value is None:
            os.environ['SAS_SUPPRESS_WARNING'] = '1'

# If SAS environment variables are not set look in the config file
from configparser import ConfigParser
from pathlib import Path

# Config class
class sas_config:
    def __init__(self, config_file=None):
        self.config = ConfigParser()

        # Raw defaults
        self.sas_cfg_defaults = {
            "suppress_warning" : 1,
            "verbosity"        : 4,
            "pysas_verbosity"  : "WARNING",
            "repo"             : "ESA"
        }
        
        # Resolve the full path to the configuration file
        if config_file is None:
            home_dir = Path.home()
            CONFIG_ROOT = os.environ.get("XDG_CONFIG_HOME", home_dir / ".config")
            CONFIG_ROOT = Path(CONFIG_ROOT).resolve()
            CONFIG_ROOT  = CONFIG_ROOT / 'sas'
            if not CONFIG_ROOT.exists():
                try:
                    os.makedirs(CONFIG_ROOT)
                except OSError:
                    pass
                    #print(f'Unable to create config directory {CONFIG_ROOT}')
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

    def get_setting(self, option, section = 'sas'):
        """
        Retrieves a setting from the configuration.
        """
        return self.config.get(section, option)

    def set_setting(self, option, value, section = 'sas'):
        """
        Sets a setting in the configuration.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)

    def set_setting_and_save(self, option, value, section = 'sas'):
        """
        Sets a setting in the configuration.
        Saves the setting to file.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.save_config()

    def save_config(self, config_file_path = None):
        """
        Saves the current configuration back to a file.
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

    def show_current_config(self):
        """
        Shows the current configuration settings.
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
        Resets config file to defaults.
        """
        self.config = ConfigParser(self.sas_cfg_defaults)
        if not self.config.has_section('sas'): self.config.add_section('sas')
        self.save_config()

    def simple_config(self, 
                      sas_dir = None, 
                      sas_ccfpath = None, 
                      data_dir = None,
                      repo = None):
        """
        For quick, simple configuration of pySAS.
        """
        home_dir = Path.home()
        if sas_dir is None: sas_dir = os.environ.get('SAS_DIR')
        if sas_ccfpath is None: sas_ccfpath = os.environ.get('SAS_CCFPATH')
        # For Fornax
        if str(home_dir) == '/home/jovyan':
            if data_dir is None: 
                data_dir = home_dir / 'xmm_data'
                data_dir = data_dir.resolve()
            if repo is None:
                repo = 'fornax'
        # For SciServer
        elif str(home_dir) == '/home/idies':
            if data_dir is None:
                user = os.environ.get('SCISERVER_USER_NAME')
                data_dir = os.path.join('/home/idies/workspace/Temporary/',user,'scratch/xmm_data')
            if repo is None:
                repo = 'sciserver'

        if sas_dir: self.set_setting('sas_dir', sas_dir)
        if sas_ccfpath: self.set_setting('sas_ccfpath', sas_ccfpath)
        if repo: self.set_setting('repo', repo)
        self.set_setting('data_dir', str(data_dir))
        self.save_config()

# Create config object
sas_cfg = sas_config()

# Get configuration settings
# Checks if defaults from config file exist.
if sas_cfg.config.has_option('sas','sas_dir'):
    sas_dir_config = sas_cfg.get_setting("sas_dir")
    if not os.path.exists(sas_dir_config):
        print('There is a problem with SAS_DIR in the config file!')
        print(f'{sas_dir_config} does not exist!')
        print('Please set manually to initialize SAS.')
        sas_initialize = False
else:
    sas_initialize = False

if sas_cfg.config.has_option('sas','sas_ccfpath'):
    sas_ccfpath_config = sas_cfg.get_setting("sas_ccfpath")
    if not os.path.exists(sas_ccfpath_config):
        print('There is a problem with SAS_CCFPATH in the config file!')
        print(f'{sas_ccfpath_config} does not exist!')
        print('Please set manually to initialize SAS.')
        sas_initialize = False
else:
    sas_initialize = False

## For initialization of pySAS from configuration file.
#from .configutils import sas_cfg
from .init_sas import initializesas

# Initializes SAS if needed.
if sas_initialize:
    sas_verbosity        = sas_cfg.get_setting("verbosity")
    sas_suppress_warning = sas_cfg.get_setting("suppress_warning")
    sas_init_info = initializesas(sas_dir_config,
                                  sas_ccfpath_config,
                                  verbosity = sas_verbosity,
                                  suppress_warning = sas_suppress_warning)
    sas_ready = True


# Import pySAS modules
from . import sastask
from . import parser
from . import param
from . import error
from . import init_sas
from . import sasutils
from . import config_pysas
from .version import VERSION, get_sas_version

# Get SAS version information
if sas_ready:
    return_list = get_sas_version()
else:
    return_list = ['NOT INITIALIZED','','','','','','']

SAS_RELEASE          = return_list[0]
SAS_AKA              = return_list[1]
SAS_COMPILATION_DATE = return_list[2]
SAS_COMPILATION_HOST = return_list[3]
SAS_COMPILATION_USER = return_list[4]
SAS_PLATFORM         = return_list[5]
SAS_COMMIT_ID        = return_list[6]

__version__ = f'pysas - (pysas-{VERSION}) [SAS-{SAS_RELEASE}]'

# Classes and functions needed at the top level
from .obsid.obsid import ObsID
from .sastask import MyTask
from .print_version import print_sas_version
from .config_pysas import run_config
from .sasutils import download_data, generate_logger, update_calibration_files

# Will be depricated at some point
from .odfcontrol import odfcontrol

# API
__all__ = ['ObsID',
           'MyTask']

# Get rid of temporary variables to prevent possible conflicts.
if sas_initialize:
    del sas_dir_config, sas_ccfpath_config, sas_verbosity, sas_suppress_warning
del sas_initialize, sas_ready
del sas_dir, sas_path, sas_ccfpath
del value, return_list
