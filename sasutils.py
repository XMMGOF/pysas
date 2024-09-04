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
import os, sys, subprocess, shutil, glob, tarfile, gzip, time

# Third party imports
from astroquery.esa.xmm_newton import XMMNewton

# Local application imports
# from .version import VERSION, SAS_RELEASE, SAS_AKA
from .logger import TaskLogger as TL

# Third party imports

# Local application imports

def download_data(odfid,data_dir,
                  level='ODF',repo='esa',logger=None,
                  encryption_key=None,proprietary=False,
                  credentials_file=None,**kwargs):
    """
    --Not intended to be used by the end user. Internal use only.--
    --Recommended to use calibrate_odf or basic_setup instead.--

    Downloads, or copies, data from chosen repository. 

    Will silently overwrite any preexisting data files and remove any existing
    pipeline products. Will create directory structure in 'data_dir' for odf.

    Inputs:

        --odfid:          (string): ID of ODF in string format.

        --data_dir:  (string/path): Path to directory where the data will be 
                                    downloaded. Automatically creates directory
                                    data_dir/odfid.
                                    Default: 'pwd', returns the current directory.

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
            logger.log('info', f'Downloading {odfid}, level {levl} into {obs_dir}')
            print(f'\nDownloading {odfid}, level {levl} into {obs_dir}. Please wait ...\n')
            XMMNewton.download_data(odfid, level=levl,
                                    prop=proprietary,
                                    credentials_file=credentials_file,
                                    **kwargs)
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
            encryption_file = glob.glob(os.path.join(data_dir,f'*{odfid}*'))
            if len(encryption_file) == 0:
                encryption_file = glob.glob(os.path.join(data_dir,'*key*'))
            if len(encryption_file) > 1:
                logger.log('error', 'Multiple possible encryption key files. Specify encryption key file.')
                raise Exception('Multiple possible encryption key files.')
            if len(encryption_file) == 0:
                encryption_file = 'None'
            if os.path.isfile(encryption_file[0]):
                logger.log('info', f'File with encryption key found: {encryption_file}')
            else:
                print('File decryption failed. No encryption key found.')
                print(f'Regular file with the encryption key needs to be placed in: {data_dir}')
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
            print(f'Regular file with the encryption key needs to be placed in: {data_dir}')
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
    print('This may take a while.')
    time.sleep(3)
    result = subprocess.run(cmd, shell=True)

    return result
