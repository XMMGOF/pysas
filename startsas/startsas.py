# ESA (C) 2000-2021
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

# startsas.py
"""startsas.py

         After Heasoft and SAS initialisations, the quickest way to start a
         working session with SAS is to run

                    startsas odfid=0122700101

         where the value given to the 'odfid' parameter is the ODF ID of an
         existing XMM-Newton Observation you want to work with.

         The startsas program will understand you want to get such Observation
         from the XMM-Newton Science Archive. The download will be done by
         means of a special version of the Python module 'astroquery' prepared
         to work with XMM-Newton data.

         By default data are obtained at level 'ODF' which provides only
         the raw observation data. The parameter named 'level' can be used to
         select an alternate level 'PPS', which will download the raw data and
         the output products resulting from processing such data with the
         XMM-Newton Pipeline.

         For level 'ODF', the file <odfid>.tar.gz is downloaded to a
         directory of your choice. You may set such directory by means of the
         parameter 'workdir'. If such directory does not exist, it is created
         new. If you do not set a specific working directory, it is assumed
         your working directory is where you started with startsas. Once the
         tar file <odfid>.tar.gz file is downloaded, it is unpacked into a
         subdirectory named <odfid>, within your working directory.

         For level 'PPS', all Pipeleine products are placed in <odfid>/pps.
         A link to the html including the Observation Summary
         (P<odfid>OBX000SUMMAR0000.HTM) is printed out.

         Instead of 'odfid', we can use the parameters 'sas_ccf' and 'sas_odf'
         to take already existing 'ccf.cif' and SAS summary files, as

             startsas sas_ccf=<path>/ccf.cif sas_odf=<path>/*SUM.SAS

         The program understands you want to use these ccf.cif and SAS
         summary file, in directory <path>,  to define SAS_CCF and SAS_ODF for
         subsequent SAS commands.

         <path> must be an absolute path (begin with '/').

         Before using effectively these files the program will check them to see
         whether

         . The PATH keyword is written inside the SAS summary file
         . The mandatory file MANIFEST.NNNNNN (where NNNNNN is the AMS
         extraction number) is present

         to ensure they belong to a real ODF.

         For the 'ccf.cif' file, it only checks for its existence.

         'sas_ccf' and 'sas_odf' are mandatory subparamaters which means that
         if they appear in the command line or arg ument list, both must be present.

         The startsas.log can be now written in 'workdir' by setting the SAS_TASKLOGDIR
         environment variable to it, before running startsas, e.g. 

         export SAS_TASKLOGDIR=`pwd`/<my_workdir>
         startsas odfid=0122700101 workdir=my_workdir

         For SAS_TASKLOGDIR to  work, the directory must exist prior to run startsas.

         By default the log file is created in mode 'append' so subsequent runs of startsas
         will og their messages to the file. However, we can change this behaviour by 
         setting the environment variable SAS_TASKLOGFMODE="w", to create a new log file
         each time startsas is run. 
"""


# Standard library imports
import os, sys, subprocess, shutil, glob

# Third party imports
# (se below for astroquery)

# Local application imports
from .version import VERSION, SAS_RELEASE, SAS_AKA
#from pysas.wrapper import Wrapper as wrap
from pysas.logger import TaskLogger as TL


__version__ = f'startsas (startsas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

logger = TL('startsas')

