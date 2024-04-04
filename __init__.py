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
from .version import *
from .odfcontrol import odfcontrol

__version__ = f'pysas - (pysas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]'

## For initialization of pySAS from configuration file.
from .configutils import sas_cfg
from .init_sas import initializesas
import os
sas_dir     = sas_cfg.get("sas", "sas_dir")
sas_ccfpath = sas_cfg.get("sas", "sas_ccfpath")

# Checks if defaults work.
if sas_cfg['DEFAULT']['on_sci_server'] == 'False':
    if os.path.exists(sas_dir) and os.path.exists(sas_ccfpath):
        initializesas(sas_dir, sas_ccfpath)
    elif sas_dir != '/does/not/exist' and sas_ccfpath != '/does/not/exist':
        print('There is a problem with either SAS_DIR or SAS_CCFPATH in the config file.')
        print('Please set manually to initialize SAS.')
        print('sas_dir....: {}'.format(sas_dir))
        print('sas_ccfpath: {}'.format(sas_ccfpath))

del sas_dir, sas_ccfpath