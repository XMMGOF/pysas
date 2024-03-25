# ESA (C) 2000-2020
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

# sasver.py

import os
from .version import * 

__version__ = f'sasver (sasver-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

'''
Shows release and information about the XMM-Newton Science Analysis System (SAS).
'''

def run(args):
    sas_dir = os.environ.get('SAS_DIR')
    if sas_dir == None:
        print('Error: sasver : SAS_DIR is undefined')
        sys.exit()


    sas_path = os.environ.get('SAS_PATH')
    sas_ccfpath = os.environ.get('SAS_CCFPATH')
    sas_ccf = os.environ.get('SAS_CCF')
    sas_odf = os.environ.get('SAS_ODF')
    sas_mmod = os.environ.get('SAS_MEMORY_MODEL')

    print(f'''
    XMM-Newton SAS - release and build information

    SAS release: {SAS_RELEASE}-{SAS_AKA}
    Compiled on: {SAS_COMPILATION_DATE}
    Compiled by: {SAS_COMPILATION_USER}@{SAS_COMPILATION_HOST}
    Platform   : {SAS_PLATFORM}

    SAS-related environment variables set:

    ''')
    print(f'SAS_DIR        = {sas_dir}')
    print(f'SAS_PATH       = {sas_path}')
    print(f'SAS_CCFPATH    = {sas_ccfpath}') if sas_ccfpath != None else None
    print(f'SAS_CCF        = {sas_ccf}') if sas_ccf != None else None
    print(f'SAS_ODF        = {sas_odf}') if sas_odf != None else None

