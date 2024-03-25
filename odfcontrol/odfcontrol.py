# odfcontrol.py
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

# odfcontrol.py

"""
odfcontrol.py

"""

# Standard library imports
import os, sys, subprocess, shutil, glob, tarfile, gzip

# Third party imports

# Local application imports
# from .version import VERSION, SAS_RELEASE, SAS_AKA
from ..logger import TaskLogger as TL
from ..configutils import sas_cfg
from ..init_sas import initializesas
from ..wrapper import Wrapper as w

# __version__ = f'odfcontrol (startsas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 
__version__ = 'odfcontrol (odfcontrol-0.1)'
__all__ = ['ODFobject', 'download_data']


class ODFobject(object):
    """
    Class for observation data files (ODF).

        An odfid is necessary.

        data_dir is the base directory where you store all XMM data.

        Data is organized as:
            data_dir = /path/to/data/
            obs_dir = /path/to/data/odfid/
        With subdirectories and files:
                odf_dir  = /path/to/data/odfid/ODF/
                work_dir = /path/to/data/odfid/work/
                SAS_CCF  = work_dir/ccf.cif
                SAS_ODF  = work_dir/*SUM.SAS

    """

    def __init__(self,odfid,data_dir=None):
        self.odfid = odfid
        self.data_dir = data_dir
        self.files = {}
        self.set_odfid()

    def inisas(self,sas_dir,sas_ccfpath,verbosity=4,suppress_warning=1):
        """
        Simple wrapper for 'initializesas' defined in init_sas.py.
        """
        self.sas_dir = sas_dir
        self.sas_ccfpath = sas_ccfpath
        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        return_info = initializesas(self.sas_dir, self.sas_ccfpath, 
                                    verbosity = self.verbosity, 
                                    suppress_warning = self.suppress_warning)
        print(return_info)

    def set_odfid(self):
        """
        Checks if obs_dir exists. If it exists looks for existing 
        odf_dir, work_dir, SAS_CCF, and SAS_ODF. Similar to odfcompile, 
        but will not download any data, will not calibrate it, or do 
        anything other than link to files and directories. 
        """

        # Where are we?
        startdir = os.getcwd()

        # Brief check to see if data_dir was 
        # given on odfobject creation.
        if self.data_dir != None:
            data_dir = self.data_dir

        # Start checking data_dir
        data_dir = sas_cfg.get("sas", "data_dir")
        if os.path.exists(data_dir):
            self.data_dir = data_dir
        else:
            # Nothing can be done! User must run odfcompile!
            return

        # Set directories for the observation, odf, pps, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.odfid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.work_dir = os.path.join(self.obs_dir,'work')

        if os.path.exists(self.obs_dir):
            print(f'obs_dir found at {self.obs_dir}.')
            if os.path.exists(self.odf_dir):
                print(f'odf_dir found at {self.odf_dir}.')
            else:
                print(f'odf_dir not found! User must run odfcompile!')
                return
            if os.path.exists(self.work_dir):
                print(f'work_dir found at {self.work_dir}.')
            else:
                print(f'work_dir not found! User must run odfcompile!')
                return
        else:
            # obs_dir not found! Nothing can be done!
            return

        logger = generate_logger(logname='odf_'+self.odfid, log_dir=self.data_dir)
        logger.log('info', f'Data directory = {self.data_dir}')
        logger.log('info', f'Existing directory for {self.odfid} found ...')
        logger.log('info', f'Searching {self.data_dir}/{self.odfid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        self.files['sas_ccf'] = os.path.join('does','not','exist')
        logger.log('info', f'Searching for ccf.cif.')
        for path, directories, files in os.walk(self.obs_dir):
            for file in files:
                if 'ccf.cif' in file:
                    logger.log('info', f'Found ccf.cif file in {path}.')
                    self.files['sas_ccf'] = os.path.join(path,file)
        # Check if ccf.cif file exists.
        if os.path.exists(self.files['sas_ccf']):
            logger.log('info', '{0} is present'.format(self.files['sas_ccf']))
        else:
            logger.log('error', 'ccf.cif file not present! User must run odfcompile!')
            print('ccf.cif file not present! User must run odfcompile!')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        logger.log('info', 'SAS_CCF = {0}'.format(self.files['sas_ccf']))
        print('SAS_CCF = {}'.format(self.files['sas_ccf']))

        # Looking for *SUM.SAS file.
        self.files['sas_odf'] = os.path.join('does','not','exist')
        logger.log('info', f'Path to *SUM.SAS file not given. Will search for it.')
        for path, directories, files in os.walk(self.obs_dir):
            for file in files:
                if 'SUM.SAS' in file:
                    logger.log('info', f'Found *SUM.SAS file in {path}.')
                    self.files['sas_odf'] = os.path.join(path,file)
        # Check if *SUM.SAS file exists.
        if os.path.exists(self.files['sas_odf']):
            logger.log('info', '{0} is present'.format(self.files['sas_odf']))
        else:
            logger.log('error', 'sas_odf file not present! User must run odfcompile!')
            print('sas_odf file not present! User must run odfcompile!')
            return
        
        # Check that the SUM.SAS file PATH keyword points to a real ODF directory
        with open(self.files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if not os.path.exists(path):
                        logger.log('error', f'Summary file PATH {path} does not exist. Rerun odfcompile with overwrite=True.')
                        print(f'\nSummary file PATH {path} does not exist. \n\n>>>>Rerun odfcompile with overwrite=True.')
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if not os.path.exists(MANIFEST[0]):
                        logger.log('error', f'Missing {MANIFEST[0]} file in {path}. Missing ODF components? Rerun odfcompile with overwrite=True.')
                        print(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components? \n\n>>>>Rerun odfcompile with overwrite=True.')
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
        print('SAS_ODF = {0}'.format(self.files['sas_odf']))

        self.get_active_instruments()

        # Check if events lists have already been made from the odf files.

        inst_list = list(self.active_instruments.keys())
        evt_list_list = {'PN': 'PNevt_list',
                         'M1': 'M1evt_list',
                         'M2': 'M2evt_list',
                         'R1': 'R1evt_list',
                         'R2': 'R2evt_list',
                         'OM': 'OMevt_list'}
        find_list =     {'PN': 'EPN',
                         'M1': 'EMOS1',
                         'M2': 'EMOS2',
                         'R1': 'R1',
                         'R2': 'R2',
                         'OM': 'OM'}
        inst_name =     {'PN': 'EPIC-pn',
                         'M1': 'EPIC-MOS1',
                         'M2': 'EPIC-MOS2',
                         'R1': 'RGS1',
                         'R2': 'RGS2',
                         'OM': 'OM'}
        for item in inst_list: self.files[evt_list_list[item]] = []

        for inst in inst_list:
            exists = False
            files = glob.glob(self.obs_dir+'/**/*.ds', recursive=True)
            for filename in files:
                if (filename.find(find_list[inst]) != -1) and filename.endswith('Evts.ds'):
                    self.files[evt_list_list[inst]].append(os.path.abspath(filename))
                    exists = True
            if exists:
                print(" > {0} {1} event list(s) found.\n".format(len(self.files[evt_list_list[inst]]),inst_name[inst]))
                for x in self.files[evt_list_list[inst]]:
                    print("    " + x + "\n")

        # Exit the set_odfid function. Everything is set.
        return

    def sastalk(self,verbosity=4,suppress_warning=1):
        """
        Simple function to set general SAS veriables 'verbosity' 
        and 'suppress_warning'.
        """

        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        os.environ['SAS_VERBOSITY'] = '{}'.format(self.verbosity)
        os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(self.suppress_warning)

    def odfcompile(self,data_dir=None,level='ODF',
               sas_ccf=None,sas_odf=None,
               cifbuild_opts=None,odfingest_opts=None,
               encryption_key=None,overwrite=False,repo='esa'):
        """
        Before running this function an ODFobject must be created first. e.g.

        odf = pysas.odfcontrol.ODFobject(obsid)

        This function can then be used as, odf.odfcompile().

        The odfcompile function will automatically look in data_dir for the subdirectory 
        data_dir/odfid. If it does not exist then it will download the data.
        
        If it exists it will search data_dir/odfid and any subdirectories for the ccf.cif
        and *SUM.SAS files. But if overwrite=True then it will remove data_dir/odfid and 
        download the data.

        Optionally the paths to the ccf.cif and *SUM.SAS files can be given through 
        sas_ccf and sas_odf respectively.

        Inputs:
            --REQUIRED--

                NONE

            --OPTIONAL--

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded, or if data is present will look for
                                        ccf.cif and *SUM.SAS files. Automatically creates 
                                        the directory data_dir/odfid.
                                        Default: None, uses the current directory.

            --level:          (string): Level of data products to download.
                                        Default: 'ODF'
                                        Can be 'ODF, 'PPS' or 'ALL'.

            --sas_ccf:   (string/path): Path to ccf.cif file for odfid.

            --sas_odf:   (string/path): Path to *SUM.SAS file for odfid.

            --cifbuild_opts:  (string): Options for cifbuild.

            --odfingest_opts: (string): Options for odfingest.

            --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                        characters long. -OR- Path to file containing 
                                        ONLY the encryption key.

            --overwrite:     (boolean): If True will force overwrite of data if odfid 
                                        data already exists in data_dir/.

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'sciserver' (if user is on sciserver)
        """

        # Where are we?
        startdir = os.getcwd()

        # Brief check to see if data_dir was 
        # given on odfobject creation.
        if self.data_dir != None:
            data_dir = self.data_dir

        # Start checking data_dir
        if data_dir == None:
            data_dir = sas_cfg.get("sas", "data_dir")
            if os.path.exists(data_dir):
                self.data_dir = data_dir
            else:
                self.data_dir = startdir
        else:
            self.data_dir = data_dir

        # If data_dir was not given as an absolute path, it is interpreted
        # as a subdirectory of startdir.
        if self.data_dir[0] != '/':
            self.data_dir = os.path.join(startdir, self.data_dir)
        elif self.data_dir[:2] == './':
            self.data_dir = os.path.join(startdir, self.data_dir[2:])

        # Check if data_dir exists. If not then create it.
        # Save comments for the logger created later.
        logcomment = ''
        if not os.path.isdir(self.data_dir):
            logcomment = f'{self.data_dir} does not exist. Creating it!'
            os.mkdir(self.data_dir)
            logcomment = logcomment + '\n' + f'{self.data_dir} has been created!'

        logger = generate_logger(logname='odf_'+self.odfid, log_dir=self.data_dir)
        logger.log('info', f'Data directory = {self.data_dir}')
        if len(logcomment) > 1:
            logger.log('warning', logcomment)

        # Deal with the rest of the inputs.
        self.level = level
        self.files['sas_ccf'] = sas_ccf
        self.files['sas_odf'] = sas_odf
        self.cifbuild_opts = cifbuild_opts
        self.odfingest_opts = odfingest_opts
        self.encryption_key = encryption_key
        self.repo = repo

        # Checking LHEASOFT, SAS_DIR and SAS_CCFPATH

        lheasoft = os.environ.get('LHEASOFT')
        if not lheasoft:
            logger.log('error', 'LHEASOFT is not set. Please initialise HEASOFT')
            raise Exception('LHEASOFT is not set. Please initialise HEASOFT')
        else:
            logger.log('info', f'LHEASOFT = {lheasoft}')

        sasdir = os.environ.get('SAS_DIR')
        if not sasdir:
            logger.log('error', 'SAS_DIR is not defined. Please initialise SAS.')
            raise Exception('SAS_DIR is not defined. Please initialise SAS.')
        else:
            logger.log('info', f'SAS_DIR = {sasdir}') 

        sasccfpath = os.environ.get('SAS_CCFPATH')
        if not sasccfpath:
            logger.log('error', 'SAS_CCFPATH not set. Please define it.')
            raise Exception('SAS_CCFPATH not set. Please define it.')
        else:
            logger.log('info',f'SAS_CCFPATH = {sasccfpath}')
        
        os.chdir(self.data_dir)
        logger.log('info', f'Changed directory to {self.data_dir}')

        print(f'''

        Starting SAS session

        Data directory = {self.data_dir}

        ''')

        # Set directories for the observation, odf, pps, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.odfid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.work_dir = os.path.join(self.obs_dir,'work')

        # Checks if obs_dir exists. Removes it if overwrite = True.
        # Default overwrite = False.
        if os.path.exists(self.obs_dir):
            if not overwrite:
                logger.log('info', f'Existing directory for {self.odfid} found ...')
                logger.log('info', f'Searching {self.data_dir}/{self.odfid} for ccf.cif and *SUM.SAS files ...')

                # Looking for ccf.cif file.
                if self.files['sas_ccf'] == None:
                    logger.log('info', f'Path to ccf.cif file not given. Will search for it.')
                    for path, directories, files in os.walk(self.obs_dir):
                        for file in files:
                            if 'ccf.cif' in file:
                                logger.log('info', f'Found ccf.cif file in {path}.')
                                self.files['sas_ccf'] = os.path.join(path,file)
                else:
                    # Check if ccf.cif file exists.
                    try:
                        os.path.exists(self.files['sas_ccf'])
                        logger.log('info', '{0} is present'.format(self.files['sas_ccf']))
                    except FileExistsError:
                        logger.log('error', 'File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                        print('File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                        sys.exit(1)

                # Set 'SAS_CCF' enviroment variable.
                #### Potential Bug Here, check it out. obs_dir exists, overwrite False, but ccf.cif doesn't exist, causes problem?
                os.environ['SAS_CCF'] = self.files['sas_ccf']
                logger.log('info', 'SAS_CCF = {0}'.format(self.files['sas_ccf']))
                print('SAS_CCF = {}'.format(self.files['sas_ccf']))

                # Looking for *SUM.SAS file.
                if self.files['sas_odf'] == None:
                    logger.log('info', f'Path to *SUM.SAS file not given. Will search for it.')
                    for path, directories, files in os.walk(self.obs_dir):
                        for file in files:
                            if 'SUM.SAS' in file:
                                logger.log('info', f'Found *SUM.SAS file in {path}.')
                                self.files['sas_odf'] = os.path.join(path,file)
                else:
                    # Check if *SUM.SAS file exists.
                    try:
                        os.path.exists(self.files['sas_odf'])
                        logger.log('info', '{0} is present'.format(self.files['sas_odf']))
                    except FileExistsError:
                        logger.log('error', 'File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                        print('File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                        sys.exit(1)
                        
                # Check that the SUM.SAS file PATH keyword points to a real ODF directory
                with open(self.files['sas_odf']) as inf:
                    lines = inf.readlines()
                    for line in lines:
                        if 'PATH' in line:
                            key, path = line.split()
                            if not os.path.exists(path):
                                logger.log('error', f'Summary file PATH {path} does not exist. Rerun odfcompile with overwrite=True.')
                                raise Exception(f'Summary file PATH {path} does not exist. Rerun odfcompile with overwrite=True.')
                            MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                            if not os.path.exists(MANIFEST[0]):
                                logger.log('error', f'Missing {MANIFEST[0]} file in {path}. Missing ODF components? Rerun odfcompile with overwrite=True.')
                                raise Exception(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components? Rerun odfcompile with overwrite=True.')
                
                # Set 'SAS_ODF' enviroment variable.
                os.environ['SAS_ODF'] = self.files['sas_odf']
                logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
                print('SAS_ODF = {0}'.format(self.files['sas_odf']))

                self.get_active_instruments()

                if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
                # Exit the odfcompile function. Everything is set.
                return
            else:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                logger.log('info', f'Removing existing directory {self.obs_dir} ...')
                print(f'\n\nRemoving existing directory {self.obs_dir} ...')
                shutil.rmtree(self.obs_dir)

        # Start fresh with new download.
        # Identify the download level.
        levelopts = ['ODF', 'PPS', 'ALL']
        if level not in levelopts:
            logger.log('error', 'ODF request level is undefined!')
            print(f'Options for level are {levelopts[0]}, {levelopts[1]}, or {levelopts[2]}')
            raise Exception('ODF request level is undefined!')
        else:
            logger.log('info', f'Will download ODF with level {level}') 

        # Function for downloading a single odfid set.
        download_data(self.odfid,self.data_dir,level=self.level,
                      encryption_key=self.encryption_key,repo=self.repo,
                      logger=logger)

        # If only PPS files were requested then odfcompile stops here.
        # Else will run cifbuild and odfingest.
        if level == 'PPS':
            ppsdir = os.path.join(self.data_dir, self.odfid, 'pps')
            ppssumhtml = 'P' + self.odfid + 'OBX000SUMMAR0000.HTM'
            ppssumhtmlfull = os.path.join(ppsdir, ppssumhtml)
            ppssumhtmllink = 'file://' + ppssumhtmlfull
            logger.log('info', f'PPS products can be found in {ppsdir}')
            print(f'\nPPS products can be found in {ppsdir}\n\nLink to Observation Summary html: {ppssumhtmllink}')
        else:
            # Run cifbuild and odfingest on the new data.
            os.chdir(self.odf_dir)
            logger.log('info', f'Changed directory to {self.odf_dir}')

            # Checks that the MANIFEST file is there
            MANIFEST = glob.glob('MANIFEST*')
            try:
                os.path.exists(MANIFEST[0])
                logger.log('info', f'File {MANIFEST[0]} exists')
            except FileExistsError:
                logger.log('error', f'File {MANIFEST[0]} not present. Please check ODF!')
                print(f'File {MANIFEST[0]} not present. Please check ODF!')
                sys.exit(1)

            # Here the ODF is fully untarred below odfid subdirectory
            # Now we start preparing the SAS_ODF and SAS_CCF
            logger.log('info', f'Setting SAS_ODF = {self.odf_dir}')
            print(f'\nSetting SAS_ODF = {self.odf_dir}')
            os.environ['SAS_ODF'] = self.odf_dir

            # Change to working directory
            if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
            os.chdir(self.work_dir)

            # Run cifbuild
            if cifbuild_opts:
                cifbuild_opts_list = cifbuild_opts.split(" ") 
                cmd = ['cifbuild']
                cmd = cmd + cifbuild_opts_list
                logger.log('info', f'Running cifbuild with {cifbuild_opts} ...')
                print(f'\nRunning cifbuild with {cifbuild_opts} ...')
            else:
                cmd = ['cifbuild']
                logger.log('info', f'Running cifbuild...')
                print(f'\nRunning cifbuild...')
            
            ##### Running cifbuild
            rc = subprocess.run(cmd)
            if rc.returncode != 0:
                logger.log('error', 'cifbuild failed to complete')
                raise Exception('cifbuild failed to complete')
            
            # Check whether ccf.cif is produced or not
            ccfcif = glob.glob('ccf.cif')
            try:
                os.path.exists(ccfcif[0])
                logger.log('info', f'CIF file {ccfcif[0]} created')
            except FileExistsError:
                logger.log('error','The ccf.cif was not produced')
                print('ccf.cif file is not produced')
                sys.exit(1)
            
            # Sets SAS_CCF variable
            fullccfcif = os.path.join(self.work_dir, 'ccf.cif')
            logger.log('info', f'Setting SAS_CCF = {fullccfcif}')
            print(f'\nSetting SAS_CCF = {fullccfcif}')
            os.environ['SAS_CCF'] = fullccfcif
            self.files['sas_ccf'] = fullccfcif

            # Now run odfingest
            if odfingest_opts:
                odfingest_opts_list = odfingest_opts.split(" ")
                cmd = ['odfingest'] 
                cmd = cmd + odfingest_opts_list
                logger.log('info', f'Running odfingest with {odfingest_opts} ...')
                print(f'\nRunning odfingest with {odfingest_opts} ...')
            else:
                cmd = ['odfingest']
                logger.log('info','Running odfingest...') 
                print('\nRunning odfingest...')
            
            ##### Running odfingest
            rc = subprocess.run(cmd)
            if rc.returncode != 0:
                logger.log('error', 'odfingest failed to complete')
                raise Exception('odfingest failed to complete.')
            else:
                logger.log('info', 'odfingest successfully completed')

            # Check whether the SUM.SAS has been produced or not
            sumsas = glob.glob('*SUM.SAS')
            try:
                os.path.exists(sumsas[0])
                logger.log('info', f'SAS summary file {sumsas[0]} created')
            except FileExistsError:
                logger.log('error','SUM.SAS file was not produced') 
                print('SUM.SAS file was not produced')
                sys.exit(1)
            
            # Set the SAS_ODF to the SUM.SAS file
            fullsumsas = os.path.join(self.work_dir, sumsas[0])
            os.environ['SAS_ODF'] = fullsumsas
            logger.log('info', f'Setting SAS_ODF = {fullsumsas}')
            print(f'\nSetting SAS_ODF = {fullsumsas}')
            self.files['sas_odf'] = fullsumsas
            
            # Check that the SUM.SAS file has the right PATH keyword
            with open(self.files['sas_odf']) as inf:
                lines = inf.readlines()
                for line in lines:
                    if 'PATH' in line:
                        key, path = line.split()
                        if path != self.odf_dir:
                            logger.log('error', f'SAS summary file PATH {path} mismatchs {self.odf_dir}')
                            raise Exception(f'SAS summary file PATH {path} mismatchs {self.odf_dir}')
                        else:
                            logger.log('info', f'Summary file PATH keyword matches {self.odf_dir}')
                            print(f'\nWarning: Summary file PATH keyword matches {self.odf_dir}')

            self.get_active_instruments()

            print(f'''\n\n
            SAS_CCF = {self.files['sas_ccf']}
            SAS_ODF = {self.files['sas_odf']}
            \n''')

    def runanalysis(self,task,inargs,rerun=False,logFile='DEFAULT'):
        """
        A wrapper for the wrapper. Yes. I know.

        For certain SAS tasks it will check if the related files are already
        present. If they are, it will not run again, unless "rerun=True". For 
        all other tasks it will simply call the standard pySAS wrapper.

        Lists of output files are stored in the dictionary self.files{}.

        SAS Tasks that it currently works for:
            --epproc
            --emproc

        More will be added as needed.
        """
        self.task = task
        self.inargs = inargs
        self.rerun = rerun
        self.logFile = logFile

        print(self.inargs)

        # Make sure we are in the right place!
        if os.path.isdir(self.work_dir):
            os.chdir(self.work_dir)
        else:
            print(f'The directory for the observation ID ({self.odfid}) does not seem to exist!\n    {self.obs_dir}')
            print('Has \'odfcompile\' been run?')
            raise Exception(f'Problem with the directory for odfID = {self.odfid}!')

        print(f"   SAS command to be executed: {self.task}, with arguments; \n{self.inargs}")
        print(f"Running {self.task} ..... \n")

        if self.task == 'epproc':
            # Check if epproc has already run. If it has, do not run again 
            exists = False
            self.files['pnevt_list'] = []
            for root, dirs, files in os.walk("."):  
                for filename in files:
                    if (filename.find('EPN') != -1) and filename.endswith('Evts.ds'):
                        self.files['pnevt_list'].append(os.path.abspath(os.path.join(root,filename)))
                        exists = True
            if exists and not self.rerun:    
                print(" > " + str(len(self.files['pnevt_list'])) + " EPIC-pn event list found. Not running epproc again.\n")
                for x in self.files['pnevt_list']:
                    print("    " + x + "\n")
                print("..... OK")
            else:
                w(self.task,self.inargs,logFile=self.logFile).run()      # <<<<< Execute SAS task
                exists = False
                self.files['pnevt_list'] = []
                for root, dirs, files in os.walk("."):  
                    for filename in files:
                        if (filename.find('EPN') != -1) and filename.endswith('Evts.ds'):
                            self.files['pnevt_list'].append(os.path.abspath(os.path.join(root,filename)))
                            exists = True
                if exists:    
                    print(" > " + str(len(self.files['pnevt_list'])) + " EPIC-pn event list found after running epproc.\n")
                    for x in self.files['pnevt_list']:
                        print("    " + x + "\n")
                    print("..... OK")
                else:
                    print("Something has gone wrong with epproc. I cant find any event list files after running. \n")
        
        elif self.task == 'emproc':
            # Check if emproc has already run. If it has, do not run again 
            exists = False
            self.files['m1evt_list'] = []
            self.files['m2evt_list'] = []
            for root, dirs, files in os.walk("."):  
                for filename in files:
                    if (filename.find('EMOS1') != -1) and filename.endswith('ImagingEvts.ds'):
                        self.files['m1evt_list'].append(os.path.abspath(os.path.join(root,filename)))
                        exists = True
                    if (filename.find('EMOS2') != -1) and filename.endswith('ImagingEvts.ds'):
                        self.files['m2evt_list'].append(os.path.abspath(os.path.join(root,filename)))
                        exists = True
            if exists and not self.rerun:    
                print(" > " + str(len(self.files['m1evt_list'])) + " EPIC-MOS1 event list found. Not running emproc again.\n")
                for x in self.files['m1evt_list']:
                    print("    " + x + "\n")
                print(" > " + str(len(self.files['m2evt_list'])) + " EPIC-MOS2 event list found. Not running emproc again.\n")
                for x in self.files['m2evt_list']:
                    print("    " + x + "\n")
                print("..... OK")
            else:
                w(self.task,self.inargs,logFile=self.logFile).run()      # <<<<< Execute SAS task
                exists = False 
                self.files['m1evt_list'] = []
                self.files['m2evt_list'] = []
                for root, dirs, files in os.walk("."):  
                    for filename in files:
                        if (filename.find('EMOS1') != -1) and filename.endswith('ImagingEvts.ds'):
                            self.files['m1evt_list'].append(os.path.abspath(os.path.join(root,filename)))
                            exists = True 
                        if (filename.find('EMOS2') != -1) and filename.endswith('ImagingEvts.ds'):
                            self.files['m2evt_list'].append(os.path.abspath(os.path.join(root,filename)))
                            exists = True            
                if exists:    
                    print(" > " + str(len(self.files['m1evt_list'])) + " EPIC-MOS1 event list found after running emproc.\n")
                    for x in self.files['m1evt_list']:
                        print("    " + x + "\n")
                    print(" > " + str(len(self.files['m2evt_list'])) + " EPIC-MOS2 event list found after running emproc.\n")
                    for x in self.files['m2evt_list']:
                        print("    " + x + "\n")
                    print("..... OK")
                else:
                    print("Something has gone wrong with emproc. I cant find any event list file. \n")
        else:
            w(self.task,self.inargs).run()      # <<<<< Execute SAS task

    def basic_setup(self, **kwargs):
        """
        Function to do all basic analysis tasks. The function will:

            1. Call the function 'odfcompile'
                A. Download data
                B. Run 'cifbuild'
                C. Run 'odfingest'
            2. Run 'epproc'
            3. Run 'emproc'

        All input arguments for 'odfcompile' can be passed to 'basic_setup'.

        Input arguments for 'epproc' and 'emproc' can also be passed in 
        using 'epproc_args' and 'emproc_args' respectively. By defaut 
        'epproc' and 'emproc' will not rerun if output files are found,
        but they can be forced to rerun by setting 'rerun=True' as an
        input to 'basic_setup'.
        """

        self.odfcompile(data_dir       = kwargs.get('data_dir', None),
                        level          = kwargs.get('level', 'ODF'),
                        sas_ccf        = kwargs.get('sas_ccf', None),
                        sas_odf        = kwargs.get('sas_odf', None),
                        cifbuild_opts  = kwargs.get('cifbuild_opts', None),
                        odfingest_opts = kwargs.get('odfingest_opts', None),
                        encryption_key = kwargs.get('encryption_key', None),
                        overwrite      = kwargs.get('overwrite', False),
                        repo           = kwargs.get('repo', 'esa'))

        self.runanalysis('epproc',
                         kwargs.get('epproc_args', []),
                         rerun = kwargs.get('rerun', False),
                         logFile=kwargs.get('logFile', 'epproc.log'))

        self.runanalysis('emproc',
                         kwargs.get('emproc_args', []),
                         rerun = kwargs.get('rerun', False),
                         logFile=kwargs.get('logFile', 'emproc.log'))
    
    def get_active_instruments(self):
        """
        Checks odf summary file for which instruments were active for that odf.

        Assumes that 'sas_odf' already exists and contains the correct path.

        Also assumes file name and path are stored in self.files['sas_odf'].
        """

        # Get information about the instruments.
        self.active_instruments = {}
        with open(self.files['sas_odf']) as inf:
            lines = inf.readlines()
            for i,line in enumerate(lines):
                if '// Instrument Record' in line:
                    active = lines[i+4][0]
                    if active == 'N': active = False
                    if active == 'Y': active = True
                    self.active_instruments[lines[i+3][0:2]] = active

        # Basic sanity checks
        bad_sum_file = False
        inst_list = list(self.active_instruments.keys())
        true_list = ['M1', 'M2', 'R1', 'R2', 'PN', 'OM']
        diff = set(inst_list) ^ set(true_list)
        if len(diff) > 0: bad_sum_file = True

        if bad_sum_file:
            print('Something is wrong with the odf summary file: {0}'.format(self.files['sas_odf']))

        return

def generate_logger(logname=None,log_dir=None):
    """
    
    """
    if not logname:
        logname = 'general_sas'

    sastasklogdir = os.environ.get('SAS_TASKLOGDIR')

    # Where are we?
    startdir = os.getcwd()

    # Check where the logger should go.
    if log_dir:
        sastasklogdir = log_dir

    if not sastasklogdir:
        sastasklogdir = startdir

    if not os.path.isdir(sastasklogdir):
        sastasklogdir = startdir

    # This will put the log files in data_dir.
    os.environ['SAS_TASKLOGDIR'] = sastasklogdir

    # Create the logger
    logger = TL(logname)

    return logger

def download_data(odfid,data_dir,level='ODF',encryption_key=None,repo='esa',logger=None):
    """
    Downloads, or copies, data from chosen repository. 

    Will silently overwrite any preexisting data files and remove any existing
    pipeline products. Will create diretory stucture in 'data_dir' for odf.

    Inputs:

            --odfid:          (string): ID of ODF in string format.

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        data_dir/odfid.
                                        Default: 'pwd', returns the current directory.

            --level:          (string): Level of data products to download.
                                        Default: 'ODF'
                                        Can be 'ODF, 'PPS' or 'ALL'.

            --encryption_key: (string): Encryption key for propietary data, a string 32 
                                        characters long. -OR- path to file containing 
                                        ONLY the encryption key.

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                          'esa' (data from Europe/ESA) or 
                                          'heasarc' (data from North America/NASA) or
                                          'sciserver' (if user is on sciserver)
    """

    if not logger:
        logger = generate_logger(logname=f'download_{odfid}',log_dir=data_dir)

    # Set directories for the observation, odf, and working
    obs_dir = os.path.join(data_dir,odfid)
    odf_dir = os.path.join(obs_dir,'ODF')
    pps_dir = os.path.join(obs_dir,'PPS')

    # Checks if obs_dir exists. Removes it.
    if os.path.exists(obs_dir):
        logger.log('info', f'Removing existing directory {obs_dir} ...')
        print(f'\n\nRemoving existing directory {obs_dir} ...')
        shutil.rmtree(obs_dir)
    
    # Creates subdirectory odfid to move or unpack observation files
    # and makes subdirectories.
    logger.log('info', f'Creating observation directory {obs_dir} ...')
    print(f'\nCreating observation directory {obs_dir} ...')
    os.mkdir(obs_dir)

    logger.log('info', 'Requesting odfid = {} from XMM-Newton Science Archive\n'.format(odfid))
    print('Requesting odfid = {} from XMM-Newton Science Archive\n'.format(odfid))
        
    if repo == 'esa':
        logger.log('info', f'Changed directory to {obs_dir}')
        os.chdir(obs_dir)
        odftar = odfid + '.tar.gz'
        if level == 'ALL':
            level = ['ODF','PPS']
        else:
            level = [level]
        for levl in level:
            # Download the odfid from ESA, using astroquery
            from astroquery.esa.xmm_newton import XMMNewton
            logger.log('info', f'Downloading {odfid}, level {levl} into {obs_dir}')
            print(f'\nDownloading {odfid}, level {levl} into {obs_dir}. Please wait ...\n')
            XMMNewton.download_data(odfid, level=levl)
            # Check that the tar.gz file has been downloaded
            try:
                os.path.exists(odftar)
                logger.log('info', f'{odftar} found.') 
            except FileExistsError:
                logger.log('error', f'File {odftar} is not present. Not downloaded?')
                print(f'File {odftar} is not present. Not downloaded?')
                sys.exit(1)

            if levl == 'ODF':    
                os.mkdir(odf_dir)
            elif levl == 'PPS':
                os.mkdir(pps_dir)

            # Untars the odfid.tar.gz file
            logger.log('info', f'Unpacking {odftar} ...')
            print(f'\nUnpacking {odftar} ...\n')

            try:
                with tarfile.open(odftar,"r:gz") as tar:
                    if levl == 'ODF':
                        tar.extractall(path=odf_dir)
                    elif levl == 'PPS':
                        tar.extractall(path=pps_dir)
                os.remove(odftar)
                logger.log('info', f'{odftar} extracted successfully!')
                logger.log('info', f'{odftar} removed')
            except tarfile.ExtractError:
                logger.log('error', 'tar file extraction failed')
                raise Exception('tar file extraction failed')
    elif repo == 'heasarc':
        #Download the odfid from HEASARC, using wget
        if level == 'ALL':
            levl = ''
        else:
            levl = level
        logger.log('info', f'Downloading {odfid}, level {levl}')
        print(f'\nDownloading {odfid}, level {level}. Please wait ...\n')
        cmd = f'wget -m -nH -e robots=off --cut-dirs=4 -l 2 -np https://heasarc.gsfc.nasa.gov/FTP/xmm/data/rev0/{odfid}/{levl}'
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f'Problem downloading data!')
            logger.log('error', f'File download failed!')
            raise Exception('File download failed!')
        for path, directories, files in os.walk('.'):
            for file in files:
                if 'index.html' in file:
                    os.remove(os.path.join(path,file))
            for direc in directories:
                if '4XMM' in direc:
                    shutil.rmtree(os.path.join(path,direc))
                if level == 'ODF' and direc == 'PPS':
                    shutil.rmtree(os.path.join(path,direc))
                if level == 'PPS' and direc == 'ODF':
                    shutil.rmtree(os.path.join(path,direc))
    elif repo == 'sciserver':
        # Copies data into personal storage space.
        dest_dir = obs_dir
        if level == 'ALL':
            levl = ''
        else:
            levl = level
            dest_dir = os.path.join(dest_dir,levl)
        if levl == 'ODF':    
            os.mkdir(odf_dir)
        elif levl == 'PPS':
            os.mkdir(pps_dir)
        archive_data = f'/home/idies/workspace/headata/FTP/xmm/data/rev0//{odfid}/{levl}'
        logger.log('info', f'Copying data from {archive_data} ...')
        print(f'\nCopying data from {archive_data} ...')
        shutil.copytree(archive_data,dest_dir,dirs_exist_ok=True)

    # Check if data is encrypted. Decrypt the data.
    encrypted = glob.glob('**/*.gpg', recursive=True)
    if len(encrypted) > 0:
        logger.log('info', f'Encrypted files found! Decrypting files!')

        # Checks for encryption key or file with key.
        # If no encryption key is given then go looking for a file.
        encryption_file = None
        if encryption_key == None:
            encryption_file = glob.glob(os.path.join(self.data_dir,f'*{odfid}*'))
            if len(encryption_file) == 0:
                encryption_file = glob.glob(os.path.join(self.data_dir,'*key*'))
            if len(encryption_file) > 1:
                logger.log('error', 'Multiple possible encryption key files. Specify encryption key file.')
                raise Exception('Multiple possible encryption key files.')
            if len(encryption_file) == 0:
                encryption_file = 'None'
            if os.path.isfile(encryption_file[0]):
                logger.log('info', f'File with encryption key found: {encryption_file}')
            else:
                print('File decryption failed. No encryption key found.')
                print(f'Regular file with the encryption key needs to be placed in: {self.data_dir}')
                logger.log('error', 'File decryption failed. No encryption key found.')
                raise Exception('File decryption failed. No encryption file found.')
        elif os.path.isfile(encryption_key):
            logger.log('info', f'Ecryption key is in file: {encryption_key}')
            encryption_file = encryption_key
        if encryption_file is not None:
            logger.log('info', f'Reading ecryption key from: {encryption_file}')
            with open(encryption_file) as f:
                lines = f.readlines()
                encryption_key = lines[0]
        if encryption_key == None:
            print(f'No encryption key found in {encryption_file}')
            print(f'Regular file with the encryption key needs to be placed in: {self.data_dir}')
            logger.log('error', 'File decryption failed. No encryption key found.')
            raise Exception('File decryption failed. No encryption key found.')
        
            
        for file in encrypted:
            out_file = file[:-4]
            if os.path.exists(out_file):
                logger.log('info', f'Already decrypted file found: {out_file}')
                print(f'Already decrypted file found: {out_file}')
            else:
                logger.log('info', f'Decrypting {file}')
                cmd = 'echo {0} | gpg --batch -o {1} --passphrase-fd 0 -d {2}'.format(encryption_key,out_file,file)
                result = subprocess.run(cmd, shell=True)
                if result.returncode != 0:
                    print(f'Problem decrypting {file}')
                    logger.log('error', f'File decryption failed, key used {encryption_key}')
                    raise Exception('File decryption failed')
                os.remove(file)
                logger.log('info', f'{file} removed')
    else:
        logger.log('info','No encrypted files found.')

    for file in glob.glob('**/*.gz', recursive=True):
        logger.log('info', f'Unpacking {file} ...')
        print(f'Unpacking {file} ...')
        with gzip.open(f'{file}', 'rb') as f_in:
            out_file = file[:-3]
            with open(out_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file)
        logger.log('info', f'{file} removed')

    for file in glob.glob('**/*.TAR', recursive=True):
        logger.log('info', f'Unpacking {file} ...')
        print(f'Unpacking {file} ...')
        with tarfile.open(file,"r") as tar:
            tar.extractall(path=odf_dir)
        os.remove(file)
        logger.log('info', f'{file} removed')
    
