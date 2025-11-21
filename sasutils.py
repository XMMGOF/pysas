# ESA (C) 2000-2024
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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SAS.  If not, see <http://www.gnu.org/licenses/>.

# sasutils.py

"""
sasutils.py

Utility functions specific to SAS or pySAS.
"""

# Standard library imports
import os, sys, subprocess, shutil, glob, tarfile, gzip, time, platform, re
from shutil import copytree
#from s3fs import S3FileSystem

# Third party imports
from astroquery.esa.xmm_newton import XMMNewton
from astroquery.heasarc import Heasarc

# Local application imports
from pysas.logger import get_logger
from .logger import TaskLogger as TL

# Third party imports

# Local application imports

def download_data(obsid,
                  data_dir,
                  level     = 'ODF',
                  repo      = 'esa',
                  overwrite = True,
                  logger    = None,
                  encryption_key   = None,
                  proprietary      = False,
                  credentials_file = None,
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
    --Not intended to be used by the end user. Internal use only.--
    --Use odf.download_data() or odf.basic_setup() instead.--

    Downloads, or copies, data from chosen repository. 

    !!!! WARNING !!!!
    Will silently overwrite any preexisting data files and remove any existing
    pipeline products. Will create directory structure in 'data_dir' for odf.

    Only the download_data function in ODFobject will check for preexisting files.

    Inputs:

        --obsid:          (string): ID of ODF in string format.

        --data_dir:  (string/path): Path to directory where the data will be 
                                    downloaded. Automatically creates directory
                                    data_dir/obsid.
                                    Default: --REQUIRED-- MUST EXIST!.

        --level:          (string): Level of data products to download.
                                    Default: 'ODF'
                                    Can be 'ODF, 'PPS' or 'ALL'.

        --repo:           (string): Which repository to use to download data. 
                                    Default: 'esa'
                                    Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'sciserver' (if user is on sciserver)

        --logger      (TaskLogger): Task logger object.

        --encryption_key: (string): Encryption key for proprietary data, a string 32 
                                    characters long. -OR- path to file containing 
                                    ONLY the encryption key.

        --proprietary    (boolean): Flag for downloading proprietary data from
                                    the XSA at ESA.

        --credentials_file (filename): Path and filename of file containing XSA
                                       username and password. For proprietary data
                                       only. (Optinal, astroquery will ask user 
                                       for username and password if filename
                                       not given.)

        --overwrite:     (boolean): If True will force overwrite of data if obsid 
                                        data already exists in data_dir/obsid.

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

            filename: Filename with no wildcards

        
    """

    if not logger:
        logger = get_logger(f'download_{obsid}')

    # Set directories for the observation, odf, and working
    obs_dir = os.path.join(data_dir,obsid)
    odf_dir = os.path.join(obs_dir,'ODF')
    pps_dir = os.path.join(obs_dir,'PPS')
    logger.debug(f'obs_dir: {obs_dir}')
    logger.debug(f'odf_dir: {odf_dir}')
    logger.debug(f'pps_dir: {pps_dir}')
    # work_dir = os.path.join(obs_dir,'work')

    # Checks if obs_dir exists. Removes it if overwrite=True.
    if os.path.exists(obs_dir) and overwrite:
        logger.info(f'Removing existing directory {obs_dir} ...')
        shutil.rmtree(obs_dir)
    
    # Creates subdirectory obsid to move or unpack observation files
    # and makes subdirectories.
    if not os.path.exists(obs_dir):
        logger.info(f'Creating observation directory {obs_dir} ...')
        os.mkdir(obs_dir)

    if level == 'PPS' and PPS_subset and not filename:
        logger.debug('Generating PPS file name.')
        PPSfile = generate_PPS_filename(obsid=obsid,instname=instname,
                                        expflag=expflag,expno=expno,
                                        product_type=product_type,
                                        datasubsetno=datasubsetno,
                                        sourceno=sourceno,extension=extension)
        logger.debug(f'PPS file name: {PPSfile}')

    if filename:
        PPS_subset = True
        PPSfile = filename

    repo = repo.lower()

    logger.debug(f'repo: {repo}')

    match repo:
        case 'esa' | 'xsa':
            logger.info(f'Requesting Obs ID = {obsid} from ESA XMM-Newton Science Archive\n')
            logger.info(f'Changed directory to {obs_dir}')
            os.chdir(obs_dir)
            if level == 'ALL':
                level = ['ODF','PPS']
            else:
                level = [level]
            for levl in level:
                # Download the obsid from ESA, using astroquery
                logger.info(f'Downloading {obsid}, level {levl} into {obs_dir}')
                if levl == 'PPS':
                    # If a filename was provided then convert it into inputs for astroquery.
                    if filename:
                        PPS_subset   = True
                        instname     = filename[11:13]
                        expflag      = filename[13]
                        expno        = filename[14:17]
                        product_type = filename[17:23]
                        datasubsetno = filename[23]
                        sourceno     = filename[24:27]
                        extension    = filename[-3:]
                    # Take care of the optional inputs.
                    if instname:     kwargs['instname']     = instname
                    if expflag:      kwargs['expflag']      = expflag
                    if expno:        kwargs['expno']        = expno
                    if product_type: kwargs['name']         = product_type
                    if datasubsetno: kwargs['datasubsetno'] = datasubsetno
                    if sourceno:     kwargs['sourceno']     = sourceno
                    if extension:    kwargs['extension']    = extension
                
                logger.debug(f'Requesting data: Obs ID={obsid}, level={levl}')
                if proprietary: logger.debug('Requesting proprietary data.')
                XMMNewton.download_data(obsid, level=levl,
                                        prop=proprietary,
                                        credentials_file=credentials_file,
                                        **kwargs)
                
                if levl == 'ODF':    
                    os.mkdir(odf_dir)

                if PPS_subset:
                    logger.debug('PPS subset, moving files into PPS directory.')
                    if not os.path.exists(pps_dir): os.mkdir(pps_dir)
                    files = glob.glob(obs_dir+'/*.*')
                    for file in files:
                        file_name = os.path.basename(file)
                        shutil.copy(file, os.path.join(pps_dir,file_name))
                else:
                    # Check that the tar.gz file has been downloaded
                    odftar = glob.glob(obs_dir+f'/{obsid}'+'*')[0]
                    try:
                        os.path.exists(odftar)
                        logger.info(f'{odftar} found.') 
                    except FileExistsError:
                        logger.error(f'File {odftar} is not present. Not downloaded?')
                        sys.exit(1)

                    tarextension = os.path.splitext(odftar)[1]
                    if tarextension == '.gz': tar_mode = 'r:gz'
                    elif tarextension == '.tar': tar_mode = 'r'
                    else:
                        logger.error(f'File {odftar} extension not recognized.')
                        raise Exception(f'File {odftar} extension not recognized.')

                    # Untars the obsid.tar.gz file
                    logger.info(f'Unpacking {odftar} ...')

                    try:
                        with tarfile.open(odftar,tar_mode) as tar:
                            if levl == 'ODF':
                                tar.extractall(path=odf_dir)
                            elif levl == 'PPS':
                                tar.extractall(path=data_dir)
                                if os.path.exists(pps_dir):
                                    copytree('pps','PPS')
                                    shutil.rmtree('pps')
                                else:
                                    os.rename('pps','PPS')
                        os.remove(odftar)
                        logger.info(f'{odftar} extracted successfully!')
                        logger.info(f'{odftar} removed')
                    except tarfile.ExtractError:
                        logger.error('tar file extraction failed')
                        raise Exception('tar file extraction failed')
        case 'heasarc' | 'nasa' | 'sciserver' | 'fornax' | 'aws':
            download_location = obs_dir
            on_host = '...'
            data_source_key = 'access_url'
            if repo == 'sciserver': 
                on_host = 'on SciServer ...'
                data_source_key = 'sciserver'
            if repo == 'aws': 
                on_host = 'on AWS ...'
                data_source_key = 'aws'
            if repo == 'fornax':
                on_host = 'on Fornax ...'
                repo = 'aws'
                logger.debug(f'repo changed to {repo}.')
                data_source_key = 'aws'
            if repo == 'nasa':
                repo = 'heasarc'
                logger.debug(f'repo changed to {repo}.')

            # This is to fix a bug between how astroquery requests data from 
            # the HEASARC vs. AWS (Fornax)
            if repo == 'heasarc':
                logger.debug(f'Setting download location to: {data_dir}')
                download_location = data_dir
            
            # Copies data into personal storage space.
            logger.info(f'Requesting XMM-Newton Obs ID = {obsid} from the HEASARC {on_host}\n')
            logger.info(f'Changed directory to {obs_dir}')
            os.chdir(obs_dir)
        
            if level in ['ALL','ODF','PPS','4XMM','om_mosaic'] and not PPS_subset:
                logger.info(f'Downloading {obsid}, level {level}')
                query = """SELECT * FROM xmmmaster WHERE obsid='{0}'""".format(obsid)
                tab = Heasarc.query_tap(query).to_table()
                if len(tab) == 0:
                    logger.error(f'Obs ID {obsid} not found in the XMM archive!')
                    raise Exception(f'Obs ID {obsid} not found in the XMM archive!')
                if level == 'ALL':
                    for lvl in ['ODF','PPS']:
                        data_source = Heasarc.locate_data(tab, catalog_name='xmmmaster')
                        data_source[data_source_key] = data_source[data_source_key]+lvl
                        Heasarc.download_data(data_source,host=repo,location=download_location)
                else:
                    data_source = Heasarc.locate_data(tab, catalog_name='xmmmaster')
                    data_source[data_source_key] = data_source[data_source_key]+level
                    Heasarc.download_data(data_source,host=repo,location=download_location)

            if PPS_subset:
                # Only if PPS_subset = True or a single file name is passed in.
                match repo:
                # If downloading a subset of PPS files instead of *all* PPS files for now
                # we have to download from the HEASARC. We are still working on how to request
                # specific files from a AWS s3 bucket. RT - 10/10/25
                    case 'heasarc' | 'nasa' | 'fornax' | 'aws':
                        wgetf = ''
                        if filename != None:
                            wgetf = filename
                            PPS_subset_note = f', file {wgetf}'
                            wgetA = ''
                        else:
                            PPS_subset_note = f' using file pattern {PPSfile}'
                            wgetA = f"-A '{PPSfile}'"

                        logger.info(f'Downloading {obsid}, level {level}{PPS_subset_note}')

                        cmd = f'wget -m -nH -e robots=off --cut-dirs=4 -l 2 -np {wgetA} https://heasarc.gsfc.nasa.gov/FTP/xmm/data/rev0/{obsid}/{level}/{wgetf}'
                        logger.info(f'Using the command:\n{cmd}')
                        result = subprocess.run(cmd, shell=True)

                        if result.returncode != 0:
                            print(f'Problem downloading data!')
                            print('Tried using the command:')
                            print(cmd)
                            logger.error(f'File download failed!')
                            raise Exception('File download failed!')
                    case 'sciserver':
                        if not os.path.exists(pps_dir): os.mkdir(pps_dir)
                        archive_data = f'/home/idies/workspace/headata/FTP/xmm/data/rev0//{obsid}/PPS'
                        file_pattern = archive_data + f'/**/{PPSfile}'
                        files = glob.glob(file_pattern, recursive=True)
                        if len(files) == 0:
                            logger.warning(f'No files of the pattern {file_pattern} found!')
                        for file in files:
                            file_name = os.path.basename(file)
                            logger.info(f'Copying file {file_name} from {archive_data} ...')
                            shutil.copy(file, os.path.join(pps_dir,file_name))
                    #case 'fornax' | 'aws':
                        # current_s3 = S3FileSystem(anon=True)
                        # s3_uri = f's3://nasa-heasarc/xmm/data/rev0/{obsid}/{level}'
                        # all_files = current_s3.ls(s3_uri)
                        # file_names = []
                        # for file_path in all_files:
                        #     file_names.append(os.path.basename(file_path))
                        # filtered_list = fnmatch.filter(file_names, PPSfile)
                        #logger.error(f'Downloading individual PPS files not supported yet {on_host}. You must download all PPS files.')
        case _:
            logger.error(f'Repo {repo} not recognized!')

    

        
        # else:
        #     logger.info(f'Copying data from {archive_data} ...')
        #     print(f'\nCopying data from {archive_data} ...')
        #     if levl == 'ODF':
        #         # Check if ALL ODF files already exist, if not copy the missing ones
        #         archive_tar_file = glob.glob(archive_data + f'/**/*.tar.gz', recursive=True)[0]
        #         odf_files = glob.glob(odf_dir + f'/**/*', recursive=True)
        #         if len(odf_files) > 0:
        #             missing_files = []
        #             odf_files_names = []
        #             for file in odf_files:
        #                 odf_files_names.append(os.path.basename(file))
        #             archive_files = glob.glob(archive_data + f'/**/*', recursive=True)
        #             for file in archive_files:
        #                 file_name = os.path.basename(file)
        #                 if file_name.endswith('.gz'):
        #                     if not file_name.endswith('.tar.gz'):
        #                         if file_name[:-3] not in odf_files_names:
        #                             missing_files.append(file)
        #                 else:
        #                     if file_name not in odf_files_names:
        #                         missing_files.append(file)
        #             for file in missing_files:
        #                 file_name = os.path.basename(file)
        #                 logger.info(f'Copying file {file_name} from {archive_data} ...')
        #                 print(f'\nCopying file {file_name} from {archive_data} ...')
        #                 shutil.copy(file, os.path.join(odf_dir,file_name))
        #         else:
        #             tar_file_name = os.path.basename(archive_tar_file)
        #             shutil.copy(archive_tar_file, os.path.join(odf_dir,tar_file_name))
        #     else:
        #         shutil.copytree(archive_data,dest_dir,dirs_exist_ok=True)      

    # Check if data is encrypted. Decrypt the data.
    encrypted = glob.glob('**/*.gpg', recursive=True)
    if len(encrypted) > 0:
        logger.info(f'Encrypted files found! Decrypting files!')

        # Checks for encryption key or file with key.
        # If no encryption key is given then go looking for a file.
        encryption_file = None
        if encryption_key == None:
            encryption_file = glob.glob(os.path.join(data_dir,f'*{obsid}*'))
            if len(encryption_file) == 0:
                encryption_file = glob.glob(os.path.join(data_dir,'*key*'))
            if len(encryption_file) > 1:
                logger.error('Multiple possible encryption key files. Specify encryption key file.')
                raise Exception('Multiple possible encryption key files.')
            if len(encryption_file) == 0:
                encryption_file = 'None'
            if os.path.isfile(encryption_file[0]):
                logger.info(f'File with encryption key found: {encryption_file}')
            else:
                logger.error('File decryption failed. No encryption key found.')
                logger.error(f'Regular file with the encryption key needs to be placed in: {data_dir}')
                raise Exception('File decryption failed. No encryption file found.')
        elif os.path.isfile(encryption_key):
            logger.info(f'Ecryption key is in file: {encryption_key}')
            encryption_file = encryption_key
        if encryption_file is not None:
            logger.info(f'Reading ecryption key from: {encryption_file}')
            with open(encryption_file) as f:
                lines = f.readlines()
                encryption_key = lines[0]
        if encryption_key == None:
            logger.error('File decryption failed. No encryption key found.')
            logger.error(f'No encryption key found in {encryption_file}')
            logger.error(f'Regular file with the encryption key needs to be placed in: {data_dir}')
            raise Exception('File decryption failed. No encryption key found.')
        
            
        for file in encrypted:
            out_file = file[:-4]
            if os.path.exists(out_file):
                logger.info(f'Already decrypted file found: {out_file}')
            else:
                logger.info(f'Decrypting {file}')
                cmd = 'echo {0} | gpg --batch -o {1} --passphrase-fd 0 -d {2}'.format(encryption_key,out_file,file)
                result = subprocess.run(cmd, shell=True)
                if result.returncode != 0:
                    logger.error(f'Problem decrypting {file}')
                    logger.error(f'File decryption failed, key used {encryption_key}')
                    raise Exception('File decryption failed')
                os.remove(file)
                logger.info(f'{file} removed')
    else:
        logger.info('No encrypted files found.')

    gzipfiles = glob.glob(odf_dir + f'/**/*.gz', recursive=True)
    if len(gzipfiles) > 0:
        logger.info('Unpacking .gz files.')
        for file in gzipfiles:
            logger.debug(f'Unpacking {file} ...')
            with gzip.open(f'{file}', 'rb') as f_in:
                out_file = file[:-3]
                with open(out_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(file)
            logger.debug(f'{file} removed')

    tarfiles = glob.glob(odf_dir + f'/**/*.tar', recursive=True)
    if len(tarfiles):
        logger.info('Unpacking .tar files.')
        for file in glob.glob(odf_dir + f'/**/*.tar', recursive=True):
            logger.debug(f'Unpacking {file} ...')
            with tarfile.open(file,"r") as tar:
                tar.extractall(path=odf_dir)
            os.remove(file)
            logger.debug(f'{file} removed')

    tar2files = glob.glob(odf_dir + f'/**/*.TAR', recursive=True)
    if len(tar2files):
        logger.info('Unpacking .TAR files.')
        for file in tar2files:
            logger.debug(f'Unpacking {file} ...')
            with tarfile.open(file,"r") as tar:
                tar.extractall(path=odf_dir)
            os.remove(file)
            logger.debug(f'{file} removed')

    ppssumhtml = 'P' + obsid + 'OBX000SUMMAR0000.HTM'
    ppssumhtmlfull = os.path.join(pps_dir, ppssumhtml)

    if os.path.exists(ppssumhtmlfull):
        ppssumhtmllink = 'file://' + ppssumhtmlfull
        logger.info(f'PPS products can be found in {pps_dir}')
        print(f'\nPPS products can be found in {pps_dir}\n\nLink to Observation Summary html: {ppssumhtmllink}')

    return

def generate_logger(logname=None,log_dir=None):
    """
    --Not intended to be used by the end user. Internal use only.--
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

def update_calibration_files(repo='NASA'):
    """
    Function to download/update XMM calibration files.
    """

    sas_ccfpath = os.environ.get('SAS_CCFPATH')
    if not sas_ccfpath:
        raise Exception('SAS_CCFPATH not set. Please define it.')

    esa_or_nasa = repo.lower()

    esa = ['esa','e','es','europe']
    nasa = ['nasa','n','na','nas','ns','nsa','us','usa','heasarc','hea']

    if esa_or_nasa in esa:
        cmd = f'rsync -v -a --delete --delete-after --force --include=\'*.CCF\' --exclude=\'*/\' sasdev-xmm.esac.esa.int::XMM_VALID_CCF {sas_ccfpath}'
    elif esa_or_nasa in nasa:
        cmd = f'wget -nH --no-remove-listing -N -np -r --cut-dirs=4 -e robots=off -l 1 -R "index.html*" https://heasarc.gsfc.nasa.gov/FTP/xmm/data/CCF/ -P {sas_ccfpath}'
    print(f'Downloading calibration data using the command:\n{cmd}')
    print('This may take a while...')
    time.sleep(3)
    result = subprocess.run(cmd, shell=True)

    return result

def install_sas(repo='NASA',sas_version='21.0.0'):
    """
    !!WARNING!! EXPERIMENTAL!
    No guarentees this will work.
    Only tested with Ubuntu v. 20 and 22
    """

    tar_file = f'sas_{sas_version}-'

    if repo == 'NASA':
        base_path = f'https://heasarc.gsfc.nasa.gov/FTP/xmm/software/sas/{sas_version}/'
    elif repo == 'ESA':
        base_path = f'https://sasdev-xmm.esac.esa.int/pub/sas/{sas_version}/'
    else:
        raise Exception(f"Repository '{repo}' not recognized. Use either 'NASA' or 'ESA'.")
        

    system = platform.system()
    
    if system == 'Linux':
        base_path = base_path+f'{system}/'
        output = subprocess.run(['lsb_release','-d'],capture_output=True,text=True)
        outlist = output.stdout.split()
        distribution = outlist[1]
        version = outlist[2]
        if distribution == 'Ubuntu':
            if '18.04' in version:
                version = '18.04'
            elif '20.04' in version:
                version = '20.04'
            elif '22.04' in version:
                version = '22.04'
            else:
                raise Exception(f"Ubuntu version {version} not recognized. Must be either '18.04', '20.04', or '22.04'.")
            dis_ver = f'{distribution}{version}'
            base_path = base_path+f'{dis_ver}/'
            tar_file = tar_file+f'{dis_ver}.tgz'
            download_link = base_path+tar_file
            print(base_path)
            print(tar_file)
            print(download_link)
            #test_link = 'https://heasarc.gsfc.nasa.gov/FTP/xmm/software/sparsebundle/components/DockerfileSAS'
            subprocess.run(['wget',download_link])
            subprocess.run(['tar','zxf',tar_file])
            subprocess.run(['./install.sh'],shell=True)
        else:
            raise Exception(f"Linux distribution {distribution} not supported.")

def generate_PPS_filename(obsid=None,instname=None,
                          expflag=None,expno=None,
                          product_type=None,datasubsetno=None,
                          sourceno=None,extension=None):
    """
    Function for generating a filename for downloading PPS files.

    PPS data product filenames take the 27.3 character form:

        POOOOOOOOOODDUEEETTTTTTSXXX.FFF

    P           The character P, to identify the files as a PPS product file

    OOOOOOOOOO  (obsid) Observation identifier 

    DD          (instname) Data source identifier (instrument name)

    U           (expflag) Exposure flag (1 character = S (sched),
                U (unsched), X (not applicable))

    EEE         (expno) Exposure number within the instrument 
                observation (3 digits)

    TTTTTT      (product_type) Product type (6 characters)

    S           (datasubsetno) 0 or data subset number/character 
                (1 character, differentiates energy bands,
                OSWs, filters, orders etc.)

    XXX         (sourceno) Source number or slew step number (3 characters, hexadecimal).
                It is set to 000 in source products from EPIC-pn Timing mode.

    FFF         (extension) File format (3 characters)

    If inputs are not given then a wildcard "*" character will 
    be inserted.

    """

    if not obsid: obsid = '*'
    if not instname: instname = '*'
    if not expflag: expflag = '*'
    if not expno: expno = '*'
    if not product_type: product_type = '*'
    if not datasubsetno: datasubsetno = '*'
    if not sourceno: sourceno = '*'
    if not extension: extension = '*'


    filename = f'P{obsid}{instname}{expflag}{expno}{product_type}{datasubsetno}{sourceno}.{extension}'

    re.sub(r'\*+', '*', filename)

    return filename


    
