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

In this file there are three classes:

Parent Class:
    - ObsID: Class with methods for dealing with a single Obs ID.

Children:
    - ODF: Class dedicated for dealing with only ODF files.
    - PPS: Class dedicated for dealing with only PPS files.

"""

# Standard library imports
import os, sys, shutil, glob, numbers
from pathlib import Path

# Third party imports

# Local application imports
from ..configutils import sas_cfg
from ..init_sas import initializesas
from ..sasutils import download_data as dl_data
from pysas.logger import get_logger
from pysas.sastask import MyTask

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
        - logger     : Logger object created by get_logger 
                       function.
    """
    def __init__(self, obsid, data_dir = None,
                 logfilename = None,
                 tasklogdir  = None,
                 output_to_terminal = True,
                 output_to_file     = False,
                 logger = None):        
        if isinstance(obsid, numbers.Number):
            obsid = str(obsid)
        self.obsid       = obsid
        self.data_dir    = data_dir
        # File names are kept at the level of the ObsID object
        self.files       = {}
        # Default log file name
        if logfilename is None:
            logfilename = 'ObsID_' + self.obsid + '.log'
        self.logfilename = logfilename
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file
        # __set_obsid uses a temporary logger, that will only
        # output to the terminal.
        self.logger = get_logger('ObsID_' + self.obsid, 
                                 toterminal  = self.output_to_terminal,
                                 tofile      = False)
        # Sets info on the data_dir, obs_dir, etc.
        self.__set_obsid()
        # Remove temporary logger
        self.__remove_attr('logger')
        
        # Set the directory for log files.
        # Log directory will be (in this order):
        # 1. Directory passed in by the user
        # 2. obs_dir
        # 3. data_dir
        # 4. cwd
        if tasklogdir is None:
            if os.path.exists(self.obs_dir):
                self.tasklogdir = self.obs_dir
            elif os.path.exists(self.data_dir):
                self.tasklogdir = self.data_dir
            else:
                # By default get_logger will use cwd
                # if tasklogdir = None
                self.tasklogdir = tasklogdir
        else:
            # User defined directory
            self.tasklogdir = tasklogdir
        
        # Create logger
        if logger is None:
            self.logger = get_logger('ObsID_' + self.obsid, 
                                    toterminal  = self.output_to_terminal,
                                    tofile      = self.output_to_file, 
                                    logfilename = self.logfilename,
                                    tasklogdir  = self.tasklogdir)
        
        # Create ODF and PPS objects, which are classes that are
        # children of the ObsID class.
        if not hasattr(self, 'ODF'):
            self.__create_ODF_object()
        if not hasattr(self, 'PPS'):
            self.__create_PPS_object()

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

        # Where are we?
        startdir = Path.cwd()

        # Brief check to see if data_dir was 
        # given on ObsID object creation.
        if self.data_dir != None:
            data_dir = self.data_dir
            self.logger.info(f'Using input data_dir: {self.data_dir}.')
        else:
            data_dir = sas_cfg.get("sas", "data_dir")
            self.logger.info(f'Using default data_dir: {self.data_dir}.')

        # Start checking data_dir
        if os.path.exists(data_dir):
            self.data_dir = data_dir
            self.logger.info(f'Data directory found {self.data_dir}')
        else:
            self.logger.info(f'Did not find {self.data_dir}, using {startdir}')
            self.data_dir = startdir   

        # Set directories for the observation, odf, pps, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.obsid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.pps_dir  = os.path.join(self.obs_dir,'PPS')
        self.work_dir = os.path.join(self.obs_dir,'work')

        if os.path.exists(self.obs_dir):
            self.logger.info(f'obs_dir found at {self.obs_dir}.')
        else:
            self.logger.info(f'obs_dir not found {self.obs_dir}. User must download data!')
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
                return
            
        # Get lists of ODF and PPS files.
        if os.path.exists(self.odf_dir):
            self.files['ODF'] = self.__get_list_of_ODF_files()
        if os.path.exists(self.pps_dir):
            self.files['PPS'] = self.__get_list_of_PPS_files()
        
        if os.path.exists(self.work_dir):
            self.logger.info(f'work_dir found at {self.work_dir}.')
        else:
            self.logger.info(f'Default work_dir not found! User must create it!')
            return

        self.logger.info(f'Data directory = {self.data_dir}')
        self.logger.info(f'Existing directory for {self.obsid} found ...')
        self.logger.info(f'Searching {self.data_dir}/{self.obsid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        exists = self.get_ccf_cif()
        if not exists:
            self.logger.info('ccf.cif file not present! User must run calibrate_odf!')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        out_note = 'SAS_CCF = {0}'.format(self.files['sas_ccf'])
        self.logger.info(out_note)
        print(out_note)

        # Looking for *SUM.SAS file.
        exists = self.get_SUM_SAS()
        if not exists:
            self.logger.info('*SUM.SAS file not present! User must run calibrate_odf!')
            return
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        out_note = 'SAS_ODF = {0}'.format(self.files['sas_odf'])
        self.logger.info(out_note)
        print(out_note)

        # Check for previously generated event lists.
        self.find_event_list_files(print_output = self.output_to_terminal)
        self.find_rgs_spectra_files(print_output = self.output_to_terminal)

        # Change to work directory.
        os.chdir(self.work_dir)
        self.logger.info(f'Changing to work_dir: {self.work_dir}')

        # Exit the __set_obsid function. Everything is set.
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
                         'OM': 'XXXXXXXXXX'}
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
            # # Need to do something different for optical monitor images.
            if exists:
                self.files[evt_list_list[inst]].sort()
                if print_output:
                    print(" > {0} {1} event list(s) found.\n".format(len(self.files[evt_list_list[inst]]),inst_name[inst]))
                    for x in self.files[evt_list_list[inst]]:
                        print("    " + x + "\n")
            
        return
    
    def find_rgs_spectra_files(self,print_output=True):
        """
        --Not intended to be used by the end user. Internal use only.--

        Check for RGS spectra files created by rgsproc. Adds them to 
        'files' dictrionary with the keys:

            'R1SPEC'
            'R2SPEC'
        """

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
            files = glob.glob(self.obs_dir+'/**/*RSPEC*FIT', recursive=True)
            for filename in files:
                if (filename.find(file_key[inst]) != -1):
                    self.files[dict_key[inst]].append(os.path.abspath(filename))
                    exists = True
            if exists:
                self.files[dict_key[inst]].sort()
                if print_output:
                    print(" > {0} {1} spectra found.\n".format(len(self.files[dict_key[inst]]),inst_name[inst]))
                    for x in self.files[dict_key[inst]]:
                        print("    " + x + "\n")

        return
    
    def get_ccf_cif(self):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the ccf.cif file. If it exists, inserts file name in 
        'files' dict.
        """

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
            self.logger.warning('ccf.cif file not present! User must run calibrate_odf!')

        return exists
    
    def get_SUM_SAS(self,user_defined_file=None):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the *SUM.SAS file. Making this a function since it is 
        used in several places.
        """

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
                        self.logger.error(f'Summary file PATH {path} does not exist. Rerun calibrate_odf with overwrite=True.')
                        print(f'\nSummary file PATH {path} does not exist. \n\n>>>>Rerun calibrate_odf with overwrite=True.')
                        exists = False
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if not os.path.exists(MANIFEST[0]):
                        self.logger.error(f'Missing {MANIFEST[0]} file in {path}. Missing ODF components? Rerun calibrate_odf with overwrite=True.')
                        print(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components? \n\n>>>>Rerun calibrate_odf with overwrite=True.')
                        exists = False

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

    def __check_for_ccf_cif(self):
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
    
    def __check_for_manifest(self):
        """
        Checks if manifest file exists.
        """

        exists = False

        MANIFEST = glob.glob(self.obs_dir+'/**/*MANIFEST*', recursive=True)
        if len(MANIFEST) > 0:
            if os.path.exists(MANIFEST[0]): exists = True
        
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

    def __create_ODF_object(self):
        self.ODF = ODF(self.obsid, data_dir = self.data_dir,
                       logfilename = self.logfilename, 
                       tasklogdir  = self.tasklogdir, 
                       output_to_terminal = self.output_to_terminal, 
                       output_to_file     = self.output_to_file,
                       logger = self.logger)
        
    def __create_PPS_object(self):
        self.PPS = PPS(self.obsid, data_dir = self.data_dir,
                       logfilename = self.logfilename, 
                       tasklogdir  = self.tasklogdir, 
                       output_to_terminal = self.output_to_terminal, 
                       output_to_file     = self.output_to_file,
                       logger = self.logger)
    
class ODF(ObsID):
    """
    Placeholder text
    """
    def __init__(self, obsid, data_dir = None, 
                 logfilename = None, 
                 tasklogdir  = None,
                 output_to_terminal = True, 
                 output_to_file     = False,
                 logger = None):
        super().__init__(obsid, data_dir = data_dir, 
                         logfilename = logfilename, 
                         tasklogdir  = tasklogdir, 
                         output_to_terminal = output_to_terminal, 
                         output_to_file     = output_to_file)

        # Clean up possible inheritance issues from Parent
        # self.__remove_attr('files')
        self.__remove_attr('ODF')
        self.__remove_attr('PPS')

        if not logger is None:
            self.logger = logger

        if logger is None and not hasattr(self, 'logger'):
            # When the ObsID class is super-instatiated a logger object
            # should automatically be generated. But this is here
            # just in case.
            self.logger = get_logger('ObsID_' + self.obsid, 
                                     toterminal  = self.output_to_terminal,
                                     tofile      = self.output_to_file, 
                                     logfilename = self.logfilename,
                                     tasklogdir  = self.obs_dir)
    
    def basic_setup(self, 
                    data_dir    = None,
                    repo        = 'esa',
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
            repo:        Download repository ('esa','heasarc','sciserver').
            overwrite:   Remove previous data files and download again.
            rerun:       Rerun the *procs or *chains.
            recalibrate: Rerun 'cifbuild' and 'odfingest'.

        All input arguments for 'download_data' and 'calibrate_odf'
        can be passed to 'basic_setup'.

        'download_data' inputs (with defaults):

            repo            = 'esa'
            level           = 'ODF'
            data_dir        = None
            overwrite       = False
            logger          = None
            proprietary     = False
            credentials_file= None
            encryption_key  = None

        'calibrate_odf' inputs (with defaults):
               
            obs_dir        = None
            sas_ccf        = None
            sas_odf        = None
            cifbuild_opts  = []
            odfingest_opts = []
            recalibrate    = False
            logger         = None

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

            odf.basic_setup(repo='heasarc',encryption_key='XXXXXXXXXXXXXXX')

                - Uses the defaults, but downloads *proprietary* data from 
                  the HEASARC. Must provide an encryption key, an alpha-numeric
                  string with 30 characters.

            odf.basic_setup(proprietary=True)

                - Uses the defaults, but downloads *proprietary* data from 
                  the XSA at ESA. Astroquery will ask for user's Cosmos
                  username and password.

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


        self.download_data(repo             = self.repo,
                           level            = self.level,
                           data_dir         = self.data_dir,
                           overwrite        = overwrite,
                           logger           = logger,
                           proprietary      = kwargs.get('proprietary', False),
                           credentials_file = kwargs.get('credentials_file', None),
                           encryption_key   = kwargs.get('encryption_key', None))
        
        if hasattr(self, 'odf_dir'):
            if os.path.exists(self.odf_dir):
                self.files['ODF'] = self.__get_list_of_ODF_files()
        if hasattr(self, 'pps_dir'):
            if os.path.exists(self.pps_dir):
                self.files['PPS'] = self.__get_list_of_PPS_files()

        self.work_dir = os.path.join(self.obs_dir,'work')
        if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
        
        # If only PPS files requested, no processing needed.
        if self.level == 'PPS': return

        self.calibrate_odf(obs_dir        = self.data_dir,
                           sas_ccf        = kwargs.get('sas_ccf', None),
                           sas_odf        = kwargs.get('sas_odf', None),
                           cifbuild_opts  = kwargs.get('cifbuild_opts', []),
                           odfingest_opts = kwargs.get('odfingest_opts', []),
                           recalibrate    = recalibrate)

        if run_epproc and not run_epchain:
            self.__run_analysis('epproc',
                                kwargs.get('epproc_args', []),
                                rerun   = rerun,
                                logFile = 'epproc.log')
        
        if run_epchain:
            self.__run_analysis('epchain',
                                kwargs.get('epchain_args', []),
                                rerun   = rerun,
                                logFile = 'epchain.log')

        if run_emproc and not run_emchain:
            self.__run_analysis('emproc',
                                kwargs.get('emproc_args', []),
                                rerun   = rerun,
                                logFile = 'emproc.log')
            
        if run_emchain:
            self.__run_analysis('emchain',
                                kwargs.get('emchain_args', []),
                                rerun   = rerun,
                                logFile = 'emchain.log')
            
        if run_rgsproc:
            self.__run_analysis('rgsproc',
                                kwargs.get('rgsproc_args', []),
                                rerun   = rerun,
                                logFile = 'rgsproc.log')
        
        #if run_omichain:
        #    self.__run_analysis('omichain',
        #                        kwargs.get('omichain_args', []),
        #                        rerun   = rerun,
        #                        logFile = 'omichain.log')
        
        return
    
    def download_data(self, repo  = 'esa',
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
                                        'sciserver' (if user is on sciserver)

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
        
        # Where are we?
        startdir = os.getcwd()

        call_download_data = True

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
        
        # Set the obs_dir
        if not os.path.exists(self.obs_dir):
            self.obs_dir = os.path.join(self.data_dir,self.obsid)

        # Set odf_dir
        self.odf_dir = os.path.join(self.obs_dir,'ODF')

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
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
                if what_exists['odf_dir'] and what_exists['manifest']:
                    self.logger.info(f'Existing ODF directory {self.odf_dir} found ...')
                    call_download_data = False
                if not call_download_data:
                    self.logger.info(f'Data found in {self.obs_dir} not downloading again.')
                    print(f'Data found in {self.obs_dir} not downloading again.')

        # Set work directory.
        self.work_dir = os.path.join(self.obs_dir,'work')

        if call_download_data:
            self.logger.info(f'Will download Obs ID data with level ODF')

            # Check chosen repository.
            repo_opts = ['esa','heasarc','sciserver']
            if repo not in repo_opts:
                self.logger.error('Download repository not found!')
                print(f'Options for repo are {repo_opts[0]}, {repo_opts[1]}, or {repo_opts[2]}')
                raise Exception('Download repository not found!')
            else:
                self.logger.info(f'Will download data from {repo}.')

            self.repo = repo

            # Function for downloading a single obsid set.
            dl_data(self.obsid,
                    self.data_dir,
                    level='ODF',
                    encryption_key=encryption_key,
                    repo=self.repo,
                    logger=self.logger,
                    proprietary=proprietary,
                    credentials_file=credentials_file,
                    overwrite=overwrite)
            
        self.logger.info(f'Data directory: {self.data_dir}')
        self.logger.info(f'ObsID directory: {self.obs_dir}')
        print(f'Data directory: {self.data_dir}')
        
        if hasattr(self, 'odf_dir'):
            if os.path.exists(self.odf_dir):
                self.files['ODF'] = self.__get_list_of_ODF_files()

        return
        
    def calibrate_odf(self,
                      obs_dir = None,
                      sas_ccf = None,
                      sas_odf = None,
                      cifbuild_opts  = [],
                      odfingest_opts = [],
                      recalibrate    = False):
        """
        Before running this function an ObsID object must be created first. e.g.

            obs = pysas.obsid.ObsID(obsid)

        *Then* the data must be downloaded using:

            obs.ODF.download_data()

        This function can then be used as, 
        
            obs.ODF.calibrate_odf()

        The calibrate_odf function will automatically look in data_dir for the subdirectory 
        data_dir/obsid. If it does not exist then it will download the data.
        
        If it exists it will search data_dir/obsid and any subdirectories for the ccf.cif
        and *SUM.SAS files. But if overwrite=True then it will remove data_dir/obsid and 
        download the data.

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

            --logger:     (TaskLogger): Only used if called from inside 'basic_setup'.

        """

        # Where are we?
        startdir = os.getcwd()

        # Brief check to see if data_dir is already defined.
        if self.data_dir == None:
            data_dir = sas_cfg.get("sas", "data_dir")
            if os.path.exists(data_dir):
                self.data_dir = data_dir
            else:
                self.data_dir = startdir

        if obs_dir == None:
            self.obs_dir = os.path.join(self.data_dir,self.obsid)

        # Check if obs_dir exists. If not then raise an Exception.
        if not os.path.isdir(self.obs_dir):
            self.logger.error('Observation directory: {self.obs_dir} does not exist!')
            print(f'Error! Observation directory: {self.obs_dir} does not exist!')
            print(f'Please provide the path to the observation directory \n \
                    using the input obs_dir=path/to/obs/dir/.')
            raise Exception(f'Error! Observation directory: {self.obs_dir} does not exist!')

        self.logger.info(f'Observation directory = {self.obs_dir}')

        # Deal with the rest of the inputs.
        self.files['sas_ccf'] = sas_ccf
        self.files['sas_odf'] = sas_odf
        if cifbuild_opts == None:
            cifbuild_opts = []
        self.cifbuild_opts = cifbuild_opts
        if odfingest_opts == None:
            odfingest_opts = []
        self.odfingest_opts = odfingest_opts
        
        os.chdir(self.obs_dir)
        self.logger.info(f'Changed directory to {self.obs_dir}')

        print(f'''

        Starting SAS session

        Data directory = {self.obs_dir}

        ''')

        # Set directories for the observation, odf, pps, and work.
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.work_dir = os.path.join(self.obs_dir,'work')

        # Check what exists in the obs_dir.
        what_exists = self.__parse_obs_dir()

        # Runs calibration if recalibrate = True. Default recalibrate = False
        # Else, looks for ccf.cif and *SUM.SAS files.
        # If ccf.cif and *SUM.SAS files are not found then will run calibration.
        
        if recalibrate:
            if what_exists['odf_dir'] and what_exists['ODF_files']:
                self.__run_calibration(cifbuild_opts,odfingest_opts)
            else:
                self.logger.error('ODF directory and files not found!')
                print('ODF directory and files not found! Try downloading data again.')
                raise Exception('ODF directory and files not found!')
            return
        else:
            self.logger.info(f'Searching {self.obs_dir} for ccf.cif and *SUM.SAS files ...')
            # Looking for ccf.cif file.
            if self.files['sas_ccf'] == None:
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
            if self.files['sas_odf'] == None:
                SUM_exists = self.get_SUM_SAS()                    
            else:
                # Check if *SUM.SAS file path given by user exists.
                try:
                    SUM_exists = self.get_SUM_SAS(,user_defined_file=self.files['sas_odf'])
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

            if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
            # Exit the calibrate_odf function. Everything is set.
        
        if os.path.exists(self.odf_dir):
            self.files['ODF'] = self.__get_list_of_ODF_files()

        return

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
        MANIFEST = glob.glob('MANIFEST*')
        try:
            os.path.exists(MANIFEST[0])
            self.logger.info(f'File {MANIFEST[0]} exists')
        except FileExistsError:
            self.logger.error(f'File {MANIFEST[0]} not present. Please check ODF!')
            print(f'File {MANIFEST[0]} not present. Please check ODF!')
            sys.exit(1)

        # Here the ODF is fully untarred below obsid subdirectory
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
               tasklogdir  = self.tasklogdir,
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
               tasklogdir  = self.tasklogdir,
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
                    if path != self.odf_dir:
                        self.logger.error(f'SAS summary file PATH {path} mismatchs {self.odf_dir}')
                        raise Exception(f'SAS summary file PATH {path} mismatchs {self.odf_dir}')
                    else:
                        self.logger.info(f'Summary file PATH keyword matches {self.odf_dir}')
                        print(f'\nSummary file PATH keyword matches {self.odf_dir}')

        self.get_active_instruments()

        print(f'''\n\n
        SAS_CCF = {self.files['sas_ccf']}
        SAS_ODF = {self.files['sas_odf']}
        \n''')

        return
    
    def __run_analysis(self,task,inargs,rerun=False,logFile='DEFAULT'):
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
        
        self.find_event_list_files(print_output=False)
        self.find_rgs_spectra_files(print_output=False)

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
        self.find_event_list_files(print_output=False)
        if (len(self.files['PNevt_list']) == 0) and run_ep:
            print("Something has gone wrong. I cant find any event list files after running epproc. \n")
        if (len(self.files['M1evt_list']) == 0 and len(self.files['M2evt_list']) == 0 and run_em):
            print("Something has gone wrong. I cant find any event list files after running emproc. \n")
        if (len(self.files['R1evt_list']) == 0 and len(self.files['R2evt_list']) == 0 and run_rgs):
            print("Something has gone wrong. I cant find any event list files after running rgsproc. \n")
        self.find_rgs_spectra_files(print_output=False)
    
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
    
    def __remove_attr(self, attr_name):
        if hasattr(self, attr_name): delattr(self, attr_name)

class PPS(ObsID):
    """
    Placeholder text
    """
    def __init__(self, obsid, data_dir = None, 
                 logfilename = None, 
                 tasklogdir  = None,
                 output_to_terminal = True, 
                 output_to_file     = False,
                 logger = None):
        super().__init__(obsid, data_dir = data_dir, 
                         logfilename = logfilename, 
                         tasklogdir  = tasklogdir, 
                         output_to_terminal = output_to_terminal, 
                         output_to_file     = output_to_file)

        # Clean up possible inheritance issues from Parent
        # self.__remove_attr('files')
        self.__remove_attr('ODF')
        self.__remove_attr('PPS')

        if not logger is None:
            self.logger = logger

        if logger is None and not hasattr(self, 'logger'):
            # When the ObsID class is super-instatiated a logger object
            # should automatically be generated. But this is here
            # just in case.
            self.logger = get_logger('ObsID_' + self.obsid, 
                                     toterminal  = self.output_to_terminal,
                                     tofile      = self.output_to_file, 
                                     logfilename = self.logfilename,
                                     tasklogdir  = self.obs_dir)
    
    def __remove_attr(self, attr_name):
        if hasattr(self, attr_name): delattr(self, attr_name)