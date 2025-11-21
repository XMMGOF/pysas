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
import os, sys, shutil, glob, numbers
from warnings import warn

# Third party imports

# Local application imports
from pysas import sas_cfg
from ..init_sas import initializesas
from ..wrapper import Wrapper as w
from ..sasutils import generate_logger
from ..sasutils import download_data as dl_data

__all__ = ['ODFobject']


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
        warn(
             """
             The ODFobject class has been depricated. Use ObsID instead.
             ex: 
                 my_obs = pysas.obsid.ObsID(obsid)
             instead of
                 odf = pysas.odfcontrol.ODFobject(obsid)
             """)
        if isinstance(odfid, numbers.Number):
            odfid = str(odfid)
        self.odfid = odfid
        self.data_dir = data_dir
        self.files = {}
        self.__set_obsid()

    def basic_setup(self,data_dir=None,level='ODF',repo='esa',
                    overwrite=False,recalibrate=False,rerun=False,
                    run_epproc=True,run_emproc=True,run_rgsproc=True,
                    run_epchain=False,run_emchain=False,
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
            level:       Level of data products ('ODF','PPS','ALL').
            repo:        Download repository ('esa','heasarc','sciserver').
            overwrite:   Remove previous data files and download again.
            recalibrate: Rerun 'cifbuild' and 'odfingest'.
            rerun:       Rerun the *procs or *chains.

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
            PPS_subset      = False
            instname        = None
            expflag         = None
            expno           = None
            product_type    = None
            datasubsetno    = None
            sourceno        = None
            extension       = None
            **kwargs

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
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'
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
                           encryption_key   = kwargs.get('encryption_key', None),
                           PPS_subset       = kwargs.get('PPS_subset', False),
                           instname         = kwargs.get('instname', None),
                           expflag          = kwargs.get('expflag', None),
                           expno            = kwargs.get('expno', None),
                           product_type     = kwargs.get('product_type', None),
                           datasubsetno     = kwargs.get('datasubsetno', None),
                           sourceno         = kwargs.get('sourceno', None),
                           extension        = kwargs.get('extension', None),
                           filename         = kwargs.get('filename', None))
        
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
    
    def download_data(self,repo='esa',level='ODF',
                      data_dir=None,overwrite=False,logger=None,
                      proprietary=False,credentials_file=None,
                      encryption_key=None,PPS_subset=False,
                      instname=None,expflag=None,expno=None,
                      product_type=None,datasubsetno=None,
                      sourceno=None,extension=None,
                      filename=None,
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
                                        'sciserver' (if user is on sciserver)

            --level:          (string): Level of data products to download.
                                        Default: 'ODF'
                                        Can be 'ODF, 'PPS' or 'ALL'.

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        data_dir/odfid.
                                        Default: Default from sas_config file, or
                                        current working directory.

            --overwrite:     (boolean): If True will force overwrite of data if odfid 
                                        data already exists in data_dir/odfid.

            --logger:     (TaskLogger): Only used if called from inside 'basic_setup'.

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
            
                instname: instrument name
                expflag: Exposure flag
                expno: Exposure number
                product_type: Product type
                datasubsetno: data subset number/character
                sourceno: Source number or slew step number
                extension: File format
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
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'
            if os.path.exists(data_dir):
                self.data_dir = data_dir
            else:
                self.data_dir = startdir
        else:
            self.data_dir = data_dir
        
        if logger == None:
            logger = generate_logger(logname=f'download_{self.odfid}', log_dir=self.data_dir)

        # Identify the download level.
        levelopts = ['ALL','ODF','PPS','4XMM','om_mosaic']
        if level not in levelopts:
            logger.log('error', 'Obs ID request level is undefined!')
            print(f'Options for level are {levelopts[0]}, {levelopts[1]}, or {levelopts[2]}')
            raise Exception('ODF request level is undefined!')
        
        # Set the obs_dir.
        self.obs_dir = os.path.join(self.data_dir,self.odfid)

        # Set odf_dir and pps_dir
        if level == 'ODF' or level == 'ALL':
            self.odf_dir = os.path.join(self.obs_dir,'ODF')
        if level == 'PPS' or level == 'ALL':
            self.pps_dir = os.path.join(self.obs_dir,'PPS')
        self.level = level

        # Checks if obs_dir exists. 
        # Removes it if overwrite = True. Default overwrite = False.
        if os.path.exists(self.obs_dir):
            logger.log('info', f'Existing directory for {self.odfid} found ...')
            if overwrite:
                # If obs_dir exists and overwrite = True then remove obs_dir.
                logger.log('info', f'Removing existing directory {self.obs_dir} ...')
                print(f'\n\nRemoving existing directory {self.obs_dir} ...')
                shutil.rmtree(self.obs_dir)
            else:
                # Check for files
                what_exists = self.__parse_obs_dir()
                if what_exists['odf_dir'] and what_exists['manifest'] and level == 'ODF':
                    logger.log('info', f'Existing ODF directory {self.odf_dir} found ...')
                    call_download_data = False
                if what_exists['pps_dir'] and what_exists['PPS_files'] and level == 'PPS':
                    logger.log('info', f'Existing PPS directory {self.pps_dir} found ...')
                    call_download_data = False
                if (what_exists['odf_dir'] and what_exists['manifest'] and 
                    what_exists['pps_dir'] and what_exists['PPS_files'] and level == 'ALL'):
                    logger.log('info', f'Existing data directories {self.odf_dir} and {self.pps_dir} found ...')
                    call_download_data = False
                if (filename or PPS_subset) and level == 'PPS':
                    logger.log('info', f'Downloading subset of PPS data. Will silently overwrite any pre-existing files.')
                    call_download_data = True
                if not call_download_data:
                    logger.log('info', f'Data found in {self.obs_dir} not downloading again.')
                    print(f'Data found in {self.obs_dir} not downloading again.')

        # Set work directory.
        self.work_dir = os.path.join(self.obs_dir,'work')

        if call_download_data:
            logger.log('info', f'Will download Obs ID data with level {level}')

            # Check chosen repository.
            repo_opts = ['esa','heasarc','sciserver']
            if repo not in repo_opts:
                logger.log('error', 'Download repository not found!')
                print(f'Options for repo are {repo_opts[0]}, {repo_opts[1]}, or {repo_opts[2]}')
                raise Exception('Download repository not found!')
            else:
                logger.log('info', f'Will download data from {repo}.')

            self.repo = repo

            # Function for downloading a single odfid set.
            dl_data(self.odfid,
                    self.data_dir,
                    level=self.level,
                    encryption_key=encryption_key,
                    repo=self.repo,
                    logger=logger,
                    proprietary=proprietary,
                    credentials_file=credentials_file,
                    overwrite=overwrite,
                    PPS_subset=PPS_subset,
                    instname=instname,
                    expflag=expflag,
                    expno=expno,
                    product_type=product_type,
                    datasubsetno=datasubsetno,
                    sourceno=sourceno,
                    extension=extension,
                    filename=filename,
                    **kwargs)
            
        logger.log('info', f'Data directory: {self.data_dir}')
        logger.log('info', f'ObsID directory: {self.obs_dir}')
        print(f'Data directory: {self.data_dir}')
        
        if hasattr(self, 'odf_dir'):
            if os.path.exists(self.odf_dir):
                self.files['ODF'] = self.__get_list_of_ODF_files()
        if hasattr(self, 'pps_dir'):
            if os.path.exists(self.pps_dir):
                self.files['PPS'] = self.__get_list_of_PPS_files()

        return
    
    def calibrate_odf(self,obs_dir=None,
                      sas_ccf=None,sas_odf=None,
                      cifbuild_opts=[],odfingest_opts=[],
                      recalibrate=False,logger=None):
        """
        Before running this function an ODFobject must be created first. e.g.

            odf = pysas.odfcontrol.ODFobject(obsid)

        *Then* the data must be downloaded using:

            odf.download_data()

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

            --obs_dir:  (string/path): Path to the obs directory. If no path 
                                       given, then will look in 
                                       data_dir/odfid/. If directory exists then 
                                       will look for ccf.cif and *SUM.SAS files. 
                                       Default: None, looks in data_dir/odfid/.

            --sas_ccf:   (string/path): Path to ccf.cif file for odfid.

            --sas_odf:   (string/path): Path to *SUM.SAS file for odfid.

            --cifbuild_opts:    (list): Options for cifbuild.

            --odfingest_opts:   (list): Options for odfingest.

            --recalibrate:   (boolean): If True will rerun odfingest and cifbuild.

            --logger:     (TaskLogger): Only used if called from inside 'basic_setup'.

        """

        # Where are we?
        startdir = os.getcwd()

        # Brief check to see if data_dir is already defined.
        if self.data_dir == None:
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'
            if os.path.exists(data_dir):
                self.data_dir = data_dir
            else:
                self.data_dir = startdir

        if obs_dir == None:
            self.obs_dir = os.path.join(self.data_dir,self.odfid)

        if logger == None:
            logger = generate_logger(logname='odf_'+self.odfid, log_dir=self.data_dir)

        # Check if obs_dir exists. If not then raise an Exception.
        if not os.path.isdir(self.obs_dir):
            logger.log('error', 'Observation directory: {self.obs_dir} does not exist!')
            print(f'Error! Observation directory: {self.obs_dir} does not exist!')
            print(f'Please provide the path to the observation directory \n \
                    using the input obs_dir=path/to/obs/dir/.')
            raise Exception(f'Error! Observation directory: {self.obs_dir} does not exist!')

        logger.log('info', f'Observation directory = {self.obs_dir}')

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
        logger.log('info', f'Changed directory to {self.obs_dir}')

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
                self.__run_calibration(cifbuild_opts,odfingest_opts,logger)
            else:
                logger.log('error', 'ODF directory and files not found!')
                print('ODF directory and files not found! Try downloading data again.')
                raise Exception('ODF directory and files not found!')
            return
        else:
            logger.log('info', f'Searching {self.obs_dir} for ccf.cif and *SUM.SAS files ...')
            # Looking for ccf.cif file.
            if self.files['sas_ccf'] == None:
                ccf_exists = self.get_ccf_cif(logger)
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
                SUM_exists = self.get_SUM_SAS(logger)                    
            else:
                # Check if *SUM.SAS file path given by user exists.
                try:
                    SUM_exists = self.get_SUM_SAS(logger,user_defined_file=self.files['sas_odf'])
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
                self.__run_calibration(cifbuild_opts,odfingest_opts,logger) 
            
            # Set 'SAS_ODF' enviroment variable.
            os.environ['SAS_ODF'] = self.files['sas_odf']
            logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
            print('SAS_ODF = {0}'.format(self.files['sas_odf']))

            self.get_active_instruments()

            if not os.path.exists(self.work_dir): os.mkdir(self.work_dir)
            # Exit the calibrate_odf function. Everything is set.
        
        if os.path.exists(self.odf_dir):
            self.files['ODF'] = self.__get_list_of_ODF_files()

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
            # # Checking for OM sky aligned image.
            # files = glob.glob(self.obs_dir+'/**/*SIMAGE*FIT', recursive=True)
            # for filename in files:
            #     if (filename.find(find_list[inst]) != -1):
            #         self.files[evt_list_list[inst]].append(os.path.abspath(filename))
            #         exists = True
            # # Checking for OM full-frame sky image.
            # files = glob.glob(self.obs_dir+'/**/*FSIMAG*FIT', recursive=True)
            # for filename in files:
            #     if (filename.find(find_list[inst]) != -1):
            #         self.files[evt_list_list[inst]].append(os.path.abspath(filename))
            #         exists = True
            # # Checking for OM sky image mosaic.
            # files = glob.glob(self.obs_dir+'/**/*RSIMAG*FIT', recursive=True)
            # for filename in files:
            #     if (filename.find(find_list[inst]) != -1):
            #         self.files[evt_list_list[inst]].append(os.path.abspath(filename))
            #         exists = True
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
    
    def get_ccf_cif(self,logger):
        """
        --Not intended to be used by the end user. Internal use only.--

        Checks for the ccf.cif file. If it exists, inserts file name in 
        'files' dict.
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
    
    def get_SUM_SAS(self,logger,user_defined_file=None):
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
    
    def clear_obs_dir(self):
        """
        Function to remove all files and subdirectories from the obs_dir.
        """
        if os.path.exists(self.obs_dir):
            print(f'\n\nRemoving existing directory {self.obs_dir} ...')
            shutil.rmtree(self.obs_dir)

    def clear_work_dir(self):
        """
        Function to remove all files and subdirectories from the work_dir.
        """
        if os.path.exists(self.work_dir):
            print(f'\n\nRemoving existing directory {self.work_dir} ...')
            shutil.rmtree(self.work_dir)
    
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
            if sas_cfg.config.has_option('sas','data_dir'):
                data_dir = sas_cfg.get_setting('data_dir')
            else:
                data_dir = '/does/not/exist'

        # Start checking data_dir
        if os.path.exists(data_dir):
            self.data_dir = data_dir
        else:
            # Nothing can be done! User must run download_data!
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
            # User must run download_data!
            return
        
        if os.path.exists(self.odf_dir):
            print(f'odf_dir found at {self.odf_dir}.')
            os.environ['SAS_ODF'] = self.odf_dir
            if os.path.exists(self.pps_dir):
                print(f'pps_dir found at {self.pps_dir}.')
        else:
            if os.path.exists(self.pps_dir):
                print(f'pps_dir found at {self.pps_dir}.')
            else:
                print(f'ODF and PPS directories not found! User must download data!')
                return
            
        # Get lists of ODF and PPS files.
        if os.path.exists(self.odf_dir):
            self.files['ODF'] = self.__get_list_of_ODF_files()
        if os.path.exists(self.pps_dir):
            self.files['PPS'] = self.__get_list_of_PPS_files()
        
        if os.path.exists(self.work_dir):
            print(f'work_dir found at {self.work_dir}.')
        else:
            print(f'Default work_dir not found! User must create it!')
            return

        # Only generate logger if observation directory exists.
        logger = generate_logger(logname='odf_'+self.odfid, log_dir=self.data_dir)
        logger.log('info', f'Data directory = {self.data_dir}')
        logger.log('info', f'Existing directory for {self.odfid} found ...')
        logger.log('info', f'Searching {self.data_dir}/{self.odfid} for ccf.cif and *SUM.SAS files ...')

        # Looking for ccf.cif file.
        exists = self.get_ccf_cif(logger)
        if not exists:
            print('ccf.cif file not present! User must run calibrate_odf!')
            return

        # Set 'SAS_CCF' enviroment variable.
        os.environ['SAS_CCF'] = self.files['sas_ccf']
        logger.log('info', 'SAS_CCF = {0}'.format(self.files['sas_ccf']))
        print('SAS_CCF = {}'.format(self.files['sas_ccf']))

        # Looking for *SUM.SAS file.
        exists = self.get_SUM_SAS(logger)
        if not exists:
            print('*SUM.SAS file not present! User must run calibrate_odf!')
            return
        
        # Set 'SAS_ODF' enviroment variable.
        os.environ['SAS_ODF'] = self.files['sas_odf']
        logger.log('info', 'SAS_ODF = {0}'.format(self.files['sas_odf']))
        print('SAS_ODF = {0}'.format(self.files['sas_odf']))

        # Check for previously generated event lists.
        self.find_event_list_files()
        self.find_rgs_spectra_files()

        # Change to work directory.
        os.chdir(self.work_dir)

        # Exit the __set_obsid function. Everything is set.
        return
    
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
        obs_dir  = os.path.join(self.data_dir,self.odfid)
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

    def __run_calibration(self,cifbuild_opts,odfingest_opts,logger):
        """
        --Not intended to be used by the end user. Internal use only.--

        Making this a separate function since it can be called from different 
        inside the function calibrate_odf. Prevents duplication of code.
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
    