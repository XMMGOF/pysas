# obsid.py
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

# obsid.py

"""
obsid.py

- ObsID: Class with methods for dealing with a single Obs ID.

"""

# Standard library imports
import os, sys, shutil, glob, numbers
from pathlib import Path

# Third party imports

# Local application imports
from pysas import sas_cfg
from ..init_sas import initializesas
from ..sasutils import download_data as dl_data
from pysas.logger import get_logger
from pysas.sastask import MyTask
from pysas.pysasplot_utils.pysasplot_utils import quick_image_plot as qip
from pysas.pysasplot_utils.pysasplot_utils import quick_light_curve_plot as qlcp

repo_opts = ['esa','xsa','heasarc','nasa','sciserver','fornax','aws']

class ObsID:
    """
    Class for and Obs ID object.
    Inputs:
    Required:
        - obsid: 10 digit number of the Obs ID

    Optional:
        - data_dir   : Data directory. If none is given, 
                       will use (in this order):
                       1. data_dir set in configuration file
                       2. Current directory
        - logfilename: Name of log file where all output
                       will be written. Overrides default
                       log file names.
        - tasklogdir : Directory for log files. Overrides
                       default log directory.
        - output_to_terminal: If True, then logger information
                              will be output to the terminal.
        - output_to_file: If True, then logger information will
                          be written to a log file.
    """
    def __init__(self, obsid, 
                 data_dir    = None,
                 logfilename = None,
                 tasklogdir  = None,
                 output_to_terminal = True,
                 output_to_file     = False):
        if isinstance(obsid, numbers.Number):
            obsid = f'{obsid:010}'
        self.obsid       = obsid
        self.data_dir    = data_dir
        self.files       = {}
        self.logfilename = logfilename
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file
        # __set_obsid uses a temporary logger, that will only
        # output to the terminal.
        self.logger = get_logger('ObsID_' + self.obsid, 
                                 toterminal  = self.output_to_terminal,
                                 tofile      = False)
        # Sets info on the data_dir, obs_dir, etc.
        self.logger.debug('Temporary logger generated')
        self.__set_obsid()
        # Remove temporary logger
        self.logger.debug('Removing temporary logger')
        self.__remove_attr('logger')
        
        # Set the directory for log files.
        # Log directory will be (in this order):
        # 1. Directory passed in by the user
        # 2. data_dir
        # 3. cwd
        if tasklogdir is None:
            if not self.data_dir is None and os.path.exists(self.data_dir):
                self.tasklogdir = self.data_dir
            else:
                # By default get_logger will use cwd
                # if tasklogdir = None
                self.tasklogdir = tasklogdir
        else:
            # User defined directory
            if not os.path.exists(tasklogdir):
                print(f'Warning: User defined tasklogdir, {tasklogdir} does not exist!')
                tasklogdir = None
                print(f'Resetting tasklogdir to the current directory!')
            self.tasklogdir = tasklogdir
        
        # Create logger
        self.logger = get_logger('ObsID_' + self.obsid, 
                                 toterminal  = self.output_to_terminal,
                                 tofile      = self.output_to_file, 
                                 logfilename = self.logfilename,
                                 tasklogdir  = self.tasklogdir)
        self.logger.debug('Logger generated')
        self.logger.debug('Finished with ObsID.__init__')

    def __set_obsid(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Basic method for setting the environment variables for a single 
        'ObsID'.

        Checks for the existence of various directories. If a directory 
        is not found then __set_obsid will stop and use 'return' command.
        Directories that will be checked for (in this order):
            
            data_dir
            obs_dir
            odf_dir -or- pps_dir
            work_dir

        Then checks for the ccf.cif, *SUM.SAS files and event lists.

        Similar to download_data, but will not download any data, 
        or do anything other than link to files and directories. 
        """
        self.logger.debug('Entered __set_obsid')
        # Check to see if data_dir was given by the user
        self.logger.debug('Checking for data_dir')
        data_dir_found = False
        if not self.data_dir is None:
            self.logger.info(f'User input data_dir: {self.data_dir}.')
            if not os.path.exists(self.data_dir):
                self.logger.error(f'Did not find: {self.data_dir}')
                self.data_dir = None
                self.logger.info(f'Resetting data_dir to "{self.data_dir}".')
                self.logger.info(f'Will check config file for default.')
            else:
                data_dir_found = True
                self.logger.debug(f'data_dir found: {self.data_dir}')
        
        # Check if data_dir is in the config file
        self.logger.debug('Checking for data_dir from config file')
        if not data_dir_found and sas_cfg.config.has_option('sas','data_dir'):
            data_dir = sas_cfg.get_setting('data_dir')
            self.logger.debug(f'Trying default data_dir from config file: {data_dir}')
            if os.path.exists(data_dir):
                self.data_dir = data_dir
                self.logger.info(f'Data directory found: {self.data_dir}')
        else:
            self.logger.info(f'No data_dir found in config file. Not setting data_dir.')
            self.logger.info(f'Leaving data_dir as "{self.data_dir}".')
            self.logger.debug(f'Exiting __set_obsid, no data_dir found')
            return
            
        # data_dir is set.
        # Setting other directory paths.

        # Set directories for the observation, odf, pps, and work.
        self.logger.debug(f'Setting obs_dir, odf_dir, pps_dir, and work_dir')
        self.obs_dir  = os.path.join(self.data_dir,self.obsid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.pps_dir  = os.path.join(self.obs_dir,'PPS')
        self.work_dir = os.path.join(self.obs_dir,'work')
        self.logger.debug(f'obs_dir: {self.obs_dir}')
        self.logger.debug(f'odf_dir: {self.odf_dir}')
        self.logger.debug(f'pps_dir: {self.pps_dir}')
        self.logger.debug(f'work_dir: {self.work_dir}')

        if os.path.exists(self.obs_dir):
            self.logger.info(f'obs_dir found at {self.obs_dir}.')
        else:
            self.logger.info(f'obs_dir not found {self.obs_dir}. User must download data!')
            self.logger.debug(f'Exiting __set_obsid, no obs_dir found')
            return
        
        if os.path.exists(self.odf_dir):
            self.logger.info(f'odf_dir found at {self.odf_dir}.')
            os.environ['SAS_ODF'] = self.odf_dir
            if os.path.exists(self.pps_dir):
                self.logger.info(f'pps_dir found at {self.pps_dir}.')
        else:
            if os.path.exists(self.pps_dir):
                self.logger.info(f'pps_dir found at {self.pps_dir}.')
            else:
                self.logger.info(f'ODF and PPS directories not found! User must download data!')
                self.logger.debug(f'Exiting __set_obsid, no odf_dir nor pps_dir found')
                return
            
        # Get lists of ODF and PPS files.
        if os.path.exists(self.odf_dir):
            self.logger.debug(f'Getting list of ODF files')
            self.files['ODF'] = self.__get_list_of_ODF_files()
        if os.path.exists(self.pps_dir):
            self.logger.debug(f'Getting list of PPS files')
            self.files['PPS'] = self.__get_list_of_PPS_files()
        
        if os.path.exists(self.work_dir):
            self.logger.info(f'work_dir found at {self.work_dir}.')
        else:
            self.logger.info(f'Default work_dir not found! User must create it!')
            self.logger.debug(f'Exiting __set_obsid, no work_dir found')
            return

        self.logger.info(f'Data directory = {self.data_dir}')
        self.logger.info(f'Existing directory for {self.obsid} found ...')
        self.logger.info(f'Searching {self.data_dir}/{self.obsid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        exists = self.get_ccf_cif()
        if not exists:
            self.logger.info('ccf.cif file not present! User must run calibrate_odf!')
            self.logger.debug(f'Exiting __set_obsid, no ccf.cif found')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        self.logger.info(f'SAS_CCF = {self.files['sas_ccf']}')

        # Looking for *SUM.SAS file.
        exists = self.get_SUM_SAS()
        if not exists:
            self.logger.info('*SUM.SAS file not present! User must run calibrate_odf!')
            self.logger.debug(f'Exiting __set_obsid, no *SUM.SAS found')
            return
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        self.logger.info(f'SAS_ODF = {self.files['sas_odf']}')

        # Check for previously generated event lists.
        self.find_event_list_files(print_output = self.output_to_terminal)
        self.find_rgs_spectra_files(print_output = self.output_to_terminal)

        # Change to work directory.
        os.chdir(self.work_dir)
        self.logger.info(f'Changing to work_dir: {self.work_dir}')

        # Exit the __set_obsid function. Everything is set.
        self.logger.debug(f'Exiting __set_obsid, success!')
        return

    def basic_setup(self, 
                    data_dir    = None,
                    repo        = None,
                    overwrite   = False,
                    rerun       = False,
                    recalibrate = False,
                    run_epproc  = True,
                    run_emproc  = True,
                    run_rgsproc = True,
                    run_epchain = False,
                    run_emchain = False,
                    **kwargs):
        """
        Function to do all basic analysis tasks. The function will:

            1. Download data by calling 'download_data'
            2. Call the function 'calibrate_odf'
                A. Run 'cifbuild'
                B. Run 'odfingest'
            2. Run 'epproc' -OR- 'epchain'
            3. Run 'emproc' -OR- 'emchain'
            4. Run 'rgsproc'

        If 'run_epchain' is set to 'True', then 'epproc' will not run.
        If 'run_emchain' is set to 'True', then 'emproc' will not run.

        Inputs:

            data_dir:    Data directory.
            repo:        Download repository ('esa','heasarc','fornax','aws').
            overwrite:   Remove previous data files and download again.
            rerun:       Rerun the *procs or *chains.
            recalibrate: Rerun 'cifbuild' and 'odfingest'.

        All input arguments for 'download_ODF_data' and 'calibrate_odf'
        can be passed to 'basic_setup'.

        'download_ODF_data' inputs (with defaults):

            repo             = 'esa'
            data_dir         = None
            overwrite        = False
            proprietary      = False
            credentials_file = None
            encryption_key   = None

        'calibrate_odf' inputs (with defaults):
               
            obs_dir        = None
            sas_ccf        = None
            sas_odf        = None
            cifbuild_opts  = {}
            odfingest_opts = {}
            recalibrate    = False

        Input arguments for 'epproc', 'emproc', and 'rgsproc' can also be 
        passed in using 'epproc_args', 'emproc_args', or 'rgsproc_args' 
        respectively (or 'epchain_args' and 'emchain_args'). By defaut 
        'epproc', 'emproc', and 'rgsproc' will not rerun if output files 
        are found, but they can be forced to rerun by setting 'rerun=True' 
        as an input to 'basic_setup'.

        Examples for use:

            my_obs.basic_setup()

                - Uses the defaults.

            my_obs.basic_setup(repo='heasarc')

                - Uses the defaults, but downloads data from the HEASARC.

            my_obs.basic_setup(overwrite=True)

                - Will erase any previous data files for the Obs ID and 
                  download a fresh set of data files.

            my_obs.basic_setup(recalibrate=True)

                - Will rerun cifbuild and odfingest to generate new 
                  ccf.cif and *SUM.SAS files.

            my_obs.basic_setup(rerun=True)

                - Will **not** download new files, but will rerun 'epproc',
                  'emproc', and 'rgsproc' and create new event lists.

            my_obs.basic_setup(repo='heasarc',
                               epproc_args=['withoutoftime=yes'])

                - Downloads data from the HEASARC and runs 'epproc' with the
                  'withoutoftime' option.

            my_obs.basic_setup(run_epchain=True,
                               run_emchain=True)

                - Will run 'epchain' and 'emchain' instead of 'epproc' and
                  'emproc'.

            my_obs.basic_setup(run_epproc=False,
                               run_emproc=False)

                - Will not run 'epproc' or 'emproc'. Will only run 'rgsproc'
                  by default.

            my_obs.basic_setup(run_epproc=False,
                               run_emproc=True,
                               run_rgsproc=False)

                - Will only run 'emproc', **not** 'epproc' or 'rgsproc'.

            my_obs.basic_setup(repo='heasarc',encryption_key='XXXXXXXXXXXXXXX')

                - Uses the defaults, but downloads *proprietary* data from 
                  the HEASARC. Must provide an encryption key, an alpha-numeric
                  string with 30 characters.

            my_obs.basic_setup(proprietary=True)

                - Uses the defaults, but downloads *proprietary* data from 
                  the XSA at ESA. Astroquery will ask for user's Cosmos
                  username and password.

        """

        self.logger.debug('Starting basic_setup')
        # Set data_dir
        self.logger.debug('Running __set_data_dir')
        self.__set_data_dir(data_dir)

        # Set directories for the observation, odf, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.obsid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.work_dir = os.path.join(self.obs_dir,'work')
        self.logger.debug(f'obs_dir: {self.obs_dir}')
        self.logger.debug(f'odf_dir: {self.odf_dir}')
        self.logger.debug(f'work_dir: {self.work_dir}')

        # Deal with the rest of the inputs.
        # Set repo from config file (default 'esa')
        self.logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self.logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self.logger.error('Download repository not found!')
                print(f'Options for repo are {repo_opts}.')
                raise Exception('Download repository not found!')
            else:
                self.logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self.logger.debug(f'repo set to: {self.repo}')

        # Checking LHEASOFT, SAS_DIR and SAS_CCFPATH
        lheasoft = os.environ.get('LHEASOFT')
        if not lheasoft:
            self.logger.error('LHEASOFT is not set. Please initialise HEASOFT')
            raise Exception('LHEASOFT is not set. Please initialise HEASOFT')
        else:
            self.logger.info(f'LHEASOFT = {lheasoft}')

        sasdir = os.environ.get('SAS_DIR')
        if not sasdir:
            self.logger.error('SAS_DIR is not defined. Please initialise SAS.')
            raise Exception('SAS_DIR is not defined. Please initialise SAS.')
        else:
            self.logger.info(f'SAS_DIR = {sasdir}') 

        sas_ccfpath = os.environ.get('SAS_CCFPATH')
        if not sas_ccfpath:
            self.logger.error('SAS_CCFPATH not set. Please define it.')
            raise Exception('SAS_CCFPATH not set. Please define it.')
        else:
            self.logger.info(f'SAS_CCFPATH = {sas_ccfpath}')
        
        os.chdir(self.data_dir)
        self.logger.info(f'Changed directory to {self.data_dir}')

        print(f'''

        Starting SAS session

        Data directory = {self.data_dir}

        ''')

        # Download the data
        self.logger.debug('Call download_ODF_data')
        self.download_ODF_data(repo             = self.repo,
                               data_dir         = self.data_dir,
                               overwrite        = overwrite,
                               proprietary      = kwargs.get('proprietary', False),
                               credentials_file = kwargs.get('credentials_file', None),
                               encryption_key   = kwargs.get('encryption_key', None))

        # Set work directory
        if not hasattr(self, 'work_dir'):
            self.work_dir = os.path.join(self.obs_dir,'work')
            self.logger.info(f'Setting work_dir: {self.work_dir}')

        if not os.path.exists(self.work_dir):
            self.logger.info(f'{self.work_dir} does not exist. Creating it!')
            os.mkdir(self.work_dir)

        # Calibrate ODF data
        self.logger.debug('Call calibrate_odf')
        self.calibrate_odf(obs_dir        = self.obs_dir,
                           sas_ccf        = kwargs.get('sas_ccf', None),
                           sas_odf        = kwargs.get('sas_odf', None),
                           cifbuild_opts  = kwargs.get('cifbuild_opts', {}),
                           odfingest_opts = kwargs.get('odfingest_opts', {}),
                           recalibrate    = recalibrate)

        # Run basic processing
        if run_epproc and not run_epchain:
            self.logger.debug('Run epproc')
            self.__run_analysis('epproc',
                                kwargs.get('epproc_args', {}),
                                rerun   = rerun,
                                logFile = 'epproc.log')
        
        if run_epchain:
            self.logger.debug('Run epchain')
            self.__run_analysis('epchain',
                                kwargs.get('epchain_args', {}),
                                rerun   = rerun,
                                logFile = 'epchain.log')

        if run_emproc and not run_emchain:
            self.logger.debug('Run emproc')
            self.__run_analysis('emproc',
                                kwargs.get('emproc_args', {}),
                                rerun   = rerun,
                                logFile = 'emproc.log')
            
        if run_emchain:
            self.logger.debug('Run emchain')
            self.__run_analysis('emchain',
                                kwargs.get('emchain_args', {}),
                                rerun   = rerun,
                                logFile = 'emchain.log')
            
        if run_rgsproc:
            self.logger.debug('Run rgsproc')
            self.__run_analysis('rgsproc',
                                kwargs.get('rgsproc_args', {}),
                                rerun   = rerun,
                                logFile = 'rgsproc.log')
        
        #if run_omichain:
        #    self.__run_analysis('omichain',
        #                        kwargs.get('omichain_args', []),
        #                        rerun   = rerun,
        #                        logFile = 'omichain.log')
        
        self.logger.debug('Exiting basic_setup')
        return
    
    def run_MyTask(self, taskname, 
                   inargs = None, 
                   **kwargs):
        """
        This acts as a wrapper around 'MyTask'. This provides a way of calling
        SAS tasks, while using the values set when the 'ObsID' object was 
        instantiated.

        Required inputs (just like MyTask):
            taskname
            inargs

        Optional inputs (just like MyTask, but **only** use these if you want 
        them to be different from the values used when instantiating 'ObsID'):
            logfilename
            tasklogdir
            output_to_terminal
            output_to_file
            logger (Only in very rare circumstances **DO NOT USE** unless you
                    know exactly what you are doing!!)
        """

        if inargs is None:
            inargs = {}

        MT = MyTask(taskname, inargs, 
                    logfilename = kwargs.get('logfilename', self.logfilename), 
                    tasklogdir  = kwargs.get('tasklogdir', self.work_dir),
                    output_to_terminal = kwargs.get('output_to_terminal', self.output_to_terminal), 
                    output_to_file     = kwargs.get('output_to_file', self.output_to_file),
                    logger = kwargs.get('logger', None)).run()
        
    def download_ODF_data(self,
                          repo        = None,
                          data_dir    = None,
                          overwrite   = False,
                          proprietary = False,
                          credentials_file = None,
                          encryption_key   = None):
        """
        This handles preliminary setup for downloading data files, then 
        calls download_data (as "dl_data") from sasutils.

        Inputs:
            --REQUIRED--

                NONE

            --OPTIONAL--

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'aws' (data from AWS s3 bucket (NASA)) or
                                        'fornax' (if user is on Fornax)

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        data_dir/obsid.
                                        Default: Default from sas_config file, or
                                        current working directory.

            --overwrite:     (boolean): If True will force overwrite of data if obsid 
                                        data already exists in data_dir/obsid.

            --proprietary    (boolean): Flag for downloading proprietary data from
                                        the XSA at ESA.

            --credentials_file (filename): Path and filename of file containing XSA
                                        username and password. For proprietary data
                                        only. (Optinal, astroquery will ask user 
                                        for username and password if filename
                                        not given.)

            --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                        characters long. -OR- path to file containing 
                                        ONLY the encryption key.
                                        Note: ONLY used for data from the HEASARC.
        """
        
        # Set data_dir
        self.__set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self.obs_dir = os.path.join(self.data_dir,self.obsid)
            self.logger.debug(f'Setting obs_dir: {self.obs_dir}')

        # Set odf_dir
        if not hasattr(self, 'odf_dir'):
            self.odf_dir = os.path.join(self.obs_dir,'ODF')
            self.logger.debug(f'Setting odf_dir: {self.odf_dir}')

        # Set repo from config file (default 'esa')
        self.logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self.logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self.logger.error('Download repository not found!')
                print(f'Options for repo are {repo_opts}.')
                raise Exception('Download repository not found!')
            else:
                self.logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self.logger.debug(f'repo set to: {self.repo}')

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
        call_download_data = True
        if os.path.exists(self.obs_dir):
            self.logger.info(f'Existing directory for {self.obsid} found ...')
            if overwrite:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                self.logger.info(f'Removing existing directory {self.obs_dir} ...')
                print(f'\nRemoving existing directory {self.obs_dir} ...')
                shutil.rmtree(self.obs_dir)
            else:
                # Check for files
                what_exists = self.__parse_obs_dir()
                if what_exists['odf_dir'] and what_exists['ODF_files'] and what_exists['manifest']:
                    self.logger.info(f'Existing ODF directory {self.odf_dir} found ...')
                    call_download_data = False
                    print(f'Data found in {self.odf_dir} not downloading again.')
                else:
                    if not what_exists['odf_dir']:
                        self.logger.info(f'Existing ODF directory missing. Will download data.')
                    else:
                        if not what_exists['ODF_files']:
                            self.logger.info(f'ODF files missing from {self.odf_dir}. Will download data.')
                            shutil.rmtree(self.odf_dir)
                        elif not what_exists['manifest']:
                            self.logger.info(f'MANIFEST missing from {self.odf_dir}. Will download data.')
                            shutil.rmtree(self.odf_dir)

        if call_download_data:
            self.logger.info(f'Will download ODF data for Obs ID {self.obsid}.')

            # Function for downloading a single obsid set.
            dl_data(self.obsid,
                    self.data_dir,
                    level          = 'ODF',
                    overwrite      = overwrite,
                    repo           = self.repo,
                    logger         = self.logger,
                    proprietary    = proprietary,
                    encryption_key = encryption_key,
                    credentials_file = credentials_file)
            
        self.logger.info(f'Data directory: {self.data_dir}')
        self.logger.info(f'ObsID directory: {self.obs_dir}')
        print(f'Data directory: {self.data_dir}')
        self.files['ODF'] = self.__get_list_of_ODF_files()

        return
        
    def download_PPS_data(self,
                          repo      = None,
                          data_dir  = None,
                          overwrite = False,
                          proprietary      = False,
                          credentials_file = None,
                          encryption_key   = None,
                          PPS_subset   = False,
                          instname     = None,
                          expflag      = None,
                          expno        = None,
                          product_type = None,
                          datasubsetno = None,
                          sourceno     = None,
                          extension    = None,
                          filename     = None,
                          **kwargs):
        """
        This handles preliminary setup for downloading data files, then 
        calls download_data (as "dl_data") from sasutils.

        Inputs:
            --REQUIRED--

                NONE

            --OPTIONAL--

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'aws' (data from AWS s3 bucket (NASA)) or
                                        'fornax' (if user is on Fornax)

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        data_dir/odfid.
                                        Default: Default from sas_config file, or
                                        current working directory.

            --overwrite:     (boolean): If True will force overwrite of data if odfid 
                                        data already exists in data_dir/odfid.

            --proprietary    (boolean): Flag for downloading proprietary data from
                                        the XSA at ESA.

            --credentials_file (filename): Path and filename of file containing XSA
                                        username and password. For proprietary data
                                        only. (Optinal, astroquery will ask user 
                                        for username and password if filename
                                        not given.)

            --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                        characters long. -OR- path to file containing 
                                        ONLY the encryption key.
                                        Note: ONLY used for data from the HEASARC.

            --PPS_subset:    (boolean): Set PPS_subset=True if downloading a subset of PPS
                                        files form the XMM-Newton archive.

            --filename:       (string): If the exact PPS file name is known, then this can
                                        be used to download a single PPS file.

            
            The remaining inputs are used for downloading groups of PPS files using a 
            particular file pattern. Using these requires an understanding of PPS 
            filenames.
            
                instname    : instrument name
                expflag     : Exposure flag
                expno       : Exposure number
                product_type: Product type
                datasubsetno: data subset number/character
                sourceno    : Source number or slew step number
                extension   : File format
        """
        
        # Set data_dir
        self.__set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self.obs_dir = os.path.join(self.data_dir,self.obsid)
            self.logger.debug(f'Setting obs_dir: {self.obs_dir}')

        # Set odf_dir
        if not hasattr(self, 'pps_dir'):
            self.pps_dir = os.path.join(self.obs_dir,'PPS')
            self.logger.debug(f'Setting pps_dir: {self.pps_dir}')

        # Set repo from config file (default 'esa')
        self.logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self.logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self.logger.error('Download repository not found!')
                print(f'Options for repo are {repo_opts}.')
                raise Exception('Download repository not found!')
            else:
                self.logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self.logger.debug(f'repo set to: {self.repo}')

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
        call_download_data = True
        if os.path.exists(self.obs_dir):
            self.logger.info(f'Existing directory for {self.obsid} found ...')
            if overwrite:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                self.logger.info(f'Removing existing directory {self.obs_dir} ...')
                print(f'\n\nRemoving existing directory {self.obs_dir} ...')
                shutil.rmtree(self.obs_dir)
            else:
                # Check for files
                what_exists = self.__parse_obs_dir()
                if what_exists['pps_dir'] and what_exists['PPS_files']:
                    self.logger.info(f'Existing PPS directory {self.pps_dir} found ...')
                    call_download_data = False
                if (filename or PPS_subset):
                    self.logger.info(f'Downloading subset of PPS data. Will silently overwrite any pre-existing files.')
                    call_download_data = True
                if not call_download_data:
                    self.logger.info(f'Data found in {self.obs_dir} not downloading again.')
                    print(f'Data found in {self.obs_dir} not downloading again.')

        # Set work directory.
        self.work_dir = os.path.join(self.obs_dir,'work')

        if call_download_data:
            self.logger.info(f'Will download PPS data for Obs ID {self.obsid}.')
            # Function for downloading a single pps data set.
            dl_data(self.obsid,
                    self.data_dir,
                    level          = 'PPS',
                    overwrite      = overwrite,
                    repo           = self.repo,
                    logger         = self.logger,
                    proprietary      = proprietary,
                    encryption_key   = encryption_key,
                    credentials_file = credentials_file,
                    PPS_subset   = PPS_subset,
                    instname     = instname,
                    expflag      = expflag,
                    expno        = expno,
                    product_type = product_type,
                    datasubsetno = datasubsetno,
                    sourceno     = sourceno,
                    extension    = extension,
                    filename     = filename,
                    **kwargs)
            
        self.logger.info(f'Data directory: {self.data_dir}')
        self.logger.info(f'ObsID directory: {self.obs_dir}')
        print(f'Data directory: {self.data_dir}')
        self.files['PPS'] = self.__get_list_of_PPS_files()

        return
    
    def download_ALL_data(self,
                          repo        = None,
                          data_dir    = None,
                          overwrite   = True,
                          proprietary      = False,
                          credentials_file = None,
                          encryption_key   = None):
        """
        This function assumes you want to overwrite everything in the
        obs_dir. Makes no checks.

        This handles preliminary setup for downloading data files, then 
        calls download_data (as "dl_data") from sasutils.

        Inputs:
            --REQUIRED--

                NONE

            --OPTIONAL--

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'aws' (data from AWS s3 bucket (NASA)) or
                                        'fornax' (if user is on Fornax)

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        data_dir/obsid.
                                        Default: Default from sas_config file, or
                                        current working directory.

            --overwrite:     (boolean): If True will force overwrite of data if obsid 
                                        data already exists in data_dir/obsid.

            --proprietary    (boolean): Flag for downloading proprietary data from
                                        the XSA at ESA.

            --credentials_file (filename): Path and filename of file containing XSA
                                        username and password. For proprietary data
                                        only. (Optinal, astroquery will ask user 
                                        for username and password if filename
                                        not given.)

            --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                        characters long. -OR- path to file containing 
                                        ONLY the encryption key.
                                        Note: ONLY used for data from the HEASARC.
        """
        
        # Set data_dir
        self.__set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self.obs_dir = os.path.join(self.data_dir,self.obsid)
            self.logger.debug(f'Setting obs_dir: {self.obs_dir}')

        # Set repo from config file (default 'esa')
        self.logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self.logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self.logger.error('Download repository not found!')
                print(f'Options for repo are {repo_opts}.')
                raise Exception('Download repository not found!')
            else:
                self.logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self.logger.debug(f'repo set to: {self.repo}')

        # Checks if obs_dir exists and removes it.

        if os.path.exists(self.obs_dir):
            self.logger.info(f'Existing directory for {self.obsid} found ...')
            self.logger.info(f'Removing existing directory {self.obs_dir} ...')
            print(f'\n\nRemoving existing directory {self.obs_dir} ...')
            shutil.rmtree(self.obs_dir)

        self.logger.info(f'Will download ALL data for Obs ID {self.obsid}.')

        # Function for downloading a single obsid set.
        dl_data(self.obsid,
                self.data_dir,
                level          = 'ALL',
                overwrite      = overwrite,
                repo           = self.repo,
                logger         = self.logger,
                proprietary    = proprietary,
                encryption_key = encryption_key,
                credentials_file = credentials_file)
            
        self.logger.info(f'Data directory: {self.data_dir}')
        self.logger.info(f'ObsID directory: {self.obs_dir}')
        print(f'Data directory: {self.data_dir}')
        self.files['ODF'] = self.__get_list_of_ODF_files()
        self.files['PPS'] = self.__get_list_of_PPS_files()

        return
    
    def calibrate_odf(self,
                      obs_dir = None,
                      sas_ccf = None,
                      sas_odf = None,
                      cifbuild_opts  = {},
                      odfingest_opts = {},
                      recalibrate    = False):
        """
        Before running this function an ObsID object must be created first. e.g.

            my_obs = pysas.obsid.ObsID(obsid)

        *Then* the data must be downloaded using:

            my_obs.download_ODF_data()

        This function can then be used as, 
        
            my_obs.calibrate_odf()
        
        If it exists it will search data_dir/obsid and any subdirectories for the ccf.cif
        and *SUM.SAS files. Will not rerun calibration if the ccf.cif and *SUM.SAS files
        exist, unless recalibrate = True.

        Optionally the paths to the ccf.cif and *SUM.SAS files can be given through 
        sas_ccf and sas_odf respectively.

        Inputs:
            --REQUIRED--

                NONE

            --OPTIONAL--

            --obs_dir:  (string/path): Path to the obs directory. If no path 
                                       given, then will look in 
                                       data_dir/obsid/. If directory exists then 
                                       will look for ccf.cif and *SUM.SAS files. 
                                       Default: None, looks in data_dir/obsid/.

            --sas_ccf:   (string/path): Path to ccf.cif file for obsid.

            --sas_odf:   (string/path): Path to *SUM.SAS file for obsid.

            --cifbuild_opts:    (list): Options for cifbuild.

            --odfingest_opts:   (list): Options for odfingest.

            --recalibrate:   (boolean): If True will rerun odfingest and cifbuild.
        """

        # If user passes in obs_dir
        if not obs_dir is None:
            self.obs_dir = obs_dir
            self.logger.debug(f'Setting obs_dir: {self.obs_dir}')

        # If no obs_dir was passed in and not set previously
        if not hasattr(self, 'obs_dir'):
            if not hasattr(self, 'data_dir'):
                # If the user has gotten this far without setting data_dir,
                # they are probably doing something very wrong.
                self.logger.debug(f'If you are seeing this, then you are probably doing something wrong.')
                self.__set_data_dir(None)
            self.obs_dir = os.path.join(self.data_dir, self.obsid)
            self.logger.info(f'Setting obs_dir to: {self.obs_dir}')

        # Check if obs_dir exists. If not then raise an Exception.
        if not os.path.isdir(self.obs_dir):
            self.logger.error(f'Observation directory: {self.obs_dir} does not exist!')
            print(f'Error! Observation directory: {self.obs_dir} does not exist!')
            print(f'Please provide the path to the observation directory \n \
                    using the input obs_dir=path/to/obs/dir/.')
            raise Exception(f'Error! Observation directory: {self.obs_dir} does not exist!')

        self.logger.info(f'Observation directory = {self.obs_dir}')

        # Deal with the rest of the inputs.
        self.files['sas_ccf'] = sas_ccf
        self.files['sas_odf'] = sas_odf
        if cifbuild_opts is None: cifbuild_opts = {}
        self.cifbuild_opts = cifbuild_opts
        self.logger.debug(f'cifbuild_opts = {cifbuild_opts}')
        if odfingest_opts is None: odfingest_opts = {}
        self.odfingest_opts = odfingest_opts
        self.logger.debug(f'odfingest_opts = {odfingest_opts}')
        
        os.chdir(self.obs_dir)
        self.logger.info(f'calibrate_odf: Changed directory to {self.obs_dir}')

        # Set directories for the odf and work.
        # Set odf_dir
        if not hasattr(self, 'odf_dir'):
            self.odf_dir = os.path.join(self.obs_dir,'ODF')
            self.logger.debug(f'Setting odf_dir: {self.odf_dir}')
        if not hasattr(self, 'work_dir'):
            self.work_dir = os.path.join(self.obs_dir,'work')
            self.logger.debug(f'Setting work_dir: {self.work_dir}')

        # Check what exists in the obs_dir.
        self.logger.debug('Parse obs_dir')
        what_exists = self.__parse_obs_dir()

        # Runs calibration if recalibrate = True. Default recalibrate = False
        # Else, looks for ccf.cif and *SUM.SAS files.
        # If ccf.cif and *SUM.SAS files are not found then will run calibration.
        
        if recalibrate:
            if what_exists['odf_dir'] and what_exists['ODF_files']:
                self.logger.debug('Run calibration')
                self.__run_calibration(cifbuild_opts,odfingest_opts)
            else:
                self.logger.error('ODF directory and files not found!')
                print('ODF directory and files not found! Try downloading data again.')
                raise Exception('ODF directory and files not found!')
            return
        else:
            self.logger.info(f'Searching {self.obs_dir} for ccf.cif and *SUM.SAS files ...')
            # Looking for ccf.cif file.
            if self.files['sas_ccf'] is None:
                ccf_exists = self.get_ccf_cif()
            else:
                # Check if ccf.cif file path given by user exists.
                try:
                    os.path.exists(self.files['sas_ccf'])
                    self.logger.info('{0} is present'.format(self.files['sas_ccf']))
                    ccf_exists = True
                except FileExistsError:
                    # The only way to get this error is if the user provided a bad filename or path.
                    self.logger.error('File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                    print('File {0} not present! Please check if path is correct!'.format(self.files['sas_ccf']))
                    sys.exit(1)
            
            # Looking for *SUM.SAS file.
            if self.files['sas_odf'] is None:
                SUM_exists = self.get_SUM_SAS()                    
            else:
                # Check if *SUM.SAS file path given by user exists.
                try:
                    SUM_exists = self.get_SUM_SAS(user_defined_file=self.files['sas_odf'])
                    if SUM_exists:
                        self.logger.info('{0} is present'.format(self.files['sas_odf']))
                except FileExistsError:
                    # The only way to get this error is if the user provided a bad filename or path.
                    self.logger.error('File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                    print('File {0} not present! Please check if path is correct!'.format(self.files['sas_odf']))
                    sys.exit(1)

            if ccf_exists and SUM_exists:
                # Set 'SAS_CCF' enviroment variable.
                os.environ['SAS_CCF'] = self.files['sas_ccf']
                self.logger.info('SAS_CCF = {0}'.format(self.files['sas_ccf']))
                print('SAS_CCF = {}'.format(self.files['sas_ccf']))

                # Set 'SAS_ODF' enviroment variable.
                os.environ['SAS_ODF'] = self.files['sas_odf']
                self.logger.info('SAS_ODF = {0}'.format(self.files['sas_odf']))
                print('SAS_ODF = {0}'.format(self.files['sas_odf']))
            else:
                # If the ccf.cif or *SUM.SAS files are not present, then run calibration.
                self.__run_calibration(cifbuild_opts,odfingest_opts) 
            
            # Set 'SAS_ODF' enviroment variable.
            os.environ['SAS_ODF'] = self.files['sas_odf']
            self.logger.info('SAS_ODF = {0}'.format(self.files['sas_odf']))
            print('SAS_ODF = {0}'.format(self.files['sas_odf']))

            self.get_active_instruments()

            if not os.path.exists(self.work_dir): 
                os.mkdir(self.work_dir)
                self.logger.debug(f'Making work_dir: {self.work_dir}')
            # Exit the calibrate_odf function. Everything is set.
        
        self.files['ODF'] = self.__get_list_of_ODF_files()

        self.logger.debug('Exiting calibrate_odf')
        return
    
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
    
    def sas_talk(self,verbosity=4,suppress_warning=1):
        """
        Simple function to set general SAS veriables 'verbosity' 
        and 'suppress_warning'.
        """

        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        os.environ['SAS_VERBOSITY'] = '{}'.format(self.verbosity)
        os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(self.suppress_warning)
    
    def find_event_list_files(self,print_output=True):
        """
        Checks the observation directory (obs_dir) for basic unfiltered 
        event list files created by 'epproc', 'emproc', and 'rgsproc'. 
        Stores paths and file names in self.files.

        'self.files' is a dictionary with the following keys:

            'PNevt_list'
            'M1evt_list'
            'M2evt_list'
            'R1evt_list'
            'R2evt_list'
        """
        self.logger.debug('Entering find_event_list_files')

        self.logger.debug('Checking active instruments')
        self.get_active_instruments()

        # Check if events lists have already been made from the odf files.
        # Have dummy value for the OM because it should be handled 
        # differently. But if not included here then too many checks 
        # will be needed later on.
        inst_list = list(self.active_instruments.keys())
        evt_list_list = {'PN': 'PNevt_list',
                         'M1': 'M1evt_list',
                         'M2': 'M2evt_list',
                         'R1': 'R1evt_list',
                         'R2': 'R2evt_list',
                         'OM': 'OMimg_list'}
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
            self.logger.debug('Checking for EPIC event lists.')
            files = glob.glob(self.obs_dir+'/**/*.ds', recursive=True)
            for filename in files:
                if (filename.find(find_list[inst]) != -1) and filename.endswith('Evts.ds'):
                    self.files[evt_list_list[inst]].append(os.path.abspath(filename))
                    exists = True
                    self.logger.debug(f'Event list found: {os.path.abspath(filename)}')
            # Checking for RGS event lists.
            self.logger.debug('Checking for RGS event lists.')
            files = glob.glob(self.obs_dir+'/**/*EVENLI*FIT', recursive=True)
            for filename in files:
                if (filename.find(find_list[inst]) != -1):
                    self.files[evt_list_list[inst]].append(os.path.abspath(filename))
                    exists = True
                    self.logger.debug(f'Event list found: {os.path.abspath(filename)}')
            # # Need to do something different for optical monitor images.
            if exists:
                self.files[evt_list_list[inst]].sort()
                if print_output:
                    print(" > {0} {1} event list(s) found.\n".format(len(self.files[evt_list_list[inst]]),inst_name[inst]))
                    for x in self.files[evt_list_list[inst]]:
                        print("    " + x + "\n")
        
        self.logger.debug('Exiting find_event_list_files')
        return
    
    def find_rgs_spectra_files(self,print_output=True):
        """
        Check for RGS spectra files created by rgsproc. Adds them to 
        'files' dictrionary with the keys:

            'R1SPEC'
            'R2SPEC'
        """
        self.logger.debug('Entering find_rgs_spectra_files')

        self.logger.debug('Checking active instruments')
        self.get_active_instruments()

        # Check if events lists have already been made from the odf files.

        inst_list = list(self.active_instruments.keys())
        rgs_list = []
        if 'R1' in inst_list: rgs_list.append('R1')
        if 'R2' in inst_list: rgs_list.append('R2')

        dict_key  = {'R1': 'R1spectra',
                     'R2': 'R2spectra'}
        file_key  = {'R1': 'R1',
                     'R2': 'R2'}
        inst_name = {'R1': 'RGS1',
                     'R2': 'RGS2'}
        
        for item in rgs_list: self.files[dict_key[item]] = []

        for inst in rgs_list:
            exists = False
            # Checking for RGS spectra.
            self.logger.debug('Checking for RGS spectra.')
            files = glob.glob(self.obs_dir+'/**/*RSPEC*FIT', recursive=True)
            for filename in files:
                if (filename.find(file_key[inst]) != -1):
                    self.files[dict_key[inst]].append(os.path.abspath(filename))
                    exists = True
                    self.logger.debug(f'Spectra found: {os.path.abspath(filename)}')
            if exists:
                self.files[dict_key[inst]].sort()
                if print_output:
                    print(" > {0} {1} spectra found.\n".format(len(self.files[dict_key[inst]]),inst_name[inst]))
                    for x in self.files[dict_key[inst]]:
                        print("    " + x + "\n")

        self.logger.debug('Exiting find_rgs_spectra_files')
        return
    
    def get_ccf_cif(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the ccf.cif file. If it exists, inserts file name in 
        'files' dict.
        """
        self.logger.debug('Entering get_ccf_cif')

        exists = False

        # Looking for ccf.cif file.
        self.files['sas_ccf'] = os.path.join('does','not','exist')
        self.logger.info(f'Searching for ccf.cif.')
        for path, directories, files in os.walk(self.obs_dir):
            for file in files:
                if 'ccf.cif' in file:
                    self.logger.info(f'Found ccf.cif file in {path}.')
                    self.files['sas_ccf'] = os.path.join(path,file)
        
        # Check if ccf.cif file exists.
        if os.path.exists(self.files['sas_ccf']):
            self.logger.info('{0} is present'.format(self.files['sas_ccf']))
            exists = True
        else:
            self.logger.info('ccf.cif file not present! User must run calibrate_odf!')

        self.logger.debug('Exiting get_ccf_cif')
        return exists
    
    def get_SUM_SAS(self,user_defined_file=None):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the *SUM.SAS file. Making this a function since it is 
        used in several places.
        """
        self.logger.debug('Entering get_SUM_SAS')

        exists = False

        if user_defined_file == None:
            # Looking for *SUM.SAS file.
            self.files['sas_odf'] = os.path.join('does','not','exist')
            self.logger.info(f'Path to *SUM.SAS file not given. Will search for it.')
            for path, directories, files in os.walk(self.obs_dir):
                for file in files:
                    if 'SUM.SAS' in file:
                        self.logger.info(f'Found *SUM.SAS file in {path}.')
                        self.files['sas_odf'] = os.path.join(path,file)
        # Check if *SUM.SAS file exists.
        if os.path.exists(self.files['sas_odf']):
            self.logger.info('{0} is present'.format(self.files['sas_odf']))
            exists = True
        else:
            self.logger.info('sas_odf file not present! User must run calibrate_odf!')
            return exists
        
        # Check that the SUM.SAS file PATH keyword points to a real ODF directory
        with open(self.files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if not os.path.exists(path):
                        self.logger.error(f'Summary file PATH {path} does not exist. Rerun basic_setup with overwrite=True.')
                        print(f'\nSummary file PATH {path} does not exist. \n\n>>>>Rerun basic_setup with overwrite=True.')
                        exists = False
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if len(MANIFEST) == 0:
                        self.logger.error(f'Missing MANIFEST file in {path}. Missing ODF components? Rerun basic_setup with overwrite=True.')
                        print(f'\nMissing MANIFEST file in {path}. Missing ODF components? \n\n>>>>Rerun basic_setup with overwrite=True.')
                        exists = False

        self.logger.debug('Exiting get_SUM_SAS')
        return exists
    
    def clear_obs_dir(self):
        """
        Function to remove all files and subdirectories from the obs_dir.
        """
        if os.path.exists(self.obs_dir):
            out_note = f'Removing existing directory {self.obs_dir} ...'
            self.logger.info(out_note)
            print(f'\n\n{out_note}')
            shutil.rmtree(self.obs_dir)

    def clear_work_dir(self):
        """
        Function to remove all files and subdirectories from the work_dir.
        """
        if os.path.exists(self.work_dir):
            out_note = f'Removing existing directory {self.work_dir} ...'
            self.logger.info(out_note)
            print(f'\n\n{out_note}')
            shutil.rmtree(self.work_dir)

    def quick_eplot(self,fits_event_list_file,
                    image_file = 'image.fits',
                    xcolumn    = 'X',
                    ycolumn    = 'Y',
                    ximagesize = '600',
                    yimagesize = '600',
                    expression = None,
                    vmin = 1.0,
                    vmax = 10.0,
                    **kwargs):
        """
        Quick plot function for EPIC event lists. As input takes an 
        event list and uses 'evselect' to create a FITS image file.

        Inputs

        (Required)
            fits_event_list_file: Filename of event list.

        (Optional)
            image_file: Output filename of the image file.
            xcolumn: FITS file header name for X column data.
            ycolumn: FITS file header name for Y column data.
            ximagesize: Output image X resolution in pixels.
            yimagesize: Output image Y resolution in pixels.
            expression: Filtering expression to be used for 'evselect'.
            vmin: Min value for color map.
            vmax: Max value for color map.
            xlabel: X axis plot label.
            ylabel: Y axis plot label.
            save_file: If set to True, then a .png image of the plot will be saved.
            out_fname: Output filename of the .png plot image.

        All standard inputs to 'MyTask' can be passed in as optional
        arguments.
        """
        
        if isinstance(ximagesize, numbers.Number):
            ximagesize = str(ximagesize)
        if isinstance(yimagesize, numbers.Number):
            yimagesize = str(yimagesize)
        
        inargs = {'table' : fits_event_list_file, 
                  'withimageset' : 'yes',
                  'imageset' : image_file, 
                  'xcolumn' : xcolumn, 
                  'ycolumn' : ycolumn, 
                  'imagebinning' : 'imageSize', 
                  'ximagesize' : ximagesize, 
                  'yimagesize' : yimagesize}
        
        if not expression is None:
            inargs['expression'] = expression

        # By default this runs silent with no output
        MyTask('evselect', inargs,
               logfilename = kwargs.get('logfilename', None),
               tasklogdir  = kwargs.get('tasklogdir', None),
               output_to_terminal = kwargs.get('output_to_terminal', False),
               output_to_file     = kwargs.get('output_to_file', False),
               logger = kwargs.get('logger', None)).run()
        
        ax = qip(image_file,
                 xlabel = kwargs.get('xlabel', 'RA'),
                 ylabel = kwargs.get('ylabel', 'Dec'),
                 vmin = vmin,
                 vmax = vmax,
                 save_file = kwargs.get('save_file', False),
                 out_fname = kwargs.get('out_fname', 'image.png'))

        return ax
    
    def quick_implot(self,image_file,
                     xlabel = 'RA',
                     ylabel = 'Dec',
                     vmin = 1.0,
                     vmax = 10.0,
                     save_file = False,
                     out_fname = 'image.png'):
        """
        Quick plot function for a FITS image file. As input takes an 
        FITS image file.

        Note: This takes a FITS image file, NOT an event list. 

        Inputs

        (Required)
            image_file: Filename of FITS image file.

        (Optional)
            vmin: Min value for color map.
            vmax: Max value for color map.
            xlabel: X axis plot label.
            ylabel: Y axis plot label.
            save_file: If set to True, then a .png image of the plot will be saved.
            out_fname: Output filename of the .png plot image.
        
        """

        ax = qip(image_file,
                 xlabel = xlabel,
                 ylabel = ylabel,
                 vmin = vmin,
                 vmax = vmax,
                 save_file = save_file,
                 out_fname = out_fname)

        return ax
    
    def quick_lcplot(self,fits_event_list_file,
                     light_curve_file = 'light_curve.fits',
                     timebinsize      = '100',
                     **kwargs):
        """
        Quick plot function to generate a light curve. As input takes an 
        event list and uses 'evselect' to create a FITS image file.

        All standard inputs to 'MyTask' can be passed in as optional
        arguments.
        """
        
        if isinstance(timebinsize, numbers.Number):
            timebinsize = str(timebinsize)
        
        inargs = {'table'          : fits_event_list_file, 
                  'withrateset'    : 'yes',
                  'rateset'        : light_curve_file, 
                  'maketimecolumn' : 'yes', 
                  'timecolumn'     : 'TIME', 
                  'imagebinning'   : 'imageSize', 
                  'timebinsize'    : timebinsize, 
                  'makeratecolumn' : 'yes'}

        # By default this runs silent with no output
        MyTask('evselect', inargs,
               logfilename = kwargs.get('logfilename', None),
               tasklogdir  = kwargs.get('tasklogdir', None),
               output_to_terminal = kwargs.get('output_to_terminal', False),
               output_to_file     = kwargs.get('output_to_file', False),
               logger = kwargs.get('logger', None)).run()
        
        qlcp(light_curve_file,
             save_file = kwargs.get('save_file', False),
             out_fname = kwargs.get('out_fname', 'light_curve.png'))

        return
    
    def __run_analysis(self, task, inargs, 
                       rerun   = False,
                       logFile = None):
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
            --epchain (Warning epchain fails in SAS v. 21)
            --emproc
            --emchain (Warning emchain fails in SAS v. 21)
            --rgsproc

        More will be added as needed.
        """

        # Make sure we are in the right place!
        if os.path.isdir(self.work_dir):
            os.chdir(self.work_dir)
            self.logger.debug('Changing into work_dir')
        else:
            print(f'The directory for the observation ID ({self.obsid}) does not seem to exist!\n    {self.obs_dir}')
            print('Has \'calibrate_odf\' been run?')
            raise Exception(f'Problem with the directory for odfID = {self.obsid}!')
        
        self.logger.debug('Finding event list files')
        self.find_event_list_files(print_output=False)
        self.logger.debug('Finding speactra files')
        self.find_rgs_spectra_files(print_output=False)

        run_ep   = False
        run_em   = False
        run_rgs  = False

        # Check if 'epproc' or 'epchain' have been run.
        if (task == 'epproc' or task == 'epchain') and self.active_instruments['PN']:
            num_evl1 = len(self.files['PNevt_list'])
            num_evl2 = 0
            inst1 = 'EPIC-pn'
            inst2 = ''
            list1 = 'PNevt_list'
            list2 = ''
            if num_evl1 == 0 or rerun:
                run_ep = True
        # Check if 'emproc' or 'emchain' have been run.
        elif (task == 'emproc' or task == 'emchain') and (self.active_instruments['M1'] or self.active_instruments['M2']):
            num_evl1 = len(self.files['M1evt_list'])
            num_evl2 = len(self.files['M2evt_list'])
            inst1 = 'EPIC-MOS1'
            inst2 = 'EPIC-MOS1'
            list1 = 'M1evt_list'
            list2 = 'M2evt_list'
            if (num_evl1 == 0 and num_evl2 == 0) or rerun:
                run_em = True
        # Check if 'rgsproc' has been run.
        elif task == 'rgsproc' and (self.active_instruments['R1'] or self.active_instruments['R2']):
            num_evl1 = len(self.files['R1evt_list'])
            num_evl2 = len(self.files['R2evt_list'])
            inst1 = 'RGS1'
            inst2 = 'RGS2'
            list1 = 'R1evt_list'
            list2 = 'R2evt_list'
            if (num_evl1 == 0 and num_evl2 == 0) or rerun:
                run_rgs  = True
        
        if run_ep or run_em or run_rgs:
            self.logger.info(f'SAS command to be executed: {task}, with arguments: {inargs}')
            print(f"   SAS command to be executed: {task}, with arguments; {inargs}")
            print(f"Running {task} ..... \n")
            MyTask(task,inargs,
                   logfilename = logFile, 
                   tasklogdir  = self.work_dir,
                   output_to_terminal = self.output_to_terminal, 
                   output_to_file     = self.output_to_file).run() # <<<<< Execute SAS task
        else:
            if self.output_to_terminal:
                print(f" > {num_evl1} {inst1} event list found. Not running {task} again.")
                for x in self.files[list1]:
                    print(f"  {x}")
                if num_evl2 > 0:
                    print(f" > {num_evl2} {inst2} event list found. Not running {task} again.")
                    for x in self.files[list2]:
                        print(f"  {x}")
            if self.output_to_file:
                self.logger.info(f" > {num_evl1} {inst1} event list found. Not running {task} again.")
                for x in self.files[list1]:
                    self.logger.info(f"  {x}")
                if num_evl2 > 0:
                    self.logger.info(f" > {num_evl2} {inst2} event list found. Not running {task} again.")
                    for x in self.files[list2]:
                        self.logger.info(f"  {x}")

        # Check if run sucsessfully
        self.find_event_list_files(print_output=False)
        if (len(self.files['PNevt_list']) == 0) and run_ep:
            print("Something has gone wrong. I cant find any event list files after running epproc. \n")
        if (len(self.files['M1evt_list']) == 0 and len(self.files['M2evt_list']) == 0 and run_em):
            print("Something has gone wrong. I cant find any event list files after running emproc. \n")
        if (len(self.files['R1evt_list']) == 0 and len(self.files['R2evt_list']) == 0 and run_rgs):
            print("Something has gone wrong. I cant find any event list files after running rgsproc. \n")
        self.find_rgs_spectra_files(print_output=False)
    
    def __run_calibration(self,cifbuild_opts,odfingest_opts):
        """
        --Not intended to be used by the end user. Internal use only.--

        Making this a separate function since it can be called from different 
        inside the function calibrate_odf. Prevents duplication of code.
        """
        # Run cifbuild and odfingest on the new data.
        os.chdir(self.odf_dir)
        self.logger.info(f'Changed directory to {self.odf_dir}')

        # Checks that the MANIFEST file is there
        exists, MANIFEST = self.__check_for_manifest(return_file_name=True)
        if exists:
            self.logger.info(f'File {MANIFEST} exists')
        else:
            self.logger.error(f'MANIFEST File not present. Please check ODF!')
            print(f'MANIFEST File not present. Please check ODF!')
            sys.exit(1)

        # Now we start preparing the SAS_ODF and SAS_CCF
        self.logger.info(f'Setting SAS_ODF = {self.odf_dir}')
        print(f'\nSetting SAS_ODF = {self.odf_dir}')
        os.environ['SAS_ODF'] = self.odf_dir

        # Change to working directory
        if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
        os.chdir(self.work_dir)

        # Run cifbuild
        self.logger.info(f'Running cifbuild with inputs: {cifbuild_opts} ...')
        print(f'\nRunning cifbuild with inputs: {cifbuild_opts} ...')
        MyTask('cifbuild',cifbuild_opts,
               logfilename = self.logfilename, 
               tasklogdir  = self.work_dir,
               output_to_terminal = self.output_to_terminal, 
               output_to_file     = self.output_to_file).run()
        
        # Check whether ccf.cif is produced or not
        ccfcif = glob.glob('ccf.cif')
        try:
            os.path.exists(ccfcif[0])
            self.logger.info(f'CIF file {ccfcif[0]} created')
        except FileExistsError:
            self.logger.error('The ccf.cif was not produced')
            print('ccf.cif file is not produced')
            sys.exit(1)
        
        # Sets SAS_CCF variable
        fullccfcif = os.path.join(self.work_dir, 'ccf.cif')
        self.logger.info(f'Setting SAS_CCF = {fullccfcif}')
        print(f'\nSetting SAS_CCF = {fullccfcif}')
        os.environ['SAS_CCF'] = fullccfcif
        self.files['sas_ccf'] = fullccfcif

        # Now run odfingest
        self.logger.info(f'Running odfingest with inputs: {odfingest_opts} ...')
        print(f'\nRunning odfingest with inputs: {odfingest_opts} ...')
        MyTask('odfingest',odfingest_opts,
               logfilename = self.logfilename, 
               tasklogdir  = self.work_dir,
               output_to_terminal = self.output_to_terminal, 
               output_to_file     = self.output_to_file).run()

        # Check whether the SUM.SAS has been produced or not
        sumsas = glob.glob('*SUM.SAS')
        try:
            os.path.exists(sumsas[0])
            self.logger.info(f'SAS summary file {sumsas[0]} created')
        except FileExistsError:
            self.logger.error('SUM.SAS file was not produced') 
            print('SUM.SAS file was not produced')
            sys.exit(1)
        
        # Set the SAS_ODF to the SUM.SAS file
        fullsumsas = os.path.join(self.work_dir, sumsas[0])
        os.environ['SAS_ODF'] = fullsumsas
        self.logger.info(f'Setting SAS_ODF = {fullsumsas}')
        print(f'\nSetting SAS_ODF = {fullsumsas}')
        self.files['sas_odf'] = fullsumsas
        
        # Check that the SUM.SAS file has the right PATH keyword
        with open(self.files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if os.path.abspath(path) != os.path.abspath(self.odf_dir):
                        self.logger.error(f'SAS summary file PATH {path} mismatches {self.odf_dir}')
                        raise Exception(f'SAS summary file PATH {path} mismatches {self.odf_dir}')
                    else:
                        self.logger.info(f'Summary file PATH keyword matches {self.odf_dir}')
                        print(f'\nSummary file PATH keyword matches {self.odf_dir}')

        self.get_active_instruments()

        print(f'''\n\n
        SAS_CCF = {self.files['sas_ccf']}
        SAS_ODF = {self.files['sas_odf']}
        \n''')

        return
    
    def __reset_logger(self,
                       logbasename = None,
                       logfilename = None,
                       tasklogdir  = None,
                       output_to_terminal = True,
                       output_to_file     = False):
        """
        Resets the logger using new inputs.
        """
        if logbasename is None:
            logbasename = 'ObsID_' + self.obsid

        self.logger = get_logger(logbasename,
                                 toterminal  = output_to_terminal,
                                 tofile      = output_to_file,
                                 logfilename = logfilename,
                                 tasklogdir  = tasklogdir)
    
    def __parse_obs_dir(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Parses the obs_dir for what is present.

        Returns a dictionary with information on what exists.
        """
        exists = {}
        items = ['obs_dir','odf_dir','pps_dir','work_dir',
                 'ccfcif','SUMSAS','manifest',
                 'ODF_files','PPS_files']
        
        for item in items: exists[item] = False

        # Set directories for the observation, odf, pps, and work.
        obs_dir  = os.path.join(self.data_dir,self.obsid)
        odf_dir  = os.path.join(obs_dir,'ODF')
        pps_dir  = os.path.join(obs_dir,'PPS')
        work_dir = os.path.join(obs_dir,'work')

        if os.path.exists(obs_dir): exists['obs_dir']  = True
        if os.path.exists(odf_dir): 
            exists['odf_dir']  = True
            # Just checks if files are there. Doesn't check if they
            # are real or correct.
            if len(os.listdir(odf_dir)) != 0:
                exists['ODF_files'] = True
        if os.path.exists(pps_dir):
            exists['pps_dir']  = True
            # Just checks if files are there. Doesn't check if they
            # are real or correct.
            if len(os.listdir(pps_dir)) != 0:
                exists['PPS_files'] = True
        if os.path.exists(work_dir): exists['work_dir'] = True
        exists['ccfcif'] = self.__check_for_ccf_cif()
        exists['SUMSAS'] = self.__check_for_SUM_SAS()
        exists['manifest'] = self.__check_for_manifest()

        return exists
    
    def __set_data_dir(self, data_dir):
        """
        Sets the data_dir using the following hierarchy:
            1. self.data_dir: data_dir given by user on object creation
            2. data_dir passed into this function
            3. data_dir from config file
            4. cwd

        If data_dir does not exist then it will be created.
        """
        self.logger.debug('Inside __set_data_dir')
        # Where are we?
        startdir = str(Path.cwd())

        # Brief check to see if data_dir was 
        # given on ObsID creation.
        self.logger.debug('Check if self.data_dir is set already')
        if self.data_dir != None:
            data_dir = self.data_dir

        # Start checking data_dir
        self.logger.debug('Check if data_dir is "None"')
        if data_dir is None:
            self.logger.debug('Check if data_dir is set in config file')
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'
            if os.path.exists(data_dir):
                self.data_dir = data_dir
                self.logger.info(f'Using data_dir from config file: {self.data_dir}')
            else:
                self.data_dir = startdir
                self.logger.info(f'Using current directory for data_dir: {self.data_dir}')
        else:
            self.logger.info(f'Setting data_dir: {data_dir}')
            self.data_dir = data_dir

        # If data_dir was not given as an absolute path, it is interpreted
        # as a subdirectory of startdir.
        self.logger.debug('Check if data_dir is an absolute path, or if it is a subdirectory of startdir')
        if self.data_dir[0] != '/':
            self.data_dir = os.path.join(startdir, self.data_dir)
        elif self.data_dir[:2] == './':
            self.data_dir = os.path.join(startdir, self.data_dir[2:])

        # Check if data_dir exists. If not then create it.
        self.logger.debug('Check if data_dir exists, if not, create it')
        if not os.path.isdir(self.data_dir):
            self.logger.info(f'{self.data_dir} does not exist. Creating it!')
            os.mkdir(self.data_dir)
            self.logger.info(f'{self.data_dir} has been created!')

        self.logger.info(f'Data directory = {self.data_dir}')
        self.logger.debug('Exiting __set_data_dir')
        return
    
    def __check_for_ccf_cif(self,):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks if the ccf.cif file exists.
        """
        exists = False

        # Check if ccf.cif file exists.
        for path, directories, files in os.walk(self.obs_dir):
            for file in files:
                if 'ccf.cif' in file:
                    if os.path.exists(os.path.join(path,file)):
                        exists = True
        return exists
    
    def __check_for_SUM_SAS(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks if the the *SUM.SAS file exists.
        """
        exists = False

        # Looking for *SUM.SAS file.
        for path, directories, files in os.walk(self.obs_dir):
            for file in files:
                if 'SUM.SAS' in file:
                    if os.path.exists(os.path.join(path,file)):
                        exists = True
        return exists
    
    def __check_for_manifest(self,return_file_name=False):
        """
        Checks if manifest file exists.
        """

        exists = False

        MANIFEST = glob.glob(self.obs_dir+'/**/*MANIFEST*', recursive=True)
        if len(MANIFEST) > 0:
            if os.path.exists(MANIFEST[0]): 
                exists = True
                MANIFEST = MANIFEST[0]
        
        if return_file_name:
            return exists, MANIFEST
        else:
            return exists
    
    def __get_list_of_ODF_files(self):
        """
        Returns list of all files in the the ODF directory.
        """
        file_list = []
        if os.path.exists(self.odf_dir):
            file_list = glob.glob(self.odf_dir+'/*')

        return file_list
    
    def __get_list_of_PPS_files(self):
        """
        Returns list of all files in the the PPS directory.
        """
        file_list = []
        if os.path.exists(self.pps_dir):
            file_list = glob.glob(self.pps_dir+'/*')

        return file_list
    
    def __remove_attr(self, attr_name):
        if hasattr(self, attr_name): delattr(self, attr_name)
