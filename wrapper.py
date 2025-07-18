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

This file is only here for legacy reasons. Its only purpose
is to point to the MyTask class in sastask.py.
"""

# Standard library imports
from warnings import warn

# Third party imports

# Local application imports
from pysas.sastask import MyTask

class Wrapper:
    """Class Wrapper

    This class is only here for legacy reasons. Its only purpose
    is to point to the MyTask class in sastask.py.

    Method run instantiates MyTask and calls 'run' from MyTask.
    """
    def __init__(self, taskname, inargs, 
                 logfilename = None, 
                 tasklogdir  = None,
                 output_to_terminal = True, 
                 output_to_file     = False):
        self.taskname    = taskname
        self.inargs      = inargs
        self.logfilename = logfilename
        self.tasklogdir  = tasklogdir
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file
        warn(
             """
             The wrapper class has been depricated. Use MyTask instead.
             ex: 
                 from pysas.sastask import MyTask
             instead of
                 from pysas.wrapper import Wrapper
             """)

    def run(self):
        MyTask(self.taskname, self.inargs, 
               logfilename = self.logfilename, 
               tasklogdir  = self.tasklogdir,
               output_to_terminal = self.output_to_terminal, 
               output_to_file     = self.output_to_file
               ).run()
