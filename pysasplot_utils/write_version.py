#! /usr/bin/env python
#
# ESA (C) 2000-{creationyear}
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
# write_version.py
#
# Writes version.py from $SAS_DIR/SasVersion.h.
# Values are written as constants to be used later on by importing them
# from version.py.
# The version of the package is also written as VERSION

import os, re
from datetime import date

# current date and year in string format
today = date.today()
creationyear = today.year
creationdate = today.strftime('%d-%b-%Y')
creationdate_chlog = today.strftime('%Y-%m-%d')


# readSasVersion reads the SAS release information from SasVersion.h

def readSasVersion(sas_dir):

    sasversion_h = {}
    sasversion_h_keys = [
            'sas_compilation_date',
            'sas_compilation_host',
            'sas_compilation_user',
            'sas_platform',
            'sas_release',
            'sas_aka'
            ]
    with open(os.path.join(sas_dir, 'SasVersion.h')) as inf:
        lines = inf.readlines()

    for key in sasversion_h_keys:
        for line in lines:
            if key in line:
                # [^"] = match any characterxs excluding "
                # ([^"]*) = match any text excluding "
                # '"([^"]*)"' = any text between " and "
                k = re.findall(r'"([^"]*)"', line)
                sasversion_h[key] = k[0]
    return sasversion_h


# main
if __name__ == '__main__':
    sas_dir = os.environ.get('SAS_DIR')
    if sas_dir == None:
        print('Error: sasver : SAS_DIR is undefined')
        sys.exit()
    
    pkgdir = '../../'

    with open(os.path.join(pkgdir, 'VERSION')) as f:
        v = f.readline().strip()

# reads the SasVersion.h

    svh = readSasVersion(sas_dir)

# writes version.py taking version.py.in as template

    with open('version.py.in') as inf, open('version.py', 'w') as outf:
        template = inf.read()
        outf.write(template.format(
            creationdate=creationdate,
            creationyear=creationyear,
            release=svh['sas_release'], 
            aka=svh['sas_aka'], 
            date=svh['sas_compilation_date'], 
            host=svh['sas_compilation_host'],
            user=svh['sas_compilation_user'],
            platform=svh['sas_platform'],
            version=v)
            )
    inf.close()
    outf.close()
