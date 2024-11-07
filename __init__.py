# __init__.py for pysas
#
#

from . import sastask
from . import parser
from . import param
from . import error
from . import runtask
from . import configutils
from . import init_sas
from . import sasutils
from . import config_pysas
from .version import *
from .odfcontrol import odfcontrol

__version__ = f'pysas - (pysas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'

## For initialization of pySAS from configuration file.
from .configutils import sas_cfg
from .init_sas import initializesas
import os
sas_dir_config     = sas_cfg.get("sas", "sas_dir")
sas_ccfpath_config = sas_cfg.get("sas", "sas_ccfpath")
sas_initialize = True

# Check if SAS_DIR, SAS_PATH, and SAS_CCFPATH are already set.
sas_dir = os.environ.get('SAS_DIR')
sas_path = os.environ.get('SAS_PATH')
sas_ccfpath = os.environ.get('SAS_CCFPATH')
if sas_dir and sas_ccfpath and sas_path:
    if os.path.exists(sas_dir) and os.path.exists(sas_ccfpath) and os.path.exists(sas_path):
        # SAS_DIR, SAS_PATH, and SAS_CCFPATH enviroment variables already set.
        # SAS already initialized.
        sas_initialize = False
        if sas_ccfpath == '/home/idies/workspace/headata/FTP/caldb/data/xmm/ccf':
            sas_cfg['DEFAULT']['on_sci_server'] = 'True'

# Checks if defaults from config file work. Initializes SAS if needed.
if sas_cfg['DEFAULT']['on_sci_server'] == 'False' and sas_initialize:
    if os.path.exists(sas_dir_config) and os.path.exists(sas_ccfpath_config):
        initializesas(sas_dir_config, sas_ccfpath_config)
    elif sas_dir_config != '/does/not/exist' and sas_ccfpath_config != '/does/not/exist':
        print('There is a problem with either SAS_DIR or SAS_CCFPATH in the config file.')
        print('Please set manually to initialize SAS.')
        print('sas_dir....: {}'.format(sas_dir_config))
        print('sas_ccfpath: {}'.format(sas_ccfpath_config))

# Get rid of temporary variables to prevent possible conflicts.
del sas_dir_config, sas_ccfpath_config, sas_initialize, sas_dir, sas_path, sas_ccfpath