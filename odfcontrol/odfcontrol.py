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
import os, sys, shutil, glob

# Third party imports

# Local application imports
# from .version import VERSION, SAS_RELEASE, SAS_AKA
from ..logger import TaskLogger as TL
from ..configutils import sas_cfg
from ..init_sas import initializesas
from ..wrapper import Wrapper as w
from ..sasutils import generate_logger,download_data

# __version__ = f'odfcontrol (startsas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 
__version__ = 'odfcontrol (odfcontrol-1.0)'
__all__ = ['ODFobject', 'download_data']


class ODFobject(object):
    """
    Class for observation data files (ODF).

        An odfid (Obs ID) is required.

        data_dir is the base directory where you store all XMM data.

        Data is organized as:
            data_dir = /path/to/data/
            obs_dir = /path/to/data/odfid/
        With subdirectories and files:
                odf_dir  = /path/to/data/odfid/ODF/
                work_dir = /path/to/data/odfid/work/
                SAS_CCF  = work_dir/ccf.cif
                SAS_ODF  = work_dir/*SUM.SAS

                
        Directory links and OdfID information are stored as
        variables in the ODFobject.

            self.odfid    : The Obs ID required to make the ODFobject
            self.data_dir : Path to the data directory
            self.files    : A dictionary containing links to event lists
                            and other important files

                            Default dictionary keys are:
                                'sas_ccf'
                                'sas_odf'
                                'PNevt_list'
                                'M1evt_list'
                                'M2evt_list'
                                'R1evt_list'
                                'R2evt_list'
                                'OMevt_list'

            self.obs_dir  : Path to the observation directory
            self.odf_dir  : Path to the ODF directory
            self.pps_dir  : Path to the PPS directory
            self.work_dir : Path to the working directory

    """

    def __init__(self,odfid,data_dir=None):
        self.odfid = odfid
        self.data_dir = data_dir
        self.files = {}
        self.set_odfid()

    def inisas(self,sas_dir,sas_ccfpath,verbosity=4,suppress_warning=1):
        """
        --Not intended to be used by the end user. Internal use only.--

        Simple wrapper for 'initializesas' defined in init_sas.py.

        SAS initialization should happen automatically.
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
        --Not intended to be used by the end user. Internal use only.--

        Basic method for setting the environment variables for a single 
        'ObsID'.

        Checks for the existence of various directories. If a directory 
        is not found then set_odfid will stop and use 'return' command.
        Directories that will be checked for (in this order):
            
            data_dir
            obs_dir
            odf_dir -or- pps_dir
            work_dir

        Then checks for the ccf.cif, *SUM.SAS files and event lists.

        Similar to calibrate_odf, but will not download any data, 
        will not calibrate it, or do anything other than link to 
        files and directories. 
        """

        # Where are we?
        startdir = os.getcwd()

        # Brief check to see if data_dir was 
        # given on odfobject creation.
        if self.data_dir != None:
            data_dir = self.data_dir
        else:
            data_dir = sas_cfg.get("sas", "data_dir")

        # Start checking data_dir
        if os.path.exists(data_dir):
            self.data_dir = data_dir
        else:
            # Nothing can be done! User must run calibrate_odf!
            return

        # Set directories for the observation, odf, pps, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.odfid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.pps_dir  = os.path.join(self.obs_dir,'PPS')
        self.work_dir = os.path.join(self.obs_dir,'work')

        if os.path.exists(self.obs_dir):
            print(f'obs_dir found at {self.obs_dir}.')
        else:
            # obs_dir not found! Nothing can be done!
            return
        
        if os.path.exists(self.odf_dir):
            print(f'odf_dir found at {self.odf_dir}.')
            if os.path.exists(self.pps_dir):
                print(f'pps_dir found at {self.pps_dir}.')
        else:
            if os.path.exists(self.pps_dir):
                print(f'pps_dir found at {self.pps_dir}.')
            else:
                print(f'ODF and PPS directories not found! User must download data!')
                return
        
        if os.path.exists(self.work_dir):
            print(f'work_dir found at {self.work_dir}.')
        else:
            print(f'work_dir not found! User must run create it!')
            return

        # Only generate logger if observation directory exists.
        logger = generate_logger(logname='odf_'+self.odfid, log_dir=self.data_dir)
        logger.log('info', f'Data directory = {self.data_dir}')
        logger.log('info', f'Existing directory for {self.odfid} found ...')
        logger.log('info', f'Searching {self.data_dir}/{self.odfid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        exists = self.check_for_ccf_cif(logger)
        if not exists:
            print('ccf.cif file not present! User must run calibrate_odf!')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        logger.log('info', 'SAS_CCF = {0}'.format(self.files['sas_ccf']))
        print('SAS_CCF = {}'.format(self.files['sas_ccf']))

        # Looking for *SUM.SAS file.
        exists = self.check_for_SUM_SAS(logger)
        if not exists:
            print('*SUM.SAS file not present! User must run calibrate_odf!')
            return
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
        print('SAS_ODF = {0}'.format(self.files['sas_odf']))

        # Check for previously generated event lists.
        self.get_event_lists()

        # Exit the set_odfid function. Everything is set.
        return

    def sas_talk(self,verbosity=4,suppress_warning=1):
        """
        Simple function to set general SAS veriables 'verbosity' 
        and 'suppress_warning'.
        """

        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        os.environ['SAS_VERBOSITY'] = '{}'.format(self.verbosity)
        os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(self.suppress_warning)

    def calibrate_odf(self,data_dir=None,level='ODF',
                      sas_ccf=None,sas_odf=None,
                      cifbuild_opts=[],odfingest_opts=[],
                      encryption_key=None,overwrite=False,
                      recalibrate=False,repo='esa'):
        """
        Before running this function an ODFobject must be created first. e.g.

            odf = pysas.odfcontrol.ODFobject(obsid)

        This function can then be used as, 
        
            odf.calibrate_odf()

        The calibrate_odf function will automatically look in data_dir for the subdirectory 
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

            --cifbuild_opts:    (list): Options for cifbuild.

            --odfingest_opts:   (list): Options for odfingest.

            --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                        characters long. -OR- Path to file containing 
                                        ONLY the encryption key.

            --overwrite:     (boolean): If True will force overwrite of data if odfid 
                                        data already exists in data_dir/.

            --recalibrate:   (boolean): If True will rerun odfingest and cifbuild.

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
        if cifbuild_opts == None:
            cifbuild_opts = []
        self.cifbuild_opts = cifbuild_opts
        if odfingest_opts == None:
            odfingest_opts = []
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

        sas_ccfpath = os.environ.get('SAS_CCFPATH')
        if not sas_ccfpath:
            logger.log('error', 'SAS_CCFPATH not set. Please define it.')
            raise Exception('SAS_CCFPATH not set. Please define it.')
        else:
            logger.log('info',f'SAS_CCFPATH = {sas_ccfpath}')
        
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

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
        # Runs calibration if recalibrate = True. Default recalibrate = False
        # Else, looks for ccf.cif and *SUM.SAS files.
        # If ccf.cif and *SUM.SAS files are not found then will run calibration.
        if os.path.exists(self.obs_dir):
            logger.log('info', f'Existing directory for {self.odfid} found ...')
            if overwrite:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                # If the obs_dir is removed then we don't have to do anything else.
                logger.log('info', f'Removing existing directory {self.obs_dir} ...')
                print(f'\n\nRemoving existing directory {self.obs_dir} ...')
                shutil.rmtree(self.obs_dir)
            elif recalibrate:
                self.run_calibration(cifbuild_opts,odfingest_opts,logger)
            else:
                logger.log('info', f'Searching {self.obs_dir} for ccf.cif and *SUM.SAS files ...')
                # Looking for ccf.cif file.
                if self.files['sas_ccf'] == None:
                    ccf_exists = self.check_for_ccf_cif(logger)
                else:
                    # Check if ccf.cif file path given by user exists.
                    try:
                        os.path.exists(self.files['sas_ccf'])
                        logger.log('info', '{0} is present'.format(self.files['sas_ccf']))
                        ccf_exists = True
                    except FileExistsError:
                        # The only way to get this error is if the user provided a bad filename or path.
                        logger.log('error', 'File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                        print('File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                        sys.exit(1)
                
                # Looking for *SUM.SAS file.
                if self.files['sas_odf'] == None:
                    SUM_exists = self.check_for_SUM_SAS(logger)                    
                else:
                    # Check if *SUM.SAS file path given by user exists.
                    try:
                        SUM_exists = self.check_for_SUM_SAS(logger,user_defined_file=self.files['sas_odf'])
                        if SUM_exists:
                            logger.log('info', '{0} is present'.format(self.files['sas_odf']))
                    except FileExistsError:
                        # The only way to get this error is if the user provided a bad filename or path.
                        logger.log('error', 'File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                        print('File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                        sys.exit(1)

                if ccf_exists and SUM_exists:
                    # Set 'SAS_CCF' enviroment variable.
                    os.environ['SAS_CCF'] = self.files['sas_ccf']
                    logger.log('info', 'SAS_CCF = {0}'.format(self.files['sas_ccf']))
                    print('SAS_CCF = {}'.format(self.files['sas_ccf']))

                    # Set 'SAS_ODF' enviroment variable.
                    os.environ['SAS_ODF'] = self.files['sas_odf']
                    logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
                    print('SAS_ODF = {0}'.format(self.files['sas_odf']))
                else:
                    # If the ccf.cif or *SUM.SAS files are not present, then run calibration.
                    self.run_calibration(cifbuild_opts,odfingest_opts,logger) 
                
                # Set 'SAS_ODF' enviroment variable.
                os.environ['SAS_ODF'] = self.files['sas_odf']
                logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
                print('SAS_ODF = {0}'.format(self.files['sas_odf']))

                self.get_active_instruments()

                if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
                # Exit the calibrate_odf function. Everything is set.
                return

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

        # If only PPS files were requested then calibrate_odf stops here.
        # Else will run cifbuild and odfingest.
        if level == 'PPS':
            ppsdir = os.path.join(self.data_dir, self.odfid, 'PPS')
            ppssumhtml = 'P' + self.odfid + 'OBX000SUMMAR0000.HTM'
            ppssumhtmlfull = os.path.join(ppsdir, ppssumhtml)
            ppssumhtmllink = 'file://' + ppssumhtmlfull
            logger.log('info', f'PPS products can be found in {ppsdir}')
            print(f'\nPPS products can be found in {ppsdir}\n\nLink to Observation Summary html: {ppssumhtmllink}')
        else:
            self.run_calibration(cifbuild_opts,odfingest_opts,logger)

    def run_calibration(self,cifbuild_opts,odfingest_opts,logger):
        """
        --Not intended to be used by the end user. Internal use only.--

        Making this a separate function since it can be called from different places.
        Prevent duplication of code.
        """
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
        logger.log('info', f'Running cifbuild with inputs: {cifbuild_opts} ...')
        print(f'\nRunning cifbuild with inputs: {cifbuild_opts} ...')
        w('cifbuild',cifbuild_opts).run()
        
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
        logger.log('info', f'Running odfingest with inputs: {odfingest_opts} ...')
        print(f'\nRunning odfingest with inputs: {odfingest_opts} ...')
        w('odfingest',odfingest_opts).run()

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

    def odfcompile(self,data_dir=None,level='ODF',
               sas_ccf=None,sas_odf=None,
               cifbuild_opts=[],odfingest_opts=[],
               encryption_key=None,overwrite=False,repo='esa'):
        # print("Deprication Warning: 'odfcompile' has been replaced by 'calibrate_odf'. \n
        # 'odfcompile' will for now point to 'calibrate_odf', but 'odfcompile' will be removed\n
        # in a future release.")
        """
        Depricated function. Replaced by self.calibrate_odf.
        """
        self.calibrate_odf(data_dir=data_dir,level=level,
                            sas_ccf=sas_ccf,sas_odf=sas_odf,
                            cifbuild_opts=cifbuild_opts,odfingest_opts=odfingest_opts,
                            encryption_key=encryption_key,overwrite=overwrite,repo=repo)

    def run_analysis(self,task,inargs,rerun=False,logFile='DEFAULT'):
        """
        --Not intended to be used by the end user. Internal use only.--

        A wrapper for the wrapper. Yes. I know.

        This function is not intended to be used by the end user, but is
        only called by 'basic_setup'.

        This will check if output files are present for the selected SAS task.
        If they are, will not rerun that SAS task unless "rerun=True".

        Lists of output files are stored in the dictionary self.files{}.

        SAS Tasks that it currently works for:
            --epproc
            --epchain (Warning current version of epchain fails in SAS v. 21)
            --emproc
            --emchain (Warning current version of emchain fails in SAS v. 21)
            --rgsproc

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
            print('Has \'calibrate_odf\' been run?')
            raise Exception(f'Problem with the directory for odfID = {self.odfid}!')
        
        self.get_event_lists(print_output=False)

        run_ep   = False
        run_em   = False
        run_rgs  = False

        # Check if 'epproc' or 'epchain' has been run.
        if (self.task == 'epproc' or self.task == 'epchain') and self.active_instruments['PN']:
            if len(self.files['PNevt_list']) == 0 or self.rerun:
                run_ep   = True
            else:
                print(" > " + str(len(self.files['PNevt_list'])) + " EPIC-pn event list found. Not running {self.task} again.\n")
                for x in self.files['PNevt_list']:
                    print("    " + x + "\n")
                print("..... OK")

        # Check if 'emproc' has been run.
        elif self.task == 'emproc' and (self.active_instruments['M1'] or self.active_instruments['M2']):
            if (len(self.files['M1evt_list']) == 0 and len(self.files['M2evt_list']) == 0) or self.rerun:
                run_em   = True
            else:
                print(" > " + str(len(self.files['M1evt_list'])) + " EPIC-MOS1 event list found. Not running emproc again.\n")
                for x in self.files['M1evt_list']:
                    print("    " + x + "\n")
                print(" > " + str(len(self.files['M2evt_list'])) + " EPIC-MOS2 event list found. Not running emproc again.\n")
                for x in self.files['M2evt_list']:
                    print("    " + x + "\n")
                print("..... OK")

        # Check if 'rgsproc' has been run.
        elif self.task == 'rgsproc' and (self.active_instruments['R1'] or self.active_instruments['R2']):
            if (len(self.files['R1evt_list']) == 0 and len(self.files['R2evt_list']) == 0) or self.rerun:
                run_rgs  = True
            else:
                print(" > " + str(len(self.files['R1evt_list'])) + " RGS1 event list found. Not running rgsproc again.\n")
                for x in self.files['R1evt_list']:
                    print("    " + x + "\n")
                print(" > " + str(len(self.files['R2evt_list'])) + " RGS2 event list found. Not running rgsproc again.\n")
                for x in self.files['R2evt_list']:
                    print("    " + x + "\n")
                print("..... OK")
        
        if run_ep or run_em or run_rgs:
            print(f"   SAS command to be executed: {self.task}, with arguments; \n{self.inargs}")
            print(f"Running {self.task} ..... \n")
            w(self.task,self.inargs,logFile=self.logFile).run()      # <<<<< Execute SAS task

        # Check if run sucsessfully
        self.get_event_lists(print_output=False)
        if (len(self.files['PNevt_list']) == 0) and run_ep:
            print("Something has gone wrong. I cant find any event list files after running epproc. \n")
        if (len(self.files['M1evt_list']) == 0 and len(self.files['M2evt_list']) == 0 and run_em):
            print("Something has gone wrong. I cant find any event list files after running emproc. \n")
        if (len(self.files['R1evt_list']) == 0 and len(self.files['R2evt_list']) == 0 and run_rgs):
            print("Something has gone wrong. I cant find any event list files after running rgsproc. \n")

    def basic_setup(self,run_epproc=True,run_emproc=True,run_rgsproc=True,
                    run_omichain=False,run_epchain=False,run_emchain=False
                    , **kwargs):
        """
        Function to do all basic analysis tasks. The function will:

            1. Call the function 'calibrate_odf'
                A. Download data
                B. Run 'cifbuild'
                C. Run 'odfingest'
            2. Run 'epproc' -OR- 'epchain'
            3. Run 'emproc' -OR- 'emchain'
            4. Run 'rgsproc'
            5. Run 'omichain' (not run by default)

        If 'run_epchain' is set to 'True', then 'epproc' will not run.
        If 'run_emchain' is set to 'True', then 'emproc' will not run.

        All input arguments for 'calibrate_odf' can be passed to 'basic_setup'.

        'calibrate_odf' inputs (with defaults):
               
            data_dir       = None
            level          = 'ODF'
            sas_ccf        = None
            sas_odf        = None
            cifbuild_opts  = []
            odfingest_opts = []
            encryption_key = None
            overwrite      = False
            recalibrate    = False
            repo           = 'esa'

        Input arguments for 'epproc', 'emproc', and 'rgsproc' can also be 
        passed in using 'epproc_args', 'emproc_args', or 'rgsproc_args' 
        respectively (or 'epchain_args' and 'emchain_args'). By defaut 
        'epproc', 'emproc', and 'rgsproc' will not rerun if output files 
        are found, but they can be forced to rerun by setting 'rerun=True' 
        as an input to 'basic_setup'.

        Examples for use:

            odf.basic_setup()

                - Uses the defaults.

            odf.basic_setup(repo='heasarc')

                - Uses the defaults, but downloads data from the HEASARC.

            odf.basic_setup(overwrite=True)

                - Will erase any previous data files for the Obs ID and 
                  download a fresh set of data files.

            odf.basic_setup(recalibrate=True)

                - Will rerun cifbuild and odfingest to generate new 
                  ccf.cif and *SUM.SAS files.

            odf.basic_setup(rerun=True)

                - Will **not** download new files, but will rerun 'epproc',
                  'emproc', and 'rgsproc' and create new event lists.

            odf.basic_setup(repo='heasarc',
                            epproc_args=['withoutoftime=yes'])

                - Downloads data from the HEASARC and runs 'epproc' with the
                  'withoutoftime' option.

            odf.basic_setup(run_epchain=True,
                            run_emchain=True)

                - Will run 'epchain' and 'emchain' instead of 'epproc' and
                  'emproc'.

            odf.basic_setup(run_epproc=False,
                            run_emproc=False)

                - Will not run 'epproc' or 'emproc'. Will only run 'rgsproc'
                  by default.

            odf.basic_setup(run_epproc=False,
                            run_emproc=True,
                            run_rgsproc=False)

                - Will only run 'emproc', **not** 'epproc' or 'rgsproc'.

        """

        self.calibrate_odf(data_dir       = kwargs.get('data_dir', None),
                           level          = kwargs.get('level', 'ODF'),
                           sas_ccf        = kwargs.get('sas_ccf', None),
                           sas_odf        = kwargs.get('sas_odf', None),
                           cifbuild_opts  = kwargs.get('cifbuild_opts', []),
                           odfingest_opts = kwargs.get('odfingest_opts', []),
                           encryption_key = kwargs.get('encryption_key', None),
                           overwrite      = kwargs.get('overwrite', False),
                           repo           = kwargs.get('repo', 'esa'))

        if run_epproc and not run_epchain:
            self.run_analysis('epproc',
                            kwargs.get('epproc_args', []),
                            rerun = kwargs.get('rerun', False),
                            logFile=kwargs.get('logFile', 'epproc.log'))
        
        if run_epchain:
            self.run_analysis('epchain',
                             kwargs.get('epchain_args', []),
                             rerun = kwargs.get('rerun', False),
                             logFile=kwargs.get('logFile', 'epchain.log'))

        if run_emproc and not run_emchain:
            self.run_analysis('emproc',
                             kwargs.get('emproc_args', []),
                             rerun = kwargs.get('rerun', False),
                             logFile=kwargs.get('logFile', 'emproc.log'))
            
        if run_emchain:
            self.run_analysis('emchain',
                             kwargs.get('emchain_args', []),
                             rerun = kwargs.get('rerun', False),
                             logFile=kwargs.get('logFile', 'emchain.log'))
            
        if run_rgsproc:
            self.run_analysis('rgsproc',
                             kwargs.get('rgsproc_args', []),
                             rerun = kwargs.get('rerun', False),
                             logFile=kwargs.get('logFile', 'rgsproc.log'))
        
        if run_omichain:
            self.run_analysis('omichain',
                             kwargs.get('omichain_args', []),
                             rerun = kwargs.get('rerun', False),
                             logFile=kwargs.get('logFile', 'omichain.log'))
    
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
    
    def get_event_lists(self,print_output=True):
        """
        Checks the observation directory (obs_dir) for basic unfiltered 
        event list files created by 'epproc', 'emproc', 'rgsproc', and 
        'omichain'. Stores paths and file names in self.files.

        'self.files' is a dictionary with the following keys:

            'PNevt_list'
            'M1evt_list'
            'M2evt_list'
            'R1evt_list'
            'R2evt_list'
            'OMevt_list'
        """

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
            # Checking for EPIC event lists.
            files = glob.glob(self.obs_dir+'/**/*.ds', recursive=True)
            for filename in files:
                if (filename.find(find_list[inst]) != -1) and filename.endswith('Evts.ds'):
                    self.files[evt_list_list[inst]].append(os.path.abspath(filename))
                    exists = True
            # Checking for RGS event lists.
            files = glob.glob(self.obs_dir+'/**/*EVENLI*FIT', recursive=True)
            for filename in files:
                if (filename.find(find_list[inst]) != -1):
                    self.files[evt_list_list[inst]].append(os.path.abspath(filename))
                    exists = True
            if exists:
                if print_output:
                    print(" > {0} {1} event list(s) found.\n".format(len(self.files[evt_list_list[inst]]),inst_name[inst]))
                    for x in self.files[evt_list_list[inst]]:
                        print("    " + x + "\n")

        return
    
    def check_for_ccf_cif(self,logger):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the ccf.cif file. Making this a function since it is 
        used in several places.
        """

        exists = False

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
            exists = True
        else:
            logger.log('warning', 'ccf.cif file not present! User must run calibrate_odf!')

        return exists
    
    def check_for_SUM_SAS(self,logger,user_defined_file=None):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the *SUM.SAS file. Making this a function since it is 
        used in several places.
        """

        exists = False

        if user_defined_file == None:
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
            exists = True
        else:
            logger.log('warning', 'sas_odf file not present! User must run calibrate_odf!')
            return exists
        
        # Check that the SUM.SAS file PATH keyword points to a real ODF directory
        with open(self.files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if not os.path.exists(path):
                        logger.log('error', f'Summary file PATH {path} does not exist. Rerun calibrate_odf with overwrite=True.')
                        print(f'\nSummary file PATH {path} does not exist. \n\n>>>>Rerun calibrate_odf with overwrite=True.')
                        exists = False
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if not os.path.exists(MANIFEST[0]):
                        logger.log('error', f'Missing {MANIFEST[0]} file in {path}. Missing ODF components? Rerun calibrate_odf with overwrite=True.')
                        print(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components? \n\n>>>>Rerun calibrate_odf with overwrite=True.')
                        exists = False

        return exists
    