def run(iparsdic):
    """
    iparsdic is a dictionary which includes all the paramaters parsed from
    the command line (or entered in a list) merged with those read from the
    parameter file,  to be used to run the task.

    The task produces a log file named 'startsas.log' which is found in 
    the directory from where the task is started. 
    The log file always collect the maximum of debugging information.
    However, the level of information shown in the console si modulated
    via the verbosity option  '-V/--verbosity.
    """

    logger.log('warning', f'Executing {__file__} {iparsdic}')

    # Checking LHEASOFT, SAS_DIR and SAS_CCFPATH

    lheasoft = os.environ.get('LHEASOFT')
    if not lheasoft:
        logger.log('error', 'LHEASOFT is not set. Please initialise HEASOFT')
        raise Exception('LHEASOFT is not set. Please initialise HEASOFT')
    else:
        logger.log('info', f'LHEASOFT = {lheasoft}')

    sasdir = os.environ.get('SAS_DIR')
    if not sasdir:
        logger.log('error', 'SAS_DIR is not defined. Please initialise SAS')
        raise Exception('SAS_DIR is not defined. Please initialise SAS')
    else:
        logger.log('info', f'SAS_DIR = {sasdir}') 

    sasccfpath = os.environ.get('SAS_CCFPATH')
    if not sasccfpath:
        logger.log('error', 'SAS_CCFPATH not set. Please define it')
        raise Exception('SAS_CCFPATH not set. Please define it')
    else:
        logger.log('info',f'SAS_CCFPATH = {sasccfpath}')


    # Where are we?
    startdir = os.getcwd()
    logger.log('info',f'startsas was initiated from {startdir}')

    if iparsdic['workdir'] == 'pwd':
        workdirectory = startdir
    else:
        workdirectory = iparsdic['workdir']
        
        # If workdir was not given as an absolute path, it is interpreted
        # as a subdirectory of startdir
        if workdirectory[0] != '/':
            workdirectory = os.path.join(startdir, workdirectory)
        elif workdirectory[:2] == './':
            workdirectory = os.path.join(startdir, workdirectory[2:])
        
        logger.log('info', f'Work directory = {workdirectory}')

        if not os.path.isdir(workdirectory):
            logger.log('warning', f'{workdirectory} does not exist. Creating it!')
            os.mkdir(workdirectory)
            logger.log('info', f'{workdirectory} has been created!')
        
        os.chdir(workdirectory)
        logger.log('info', f'Changed directory to {workdirectory}')

        print(f'''

        Starting SAS session
    
        Working directory = {workdirectory}
    
        ''')

    # Identify the download level
    level = iparsdic['level']
    if level != 'ODF' and level != 'PPS':
        logger.log('error', 'ODF request level is undefined!')
        raise Exception('ODF request level is undefined!')
    else:
        logger.log('info', f'Will download ODF with level {level}') 


    # Processing odfid
    if iparsdic['odfid'] and level == 'ODF':
        
        if iparsdic['sas_ccf'] or iparsdic['sas_odf']:
            logger.log('error', 'Parameter odfid icompatible with sas_ccf and sas_odf')
            raise Exception('Parameter odfid icompatible with sas_ccf and sas_odf')

        odfid = iparsdic['odfid']
        logger.log('info', 'Requesting odfid  = {} to XMM-Newton Science Archive\n'.format(iparsdic['odfid']))
        print('Requesting odfid  = {} to XMM-Newton Science Archive\n'.format(iparsdic['odfid']))
        
        # Download the odfid from XMM-Newton, using astroquery

        from astroquery.esa.xmm_newton import XMMNewton
        logger.log('info', f'Downloading {odfid}, level {level}')
        print(f'\nDownloading {odfid}, level {level}. Please wait ...\n')
        XMMNewton.download_data(odfid, level=level)

        tarfile = odfid + '.tar.gz'
        
        # Check that the tar.gz file has been downloaded
        try:
            os.path.exists(tarfile)
            logger.log('info', f'{tarfile} downloaded.') 
        except FileExistsError:
            logger.log('error', f'File {tarfile} is not present. Not downloaded?')
            print(f'File {tarfile} is not present. Not downloaded?')
            sys.exit(1)
        
        # Creates subdirectory odfid to move and unpack the odfid.tar.gz file
        if os.path.exists(os.path.join(workdirectory, odfid)):
            logger.log('info', f'Removing existing directory {odfid} ...')
            print(f'\n\nRemoving existing directory {odfid} ...')
            shutil.rmtree(os.path.join(workdirectory, odfid))
        logger.log('info', f'Creating directory {odfid} ...')
        print(f'\nCreating directory {odfid} ...')
        os.mkdir(odfid)
        
        # Moves odfid.tar.gz file to odfid
        shutil.move(tarfile, odfid)
        
        # Changes dir to odfid
        os.chdir(odfid)
        
        # Untars the odfid.tar.gz file
        cmd = ['tar', 'zxf', tarfile]
        logger.log('info', f'Unpacking {tarfile} ...')
        print(f'\nUnpacking {tarfile} ...\n')
        rc = subprocess.run(cmd)
        if rc.returncode != 0:
            logger.log('error', 'tar file extraction failed')
            raise Exception('tar file extraction failed')
        else:
            logger.log('info', f'{tarfile} extracted successfully!')

        os.remove(tarfile)
        logger.log('info', f'{tarfile} removed')

        # Obtains the name of the file with ext TAR
        TARFILE = glob.glob('*.TAR')
        cmd = ['tar', 'xf', TARFILE[0]]
        # Untars the TAR file
        logger.log('info', f'Unpacking {TARFILE[0]} ...')
        print(f'Unpacking {TARFILE[0]} ...')
        rc = subprocess.run(cmd)
        
        os.remove(TARFILE[0])
        logger.log('info', f'{TARFILE[0]} removed')

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
        logger.log('info', f'Setting SAS_ODF = {os.getcwd()}')
        print(f'\nSetting SAS_ODF = {os.getcwd()}')
        os.environ['SAS_ODF'] = os.getcwd()

        # Change back workdirectory (we made it absolute if not so)
        os.chdir(workdirectory)

        # Run cifbuild
        if iparsdic['cifbuild_opts']:
            cifbuild_opts = iparsdic['cifbuild_opts']
            cifbuild_opts_list = cifbuild_opts.split(" ") 
            cmd = ['cifbuild']
            cmd = cmd + cifbuild_opts_list
            logger.log('info', f'Running cifbuild with {cifbuild_opts} ...')
            print(f'\nRunning cifbuild with {cifbuild_opts} ...')
        else:
            cmd = ['cifbuild']
            logger.log('info', f'Running cifbuild...')
            print(f'\nRunning cifbuild...')
        
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
        fullccfcif = os.path.join(workdirectory, 'ccf.cif')
        logger.log('info', f'Setting SAS_CCF = {fullccfcif}')
        print(f'\nSetting SAS_CCF = {fullccfcif}')
        os.environ['SAS_CCF'] = fullccfcif

        # Now run odfingest
        if iparsdic['odfingest_opts']:
            odfingest_opts = iparsdic['odfingest_opts']
            odfingest_opts_list = odfingest_opts.split(" ")
            cmd = ['odfingest'] 
            cmd = cmd + odfingest_opts_list
            logger.log('info', f'Running odfingest with {odfingest_opts} ...')
            print(f'\nRunning odfingest with {odfiingest_opts} ...')
        else:
            cmd = ['odfingest']
            logger.log('info','Running odfingest...') 
            print('\nRunning odfingest...')
        
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
        fullsumsas = os.path.join(workdirectory, sumsas[0])
        os.environ['SAS_ODF'] = fullsumsas
        logger.log('info', f'Setting SAS_ODF = {fullsumsas}')
        print(f'\nSetting SAS_ODF = {fullsumsas}')

        # sasodf is the dirname of fullsumsas + odfid. It will be used below.
        sasodf = os.path.join(os.path.dirname(fullsumsas), odfid)

        # Check that the SUM.SAS file has the right PATH keyword
        with open(fullsumsas) as inf:
            lines = inf.readlines()
        for line in lines:
            if 'PATH' in line:
                key, path = line.split()
                if path != sasodf:
                    logger.log('error', f'SAS summary file PATH mismatchs {sasodf}')
                    raise Exception(f'SAS summary file PATH mismatchs {sasodf}')
                else:
                    logger.log('info', f'Summary file PATH keyword matches {sasodf}')
                    print(f'\nWarning: Summary file PATH keyword matches {sasodf}')

        print(f'''\n\n
        SAS_CCF = {fullccfcif}
        SAS_ODF = {fullsumsas}
        \n''')

    # Process odfid with level=PPS
    elif iparsdic['odfid'] and level == 'PPS':
        
        if iparsdic['sas_ccf'] or iparsdic['sas_ccf']:
            logger.log('error', 'Parameter odfid icompatible with sas_ccf and sas_odf')
            raise Exception('Parameter odfid icompatible with sas_ccf and sas_odf')

        odfid = iparsdic['odfid']
        logger.log('info', 'Requesting odfid  = {} to XMM-Newton Science Archive\n'.format(iparsdic['odfid']))
        print('Requesting odfid  = {} to XMM-Newton Science Archive\n'.format(iparsdic['odfid']))

        # Download the odfid from XMM-Newton, using astroquery

        from astroquery.esa.xmm_newton import XMMNewton
        logger.log('info', f'Downloading {odfid}, level {level}.')
        print(f'\nDownloading {odfid}, level {level}. Please wait ...\n')
        XMMNewton.download_data(odfid, level=level)

        tarfile = odfid + '.tar'

        # Check that the tar file has been downloaded
        try:
            os.path.exists(tarfile)
            logger.log('info', f'Tarfile {tarfile} downloaded')
        except FileExistsError:
            logger.log('error', f'File {tarfile} is not present. Not downloaded?')
            print(f'File {tarfile} is not present. Not downloaded?')
            sys.exit(1)

        # If does not exist, it creates subdirectory odfid 
        # to move and unpack the odfid.tar file
        odfid_dir = os.path.join(workdirectory, odfid)
        if not os.path.exists(odfid_dir):
            os.mkdir(odfid_dir)
            logger.log('info',f'Directory {odfid_dir} created')
        else:
            logger.log('info', f'Directory {odfid_dir} already exists. Not removed!')

        os.chdir(workdirectory)
        logger.log('info', f'Changed directory to {workdirectory}')


        # Untars the odfid.tar.gz file
        cmd = ['tar', 'xf', tarfile]
        logger.log('info', f'Unpacking {tarfile} ...')
        print(f'\nUnpacking {tarfile} ...\n')
        rc = subprocess.run(cmd)
        if rc.returncode != 0:
            logger.log('error', 'tar file extraction failed')
            raise Exception('tar file extraction failed')
        else:
            logger.log('info', 'Tar file {tarfile} extracted successfully')

        os.remove(tarfile)
        logger.log('info', f'{tarfile} removed')

        ppsdir = os.path.join(workdirectory, odfid, 'pps')
        ppssumhtml = 'P' + odfid + 'OBX000SUMMAR0000.HTM'
        ppssumhtmlfull = os.path.join(ppsdir, ppssumhtml)
        ppssumhtmllink = 'file://' + ppssumhtmlfull
        logger.log('info', f'PPS products can be found in {ppsdir}')
        print(f'\nPPS products can be found in {ppsdir}\n\nLink to Observation Summary html: {ppssumhtmllink}')

    # Process sas_ccf and sas_odf parameters
    elif iparsdic['sasfiles'] == 'yes':
        if iparsdic['odfid']:
            logger.log('error', 'Parameters sas_ccf and sas_odf incompatible with parameter odfid') 
            raise Exception('Parameters sas_ccf and sas_odf incompatible with parameter odfid')
        
        sasccf = iparsdic['sas_ccf']
        sasodf = iparsdic['sas_odf'] 

        if sasccf[0] != '/':
            raise Exception(f'{sasccf} must be defined with absolute path')

        if sasodf[0] != '/':
            raise Exception(f'{sasodf} must be defined with absolute path')

        try:
            os.path.exists(sasccf)
            logger.log('info', f'{sasccf} is present')
        except FileExistsError:
            logger.log('error', f'File {sasccf} not found.')
            print(f'File {sasccf} not found.')
            sys.exit(1)

        try:
            os.path.exists(sasodf)
            logger.log('info', f'{sasodf} is present')
        except FileExistsError:
            logger.log('error', f'File {sasodf} not found.')
            print(f'File {sasodf} not found.')
            sys.exit(1)
        
        os.environ['SAS_CCF'] = sasccf
        logger.log('info', f'SAS_CCF = {sasccf}')
        print(f'SAS_CCF = {sasccf}')

        if 'SUM.SAS' not in iparsdic['sas_odf']:
            logger.log('error', '{} does not refer to a SAS SUM file'.format(iparsdic['sas_odf']))
            raise Exception('{} does not refer to a SAS SUM file'.format(iparsdic['sas_odf']))
        
        # Check that the SUM.SAS file PATH keyword points to a real ODF directory
        with open(sasodf) as inf:
            lines = inf.readlines()
        for line in lines:
            if 'PATH' in line:
                key, path = line.split()
                if not os.path.exists(path):
                    logger.log('error', f'Summary file PATH {path} does not exist.')
                    raise Exception(f'Summary file PATH {path} does not exist.')
                MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                if not os.path.exists(MANIFEST[0]):
                    logger.log('error', f'Missing {MANIFEST[0]} file in {path}. Missing ODF components?')
                    raise Exception(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components?')
        
        os.environ['SAS_ODF'] = sasodf
        logger.log('info', f'SAS_ODF = {sasodf}')
        print(f'SAS_ODF = {sasodf}')

