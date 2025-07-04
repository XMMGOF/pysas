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

"""

# Standard library imports
import os, sys, shutil, glob, numbers

# Third party imports

# Local application imports
from ..configutils import sas_cfg
from ..init_sas import initializesas
from ..sasutils import download_data as dl_data
from pysas.logger import pyget_logger as get_logger

class ObsID:
    """
    Class for and Obs ID object.
    """
    def __init__(self, obsid, data_dir = None,
                 logfilename = None,
                 tasklogdir  = None,
                 output_to_terminal = False,
                 output_to_file     = False):
        
        if isinstance(obsid, numbers.Number):
            obsid = str(obsid)
        self.obsid       = obsid
        self.data_dir    = data_dir
        self.files       = {}
        self.logfilename = logfilename
        self.tasklogdir  = tasklogdir
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file
        self.__set_obsid()

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
            # Nothing can be done! User must run download_data!
            return

        # Set directories for the observation, odf, pps, and work.
        self.obs_dir  = os.path.join(self.data_dir,self.obsid)
        self.odf_dir  = os.path.join(self.obs_dir,'ODF')
        self.pps_dir  = os.path.join(self.obs_dir,'PPS')
        self.work_dir = os.path.join(self.obs_dir,'work')

        # Generate logger. By default it runs silent with
        # toterminal and tofile = False
        self.logger = get_logger('ObsID_' + self.obsid, 
                                 toterminal  = self.output_to_terminal, 
                                 tofile      = self.output_to_file, 
                                 logfilename = self.logfilename,
                                 tasklogdir  = self.obs_dir)

        if os.path.exists(self.obs_dir):
            self.logger.info(f'obs_dir found at {self.obs_dir}.')
        else:
            # obs_dir not found! Nothing can be done!
            # User must run download_data!
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
                self.logger.warning(f'ODF and PPS directories not found! User must download data!')
                return
            
        # Get lists of ODF and PPS files.
        if os.path.exists(self.odf_dir):
            self.files['ODF'] = self.__get_list_of_ODF_files()
        if os.path.exists(self.pps_dir):
            self.files['PPS'] = self.__get_list_of_PPS_files()
        
        if os.path.exists(self.work_dir):
            self.logger.info(f'work_dir found at {self.work_dir}.')
        else:
            self.logger.warning(f'Default work_dir not found! User must create it!')
            return

        self.logger.info(f'Data directory = {self.data_dir}')
        self.logger.info(f'Existing directory for {self.obsid} found ...')
        self.logger.info(f'Searching {self.data_dir}/{self.obsid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        exists = self.get_ccf_cif(self.logger)
        if not exists:
            self.logger.warning('ccf.cif file not present! User must run calibrate_odf!')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        out_note = 'SAS_CCF = {0}'.format(self.files['sas_ccf'])
        self.logger.info(out_note)
        print(out_note)

        # Looking for *SUM.SAS file.
        exists = self.get_SUM_SAS(self.logger)
        if not exists:
            self.logger.warning('*SUM.SAS file not present! User must run calibrate_odf!')
            return
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        out_note = 'SAS_ODF = {0}'.format(self.files['sas_odf'])
        self.logger.info(out_note)
        print(out_note)

        # Change to work directory.
        os.chdir(self.work_dir)

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