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
# 
# obsid.py

# Standard library imports
import os, sys, shutil, glob, numbers, re, subprocess
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from warnings import warn

# Third party imports
from astropy.io import fits
from astroquery.heasarc import Heasarc

# Local application imports
from pysas import sas_cfg
from pysas.init_sas import initializesas
from pysas.sasutils import download_data as dl_data
from pysas.logger import get_logger
from pysas.sastask import MyTask
from pysas.sasutils import load_json_from_package
from pysas.pysasplotutils import quick_image_plot as qip
from pysas.pysasplotutils import quick_light_curve_plot as qlcp

repo_opts = ['esa','xsa','heasarc','nasa','sciserver','fornax','aws']

class ObsID:
    """
    Class for handling XMM data files for a single Obs ID.

    Parameters
    ----------
    obsid : str or int
        The 10 digit Observation ID.
    data_dir : str, optional
        Data directory. Defaults to the current directory or set by 
        sas_config file.
    
    Other Parameters
    ----------------
    logfilename : str, optional
        Name of log file where all output will be written. Overrides 
        default log file names. Defaults to either {obsid}.log or 
        {taskname}.log.
    tasklogdir : str, optional
        Directory for log files. Overrides default log directory. Defaults 
        to work_dir.
    output_to_terminal : bool, optional
        Whether to print log output to the terminal.
        Defaults to True.
    output_to_file : bool, optional
        Whether to write log output to a file.
        Defaults to False.
    """
    def __init__(self, obsid, 
                 data_dir    = None,
                 logfilename = None,
                 tasklogdir  = None,
                 output_to_terminal = True,
                 output_to_file     = False):
        """
        Initialisation method for file handling super class. Checks for the 
        presence of data files for the obsid. Sets file links.
        """        
        if isinstance(obsid, numbers.Number):
            obsid = f'{obsid:010}'
        self._obsid       = obsid
        self._data_dir    = data_dir
        self._files       = {}
        self._logfilename = logfilename
        self._output_to_terminal = output_to_terminal
        self._output_to_file     = output_to_file
        # _set_obsid uses a temporary logger, that will only
        # output to the terminal.
        self._logger = get_logger('ObsID_' + self._obsid, 
                                 toterminal  = self._output_to_terminal,
                                 tofile      = False)
        # Sets info on the data_dir, obs_dir, etc.
        self._logger.debug('Temporary logger generated')
        self._set_obsid()
        # Remove temporary logger
        self._logger.debug('Removing temporary logger')
        self._remove_attr('logger')
        
        # Set the directory for log files.
        # Log directory will be (in this order):
        # 1. Directory passed in by the user
        # 2. data_dir
        # 3. cwd
        if tasklogdir is None:
            if not self._data_dir is None and os.path.exists(self._data_dir):
                self._tasklogdir = self._data_dir
            else:
                # By default get_logger will use cwd
                # if tasklogdir = None
                self._tasklogdir = tasklogdir
        else:
            # User defined directory
            if not os.path.exists(tasklogdir):
                if self._output_to_terminal:
                    print(f'Warning: User defined tasklogdir, {tasklogdir} does not exist!')
                    print(f'Resetting tasklogdir to the current directory!')
                tasklogdir = None
            self._tasklogdir = tasklogdir
        
        # Create logger
        self._logger = get_logger('ObsID_' + self._obsid, 
                                  toterminal  = self._output_to_terminal,
                                  tofile      = self._output_to_file, 
                                  logfilename = self._logfilename,
                                  tasklogdir  = self._tasklogdir)
        self._logger.debug('Logger generated')

        # This simplifies discovery of several common PPS files.
        # Reasoning: While these files can be found using 
        # 'return_PPS_filenames', the returned list(s) 
        # would need additional filtering.
        # For example, 'EPIC_images' would take two calls to 
        # 'return_PPS_filenames' depending on whether the
        # Obs is slew or not. This gets around that.
        # Also, 'return_PPS_filenames' for SUMMAR files 
        # would return a list of multiple files. This allows the 
        # main file to be selected directly.
        self._file_patterns = {'main_summary'     : '.*OBX.*SUMMAR.*.HTM$',
                               'RGS_event_lists'  : '.*(R1|R2).*EVENLI.*.FTZ$',
                               'RGS_spectra'      : '.*(R1|R2).*RSPEC.*.FTZ$',
                               'EPIC_event_lists' : '.*(M1|M2|PN).*EVLI.*.FTZ$',
                               'EPIC_images'      : '.*(M1|M2|PN).*IMAGE_.*.FTZ$'}

        products = load_json_from_package(os.path.join('_data','PPS_product_names.json'))

        self.EPIC_PPS_products = products['EPIC_products']
        self.RGS_PPS_products  = products['RGS_products']
        self.OBS_PPS_products  = products['Obs_products']
        self.OM_PPS_products   = products['OM_products']
        self._logger.debug('PPS product dicts loaded.')

        self.parse_PPS_dir()

        self._logger.debug('Finished with ObsID.__init__')

    @property
    def obsid(self):
        """The 10 digit Observation ID."""
        return self._obsid

    @property
    def data_dir(self):
        """Path to the base data directory."""
        return self._data_dir

    @property
    def obs_dir(self):
        """Path to the observation data directory, 
        by default 'data_dir/obsid'."""
        return self._obs_dir

    @property
    def odf_dir(self):
        """Path to the directory containing the ODF data products, 
        by default 'obs_dir/ODF'.
        """
        return self._odf_dir

    @property
    def pps_dir(self):
        """Path to the directory containing the PPS data products, 
        by default 'obs_dir/PPS'.
        """
        return self._pps_dir

    @property
    def work_dir(self):
        """Path to the directory containing the SAS generated data products, 
        by default 'obs_dir/work'.
        """
        return self._work_dir

    @property
    def files(self):
        """Dictionary with lists of data files."""
        return self._files        

    def _set_obsid(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Basic method for setting the environment variables for a single 
        'ObsID'.

        Checks for the existence of various directories. If a directory 
        is not found then _set_obsid will stop and use 'return' command.
        Directories that will be checked for (in this order):
            
            data_dir
            obs_dir
            odf_dir -or- pps_dir
            work_dir

        Then checks for the ccf.cif, SUM.SAS files and event lists.

        Similar to download_data, but will not download any data, 
        or do anything other than link to files and directories. 
        """
        self._logger.debug('Entered _set_obsid')
        # Check to see if data_dir was given by the user
        self._logger.debug('Checking for data_dir')
        data_dir_found = False
        if not self._data_dir is None:
            self._logger.info(f'User input data_dir: {self._data_dir}.')
            if not os.path.exists(self._data_dir):
                # If data_dir given by user does **not** exist
                self._logger.error(f'Did not find: {self._data_dir}')
                self._data_dir = os.getcwd()
                self._logger.info(f'Resetting data_dir to the current directory: "{self._data_dir}".')
                self._logger.info(f'Will check config file for default.')
            else:
                # If data_dir given by user **does** exist
                data_dir_found = True
                self._logger.debug(f'data_dir found: {self._data_dir}')
        
        # Check if data_dir is in the config file
        self._logger.debug('Checking for data_dir from config file')
        if not data_dir_found and sas_cfg.config.has_option('sas','data_dir'):
            # If data_dir is in the config file
            data_dir = sas_cfg.get_setting('data_dir')
            self._logger.debug(f'Trying default data_dir from config file: {data_dir}')
            if os.path.exists(data_dir):
                # data_dir from config file exists
                self._data_dir = data_dir
                self._logger.info(f'Data directory found: {self._data_dir}')
            else:
                # data_dir from config file does **not** exist!
                self._logger.error(f'Did not find data_dir set in the config file: {self._data_dir}')
                self._data_dir = os.getcwd()
                self._logger.info(f'Resetting data_dir to the current directory: "{self._data_dir}".')
        else:
            self._logger.info(f'No data_dir found in config file.')
            self._data_dir = os.getcwd()
            self._logger.info(f'Resetting data_dir to the current directory: "{self._data_dir}".')
            self._logger.debug(f'Exiting _set_obsid, no data_dir found.')
            return
            
        # data_dir is set.
        # Setting other directory paths.

        # Set directories for the observation, odf, pps, and work.
        # This allows customization of the name of the work directory.
        # The name of the work_dir can even be empty (''). This will
        # place all output files directly in the obs_dir.
        # Makes pySAS compatible with XGA. You're welcome David.
        work_dir_name = sas_cfg.get_setting('work_dir_name')
        self._logger.debug(f'Setting obs_dir, odf_dir, pps_dir, and work_dir')
        self._obs_dir  = os.path.join(self._data_dir,self._obsid)
        self._odf_dir  = os.path.join(self._obs_dir,'ODF')
        self._pps_dir  = os.path.join(self._obs_dir,'PPS')
        self._work_dir = os.path.join(self._obs_dir,work_dir_name)
        self._logger.debug(f'obs_dir: {self._obs_dir}')
        self._logger.debug(f'odf_dir: {self._odf_dir}')
        self._logger.debug(f'pps_dir: {self._pps_dir}')
        self._logger.debug(f'work_dir: {self._work_dir}')

        if os.path.exists(self._obs_dir):
            self._logger.info(f'obs_dir found at {self._obs_dir}.')
        else:
            self._logger.info(f'obs_dir not found {self._obs_dir}. User must download data!')
            self._logger.debug(f'Exiting _set_obsid, no obs_dir found')
            return
        
        if os.path.exists(self._odf_dir):
            self._logger.info(f'odf_dir found at {self._odf_dir}.')
            os.environ['SAS_ODF'] = self._odf_dir
            if os.path.exists(self._pps_dir):
                self._logger.info(f'pps_dir found at {self._pps_dir}.')
        else:
            if os.path.exists(self._pps_dir):
                self._logger.info(f'pps_dir found at {self._pps_dir}.')
            else:
                self._logger.info(f'ODF and PPS directories not found! User must download data!')
                self._logger.debug(f'Exiting _set_obsid, no odf_dir nor pps_dir found')
                return
            
        # Get lists of ODF and PPS files.
        if os.path.exists(self._odf_dir):
            self._logger.debug(f'Getting list of ODF files')
            self._files['ODF'] = self._get_list_of_ODF_files()
        if os.path.exists(self._pps_dir):
            self._logger.debug(f'Getting list of PPS files')
            self._files['PPS'] = self._get_list_of_PPS_files()
        
        if os.path.exists(self._work_dir):
            self._logger.info(f'work_dir found at {self._work_dir}.')
            self._files['work'] = self._get_list_of_work_files()
        else:
            self._logger.info(f'Default work_dir not found! User must create it!')
            self._logger.debug(f'Exiting _set_obsid, no work_dir found')
            return

        self._logger.info(f'Data directory = {self._data_dir}')
        self._logger.info(f'Existing directory for {self._obsid} found ...')
        self._logger.info(f'Searching {self._data_dir}/{self._obsid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        _ = self.get_cal_ind()
        if self._files['sas_ccf'] is not None:
            # Set 'SAS_CCF' enviroment variable.
            os.environ['SAS_CCF'] = self._files['sas_ccf']
            self._logger.info('SAS_CCF = {0}'.format(self._files['sas_ccf']))

        # Looking for *SUM.SAS file.
        exists = self.get_SUM_SAS()
        if exists:
            # Set 'SAS_ODF' enviroment variable.
            os.environ['SAS_ODF'] = self._files['sas_odf']
            self._logger.info('SAS_ODF = {0}'.format(self._files['sas_odf']))

        # Check for previously generated event lists.
        self.find_event_list_files(print_output = self._output_to_terminal)
        self.find_rgs_spectra_files(print_output = self._output_to_terminal)

        # Change to work directory.
        os.chdir(self._work_dir)
        self._logger.info(f'Changing to work_dir: {self._work_dir}')

        # Exit the _set_obsid function. Everything is set.
        self._logger.debug(f'Exiting _set_obsid, success!')
        return

    def basic_setup(self, 
                    data_dir: str     = None,
                    repo: str         = None,
                    overwrite: bool   = False,
                    rerun: bool       = False,
                    recalibrate: bool = False,
                    run_epproc: bool  = True,
                    run_emproc: bool  = True,
                    run_rgsproc: bool = True,
                    run_epchain: bool = False,
                    run_emchain: bool = False,
                    **kwargs):
        """
        Function to do all basic analysis tasks. The function will:

        1. Download data by calling 'download_ODF_data'
        2. Call the function 'calibrate_odf'

            A. Run 'cifbuild'
            B. Run 'odfingest'

        3. Run 'epproc' -OR- 'epchain'
        4. Run 'emproc' -OR- 'emchain'
        5. Run 'rgsproc'

        If 'run_epchain' is set to 'True', then 'epproc' will not run.
        If 'run_emchain' is set to 'True', then 'emproc' will not run.

        All input arguments for 'download_ODF_data' and 'calibrate_odf'
        can be passed to 'basic_setup'.

        Parameters
        ----------
        data_dir : str, optional
            Data directory. Defaults to the current directory or set by 
            sas_config file.
        repo : str, optional
            Which repository to use to download data. Accepted values are, 
            'ESA' (data from the XSA), 
            'NASA' (data from the HEASARC), 
            'AWS' (data from AWS s3 bucket (NASA)), 
            'Fornax' (if user is on Fornax),
            'SciServer' (if user is on SciServer).
            Defaults to 'ESA' ('XSA') or set by sas_config file.
        overwrite : bool, optional
            If True will force overwrite of data if obsid data already exists 
            in 'data_dir/obsid'. Defaults to False.
        rerun : bool, optional
            Rerun the 'procs' or 'chains'.
            Defaults to False.
        recalibrate : bool, optional
            Rerun 'cifbuild' and 'odfingest'.
            Defaults to False.
        run_epproc : bool, optional
            Whether to run the EPIC-pn processing pipeline (`epproc`). 
            Defaults to True.
        run_emproc : bool, optional
            Whether to run the EPIC-MOS processing pipeline (`emproc`). 
            Defaults to True.
        run_rgsproc : bool, optional
            Whether to run the RGS processing pipeline (`rgsproc`). 
            Defaults to True.
        run_epchain : bool, optional
            Whether to run the EPIC-pn chain-level pipeline (`epchain`). 
            Defaults to False.
        run_emchain : bool, optional
            Whether to run the EPIC-MOS chain-level pipeline (`emchain`). 
            Defaults to False.
        **kwargs
            Additional keyword arguments passed to 'download_ODF_data' and 
            'calibrate_odf'.

        Raises
        ------
        ValueError
            Download repository not recognized.
        EnvironmentError
            LHEASOFT is not set. Please initialise HEASOFT.
        EnvironmentError
            SAS_DIR is not defined. Please initialise SAS.
        EnvironmentError
            SAS_CCFPATH not set. Please define it.
        """

        self._logger.debug('Starting basic_setup')
        # Set data_dir
        self._logger.debug('Running _set_data_dir')
        self._set_data_dir(data_dir)

        # Set directories for the observation, odf, and work.
        # This allows customization of the name of the work directory.
        # The name of the work_dir can even be empty (''). This will
        # place all output files directly in the obs_dir.
        # Makes pySAS compatible with XGA. You're welcome David.
        work_dir_name = sas_cfg.get_setting('work_dir_name')
        self._obs_dir  = os.path.join(self._data_dir,self._obsid)
        self._odf_dir  = os.path.join(self._obs_dir,'ODF')
        self._work_dir = os.path.join(self._obs_dir,work_dir_name)
        self._logger.debug(f'obs_dir: {self._obs_dir}')
        self._logger.debug(f'odf_dir: {self._odf_dir}')
        self._logger.debug(f'work_dir: {self._work_dir}')

        # Deal with the rest of the inputs.
        # Set repo from config file (default 'esa')
        self._logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self._logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self._logger.error('Download repository not recognized!')
                raise ValueError(f'Download repository {repo} not recognized. '\
                                 f'Allowed Options for repo are {repo_opts}.')
            else:
                self._logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self._logger.debug(f'repo set to: {self.repo}')

        # Checking LHEASOFT, SAS_DIR and SAS_CCFPATH
        lheasoft = os.environ.get('LHEASOFT')
        if not lheasoft:
            self._logger.error('LHEASOFT is not set. Please initialise HEASOFT.')
            raise EnvironmentError('LHEASOFT is not set. Please initialise HEASOFT.')
        else:
            self._logger.info(f'LHEASOFT = {lheasoft}')

        sasdir = os.environ.get('SAS_DIR')
        if not sasdir:
            self._logger.error('SAS_DIR is not defined. Please initialise SAS.')
            raise EnvironmentError('SAS_DIR is not defined. Please initialise SAS.')
        else:
            self._logger.info(f'SAS_DIR = {sasdir}') 

        sas_ccfpath = os.environ.get('SAS_CCFPATH')
        if not sas_ccfpath:
            self._logger.error('SAS_CCFPATH not set. Please define it.')
            raise EnvironmentError('SAS_CCFPATH not set. Please define it.')
        else:
            self._logger.info(f'SAS_CCFPATH = {sas_ccfpath}')
        
        os.chdir(self._data_dir)
        self._logger.info(f'Changed directory to {self._data_dir}')
        if self._output_to_terminal:
            print(f'''

            Starting SAS session

            Data directory = {self._data_dir}

            ''')

        # Download the data
        self._logger.debug('Call download_ODF_data')
        self.download_ODF_data(repo             = self.repo,
                               data_dir         = self._data_dir,
                               overwrite        = overwrite,
                               proprietary      = kwargs.get('proprietary', False),
                               credentials_file = kwargs.get('credentials_file', None),
                               encryption_key   = kwargs.get('encryption_key', None))

        # Set work directory
        if not hasattr(self, 'work_dir'):
            work_dir_name = sas_cfg.get_setting('work_dir_name')
            self._work_dir = os.path.join(self._obs_dir,work_dir_name)
            self._logger.info(f'Setting work_dir: {self._work_dir}')

        if not os.path.exists(self._work_dir):
            self._logger.info(f'{self._work_dir} does not exist. Creating it!')
            os.mkdir(self._work_dir)

        verbosity     = kwargs.get('verbosity', None)
        old_verbosity = None
        if verbosity:
            old_verbosity = os.environ.get('SAS_VERBOSITY')
            if isinstance(verbosity, numbers.Number):
                verbosity = f'{verbosity}'
            self._logger.debug(f'Temporarily setting verbosity to {verbosity}')
            os.environ['SAS_VERBOSITY'] = verbosity

        # Calibrate ODF data
        self._logger.debug('Call calibrate_odf')
        self.calibrate_odf(obs_dir        = self._obs_dir,
                           sas_ccf        = kwargs.get('sas_ccf', None),
                           sas_odf        = kwargs.get('sas_odf', None),
                           cifbuild_opts  = kwargs.get('cifbuild_opts', {}),
                           odfingest_opts = kwargs.get('odfingest_opts', {}),
                           recalibrate    = recalibrate)

        # Run basic processing
        if run_epproc and not run_epchain:
            self._logger.debug('Run epproc')
            self._run_analysis('epproc',
                                kwargs.get('epproc_args', {}),
                                rerun   = rerun,
                                logFile = 'epproc.log')
        
        if run_epchain:
            self._logger.debug('Run epchain')
            self._run_analysis('epchain',
                                kwargs.get('epchain_args', {}),
                                rerun   = rerun,
                                logFile = 'epchain.log')

        if run_emproc and not run_emchain:
            self._logger.debug('Run emproc')
            self._run_analysis('emproc',
                                kwargs.get('emproc_args', {}),
                                rerun   = rerun,
                                logFile = 'emproc.log')
            
        if run_emchain:
            self._logger.debug('Run emchain')
            self._run_analysis('emchain',
                                kwargs.get('emchain_args', {}),
                                rerun   = rerun,
                                logFile = 'emchain.log')
            
        if run_rgsproc:
            self._logger.debug('Run rgsproc')
            self._run_analysis('rgsproc',
                                kwargs.get('rgsproc_args', {}),
                                rerun   = rerun,
                                logFile = 'rgsproc.log')
        
        #if run_omichain:
        #    self._run_analysis('omichain',
        #                        kwargs.get('omichain_args', []),
        #                        rerun   = rerun,
        #                        logFile = 'omichain.log')

        if old_verbosity:
            self._logger.debug(f'Resetting verbosity to {old_verbosity}')
            os.environ['SAS_VERBOSITY'] = old_verbosity
        
        self._logger.debug('Exiting basic_setup')
        return
    
    def calibrate_odf(self,
                      obs_dir: str | Path  = None,
                      sas_ccf: str | Path  = None,
                      sas_odf: str | Path  = None,
                      cifbuild_opts: dict  = {},
                      odfingest_opts: dict = {},
                      recalibrate: bool    = False):
        """
        Function to run 'cifbuild' and 'odfingest' on ODF files.
        
        If obs_dir exists it will search it and any subdirectories for the 
        ccf.cif and SUM.SAS files. Will not rerun calibration if the ccf.cif 
        and SUM.SAS files exist, unless recalibrate = True.

        Optionally the paths to the ccf.cif and SUM.SAS files can be given 
        through sas_ccf and sas_odf respectively.

        Parameters
        ----------
        obs_dir : str | Path, optional
            Path to the obs directory. By default will use the obs_dir in the 
            default data_dir.
        sas_ccf : str | Path, optional
            Path to the Calibration Configuration File (ccf.cif). Defaults to 
            None.
        sas_odf : str | Path, optional
            Path to the SUM.SAS file. Defaults to None.
        cifbuild_opts : dict, optional
            Additional keyword options passed to the SAS `cifbuild` task.
            Defaults to an empty dictionary.
        odfingest_opts : dict, optional
            Additional keyword options passed to the SAS `odfingest` task.
            Defaults to an empty dictionary.
        recalibrate : bool, optional
            Whether to force recalibration even if calibration products already 
            exist.
            Defaults to False.

        Raises
        ------
        IsADirectoryError
            Observation directory: {self._obs_dir} does not exist.
        FileNotFoundError
            ODF directory and files not found.
        """

        # If user passes in obs_dir
        if not obs_dir is None:
            self._obs_dir = obs_dir
            self._logger.debug(f'Setting obs_dir: {self._obs_dir}')

        # If no obs_dir was passed in and not set previously
        if not hasattr(self, 'obs_dir'):
            if not hasattr(self, 'data_dir'):
                # If the user has gotten this far without setting data_dir,
                # they are probably doing something very wrong.
                self._logger.debug(f'If you are seeing this, then you are '\
                                  f'probably doing something wrong.')
                self._set_data_dir(None)
            self._obs_dir = os.path.join(self._data_dir, self._obsid)
            self._logger.info(f'Setting obs_dir to: {self._obs_dir}')

        # Check if obs_dir exists. If not then raise an Exception.
        if not os.path.isdir(self._obs_dir):
            self._logger.error(f'Observation directory: {self._obs_dir} does '\
                               'not exist!')
            print(f'Error! Observation directory: {self._obs_dir} does not '\
                   'exist!')
            print('Please provide the path to the observation directory \n '\
                  'using the input obs_dir=path/to/obs/dir/.')
            raise IsADirectoryError(f'Observation directory: {self._obs_dir} '\
                                     'does not exist!')

        self._logger.info(f'Observation directory = {self._obs_dir}')

        # Deal with the rest of the inputs.
        self._files['sas_ccf'] = sas_ccf
        self._files['sas_odf'] = sas_odf
        if cifbuild_opts is None: cifbuild_opts = {}
        self.cifbuild_opts = cifbuild_opts
        self._logger.debug(f'cifbuild_opts = {cifbuild_opts}')
        if odfingest_opts is None: odfingest_opts = {}
        self.odfingest_opts = odfingest_opts
        self._logger.debug(f'odfingest_opts = {odfingest_opts}')
        
        os.chdir(self._obs_dir)
        self._logger.info(f'calibrate_odf: Changed directory to {self._obs_dir}')

        # Set directories for the odf and work.
        # Set odf_dir
        if not hasattr(self, 'odf_dir'):
            self._odf_dir = os.path.join(self._obs_dir,'ODF')
            self._logger.debug(f'Setting odf_dir: {self._odf_dir}')
        if not hasattr(self, 'work_dir'):
            work_dir_name = sas_cfg.get_setting('work_dir_name')
            self._work_dir = os.path.join(self._obs_dir,work_dir_name)
            self._logger.debug(f'Setting work_dir: {self._work_dir}')

        # Runs calibration if recalibrate = True. Default recalibrate = False
        # Else, looks for ccf.cif and *SUM.SAS files.
        # If ccf.cif and *SUM.SAS files are not found then will run calibration.
        
        if recalibrate:
            if os.path.exists(self._odf_dir):
                # odf_dir exists
                if len(os.listdir(self._odf_dir)) != 0:
                    # If files exist in odf_dir
                    self._logger.debug('Run calibration')
                    self._run_calibration(cifbuild_opts,odfingest_opts)
                else:
                    self._logger.error('ODF directory and files not found!')
                    print('ODF directory and files not found! Try downloading '\
                          'data again.')
                    raise FileNotFoundError('ODF directory and files not '\
                                            'found!')
            # No need for further checks recalibration run. Return control to 
            # calling function.
            return
        else:
            ccf_exists = False
            SUM_exists = False
            self._logger.info(f'Searching {self._obs_dir} for ccf.cif and '\
                              '*SUM.SAS files ...')

            # Looking for ccf.cif file.
            if self._files['sas_ccf'] is None:
                # get_cal_ind should set self._files['sas_ccf'] if file is found.
                _ = self.get_cal_ind()
                # Will only accept locally generated calibration files. 
                # No PPS CALIND file accepted.
                if (self._files['sas_ccf'] is not None and 
                'ccf.cif' in self._files['sas_ccf']): ccf_exists = True
            else:
                # Check if ccf.cif file path given by user exists.
                try:
                    os.path.exists(self._files['sas_ccf'])
                    self._logger.info('{0} is '\
                    'present'.format(self._files['sas_ccf']))
                    ccf_exists = True
                except FileExistsError:
                    # The only way to get this error is if the user provided a 
                    # bad filename or path.
                    self._logger.error('File {0} not present! Please check if '\
                    'path is correct!'.format(self._files['sas_ccf']))
                    print('File {0} not present! Please check if path is '\
                    'correct!'.format(self._files['sas_ccf']))
                    sys.exit(1)
            
            # Looking for *SUM.SAS file.
            if self._files['sas_odf'] is None:
                SUM_exists = self.get_SUM_SAS()                    
            else:
                # Check if *SUM.SAS file path given by user exists.
                try:
                    SUM_exists = self.get_SUM_SAS(user_defined_file = 
                                                  self._files['sas_odf'])
                    if SUM_exists:
                        self._logger.info('{0} is '\
                        'present'.format(self._files['sas_odf']))
                except FileExistsError:
                    # The only way to get this error is if the user provided a 
                    # bad filename or path.
                    self._logger.error('File {0} not present! Please check if ' \
                    'path is correct!'.format(self._files['sas_odf']))
                    print('File {0} not present! Please check if path is ' \
                    'correct!'.format(self._files['sas_odf']))
                    sys.exit(1)

            if ccf_exists and SUM_exists:
                # Set 'SAS_CCF' enviroment variable.
                os.environ['SAS_CCF'] = self._files['sas_ccf']
                self._logger.info('SAS_CCF = {0}'.format(self._files['sas_ccf']))
                if self._output_to_terminal:
                    print('SAS_CCF = {}'.format(self._files['sas_ccf']))

                # Set 'SAS_ODF' enviroment variable.
                os.environ['SAS_ODF'] = self._files['sas_odf']
                self._logger.info('SAS_ODF = {0}'.format(self._files['sas_odf']))
                if self._output_to_terminal:
                    print('SAS_ODF = {0}'.format(self._files['sas_odf']))
            else:
                # If either the ccf.cif or *SUM.SAS files are not present, 
                # then run calibration.
                self._run_calibration(cifbuild_opts,odfingest_opts) 
            
            # Set 'SAS_ODF' enviroment variable.
            os.environ['SAS_ODF'] = self._files['sas_odf']
            self._logger.info('SAS_ODF = {0}'.format(self._files['sas_odf']))
            if self._output_to_terminal:
                print('SAS_ODF = {0}'.format(self._files['sas_odf']))

            self.get_active_instruments()

            if not os.path.exists(self._work_dir): 
                os.mkdir(self._work_dir)
                self._logger.debug(f'Making work_dir: {self._work_dir}')
            # Exit the calibrate_odf function. Everything is set.
        
        self._files['ODF'] = self._get_list_of_ODF_files()

        self._logger.debug('Exiting calibrate_odf')
        return
    
    def download_ODF_data(self,
                          repo: str = None,
                          data_dir: str = None,
                          overwrite: bool = False,
                          proprietary: bool = False,
                          credentials_file: str = None,
                          encryption_key: str = None):
        """
        This handles preliminary setup for downloading ODF data files, then 
        calls download_data from sasutils. If ODF files are present then will 
        not download the files again, unless overwrite=True.

        Parameters
        ----------
        repo : str, optional
            Which repository to use to download data. Accepted values are, 
            'ESA' (data from the XSA), 
            'NASA' (data from the HEASARC), 
            'AWS' (data from AWS s3 bucket (NASA)), 
            'Fornax' (if user is on Fornax),
            'SciServer' (if user is on SciServer).
            Defaults to 'ESA' ('XSA') or set by sas_config file.
        data_dir : str | Path, optional
            Path to directory where the data will be downloaded. Automatically 
            creates directory 'data_dir/obsid'. 
            Default from sas_config file, or current working directory.
        overwrite : bool, optional
            If True will force overwrite of data if obsid data already exists 
            in 'data_dir/obsid'. 
            Defaults to False.
        proprietary : bool, optional
            Flag for downloading proprietary data from the XSA at ESA. 
            Defaults to False.
        credentials_file : str, optional
            Path and filename of file containing XSA username and password. For 
            proprietary data only. (If not given then astroquery will ask user 
            for username and password.) 
            Defaults to None.
        encryption_key : str, optional
            Encryption key for proprietary data, a string 32 characters long. 
            -OR- path to file containing ONLY the encryption key. Note: ONLY 
            used for data from the HEASARC. 
            Defaults to None.

        Raises
        ------
        ValueError
            Download repository not recognized.
        """
        
        # Set data_dir
        self._set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self._obs_dir = os.path.join(self._data_dir,self._obsid)
            self._logger.debug(f'Setting obs_dir: {self._obs_dir}')

        # Set odf_dir
        if not hasattr(self, 'odf_dir'):
            self._odf_dir = os.path.join(self._obs_dir,'ODF')
            self._logger.debug(f'Setting odf_dir: {self._odf_dir}')

        # Set repo from config file (default 'esa')
        self._logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self._logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self._logger.error('Download repository not recognized!')
                raise ValueError(f'Download repository {repo} not recognized. '\
                                 f'Allowed Options for repo are {repo_opts}.')
            else:
                self._logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self._logger.debug(f'repo set to: {self.repo}')

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
        call_download_data = True
        if os.path.exists(self._obs_dir):
            self._logger.info(f'Existing directory for {self._obsid} found ...')
            if overwrite:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                self._logger.info(f'Removing existing directory {self._obs_dir} ...')
                shutil.rmtree(self._obs_dir)
            else:
                # Check for files
                # Check for (in this order): odf_dir, ODF files, MANIFEST
                if os.path.exists(self._odf_dir):
                    # odf_dir exists
                    if len(os.listdir(self._odf_dir)) != 0:
                        # If files exist in odf_dir
                        manifest_exists = self._check_for_manifest()
                        if manifest_exists:
                            # If MANIFEST exists
                            self._logger.debug(f'Existing ODF directory {self._odf_dir} found ...')
                            self._logger.info(f'Data found in {self._odf_dir} not downloading again.')
                            call_download_data = False
                        else:
                            # If MANIFEST does not exist
                            self._logger.info(f'MANIFEST missing from {self._odf_dir}. Will download data.')
                            shutil.rmtree(self._odf_dir)
                    else:
                        # If no files in odf_dir
                        self._logger.info(f'ODF files missing from {self._odf_dir}. Will download data.')
                        shutil.rmtree(self._odf_dir)
                else:
                    # If odf_dir does not exist
                    self._logger.info(f'Existing ODF directory missing. Will download data.')

        if call_download_data:
            self._logger.info(f'Will download ODF data for Obs ID {self._obsid}.')

            # Function for downloading a single obsid set.
            dl_data(self._obsid,
                    self._data_dir,
                    level          = 'ODF',
                    overwrite      = overwrite,
                    repo           = self.repo,
                    logger         = self._logger,
                    proprietary    = proprietary,
                    encryption_key = encryption_key,
                    credentials_file = credentials_file)
            
        self._logger.info(f'Data directory: {self._data_dir}')
        self._logger.info(f'ObsID directory: {self._obs_dir}')
        self._files['ODF'] = self._get_list_of_ODF_files()

        return
        
    def download_PPS_data(self,
                          repo: str = None,
                          data_dir: str | Path  = None,
                          overwrite: bool = False,
                          proprietary: bool = False,
                          credentials_file: str = None,
                          encryption_key: str = None,
                          PPS_subset: bool = False,
                          instname: str = None,
                          expflag: str = None,
                          expno: str = None,
                          product_type: str = None,
                          datasubsetno: str = None,
                          sourceno: str = None,
                          extension: str = None,
                          filename: str = None,
                          **kwargs
                         ):
        """
        This handles preliminary setup for downloading PPS data files, then 
        calls download_data from sasutils. If PPS files are present then will 
        not download the files again, unless overwrite=True.

        If only a subset of PPS files is needed (i.e. not every thing) then set
        PPS_subset to True. The remaining inputs are used for downloading groups 
        of PPS files using a particular file pattern. Using these requires an 
        understanding of PPS filenames.

        Parameters
        ----------
        repo : str, optional
            Which repository to use to download data. Accepted values are, 
            'ESA' (data from the XSA), 
            'NASA' (data from the HEASARC), 
            'AWS' (data from AWS s3 bucket (NASA)), 
            'Fornax' (if user is on Fornax),
            'SciServer' (if user is on SciServer).
            Defaults to 'ESA' ('XSA') or set by sas_config file.
        data_dir : str | Path, optional
            Path to directory where the data will be downloaded. Automatically 
            creates directory 'data_dir/obsid'. 
            Default from sas_config file, or current working directory.
        overwrite : bool, optional
            If True will force overwrite of data if obsid data already exists 
            in 'data_dir/obsid'. 
            Defaults to False.
        proprietary : bool, optional
            Flag for downloading proprietary data from the XSA at ESA. 
            Defaults to False.
        credentials_file : str, optional
            Path and filename of file containing XSA username and password. For 
            proprietary data only. (If not given then astroquery will ask user 
            for username and password.) 
            Defaults to None.
        encryption_key : str, optional
            Encryption key for proprietary data, a string 32 characters long. 
            -OR- path to file containing ONLY the encryption key. Note: ONLY 
            used for data from the HEASARC. 
            Defaults to None.
        PPS_subset : bool, optional
            Set PPS_subset=True if downloading a subset of PPS.
            Defaults to False.
        instname : str, optional
            Instrument name.
            Defaults to None.
        expflag : str, optional
            Exposure flag.
            Defaults to None.
        expno : int or str, optional
            Exposure number.
            Defaults to None.
        product_type : str, optional
            PPS product type.
            Defaults to None.
        datasubsetno : str, optional
            Data subset number/character.
            Defaults to None.
        sourceno : int or str, optional
            Source number or slew step number.
            Defaults to None.
        extension : str, optional
            File format/extension.
            Defaults to None.
        filename : str, optional
            If the exact PPS file name is known, then this can be used to 
            download a single PPS file.
            Defaults to None.
        **kwargs
            Additional keyword arguments passed through to underlying download 
            handler (Astroquery).
        
        Raises
        ------
        ValueError
            Download repository not recognized.
        """
        
        # Set data_dir
        self._set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self._obs_dir = os.path.join(self._data_dir,self._obsid)
            self._logger.debug(f'Setting obs_dir: {self._obs_dir}')

        # Set pps_dir
        if not hasattr(self, 'pps_dir'):
            self._pps_dir = os.path.join(self._obs_dir,'PPS')
            self._logger.debug(f'Setting pps_dir: {self._pps_dir}')

        # Set repo from config file (default 'esa')
        self._logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self._logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self._logger.error('Download repository not recognized!')
                raise ValueError(f'Download repository {repo} not recognized. '\
                                 f'Allowed Options for repo are {repo_opts}.')
            else:
                self._logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self._logger.debug(f'repo set to: {self.repo}')

        if instname or \
           expflag or \
           expno or \
           product_type or \
           datasubsetno or \
           sourceno or \
           extension:
           PPS_subset = True

        if filename:
            # Temporarily setting PPS_subset to False
            self._logger.debug('filename passed in. Setting PPS_subset = False')
            PPS_subset = False
            if isinstance(filename,str):
                self._logger.debug('Converting filename string to list.')
                filename = [filename]

        # Checks if pps_dir exists. Will ONLY check for PPS directory.
        # Removes it if overwrite = True. Default overwrite = False.
        call_download_data = True
        if os.path.exists(self._pps_dir):
            self._logger.debug(f'Changing into pps_dir.')
            os.chdir(self._pps_dir)
            self._logger.info(f'Existing directory for PPS files for Obs ID {self._obsid} found ...')
            self._files['PPS'] = self._get_list_of_PPS_files()
            # Handle things differently if PPS_subset or filename for download
            if filename:
                # If filename is passed in only download if overwrite=True or if files are not there
                if overwrite:
                    for file in filename:
                        if os.path.exists(file):
                            self._logger.debug(f'Removing {file}')
                            os.remove(file)
                    self._logger.info(f'Downloading filenames from list. Will silently overwrite any pre-existing files.')
                else:
                    file_remove = []
                    for file in filename:
                        if os.path.abspath(file) in self._files['PPS']:
                            # File is already there, remove it from the list
                            self._logger.debug(f'{file} already present.')
                            file_remove.append(file)
                    for file in file_remove:
                        filename.remove(file)
                    if len(filename) == 0:
                        # All files requested are present! No need to download anything
                        self._logger.debug('All files requested are already present. Not downloading again.')
                        call_download_data = False
                    else:
                        self._logger.debug('Requested files not found. Will download.')
            elif PPS_subset:
                # If PPS_subset then download files no matter what
                self._logger.info(f'Downloading subset of PPS data. Will silently overwrite any pre-existing files.')
            else:
                # If downloading ALL PPS files
                if overwrite:
                    # If obs_dir exists and overwrite = True then remove pps_dir.
                    self._logger.debug(f'Changing into obs_dir.')
                    os.chdir(self._obs_dir)
                    self._logger.info(f'Removing existing PPS directory {self._pps_dir} ...')
                    shutil.rmtree(self._pps_dir)
                else:
                    # Check for files
                    if len(self._files['PPS']) > 0:
                        self._logger.info(f'Data found in {self._pps_dir} not downloading again.')
                        call_download_data = False
        else:
            # PPS directory does not exist
            # First check if obs_dir exists, if not create it.
            if not os.path.exists(self._obs_dir):
                self._logger.debug(f'Creating obs_dir: {self._obs_dir}')
                os.mkdir(self._obs_dir)
            # Create pps_dir
            os.mkdir(self._pps_dir)
            self._logger.debug('Resetting: overwrite = False')

        # No matter what, reset overwrite = False 
        # Because 'overwrite' is passed into 'dl_data', and 'overwrite' in
        # 'dl_data' will remove the WHOLE obs_dir.
        overwrite = False

        if call_download_data:
            self._logger.info(f'Will download PPS data for Obs ID {self._obsid}.')
            # Function for downloading a single pps data set.
            dl_data(self._obsid,
                    self._data_dir,
                    level          = 'PPS',
                    overwrite      = overwrite,
                    repo           = self.repo,
                    logger         = self._logger,
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

        # Set work directory.
        work_dir_name = sas_cfg.get_setting('work_dir_name')
        self._work_dir = os.path.join(self._obs_dir,work_dir_name)
        if not os.path.exists(self._work_dir):
            self._logger.debug(f'Creating work_dir: {self._work_dir}')
            os.mkdir(self._work_dir)
            
        self._logger.info(f'Data directory: {self._data_dir}')
        self._logger.info(f'ObsID directory: {self._obs_dir}')
        self._files['PPS'] = self._get_list_of_PPS_files()
        self.parse_PPS_dir()

        return
    
    def download_ALL_data(self,
                          repo: str = None,
                          data_dir: str = None,
                          overwrite: bool = True,
                          proprietary: bool = False,
                          credentials_file: str = None,
                          encryption_key: str = None):
        """
        This function assumes you want to overwrite everything in the
        obs_dir. Makes no checks.

        This handles preliminary setup for downloadingboth ODF and PPS data 
        files, then calls download_data from sasutils.

        Parameters
        ----------
        repo : str, optional
            Which repository to use to download data. Accepted values are, 
            'ESA' (data from the XSA), 
            'NASA' (data from the HEASARC), 
            'AWS' (data from AWS s3 bucket (NASA)), 
            'Fornax' (if user is on Fornax),
            'SciServer' (if user is on SciServer).
            Defaults to 'ESA' ('XSA') or set by sas_config file.
        data_dir : str | Path, optional
            Path to directory where the data will be downloaded. Automatically 
            creates directory 'data_dir/obsid'. 
            Default from sas_config file, or current working directory.
        overwrite : bool, optional
            If True will force overwrite of data if obsid data already exists 
            in 'data_dir/obsid'. 
            Defaults to True.
        proprietary : bool, optional
            Flag for downloading proprietary data from the XSA at ESA. 
            Defaults to False.
        credentials_file : str, optional
            Path and filename of file containing XSA username and password. For 
            proprietary data only. (If not given then astroquery will ask user 
            for username and password.) 
            Defaults to None.
        encryption_key : str, optional
            Encryption key for proprietary data, a string 32 characters long. 
            -OR- path to file containing ONLY the encryption key. Note: ONLY 
            used for data from the HEASARC. 
            Defaults to None.
        
        Raises
        ------
        ValueError
            Download repository not recognized.
        """
        
        # Set data_dir
        self._set_data_dir(data_dir)
        
        # Set the obs_dir
        if not hasattr(self, 'obs_dir'):
            self._obs_dir = os.path.join(self._data_dir,self._obsid)
            self._logger.debug(f'Setting obs_dir: {self._obs_dir}')

        # Set odf_dir
        if not hasattr(self, 'odf_dir'):
            self._odf_dir = os.path.join(self._obs_dir,'ODF')
            self._logger.debug(f'Setting odf_dir: {self._odf_dir}')

        # Set pps_dir
        if not hasattr(self, 'pps_dir'):
            self._pps_dir = os.path.join(self._obs_dir,'PPS')
            self._logger.debug(f'Setting pps_dir: {self._pps_dir}')

        # Set repo from config file (default 'esa')
        self._logger.debug(f'Checking repo: {repo}')
        if repo is None:
            self.repo = sas_cfg.get_setting('repo')
            self._logger.debug(f'repo from config: {self.repo}')
        else:
            if repo.lower() not in repo_opts:
                self._logger.error('Download repository not recognized!')
                raise ValueError(f'Download repository {repo} not recognized. '\
                                 f'Allowed Options for repo are {repo_opts}.')
            else:
                self._logger.info(f'Will download data from {repo}.')
            self.repo = repo
            self._logger.debug(f'repo set to: {self.repo}')

        # Checks if obs_dir exists and removes it.

        if os.path.exists(self._obs_dir):
            self._logger.debug(f'Existing directory for {self._obsid} found ...')
            self._logger.info(f'Removing existing directory {self._obs_dir} ...')
            shutil.rmtree(self._obs_dir)

        self._logger.info(f'Will download ALL data for Obs ID {self._obsid}.')

        # Function for downloading a single obsid set.
        dl_data(self._obsid,
                self._data_dir,
                level          = 'ALL',
                overwrite      = overwrite,
                repo           = self.repo,
                logger         = self._logger,
                proprietary    = proprietary,
                encryption_key = encryption_key,
                credentials_file = credentials_file)
            
        self._logger.info(f'Data directory: {self._data_dir}')
        self._logger.info(f'ObsID directory: {self._obs_dir}')
        self._files['ODF'] = self._get_list_of_ODF_files()
        self._files['PPS'] = self._get_list_of_PPS_files()

        return
    
    def run_MyTask(self, 
                   taskname: str, 
                   inargs: dict | list | str = {}, 
                   **kwargs):
        """
        This acts as a wrapper around 'MyTask'. This provides a way of calling
        SAS tasks, while using the values set when the 'ObsID' object was 
        instantiated.
        
        Parameters
        ----------
        taskname : str
            Name of the SAS task to be run.
        inargs : dict | list | str
            Input arguments for the SAS task.
        logfilename : str, optional
            Name of log file where all output will be written. Overrides 
            default log file names. Defaults to either {obsid}.log or 
            {taskname}.log.
        tasklogdir : str, optional
            Directory for log files. Overrides default log directory. Defaults 
            to work_dir.
        output_to_terminal : bool, optional
            Whether to print log output to the terminal.
            Defaults to True.
        output_to_file : bool, optional
            Whether to write log output to a file.
            Defaults to False.
        """

        MT = MyTask(taskname, inargs, 
                    logfilename = kwargs.get('logfilename', self._logfilename), 
                    tasklogdir  = kwargs.get('tasklogdir', self._work_dir),
                    output_to_terminal = kwargs.get('output_to_terminal', self._output_to_terminal), 
                    output_to_file     = kwargs.get('output_to_file', self._output_to_file),
                    logger = kwargs.get('logger', None)).run()

    def quick_eplot(self,fits_event_list_file: str,
                    image_file: str = 'image.fits',
                    xcolumn: str = 'X',
                    ycolumn: str = 'Y',
                    ximagesize: str | int = '600',
                    yimagesize: str | int = '600',
                    expression: str = None,
                    vmin: float | int = 1.0,
                    vmax: float | int = 10.0,
                    **kwargs
                   ):
        """
        Quick plot function for EPIC event lists. Uses 'evselect' to create a 
        FITS image file. All standard inputs to 'MyTask' can be passed in as 
        optional arguments.

        Parameters
        ----------
        fits_event_list_file : str
            Filename of event list in FITS format
        image_file : str, optional
            Output filename of the image FITS file, by default 'image.fits'
        xcolumn : str, optional
            FITS file header name for X column data, by default 'X'
        ycolumn : str, optional
            FITS file header name for Y column data, by default 'Y'
        ximagesize : str | int, optional
            Output image X resolution in pixels, by default '600'
        yimagesize : str | int, optional
            Output image Y resolution in pixels, by default '600'
        expression : str, optional
            Filtering expression to be used for 'evselect', by default None
        vmin : float | int, optional
            Min value for color map, by default 1.0
        vmax : float | int, optional
            Max value for color map, by default 10.0
        xlabel : str, optional 
            X axis plot label, by default RA
        ylabel : str, optional 
            Y axis plot label, by default DEC
        title : str, optional 
            Plot title, by default {instrument} Image
        save_file : bool, optional
            Whether or not to save an image of the plot, by default False
        out_fname : str, optional
            Output filename of the plot image file, by default image.png

        Returns
        -------
        Axes
            Handle to the plot axis.
        """

        # Change to work directory.
        if os.getcwd() != self._work_dir:
            os.chdir(self._work_dir)
            self._logger.debug(f'Changing to work_dir: {self._work_dir}')
        
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

        with fits.open(image_file) as hdu:
            instrument = hdu[0].header['INSTRUME']
        
        ax = qip(image_file,
                 xlabel = kwargs.get('xlabel', 'RA'),
                 ylabel = kwargs.get('ylabel', 'Dec'),
                 title  = kwargs.get('title', f'{instrument} Image'),
                 vmin   = vmin,
                 vmax   = vmax,
                 grid   = kwargs.get('grid', True),
                 save_file = kwargs.get('save_file', False),
                 out_fname = kwargs.get('out_fname', 'image.png'))

        return ax
    
    def quick_implot(self,image_file: str,
                     xlabel: str = "RA",
                     ylabel: str = "Dec",
                     title: str = None,
                     vmin: float = 1.0,
                     vmax: float = 10.0,
                     grid: bool = True,
                     save_file: bool = False,
                     out_fname: str = "image.png"
                    ):
        """
        Quick plot function for a FITS image file.

        This function takes a FITS image file (not an event list) and produces a quick-look
        plot of the image data.

        Parameters
        ----------
        image_file : str
            Filename of the FITS image file.
        xlabel : str, optional
            Label for the X axis. Defaults to 'RA'.
        ylabel : str, optional
            Label for the Y axis. Defaults to 'Dec'.
        title : str, optional
            Title for the plot. Defaults to '{instrument} Image'.
        vmin : float, optional
            Minimum value for the color map. Defaults to 1.0.
        vmax : float, optional
            Maximum value for the color map. Defaults to 10.0.
        grid : bool, optional
            Whether to display a grid on the plot face. Defaults to True.
        save_file : bool, optional
            Whether to save the plot as a file. Defaults to False.
        out_fname : str, optional
            Output filename for the saved plot. Defaults to 'image.png'.

        Returns
        -------
        Axes
            Handle to the plot axis.

        """

        if title is None:
            with fits.open(image_file) as hdu:
                instrument = hdu[0].header['INSTRUME']
            title = f'{instrument} Image'

        ax = qip(image_file,
                 xlabel = xlabel,
                 ylabel = ylabel,
                 title  = title,
                 vmin   = vmin,
                 vmax   = vmax,
                 grid   = grid,
                 save_file = save_file,
                 out_fname = out_fname)

        return ax
    
    def quick_lcplot(self,fits_event_list_file: str,
                     light_curve_file: str = "light_curve.fits",
                     timebinsize: str = "100",
                     tstart: float | None = None,
                     tend: float | None = None,
                     title: str = None,
                     save_file: bool = False,
                     out_fname: str = "light_curve.png",
                     **kwargs
                    ):
        """
        Quick plot function to generate a light curve.

        This function produces a light curve from a FITS event list. All 
        standard inputs to 'MyTask' may be passed as optional arguments.

        Parameters
        ----------
        fits_event_list_file : str
            Input event list in FITS format.
        light_curve_file : str, optional
            Name of the output FITS file containing the light curve.
            Defaults to 'light_curve.fits'.
        timebinsize : str, optional
            Size of the time bins. Defaults to '100'.
        tstart : float, optional
            Start time for plotting. Defaults to None.
        tend : float, optional
            End time for plotting. Defaults to None.
        title : str, optional
            Title for the plot. Defaults to '{instrument} Light Curve'.
        save_file : bool, optional
            Whether to save the plot as a file. Default is False.
        out_fname : str, optional
            Name of the output plot file. Defaults to 'light_curve.png'

        Returns
        -------
        Axes
            Plot axis handle.

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

        if title is None:
            with fits.open(fits_event_list_file) as hdu:
                instrument = hdu[0].header['INSTRUME']
            title = f'{instrument} Light Curve'
        
        ax = qlcp(light_curve_file,
                  tstart = tstart,
                  tend   = tend,
                  title  = title,
                  save_file = save_file,
                  out_fname = out_fname)

        return ax
 
    def find_event_list_files(self, print_output: bool = True):
        """
        Checks the observation directory (obs_dir) for basic unfiltered 
        event list files created by 'epproc', 'emproc', 'epchain', 
        'emchain', and 'rgsproc'.

        Adds them to 'files' dictrionary with the keys:

            'PNevt_list'
            'M1evt_list'
            'M2evt_list'
            'R1evt_list'
            'R2evt_list'

        Parameters
        ----------
        print_output : bool, optional
            Print list of files found, by default True
        """
        
        self._logger.debug('Entering find_event_list_files')

        file_keys = ['PNevt_list','M1evt_list','M2evt_list','R1evt_list','R2evt_list']
        inst_list = ['EPN','EMOS1','EMOS2','RGS1','RGS2']
        for key in file_keys: self._files[key] = []

        event_lists = glob.glob(self._obs_dir+'/**/*Evts.ds', recursive=True) + \
                      glob.glob(self._obs_dir+'/**/*EVLI*', recursive=True)   + \
                      glob.glob(self._obs_dir+'/**/*EVENLI*', recursive=True)

        for filename in event_lists:
            file = os.path.abspath(filename)
            if re.search('(.*EPN.*Evts.ds$|.*PN.*EVLI.*.(FIT|FTZ)$)',file):
                self._files['PNevt_list'].append(file)
                self._logger.debug(f'EPN event list found: {file}')

            if re.search('(.*EMOS1.*Evts.ds$|.*M1.*EVLI.*.(FIT|FTZ)$)',file):
                self._files['M1evt_list'].append(file)
                self._logger.debug(f'EMOS1 event list found: {file}')

            if re.search('(.*EMOS2.*Evts.ds$|.*M2.*EVLI.*.(FIT|FTZ)$)',file):
                self._files['M2evt_list'].append(file)
                self._logger.debug(f'EMOS2 event list found: {file}')

            if re.search('.*R1.*EVENLI.*.(FIT|FTZ)$',filename):
                self._files['R1evt_list'].append(file)
                self._logger.debug(f'RGS1 event list found: {file}')

            if re.search('.*R2.*EVENLI.*.(FIT|FTZ)$',filename):
                self._files['R2evt_list'].append(file)
                self._logger.debug(f'RGS1 event list found: {file}')

        for i, key in enumerate(file_keys):
            if len(self._files[key]) > 0:
                self._files[key].sort()
                if print_output:
                    print(" > {0} {1} event list(s) found.\n".format(len(self._files[key]),inst_list[i]))
                    for x in self._files[key]:
                        print("    " + x + "\n")
            else:
                self._logger.debug(f'No event lists for {inst_list[i]} found.')

        
        self._logger.debug('Exiting find_event_list_files')
        return
    
    def find_rgs_spectra_files(self, print_output: bool = True):
        """
        Check for RGS spectra files created by rgsproc. Adds them to 
        'files' dictrionary with the keys:

            'R1SPEC'
            'R2SPEC'

        Parameters
        ----------
        print_output : bool, optional
            Print list of files found, by default True
        """
        self._logger.debug('Entering find_rgs_spectra_files')

        file_keys = ['R1spectra','R2spectra']
        inst_list = ['RGS1','RGS2']
        for key in file_keys: self._files[key] = []

        spectra = glob.glob(self._obs_dir+'/**/*RSPEC*', recursive=True)

        for filename in spectra:
            file = os.path.abspath(filename)
            if re.search('.*R1.*RSPEC.*.(FIT|FTZ)$',file):
                self._files['R1spectra'].append(file)
                self._logger.debug(f'RGS1 spectrum found: {file}')

            if re.search('.*R2.*RSPEC.*.(FIT|FTZ)$',file):
                self._files['R2spectra'].append(file)
                self._logger.debug(f'RGS2 spectrum found: {file}')

        for i, key in enumerate(file_keys):
            if len(self._files[key]) > 0:
                self._files[key].sort()
                if print_output:
                    print(" > {0} {1} spectra found.\n".format(len(self._files[key]),inst_list[i]))
                    for x in self._files[key]:
                        print("    " + x + "\n")
            else:
                self._logger.debug(f'No RGS spectra for {inst_list[i]} found.')

        self._logger.debug('Exiting find_rgs_spectra_files')
        return
    
    def get_cal_ind(self):
        """
        Checks for the calibration index file (ccf.cif). If it exists, 
        inserts file name in 'files' dict.

        Returns
        -------
        str
            Filename and path of the calibration index file.
        """
        self._logger.debug('Entering get_cal_ind')

        # Looking for calibration index file (ccf.cif or CALIND).
        self._files['sas_ccf'] = None
        self._logger.info(f'Searching for ccf.cif.')
        ccfcif_list = glob.glob(self._obs_dir+'/**/*ccf.cif', recursive=True)
        if len(ccfcif_list) > 0:
            self._logger.info(f'Found ccf.cif file in {ccfcif_list[0]}.')
            self._files['sas_ccf'] = ccfcif_list[0]
        else:
            self._logger.debug('No ccf.cif file found. Searching for CALIND file.')
            calind_list = glob.glob(self._obs_dir+'/**/*OBX*CALIND*.FTZ', recursive=True)
            if len(calind_list) > 0:
                self._logger.info(f'Found CALIND file in {calind_list[0]}.')
                self._files['sas_ccf'] = calind_list[0]
            else:
                self._logger.info('Neither ccf.cif nor CALIND files found!')

        self._logger.debug('Exiting get_cal_ind')
        return self._files['sas_ccf']
    
    def get_SUM_SAS(self,user_defined_file: str = None) -> bool:
        """
        Checks for the SUM.SAS file.

        Parameters
        ----------
        user_defined_file : str, optional
            Filename and path of the SUM.SAS file, checks if it is valid. 
            By default it will search the obs_dir for the SUM.SAS file.

        Returns
        -------
        bool
            Returns True if the SUM.SAS file is found.
        """
        self._logger.debug('Entering get_SUM_SAS')

        if user_defined_file is not None:
            self._logger.info(f'Checking file path given by user: {user_defined_file}')
            if os.path.exists(user_defined_file):
                self._files['sas_odf'] = user_defined_file
                self._logger.info('{0} is present'.format(self._files['sas_odf']))
            else:
                self._logger.error('User provided file does not exist!')
                self._logger.error(f'File provided by user: {user_defined_file}')
                return False
        else:
            self._logger.debug('Searching for *SUM.SAS file.')
            sum_sas_file = glob.glob(self._obs_dir+'/**/*SUM.SAS', recursive=True)
            if sum_sas_file:
                self._files['sas_odf'] = sum_sas_file[0]
                self._logger.info('{0} is present'.format(self._files['sas_odf']))
            else:
                self._logger.info('*SUM.SAS file not found.')
                return False
        
        # Check that the SUM.SAS file PATH keyword points to a real ODF directory
        with open(self._files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if not os.path.exists(path):
                        self._logger.error(f'Summary file PATH {path} does not exist. Rerun basic_setup with overwrite=True.')
                        print(f'\nSummary file PATH {path} does not exist. \n\n>>>>Rerun basic_setup with overwrite=True.')
                        return False
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if len(MANIFEST) == 0:
                        self._logger.error(f'Missing MANIFEST file in {path}. Missing ODF components? Rerun basic_setup with overwrite=True.')
                        print(f'\nMissing MANIFEST file in {path}. Missing ODF components? \n\n>>>>Rerun basic_setup with overwrite=True.')
                        return False

        self._logger.debug('Exiting get_SUM_SAS')
        return True
    
    def parse_PPS_dir(self):
        """
        Parses the PPS directory and sets standard filenames.
        """

        self.summary_file     = None
        self.attitude_file    = None
        self.calind_file      = None
        self.EPIC_event_lists = None
        self.EPIC_images      = None
        self.EPIC_source_list = None
        self.RGS_event_lists  = None
        self.RGS_spectra      = None

        self._files['PPS'] = self._get_list_of_PPS_files()

        # If no files in pps_dir, skip the rest
        if len(self._files['PPS']) == 0:
            self._logger.info('No PPS files found in PPS directory.')
            self._logger.debug(f'pps_dir: {self._pps_dir}')
            return

        # If the file is not present then the value is set to 'None'
        # Main Summary File
        summary_file = self.return_file_list_on_pattern(self._file_patterns['main_summary'])
        if summary_file:
            self.summary_file = summary_file[0]
            self._logger.info(f'Observation summary file found.')
            self._logger.debug(f'summary_file: {self.summary_file}')
            self.get_active_instruments()
        else:
            self._logger.info('No main summary file found in PPS directory.')

        # Attitude File
        attitude_file = self.return_PPS_filenames(self.OBS_PPS_products['ATTTSR_FIT'])
        if attitude_file:
            self.attitude_file = attitude_file[0]
            self._logger.info(f'Attitude file found.')
            self._logger.debug(f'attitude_file: {self.attitude_file}')
        else:
            self._logger.info('No attitude file found in PPS directory.')

        # Calibration Index File (CALIND)
        calind_file = self.return_PPS_filenames(self.OBS_PPS_products['CALIND_FIT'])
        if calind_file:
            self.calind_file = calind_file[0]
            self._logger.info(f'Calibration index (CALIND) file found.')
            self._logger.debug(f'calind_file: {self.calind_file}')
            # Assume the user wants to use the CALIND file even if a ccf.cif file exists.
            self._logger.debug('Setting calind_file to environment variable "SAS_CCF".')
            self._files['sas_ccf'] = self.calind_file
            os.environ['SAS_CCF'] = self.calind_file
        else:
            self._logger.info('No calibration index (CALIND) file found in PPS directory.')

        # EPIC Event Lists
        self.EPIC_event_lists = self.return_file_list_on_pattern(self._file_patterns['EPIC_event_lists'])
        if self.EPIC_event_lists:
            self.EPIC_event_lists.sort()
            self._logger.info(f'EPIC event lists found.')
            for file in self.EPIC_event_lists:
                self._logger.debug(f' >{file}')
        else:
            self._logger.info('No EPIC event lists found in PPS directory.')

        # EPIC Images
        self.EPIC_images = self.return_file_list_on_pattern(self._file_patterns['EPIC_images'])
        if self.EPIC_images:
            self.EPIC_images.sort()
            self._logger.info(f'EPIC FITS images found.')
            for file in self.EPIC_images:
                self._logger.debug(f' >{file}')
        else:
            self._logger.info('No EPIC images (FITS) found in PPS directory.')

        # EPIC Source List
        self.EPIC_source_list = self.return_PPS_filenames(self.EPIC_PPS_products['OBSMLI_FIT'])
        if self.EPIC_source_list:
            self.EPIC_source_list.sort()
            self._logger.info(f'EPIC source list found.')
            for file in self.EPIC_source_list:
                self._logger.debug(f' >{file}')
        else:
            self._logger.info('No EPIC source list found in PPS directory.')

        # RGS Event Lists
        self.RGS_event_lists = self.return_file_list_on_pattern(self._file_patterns['RGS_event_lists'])
        if self.RGS_event_lists:
            self.RGS_event_lists.sort()
            self._logger.info(f'RGS event lists found.')
            for file in self.RGS_event_lists:
                self._logger.debug(f' >{file}')
        else:
            self._logger.info('No RGS event lists found in PPS directory.')

        # RGS Spectra
        self.RGS_spectra = self.return_file_list_on_pattern(self._file_patterns['RGS_spectra'])
        if self.RGS_spectra:
            self.RGS_spectra.sort()
            self._logger.info(f'RGS spectra found.')
            for file in self.RGS_spectra:
                self._logger.debug(f' >{file}')
        else:
            self._logger.info('No RGS spectra (FITS) found in PPS directory.')

        self._logger.debug('Exiting parse_PPS_dir.')
        return

    def return_file_list_on_pattern(self, 
                                    pattern: str, 
                                    list_of_files: list | None = None):
        """
        Returns a list of PPS filenames based on the regular expression pattern 
        passed in.

        Parameters
        ----------
        pattern : str
            A string with a regular expression (re) pattern. The pattern must 
            use proper 're' operators for the 're' python package.
        list_of_files : list | None, optional
            A list of filenames to search, by default will use 
            self._files['PPS'].

        Returns
        -------
        list
            List of files matching the pattern passed in.
        """

        self._logger.debug(f'Searching PPS files for pattern: {pattern}')

        if list_of_files is None:
            list_of_files = self._get_list_of_PPS_files()

        files = []
        for filename in list_of_files:
            if re.search(pattern,filename):
                files.append(filename)

        # Return 'None' if no files of pattern were found.
        self._logger.debug(f'Number of files found: {len(files)}')
        
        return files
    
    def run_cifbuild(self):
        """
        Runs 'cifbuild' for this Obs ID. Must have --at least one-- PPS FITS 
        file in the PPS directory to get the observation date from the header.
        """

        self._logger.debug('Entering run_cifbuild.')

        obs_date = None

        # Finds a FITS file and looks for 'DATE-OBS' in the header
        for file in self._files['PPS']:
            _, ext = os.path.splitext(file)
            if ext == '.FTZ' or ext == '.FIT':
                header = fits.getheader(file)
                if 'DATE-OBS' in header:
                    obs_date = header['DATE-OBS']
                    self._logger.debug(f'Obs Date found: {obs_date}')
                    break
        
        # Failsafe. Downloads Obs ID summary file.
        if obs_date is None:
            self._logger.debug('Obs Date not found. Looking in Obs ID summary file.')
            summary_file = self.get_main_summary_filename()
            with open(summary_file, "r", encoding="utf-8") as file:
                html_content = file.readlines()
            for line in html_content:
                if re.search('<tr><td class="string">Start time</td><td class="string">:</td><td class="string">.*</td></tr>',line):
                    obs_date = re.findall('<tr><td class="string">Start time</td><td class="string">:</td><td class="string">(.*)</td></tr>',line)
                    obs_date = obs_date[0]
                    self._logger.debug(f'Obs Date found: {obs_date}')

        self._logger.debug('Running cifbuild.')
        MyTask('cifbuild',{'observationdate' : obs_date}).run()

        _ = self.get_cal_ind()

        os.environ['SAS_CCF'] = self._files['sas_ccf']
        self._logger.info('SAS_CCF = {0}'.format(self._files['sas_ccf']))

    def get_main_summary_filename(self):
        """
        Returns the filename of the main summary (HTML) file. Checks if it has 
        been downloaded, and if not it will download the file.
        """

        summary_filename = self.return_file_list_on_pattern(self._file_patterns['main_summary'])

        if not summary_filename:
            download_filename = f'P{self._obsid}OBX000SUMMAR0000.HTM'
            self.download_PPS_data(filename=download_filename)

        summary_filename = self.return_file_list_on_pattern(self._file_patterns['main_summary'])[0]

        return summary_filename
    
    def return_PPS_filenames(self,
                             pattern_dict: dict, 
                             list_of_files: list | None = None):
        """
        Returns a list of PPS filenames based on a filename pattern dictionary.

        The dictionary passed in must have the keys:

            'Source' : Data source identifier (DD)

            'Product': Product filename field (TTTTTT)

            'Format' : File format or extension (FFF)

        This follows the general format for PPS file names:

            POOOOOOOOOODDUEEETTTTTTSXXX.FFF

        Parameters
        ----------
        pattern_dict : dict
            PPS product type pattern dictionary.
        list_of_files : list | None, optional
            List of files to search, by default will use self._files['PPS'].

        Returns
        -------
        list
            List of PPS files matching the product type pattern dictionary.
        """

        source  = pattern_dict['Source']
        product = pattern_dict['Product']
        format  = pattern_dict['Format']

        pattern = f'.*{source}.*{product}.*{format}'

        files = self.return_file_list_on_pattern(pattern, list_of_files=list_of_files)

        return files

    def get_all_PPS_filenames(self):
        """
        This returns a list of all possible PPS filenames, regardless of
        whether or not the PPS files have already been downloaded.

        Returns
        -------
        list
            List of all PPS files for the Obs ID.
        """

        cwd = os.getcwd()

        self._logger.debug(f'CWD: {cwd}')

        if not hasattr(self, 'obs_dir'):
            self._obs_dir = os.path.join(self._data_dir,self._obsid)

        if not hasattr(self, 'pps_dir'):
            self._pps_dir = os.path.join(self._obs_dir,'PPS')

        if not os.path.exists(self._obs_dir):
            self._logger.info('obs_dir does not exist!')
            self._logger.info(f'Making obs_dir: {self._obs_dir}')
            os.mkdir(self._obs_dir)

        if not os.path.exists(self._pps_dir):
            self._logger.info('pps_dir does not exist!')
            self._logger.info(f'Making pps_dir: {self._pps_dir}')
            os.mkdir(self._pps_dir)

        self._logger.debug(f'Changing into the pps_dir: {self._pps_dir}')
        os.chdir(self._pps_dir)

        reqs = requests.get(f'https://heasarc.gsfc.nasa.gov/FTP/xmm/data/rev0/{self._obsid}/PPS/')
        soup = BeautifulSoup(reqs.text, 'html.parser')

        self.ALL_PPS_FILES = []
        for link in soup.find_all('a'):
            file = link.get('href')
            if file[0] == 'P':
                self.ALL_PPS_FILES.append(file)

        self._logger.debug(f'Changing back to original dir: {cwd}')
        os.chdir(cwd)

        self._logger.debug(f'{len(self.ALL_PPS_FILES)} files found.')

        return self.ALL_PPS_FILES
    
    def clear_obs_dir(self):
        """
        Function to remove all files and subdirectories from the obs_dir.
        """
        if os.path.exists(self._obs_dir):
            os.chdir(self._data_dir)
            self._logger.info(f'Removing existing directory {self._obs_dir} ...')
            shutil.rmtree(self._obs_dir)

        return

    def clear_work_dir(self):
        """
        Function to remove all files and subdirectories from the work_dir.
        """
        if os.path.exists(self._work_dir):
            self._logger.info(f'Removing existing directory {self._work_dir} ...')
            shutil.rmtree(self._work_dir)
            os.mkdir(self._work_dir)

        return

    def make_work_dir(self):
        """
        Function to make a work directory in the obs_dir.

        Will also make the obs_dir if it doesn't exist.
        """

        if not os.path.exists(self._obs_dir):
            self._logger.info(f'Creating {self._obs_dir} ...')
            os.mkdir(self._obs_dir)

        if not os.path.exists(self._work_dir):
            self._logger.info(f'Creating {self._work_dir} ...')
            os.mkdir(self._work_dir)
        
        return

    def resolve_obs_dir(self):
        """
        Finds files in the obs_dir and stores paths and file names in 
        self._files.
        """

        self._files['ODF'] = self._get_list_of_ODF_files()
        self._files['PPS'] = self._get_list_of_PPS_files()
        self._files['work'] = self._get_list_of_work_files()
        _ = self.get_cal_ind()
        _ = self.get_SUM_SAS()
        self.find_event_list_files(print_output = self._output_to_terminal)
        self.find_rgs_spectra_files(print_output = self._output_to_terminal)

    def get_obs_info(self):
        """
        Retrieves information on the Obs ID using the HEASARC TAP service.

        Stores the information as a dictionary named 'obs_info'.

        Also returns the dictionary.

        Returns
        -------
        dict
            Dictionary containing the observation information from the 
            HEASARC TAP service.
        """

        tab = self.return_tap_table()

        self.obs_info = {}

        for col in tab.columns:
            self.obs_info[col] = tab[0][col]

        return self.obs_info

    def return_tap_table(self):
        """
        Retrieves information on the Obs ID using the HEASARC TAP service.

        Returns the data as an Astropy table.

        Returns
        -------
        Table
            Astropy table containing the observation information from the 
            HEASARC TAP service.
        """

        query = """SELECT * FROM xmmmaster WHERE obsid='{0}'""".format(self._obsid)
        tab = Heasarc.query_tap(query).to_table()

        return tab

    def get_active_instruments(self):
        """
        Checks odf summary file for which instruments were active for that odf.

        Assumes that 'sas_odf' already exists and contains the correct path.

        Also assumes file name and path are stored in self._files['sas_odf'].
        """

        # Get information about the instruments.
        self.active_instruments = {}
        # If ODF summary file is present
        if 'sas_odf' in self._files.keys():
            if self._files['sas_odf'] is not None:
                self._logger.debug('Searching *SUM.SAS file for active instruments.')
                summary_file = self._files['sas_odf']
                with open(self._files['sas_odf']) as inf:
                    lines = inf.readlines()
                    for i,line in enumerate(lines):
                        if '// Instrument Record' in line:
                            active = lines[i+4][0]
                            if active == 'N': active = False
                            if active == 'Y': active = True
                            self.active_instruments[lines[i+3][0:2]] = active
        else: # Check PPS Summary File
            self._logger.debug('Searching PPS Summary file for active instruments.')
            summary_file = None
            for filename in self._files['PPS']:
                if re.search('.*OBX.*SUMMAR.*.HTM$',filename):
                    summary_file = filename
            if summary_file is not None:
                with open(summary_file, "r", encoding="utf-8") as file:
                    html_content = file.readlines()
                for line in html_content:
                    if re.search('<th class="string">Instrument</th><th class="flag">Active</th>',line):
                        inst_tuple = re.findall('>(EMOS1|EMOS2|EPN|RGS1|RGS2|OM)</a></td><td class="flag">(Y|N)</td>',line)
                        break
                for tup in inst_tuple:
                    if tup[0] == 'EMOS1': inst = 'M1'
                    if tup[0] == 'EMOS2': inst = 'M2'
                    if tup[0] == 'EPN'  : inst = 'PN'
                    if tup[0] == 'RGS1' : inst = 'R1'
                    if tup[0] == 'RGS2' : inst = 'R2'
                    if tup[0] == 'OM'   : inst = 'OM'
                    if tup[1] == 'N': active = False
                    if tup[1] == 'Y': active = True
                    self.active_instruments[inst] = active

        # Basic sanity checks
        bad_sum_file = False
        inst_list = list(self.active_instruments.keys())
        true_list = ['M1', 'M2', 'R1', 'R2', 'PN', 'OM']
        diff = set(inst_list) ^ set(true_list)
        if len(diff) > 0: bad_sum_file = True
        if bad_sum_file:
            self._logger.error('Something is wrong with the summary file: {0}'.format(summary_file))

        return
    
    def write_bash_source_script(self, filename: str = 'set_env_variables.sh'):
        """
        For diagnostic purposes. Will write a bash file that can be
        sourced from the command line to set key environment variables 
        for this data set.

        SAS HAS TO BE INITIALIZED FROM THE COMMAND LINE FIRST.

        The bash file will just set 'SAS_ODF' and 'SAS_CCF' for this 
        Obs ID. All SAS tasks can then be run from the command line.

        How to use:

        In a terminal go to the Obs ID work directory and run: 

            > source set_env_variables.sh

        or

            > . set_env_variables.sh

        Parameters
        ----------
        filename : str, optional
            Output filename of the shell script. Defaults to 
            'set_env_variables.sh' in the work_dir.
        """

        os.chdir(self._work_dir)

        SAS_ODF = os.environ.get('SAS_ODF')
        SAS_CCF = os.environ.get('SAS_CCF')

        file_contents = [f'#!/bin/bash\n',
                         f'export SAS_ODF={SAS_ODF}\n',
                         f'export SAS_CCF={SAS_CCF}\n']

        with open(filename, 'w') as file:
            file.writelines(file_contents)

    def _run_analysis(self,
                      task: str, 
                      inargs: dict | list | str, 
                      rerun: bool = False,
                      logFile: str = None):
        """
        A wrapper for the wrapper. Yes. I know.

        This function is not intended to be used by the end user, but is
        only called by 'basic_setup'.

        This will check if output files are present for the selected SAS task.
        If they are, will not rerun that SAS task unless "rerun=True".

        Lists of output files are stored in the dictionary self._files{}.

        SAS Tasks that it currently works for:
            --epproc
            --epchain (Warning epchain fails in SAS v. 21)
            --emproc
            --emchain (Warning emchain fails in SAS v. 21)
            --rgsproc

        More will be added as needed.

        Parameters
        ----------
        task : str
            Name of SAS task.
        inargs : dict | list | str
            Input arguments for the SAS task to run.
        rerun : bool
            Whether to for the SAS task to rerun. Defaults to False.
        logFile : str
            Custom log file name. Defaults to '{sas task}.log'.

        Raises
        ------
        IsADirectoryError
            Obs ID directory not found.
        """

        # Make sure we are in the right place!
        if os.path.isdir(self._work_dir):
            os.chdir(self._work_dir)
            self._logger.debug('Changing into work_dir')
        else:
            print(f'The directory for the observation ID ({self._obsid}) does '\
                  f'not seem to exist!\n    {self._obs_dir}')
            print('Has \'calibrate_odf\' been run?')
            raise IsADirectoryError(f'Obs ID directory for '\
                                    f'obsid = {self._obsid} not found!')
        
        self._logger.debug('Finding event list files')
        self.find_event_list_files(print_output=False)
        self._logger.debug('Finding speactra files')
        self.find_rgs_spectra_files(print_output=False)

        # Check if corresponding instrument was active
        out_message = {}
        self._logger.debug('Check if corresponding instrument was active.')
        match task:
            case 'epproc' | 'epchain':
                active = self.active_instruments['PN']
                inst = 'EPIC-pn'
                out_message['PNevt_list'] = inst
            case 'emproc' | 'emchain':
                active = self.active_instruments['M1'] or self.active_instruments['M2']
                inst = 'EPIC-MOS'
                out_message['M1evt_list'] = inst+'1'
                out_message['M2evt_list'] = inst+'2'
            case 'rgsproc':
                active = self.active_instruments['R1'] or self.active_instruments['R2']
                inst  = 'RGS'
                out_message['R1evt_list'] = inst+'1'
                out_message['R2evt_list'] = inst+'2'

        run_ep  = False
        run_em  = False
        run_rgs = False

        if not active:
            # Instrument not active, cannot run
            self._logger.info(f'{inst} was not active for this ObsID. '\
            f'Not running {task}.')
            if self._output_to_terminal:
                print(f' > {inst} was not active for this ObsID. '\
                      f'Not running {task}.')
        elif rerun:
            self._logger.debug(f'rerun set as True. Running {task}.')
            # rerun, don't bother checking for event lists
            match task:
                case 'epproc' | 'epchain':
                    if active: run_ep  = True
                case 'emproc' | 'emchain':
                    if active: run_em  = True
                case 'rgsproc':
                    if active: run_rgs = True
        else:
            # If not rerun, and active instrument, then check for event lists
            match task:
                case 'epproc':
                    # Check if 'epproc' has been run.
                    # Check for event lists
                    found = False
                    for filename in self._files['PNevt_list']:
                        if re.search('.*EPN.*Evts.ds$',filename): found = True

                    # If no event lists
                    if not found: run_ep = True

                case 'epchain':
                    # Check if 'epchain' has been run.
                    # Check for event lists
                    found = False
                    for filename in self._files['PNevt_list']:
                        if re.search('.*PN.*EVLI.*FIT$',filename): found = True

                    # If no event lists
                    if not found: run_ep = True

                case 'emproc':
                    # Check if 'emproc' has been run.
                    # Check for event lists
                    found = False
                    for filename in self._files['M1evt_list']:
                        if re.search('.*EMOS1.*Evts.ds$',filename): found = True
                        
                    # If no event lists
                    if not found: run_em = True
                    
                    # Check for event lists
                    found = False
                    for filename in self._files['M2evt_list']:
                        if re.search('.*EMOS2.*Evts.ds$',filename): found = True
                    
                    # If no event lists
                    if not found: run_em = True

                case 'emchain':
                    # Check if 'emchain' has been run.
                    # Check for event lists
                    found = False
                    for filename in self._files['M1evt_list']:
                        if re.search('.*M1.*EVLI.*FIT$',filename): found = True

                    # If no event lists
                    if not found: run_em = True

                    # Check for event lists
                    found = False
                    for filename in self._files['M2evt_list']:
                        if re.search('.*M2.*EVLI.*FIT$',filename): found = True

                    # If no event lists
                    if not found: run_em = True

                case 'rgsproc':
                    # Check if 'rgsproc' has been run.
                    # Check for event lists
                    found = False
                    for filename in self._files['R1evt_list']:
                        if re.search('.*R1.*EVENLI.*FIT$',filename): found = True

                    # If no event lists
                    if not found: run_rgs = True
                    
                    # Check for event lists
                    found = False
                    for filename in self._files['R2evt_list']:
                        if re.search('.*R2.*EVENLI.*FIT$',filename): found = True

                    # If no event lists
                    if not found: run_rgs = True
        
        if run_ep or run_em or run_rgs:
            self._logger.info(f'SAS command to be executed: {task}, with arguments: {inargs}')
            if self._output_to_terminal:
                print(f"   SAS command to be executed: {task}, with arguments; {inargs}")
                print(f"Running {task} ..... \n")
            MyTask(task,inargs,
                   logfilename = logFile, 
                   tasklogdir  = self._work_dir,
                   output_to_terminal = self._output_to_terminal, 
                   output_to_file     = self._output_to_file).run() # <<<<< Execute SAS task
        else:
            self._logger.debug(f'Not running {task} again.')
            for k,v in out_message.items():
                num_evtli = len(self._files[k])
                if num_evtli > 0:
                    out_note = f" > {num_evtli} {v} event list(s) found."
                    self._logger.info(out_note)
                    for x in self._files[k]:
                        self._logger.debug(f'{x}')
                    if self._output_to_terminal:
                        print(out_note)
                        for x in self._files[k]:
                            print(f"  {x}")

        # Check if run sucsessfully
        self.find_event_list_files(print_output=False)
        if (len(self._files['PNevt_list']) == 0) and run_ep:
            print("Something has gone wrong. I cant find any event list files after running epproc. \n")
        if (len(self._files['M1evt_list']) == 0 and len(self._files['M2evt_list']) == 0 and run_em):
            print("Something has gone wrong. I cant find any event list files after running emproc. \n")
        if (len(self._files['R1evt_list']) == 0 and len(self._files['R2evt_list']) == 0 and run_rgs):
            print("Something has gone wrong. I cant find any event list files after running rgsproc. \n")
        self.find_rgs_spectra_files(print_output=False)
    
    def _run_calibration(self,
                         cifbuild_opts: dict | list | str,
                         odfingest_opts: dict | list | str):
        """
        --Not intended to be used by the end user. Internal use only.--

        Making this a separate function since it can be called from different 
        inside the function calibrate_odf. Prevents duplication of code.

        Parameters
        ----------
        cifbuild_opts : dict | list | str
            cifbuild input parameters.
        odfingest_opts : dict | list | str
            odfingest input parameters.

        Raises
        ------
        FileNotFoundError
            MANIFEST File not present with ODF. Incomplete number of ODF files.
        FileNotFoundError
            ccf.cif file not created.
        FileNotFoundError
            SUM.SAS file not created.
        Exception
            SAS summary file PATH mismatches odf_dir.
        """
        
        # Run cifbuild and odfingest on the new data.
        os.chdir(self._odf_dir)
        self._logger.info(f'Changed directory to {self._odf_dir}')

        # Checks that the MANIFEST file is there
        exists, MANIFEST = self._check_for_manifest(return_file_name=True)
        if exists:
            self._logger.info(f'File {MANIFEST} exists')
        else:
            self._logger.critical('MANIFEST File not present. '\
                                 'Incomplete number of ODF files.')
            raise FileNotFoundError('MANIFEST File not present with ODF. '\
                                    'Incomplete number of ODF files.')

        # Now we start preparing the SAS_ODF and SAS_CCF
        self._logger.info(f'Setting SAS_ODF = {self._odf_dir}')
        if self._output_to_terminal:
            print(f'Setting SAS_ODF = {self._odf_dir}')
        os.environ['SAS_ODF'] = self._odf_dir

        # Change to working directory
        if not os.path.exists(self._work_dir): os.mkdir(self._work_dir)
        os.chdir(self._work_dir)

        # Run cifbuild
        self._logger.info(f'Running cifbuild with inputs: {cifbuild_opts} ...')
        if self._output_to_terminal:
            print(f'Running cifbuild with inputs: {cifbuild_opts} ...')
        MyTask('cifbuild',cifbuild_opts,
               logfilename = self._logfilename, 
               tasklogdir  = self._work_dir,
               output_to_terminal = self._output_to_terminal, 
               output_to_file     = self._output_to_file).run()
        
        # Check whether ccf.cif is produced or not
        ccfcif = glob.glob('ccf.cif')
        if ccfcif and os.path.exists(ccfcif[0]):
            self._logger.info('CIF file {0} created'.format(ccfcif[0]))
        else:
            self._logger.critical('The ccf.cif was not created.')
            raise FileNotFoundError('ccf.cif file not created.')
        
        # Sets SAS_CCF variable
        fullccfcif = os.path.join(self._work_dir, 'ccf.cif')
        self._logger.info(f'Setting SAS_CCF = {fullccfcif}')
        if self._output_to_terminal:
            print(f'Setting SAS_CCF = {fullccfcif}')
        os.environ['SAS_CCF'] = fullccfcif
        self._files['sas_ccf'] = fullccfcif

        # Now run odfingest
        self._logger.info(f'Running odfingest with inputs: {odfingest_opts} ...')
        if self._output_to_terminal:
            print(f'Running odfingest with inputs: {odfingest_opts} ...')
        MyTask('odfingest',odfingest_opts,
               logfilename = self._logfilename, 
               tasklogdir  = self._work_dir,
               output_to_terminal = self._output_to_terminal, 
               output_to_file     = self._output_to_file).run()

        # Check whether the SUM.SAS has been produced or not
        sumsas = glob.glob('*SUM.SAS')
        if sumsas and os.path.exists(sumsas[0]):
            self._logger.info('SAS summary file {0} created'.format(sumsas[0]))
        else:
            self._logger.critical('The SUM.SAS was not created.')
            raise FileNotFoundError('SUM.SAS file not created.')
        
        # Set the SAS_ODF to the SUM.SAS file
        fullsumsas = os.path.join(self._work_dir, sumsas[0])
        os.environ['SAS_ODF'] = fullsumsas
        self._logger.info(f'Setting SAS_ODF = {fullsumsas}')
        if self._output_to_terminal:
            print(f'Setting SAS_ODF = {fullsumsas}')
        self._files['sas_odf'] = fullsumsas
        
        # Check that the SUM.SAS file has the right PATH keyword
        with open(self._files['sas_odf']) as inf:
            lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if os.path.abspath(path) != os.path.abspath(self._odf_dir):
                        self._logger.error(f'SAS summary file PATH {path} '\
                                          f'mismatches {self._odf_dir}')
                        raise Exception(f'SAS summary file PATH {path} '\
                                        f'mismatches {self._odf_dir}')
                    else:
                        self._logger.info(f'Summary file PATH keyword matches '\
                                         f'{self._odf_dir}')

        self.get_active_instruments()

        if self._output_to_terminal:
            print(f'''\n\n
            SAS_CCF = {self._files['sas_ccf']}
            SAS_ODF = {self._files['sas_odf']}
            \n''')

        return

    def _reset_logger(self,
                       logbasename: str = None,
                       logfilename: str = None,
                       tasklogdir: str  = None,
                       output_to_terminal: bool = True,
                       output_to_file: bool     = False):
        """
        Resets the logger using new inputs.

        Parameters
        ----------
        logbasename : str, optional
            Basename of the log file to generate the log filename.
        logfilename : str, optional
            Name of log file where all output will be written. Overrides 
            default log file names. Defaults to either {obsid}.log or 
            {taskname}.log.
        tasklogdir : str, optional
            Directory for log files. Overrides default log directory. Defaults 
            to work_dir.
        output_to_terminal : bool, optional
            Whether to print log output to the terminal.
            Defaults to True.
        output_to_file : bool, optional
            Whether to write log output to a file.
            Defaults to False.
        """
        if logbasename is None:
            logbasename = 'ObsID_' + self._obsid

        self._logger = get_logger(logbasename,
                                 toterminal  = output_to_terminal,
                                 tofile      = output_to_file,
                                 logfilename = logfilename,
                                 tasklogdir  = tasklogdir)
    
    def _set_data_dir(self, data_dir):
        """
        Sets the data_dir using the following hierarchy:
            1. self._data_dir: data_dir given by user on object creation
            2. data_dir passed into this function
            3. data_dir from config file
            4. cwd

        If data_dir does not exist then it will be created.

        Parameters
        ----------
        data_dir : str
            Sets the data directory.
        """
        self._logger.debug('Inside _set_data_dir')
        # Where are we?
        startdir = str(Path.cwd())

        # Brief check to see if data_dir was 
        # given on ObsID creation.
        self._logger.debug('Check if self._data_dir is set already')
        if self._data_dir != None:
            data_dir = self._data_dir

        # Start checking data_dir
        self._logger.debug('Check if data_dir is "None"')
        if data_dir is None:
            self._logger.debug('Check if data_dir is set in config file')
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'
            if os.path.exists(data_dir):
                self._data_dir = data_dir
                self._logger.info(f'Using data_dir from config file: {self._data_dir}')
            else:
                self._data_dir = startdir
                self._logger.info(f'Using current directory for data_dir: {self._data_dir}')
        else:
            self._logger.info(f'Setting data_dir: {data_dir}')
            self._data_dir = data_dir

        # If data_dir was not given as an absolute path, it is interpreted
        # as a subdirectory of startdir.
        self._logger.debug('Check if data_dir is an absolute path, or if it is a subdirectory of startdir')
        if self._data_dir[0] != '/':
            self._data_dir = os.path.join(startdir, self._data_dir)
        elif self._data_dir[:2] == './':
            self._data_dir = os.path.join(startdir, self._data_dir[2:])

        # Check if data_dir exists. If not then create it.
        self._logger.debug('Check if data_dir exists, if not, create it')
        if not os.path.isdir(self._data_dir):
            self._logger.info(f'{self._data_dir} does not exist. Creating it!')
            os.mkdir(self._data_dir)
            self._logger.info(f'{self._data_dir} has been created!')

        self._logger.info(f'Data directory = {self._data_dir}')
        self._logger.debug('Exiting _set_data_dir')
        return
    
    def _check_for_ccf_cif(self):
        """
        Checks if the ccf.cif file exists.

        Returns
        -------
        bool
            Whether or not the ccf.cif file was found.
        """
        exists = False

        # Check if ccf.cif file exists.
        for path, directories, files in os.walk(self._obs_dir):
            for file in files:
                if 'ccf.cif' in file:
                    if os.path.exists(os.path.join(path,file)):
                        exists = True
        return exists
    
    def _check_for_SUM_SAS(self):
        """
        Checks if the the SUM.SAS file exists.

        Returns
        -------
        bool
            Whether or not the SUM.SAS file was found.
        """
        exists = False

        # Looking for *SUM.SAS file.
        for path, directories, files in os.walk(self._obs_dir):
            for file in files:
                if 'SUM.SAS' in file:
                    if os.path.exists(os.path.join(path,file)):
                        exists = True
        return exists
    
    def _check_for_manifest(self,return_file_name: bool = False):
        """
        Checks if manifest file exists.

        Parameters
        ----------
        return_file_name : bool, optional
            Whether or not to return the name of the MANIFEST file.
        
        Returns
        -------
        str
            Name of the MANIFEST file.
        """

        exists = False

        MANIFEST = glob.glob(self._obs_dir+'/**/*MANIFEST*', recursive=True)
        if len(MANIFEST) > 0:
            if os.path.exists(MANIFEST[0]): 
                exists = True
                MANIFEST = MANIFEST[0]
        
        if return_file_name:
            return exists, MANIFEST
        else:
            return exists
    
    def _get_list_of_ODF_files(self):
        """
        Returns list of all files in the the ODF directory.

        Returns
        -------
        list
            List of all files in the odf_dir.
        """
        file_list = []
        if os.path.exists(self._odf_dir):
            file_list = glob.glob(self._odf_dir+'/*')

        return file_list
    
    def _get_list_of_PPS_files(self):
        """
        Returns list of all files in the the PPS directory.

        Returns
        -------
        list
            List of all files in the pps_dir.
        """
        file_list = []
        if os.path.exists(self._pps_dir):
            file_list = glob.glob(self._pps_dir+'/*')
        
        # Remove 'index.html' from the list if present.
        try:
            file_list.remove(os.path.join(self._pps_dir,'index.html'))
        except ValueError:
            pass

        return file_list
    
    def _get_list_of_work_files(self):
        """
        Returns list of all files in the the work directory.

        Returns
        -------
        list
            List of all files in the work_dir.
        """
        file_list = []
        if os.path.exists(self._work_dir):
            file_list = glob.glob(self._work_dir+'/*')

        return file_list
    
    def _inisas(self,sas_dir,sas_ccfpath,verbosity=4,suppress_warning=1):
        """
        --Not intended to be used by the end user. Internal use only.--

        Simple wrapper for 'initializesas' defined in init_sas.py.

        SAS initialization should happen automatically.

        Parameters
        ----------
        sas_dir : str
            Path to SAS directory.
        sas_ccfpath : str
            Path to SAS calibration directory.
        verbosity : int
            SAS verbosity value. Defaults to 4.
        suppress_warning : int
            SAS suppress warning value. Defaults to 1.
        """
        self.sas_dir = sas_dir
        self.sas_ccfpath = sas_ccfpath
        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        return_info = initializesas(self.sas_dir, self.sas_ccfpath, 
                                    verbosity = self.verbosity, 
                                    suppress_warning = self.suppress_warning)
        print(return_info)
        return

    def _sas_talk(self,verbosity=4,suppress_warning=1):
        """
        Simple function to set general SAS veriables 'verbosity' and 
        'suppress_warning'.

        Parameters
        ----------
        verbosity : int
            SAS verbosity value. Defaults to 4.
        suppress_warning : int
            SAS suppress warning value. Defaults to 1.
        """

        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        os.environ['SAS_VERBOSITY'] = '{}'.format(self.verbosity)
        os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(self.suppress_warning)
    
    def _remove_attr(self, attr_name):
        """
        Removes an attribute from 'self'.

        Parameters
        ----------
        attr_name : str
            Name of attribute to remove from 'self'.
        """
        if hasattr(self, attr_name): delattr(self, attr_name)

class PPSFiles(ObsID):
    """
    The PPSFiles class has been depricated. All functionality has been
    incorporated into the ObsID class.
    """
    def __init__(self, obsid, 
                 data_dir    = None,
                 logfilename = None,
                 tasklogdir  = None,
                 output_to_terminal = True,
                 output_to_file     = False):
        super().__init__(obsid, 
                         data_dir    = data_dir,
                         logfilename = logfilename,
                         tasklogdir  = tasklogdir,
                         output_to_terminal = output_to_terminal,
                         output_to_file     = output_to_file)
        warn("""
             The PPSFiles class has been depricated. All functionality has been
             incorporated into the ObsID class.
             """)