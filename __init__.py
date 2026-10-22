# __init__.py for pysas
# 
###########################################################
# Several things need to be done in this order:
# 
#   1. Load config file and initialize SAS if necessary
#   2. Generate the logger
#   3. Get VERSION
#   4. Import modules
#   5. Clean up
# 
###########################################################

# ---------------------------------------------------------
# 1. Load config file and initialize SAS if necessary
# ---------------------------------------------------------

from pysas.config_pysas import sas_cfg
sas_ready = sas_cfg._set_sas_dirs()

# ---------------------------------------------------------
# 2. Generate the logger
# ---------------------------------------------------------
from pysas import logger
# Default behavior: Terminal ON, File OFF
pysas_verbosity = sas_cfg.get_setting('pysas_verbosity')
logger._log_enable_terminal(level=pysas_verbosity)

# ---------------------------------------------------------
# 3. Get VERSION.
# ---------------------------------------------------------
SAS_RELEASE          = 'NOT INITIALIZED'
SAS_AKA              = ''
SAS_COMPILATION_DATE = ''
SAS_COMPILATION_HOST = ''
SAS_COMPILATION_USER = ''
SAS_PLATFORM         = ''
SAS_COMMIT_ID        = ''

from pysas.version import get_sas_version

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

from pysas.version import VERSION, print_sas_version

__version__ = f'pysas - (pysas-{VERSION}) [SAS-{SAS_RELEASE}]'

# ---------------------------------------------------------
# 4. Import modules
# ---------------------------------------------------------
# Import pySAS modules
from pysas import obsid
from pysas import sastask
from pysas import parser
from pysas import param
from pysas import init_sas
from pysas import sasutils
from pysas import xmmfiles
from pysas import lightcurve

# Classes and functions needed at the top level
from pysas.obsid import ObsID, PPSFiles
from pysas.sastask import MyTask
from pysas.config_pysas import run_config
from pysas.lightcurve import XMMLightCurve
from pysas.xmmfiles import XMMEventList
from pysas.sasutils import (download_data,
                            update_calibration_files,
                            parse_value,
                            set_unit,
                            )
# API
__all__ = ['ObsID',
           'MyTask',
           'XMMEventList',
           'XMMLightCurve',
           'sas_cfg',
           'get_sas_version',
           'update_calibration_files']

# ---------------------------------------------------------
# 5. Clean up
# Get rid of temporary variables to prevent possible conflicts.
# ---------------------------------------------------------
del sas_ready, pysas_verbosity
