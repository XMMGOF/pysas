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
# from .config_pysas import sas_config
from . import config_pysas

# Create config object
sas_cfg = config_pysas.sas_config()

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

SAS_RELEASE          = 'NOT INITIALIZED'
SAS_AKA              = ''
SAS_COMPILATION_DATE = ''
SAS_COMPILATION_HOST = ''
SAS_COMPILATION_USER = ''
SAS_PLATFORM         = ''
SAS_COMMIT_ID        = ''

from .version import get_sas_version

# Get SAS version information
if sas_ready:
    sas_info = get_sas_version()
    SAS_RELEASE          = sas_info['RELEASE']
    SAS_AKA              = sas_info['AKA']
    SAS_COMPILATION_DATE = sas_info['COMPILATION_DATE']
    SAS_COMPILATION_HOST = sas_info['COMPILATION_HOST']
    SAS_COMPILATION_USER = sas_info['COMPILATION_USER']
    SAS_PLATFORM         = sas_info['PLATFORM']
    SAS_COMMIT_ID        = sas_info['COMMIT_ID']
    del sas_info

from .version import VERSION, print_sas_version

__version__ = f'pysas - (pysas-{VERSION}) [SAS-{SAS_RELEASE}]'

# Import pySAS modules
from . import sastask
from . import parser
from . import param
from . import init_sas
from . import sasutils

# Classes and functions needed at the top level
from .obsid import ObsID, PPSFiles
from .sastask import MyTask
from .config_pysas import run_config
from .sasutils import download_data, generate_logger, update_calibration_files

# API
__all__ = ['ObsID',
           'PPSFiles',
           'MyTask',
           'sas_cfg',
           'get_sas_version',
           'update_calibration_files']

# Get rid of temporary variables to prevent possible conflicts.
if sas_initialize:
    del sas_dir_config, sas_ccfpath_config, sas_verbosity, sas_suppress_warning
del sas_initialize, sas_ready
del sas_dir, sas_path, sas_ccfpath
del value
