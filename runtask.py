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
import importlib.resources
import os, sys
import subprocess
# import time

# Third party imports

# Local application imports

from pysas.logger import get_logger


class RunTask:
    """
    Class RunTask
    
    Parameters are entered in dictionary iparsdic.

    Method run executes the task depending on whether
    is a SAS native task or a Python task.
    
    """

    def __init__(self, taskname, iparsdic, 
                 logFile = 'DEFAULT', 
                 output_to_terminal = True, 
                 output_to_file = False):
        self.taskname    = taskname
        self.iparsdic    = iparsdic
        self.logFile     = logFile
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file

    def run(self):
        """
        Method run

        If taskname is a Python module, therefore it is in the
        list pysaspkgs, then import it and pass to its run
        function the dictionary of parameters, iparsdic

        If taskname is not a Python SAS task, there will not be
        a run function, so we will invoke subprocess
        """

        sas_path = os.environ.get('SAS_PATH')

        if not sas_path:
            raise Exception('SAS_PATH is undefined! SAS not initialised?')

        pysaspkgs = []

        my_resources = importlib.resources.files("pysas")
        for line in (my_resources / "pysaspkgs").read_text().splitlines():
            pysaspkgs.append(line)

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

            try:
                logger = get_logger(self.taskname,
                                    toterminal = self.output_to_terminal, 
                                    tofile = self.output_to_file, 
                                    logfilename = self.logFile)
                # time.sleep(0.5)
                # Start the subprocess
                process = subprocess.Popen(cmd, 
                                           bufsize=1,
                                           shell=True,
                                           text=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)

                # Log stdout and stderr in real-time
                # For non-Python SAS tasks the stout and stderr are combined
                for line in process.stdout:
                    logger.info(f"{line.strip()}")
                for line in process.stderr:
                    logger.info(f"{line.strip()}")

                # Wait for the process to complete and get the return code
                process.wait()

                if process.returncode == 0:
                    logger.success(f"{self.taskname} executed successfully!")
                else:
                    logger.critical(f"{self.taskname} failed!")

            except Exception as e:
                logger.exception(f"An error occurred while running the command: {e}")

