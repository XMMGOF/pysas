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

"""wrapper.py

This is a wrapper for SAS tasks which are not based on Python.
This code can be used from Jupyter Notebooks and ipython interactive
sessions
"""

# Standard library imports
import subprocess

# Third party imports

# Local application imports
from pysas.sastask import MyTask


class Wrapper:
    """Class Wrapper

    Method run instantiates MyTask to read the parameter file,
    process the input arguments and run the task.
    """
    def __init__(self, taskname, inargs,logFile='DEFAULT'):
        self.taskname = taskname
        self.inargs = inargs
        self.logFile = logFile

    def run(self):
        t = MyTask(self.taskname, self.inargs,self.logFile)
        t.readparfile()
        t.processargs()
        t.runtask()
