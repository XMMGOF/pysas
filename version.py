# version.py 
#
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
#

# pySAS version
VERSION = '2.2.6'

import subprocess, os, sys

def get_sas_version():
    sas_dir = os.environ.get('SAS_DIR')
    if sas_dir == None:
        print('Error: SAS_DIR is undefined')
        sys.exit()
    SAS_RELEASE          = ''
    SAS_AKA              = ''
    SAS_COMPILATION_DATE = ''
    SAS_COMPILATION_HOST = ''
    SAS_COMPILATION_USER = ''
    SAS_PLATFORM         = ''
    SAS_COMMIT_ID        = ''
    cmd = 'sasversion'
    # Start the subprocess
    process = subprocess.Popen(cmd, 
                               bufsize=1,
                               shell=True,
                               text=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)

    # Log stdout and stderr in real-time
    # For non-Python SAS tasks the stout and stderr are combined
    output = []
    for line in process.stdout:
        output.append(f"{line.strip()}")

    # Wait for the process to complete and get the return code
    process.wait()

    for line in output:
        if line.startswith('SAS release'):
            SAS_RELEASE = line.split(':')[1].lstrip()
            if '-' in SAS_RELEASE:
                # If SAS_RELEASE uses dashes (v22>=)
                SAS_AKA = SAS_RELEASE.split('-')[0]
                SAS_COMMIT_ID = SAS_RELEASE.split('-')[1]
            else:
                # If SAS_RELEASE uses underscores (v21<=)
                SAS_AKA = SAS_RELEASE.split('_')[0]
        if line.startswith('Compiled on'):
            SAS_COMPILATION_DATE = line.split(':', 1)[1].lstrip()
        if line.startswith('Compiled by'):
            temp = line.split(':')[1].lstrip()
            try:
                SAS_COMPILATION_USER = temp.split('@')[0]
                SAS_COMPILATION_HOST = temp.split('@')[1]
            except Exception:
                pass
        if line.startswith('Platform'):
            SAS_PLATFORM = line.split(':')[1].lstrip()
    return_list = [SAS_RELEASE,
                   SAS_AKA,
                   SAS_COMPILATION_DATE,
                   SAS_COMPILATION_HOST,
                   SAS_COMPILATION_USER,
                   SAS_PLATFORM,
                   SAS_COMMIT_ID]
    return return_list