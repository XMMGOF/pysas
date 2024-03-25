# init_sas.py
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

# init_sas.py

"""
init_sas.py

For auto initializing SAS on import of pySAS.

"""

# Standard library imports
import os, subprocess

# Third party imports

# Local application imports

# Function to initialize SAS

def add_environ_variable(variable,invalue,prepend=True):
        """
        variable (str) is the name of the environment variable to be set.
        
        value (str, or list) is the value to which the environment variable
        will be set.
        
        prepend (boolean) default=True, whether to prepend or append the 
        variable
        
        The function first checks if the enviroment variable already exists.
        If not it will be created and set to value.
        If variable alread exists the function will check if value is already
        present. If not it will add it either prepending (default) or appending.

        Returns
        -------
        None.

        """
        
        if isinstance(invalue, str):
            listvalue = [invalue]
        else:
            listvalue = invalue
            
        if not isinstance(listvalue, list):
            raise Exception('Input to add_environ_variable must be str or list!')
        
        for value in listvalue:
            environ_var = os.environ.get(variable)
            # Create variable if it does not exist.
            if not environ_var:
                os.environ[variable] = value
            else:
                splitpath = environ_var.split(os.pathsep)
                # Only add if the new value does not exist in the variable.
                if not value in splitpath:
                    if prepend:
                        splitpath.insert(0,value)
                    else:
                        splitpath.append(value)
                    os.environ[variable] = os.pathsep.join(splitpath)

def overwrite_environ_variable(variable,invalue):
    """
        variable (str) is the name of the environment variable to be set.
        
        value (str, or list) is the value to which the environment variable
        will be set.

        Will overwrite an environment variable to a new value. Will not check
        if variable exists or if it is defined.

        Returns
        -------
        None.
    """
    if isinstance(invalue, str):
        listvalue = [invalue]
    else:
        listvalue = invalue
        
    if not isinstance(listvalue, list):
        raise Exception('Input to overwrite_environ_variable must be str or list!')
    
    os.environ[variable] = os.pathsep.join(listvalue)

def initializesas(sas_dir, sas_ccfpath, verbosity = 4, suppress_warning = 1, image_viewer = 'ds9'):
    """
    Heasoft must be initialized first, separately.

    Inputs are:

        - sas_dir (required) directory where SAS is installed.

        - sas_ccfpath (required) directory where calibration files are located.

        - verbosity (optional, default = 4) SAS verbosity.

        - suppress_warning (optional, default = 1) 

    Returns:
    --------
    Information about SAS envirment veriables that were set.
    """

    ######
    # Checking LHEASOFT and inputs

    lheasoft = os.environ.get('LHEASOFT')
    if not lheasoft:
        raise Exception('LHEASOFT is not set. Please initialise HEASOFT')

    # Necessary to fix a problem with calls to heasoft from certain SAS functions.
    add_environ_variable('HEADASNOQUERY','')
    add_environ_variable('HEADASPROMPT','/dev/null')

    # Checks if a basic call to HEASOFT works.
    try:
        heasoft_test = subprocess.run(["fversion"],stdout = subprocess.DEVNULL)
    except FileNotFoundError:
        raise Exception('HEASOFT is not initialized. Please initialise HEASOFT')

    # Will not check the configuration file. Configuration file checking must happen 
    # in the calling script or function. sas_dir and sas_ccfpath must be passed in.
    if sas_dir is None:
        raise Exception('sas_dir must be provided to initialize SAS.')
    if sas_ccfpath is None:
        raise Exception('sas_ccfpath must be provided to initialize SAS.')

    # Hard overwrite. To set or reset values.
    overwrite_environ_variable('SAS_DIR',sas_dir)
    overwrite_environ_variable('SAS_CCFPATH',sas_ccfpath)
    overwrite_environ_variable('SAS_PATH',[sas_dir])
    
    binpath = [os.path.join(sas_dir,'bin'), os.path.join(sas_dir,'bin','devel')]
    libpath = [os.path.join(sas_dir,'lib'),os.path.join(sas_dir,'libextra'),os.path.join(sas_dir,'libsys')]
    perlpath = [os.path.join(sas_dir,'lib','perl5')]
    pythonpath = [os.path.join(sas_dir,'lib','python')]

    # Soft add. Will only add if value does not exist in enviroment variable.
    add_environ_variable('SAS_PATH',binpath+libpath+perlpath+pythonpath,prepend=False)
    add_environ_variable('PATH',binpath)
    add_environ_variable('LIBRARY_PATH',libpath,prepend=False)
    add_environ_variable('LD_LIBRARY_PATH',libpath,prepend=False)
    add_environ_variable('PERL5LIB',perlpath)
    add_environ_variable('PYTHONPATH',pythonpath)

    perllib = os.environ.get('PERLLIB')
    if perllib:
        splitpath = perllib.split(os.pathsep)
        add_environ_variable('PERL5LIB',splitpath,prepend=False)

    os.environ['SAS_VERBOSITY'] = '{}'.format(verbosity)
    os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(suppress_warning)
    os.environ['SAS_IMAGEVIEWER'] = '{}'.format(image_viewer)

    sas_path = os.environ.get('SAS_PATH')

    return_info = f"""
        SAS_DIR set to {sas_dir}
        SAS_CCFPATH set to {sas_ccfpath}
        SAS_PATH set to {sas_path}

        {libpath} added to LIBRARY_PATH
        {libpath} added to LD_LIBRARY_PATH
        {perlpath} added to PERL5LIB
        {pythonpath} added to PYTHONPATH
    """
    if perllib:
        return_info += f"""{perllib} added to PERLLIB"""
    return_info += f"""

    SAS_VERBOSITY set to {verbosity}
    SAS_SUPPRESS_WARNING set to {suppress_warning}
    """

    return return_info