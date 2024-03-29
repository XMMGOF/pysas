# configutils.py
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

# configutils.py

"""
configutils.py

For configuring defaults of SAS enviroment variables.

"""

# Standard library imports
import os
from configparser import ConfigParser

# Third party imports

# Local application imports

__version__ = 'configutils (configutils-1.0)'

###############
# Configuration

sas_cfg_defaults = {
    "sas_dir": "/does/not/exist",
    "sas_ccfpath": "/does/not/exist",
    "data_dir": "/does/not/exist",
    "verbosity": 4,
    "suppress_warning": 1,
    "on_sci_server": False
}

CURRENT_CONFIG_FILE = None

if (os.path.expanduser("~") == '/home/idies') and \
    os.path.exists('/home/idies/workspace/Storage/'):
    # If on SciServer, get enviroment variables. Replace defaults.
    sas_cfg_defaults['on_sci_server'] = True
    sas_cfg_defaults['usr'] = os.listdir('/home/idies/workspace/Storage/')[0]
    sas_dir     = os.environ.get('SAS_DIR')
    sas_ccfpath = os.environ.get('SAS_CCFPATH')
    sas_cfg_defaults['sas_dir']     = sas_dir
    sas_cfg_defaults['sas_ccfpath'] = sas_ccfpath
    sas_cfg = ConfigParser(sas_cfg_defaults)
    sas_cfg.add_section("sas")
else:
    # If not on SciServer.
    # Check if .config directory exists. If not, make it.
    config_root = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ.get('HOME'), ".config")
    )
    CONFIG_DIR = os.path.join(config_root, "sas")
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
        except OSError:
            raise Exception( f'Unable to make SAS config directory: {CONFIG_DIR}')

    # Check if sas.cfg file exists. If not, make it. Populate with defaults.
    CURRENT_CONFIG_FILE = os.path.join(CONFIG_DIR, "sas.cfg")
    if not os.path.exists(CURRENT_CONFIG_FILE):
        cp = ConfigParser(sas_cfg_defaults)
        cp.add_section("sas")
        try:
            with open(CURRENT_CONFIG_FILE, "w") as new_cfg:
                cp.write(new_cfg)
        except IOError:
            raise Exception( f'Unable to write to SAS config file: {CURRENT_CONFIG_FILE}')

    sas_cfg = ConfigParser(sas_cfg_defaults)
    sas_cfg.read([CURRENT_CONFIG_FILE, "sas.cfg"])
    if not sas_cfg.has_section("sas"): sas_cfg.add_section("sas")    

######### Functions #########

def set_sas_config_option(option, value):
    """
    Set default SAS configuration values.

    This sets values as default for future sessions.

    Parameters
    ----------
    option : string
        The option to change.
    value : number or string
        The value to set the option to.
    """
    if os.path.exists(CURRENT_CONFIG_FILE):
        option = option.lower()
        sas_cfg.set("sas", option, value=str(value))
        with open(CURRENT_CONFIG_FILE, "w") as new_cfg:
            sas_cfg.write(new_cfg)
    else:
        print('No SAS configuration file found! Cannot set default value for:')
        print('Option: {0} ; Value: {1}'.format(option,value))

def clear_sas_defaults():
    """
    Clears all SAS defaults set by user. User will have to reset SAS defaults.
            sas_dir
            sas_ccfpath
            data_dir
            verbosity
            suppress_warning
    """
    if os.path.exists(CURRENT_CONFIG_FILE):
        os.remove(CURRENT_CONFIG_FILE)
    else:
        print('SAS configuration file, {0}, not found! Cannot remove!'.format(CURRENT_CONFIG_FILE))

