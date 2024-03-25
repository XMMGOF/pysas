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
""""runtask.py

It will run a Python task which has been coded into a module
named taskname.py.

It is assumed that taskname.py is part of package taskname which
will be placed below pysas.

iparsdic is a dictionary which includes all task parameters (as read
from par file) and their defaults except those modified in the
command line in the form param=value pairs.

iparsdic is passed to the task module, which will be taken in its
run function defined there.
"""

# Standard library imports
from importlib import import_module
import pkgutil
import os
import subprocess

# Third party imports

# Local application imports



class RunTask:
    """Class RunTask
    
    Parameters are entered in dictionary iparsdic.

    Method run executes the task depending on whether
    is a SAS native task or a Python task.
    
    """

    def __init__(self, taskname, iparsdic,logFile):
        self.taskname = taskname
        self.iparsdic = iparsdic
        self.logFile = logFile

    def run(self):
        """"Method run

            If taskname is a Python module, therefore it is in the
            list pysaspkgs, then import it and pass to its run
            function the dictionary of parameters, iparsdic

            If taskname is not a Python SAS task, there will not be
            a run function, so we will invoke subprocess
            """

        sas_path = os.environ.get('SAS_PATH')

        if not sas_path:
            raise Exception('SAS_PATH is undefined! SAS not initialised?')

        saspath = sas_path.split(':')

        sasdev = saspath[0]

        pysasdevdir = os.path.join(sasdev, 'lib', 'python', 'pysas')

        pysaspkgs = []

        for p in pkgutil.walk_packages([pysasdevdir]):
            if p.ispkg:
                pysaspkgs.append(p.name)


        if self.taskname in pysaspkgs:

            m = import_module('pysas.' + self.taskname + '.' + self.taskname)

            m.run(self.iparsdic)

        else:
            cmd = ''
            cmd += self.taskname + ' '
            for parval in self.iparsdic.items():
                k, v = parval
                #Remove single quotes a double quotes from the python input parameters
                #SOC-SPR-7684
                if v.startswith("\"") or v.endswith("\""):
                    v = v.replace('"','')
                if v.startswith("'") or v.endswith("'"):
                    v = v.replace('\'','')
                
                if ' ' or '|' in v:
                    cmd += k + '=' + "'"
                    vc = v.split(' ')
                    for i in range(len(vc)):
                        if i == len(vc) - 1:
                            cmd += vc[i]
                        else:
                            cmd += vc[i] + ' '
                    cmd += "' "
                else:
                    cmd += k + '=' + v + ' '
                
            print(f'Executing: \n{cmd}')
            self.p= None
            self.stdoutFile = None

            if self.logFile == 'DEFAULT':
                with subprocess.Popen(cmd,
                                      bufsize=1,
                                      shell=True,
                                      text=True,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,
                                      universal_newlines=True) as p:
                    for line in p.stdout:
                        print(line, end='')
            else:
                self.stdoutFile=open(self.logFile,'w')
                p = subprocess.Popen(cmd, 
                                     bufsize=1,
                                     shell=True,
                                     text=True,
                                     stdout=self.stdoutFile,
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True)                              
                p.wait()

            #for line in p.stdout:
            #    print(line, end='')                 
            
            if p.returncode != 0:
                if self.logFile != 'DEFAULT':
                    self.stdoutFile.close()
                raise subprocess.CalledProcessError(p.returncode, p.args)

            if self.logFile != 'DEFAULT':
                self.stdoutFile.close()
