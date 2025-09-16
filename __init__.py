# __init__.py for pysas
#
#

from . import sastask
from . import parser
from . import param
from . import error
from . import configutils
from . import init_sas
from . import sasutils
from . import config_pysas
from .version import VERSION, get_sas_version
from .obsid import obsid
from .odfcontrol import odfcontrol

## For initialization of pySAS from configuration file.
from .configutils import sas_cfg
from .init_sas import initializesas
import os
sas_dir_config       = sas_cfg.get("sas", "sas_dir")
sas_ccfpath_config   = sas_cfg.get("sas", "sas_ccfpath")
sas_verbosity        = sas_cfg.get("sas", "verbosity")
sas_suppress_warning = sas_cfg.get("sas", "suppress_warning")
sas_initialize = True
sas_ready      = False 

# Check if SAS_DIR, SAS_PATH, and SAS_CCFPATH are already set.
sas_dir = os.environ.get('SAS_DIR')
sas_path = os.environ.get('SAS_PATH')
sas_ccfpath = os.environ.get('SAS_CCFPATH')
if sas_dir and sas_ccfpath and sas_path:
    if os.path.exists(sas_dir) and os.path.exists(sas_ccfpath) and os.path.exists(sas_path):
        # SAS_DIR, SAS_PATH, and SAS_CCFPATH enviroment variables already set.
        # SAS already initialized.
        sas_initialize = False
        sas_ready      = True
        value = os.environ.get("SAS_VERBOSITY")
        if value is not None:
            sas_verbosity = value
        else:
            os.environ['SAS_VERBOSITY'] = f'{sas_verbosity}'
        value = os.environ.get("SAS_SUPPRESS_WARNING")
        if value is not None:
            sas_suppress_warning = value
        else:
            os.environ['SAS_SUPPRESS_WARNING'] = f'{sas_suppress_warning}'

# Checks if defaults from config file work. Initializes SAS if needed.
if sas_initialize:
    if os.path.exists(sas_dir_config) and os.path.exists(sas_ccfpath_config):
        sas_init_info = initializesas(sas_dir_config,
                                      sas_ccfpath_config,
                                      verbosity = sas_verbosity,
                                      suppress_warning = sas_suppress_warning)
        sas_ready = True
    elif sas_dir_config != '/does/not/exist' and sas_ccfpath_config != '/does/not/exist':
        print('There is a problem with either SAS_DIR or SAS_CCFPATH in the config file.')
        print('Please set manually to initialize SAS.')
        print('sas_dir....: {}'.format(sas_dir_config))
        print('sas_ccfpath: {}'.format(sas_ccfpath_config))

# Get SAS version information
if sas_ready:
    return_list = get_sas_version()
else:
    return_list = ['','','','','','','']

SAS_RELEASE          = return_list[0]
SAS_AKA              = return_list[1]
SAS_COMPILATION_DATE = return_list[2]
SAS_COMPILATION_HOST = return_list[3]
SAS_COMPILATION_USER = return_list[4]
SAS_PLATFORM         = return_list[5]
SAS_COMMIT_ID        = return_list[6]

__version__ = f'pysas - (pysas-{VERSION}) [{SAS_RELEASE}]'

from .print_version import print_sas_version

# Get rid of temporary variables to prevent possible conflicts.
del sas_dir_config, sas_ccfpath_config, sas_initialize, sas_ready
del sas_dir, sas_path, sas_ccfpath, return_list