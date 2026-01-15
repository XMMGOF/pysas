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
# error.py
#
"""error.py

The class Error is an interface to the SAS task saserrstr
 
Instances of class Error, can have the following parameters:

client     : The task that produces the error
msgLayer   : The task layer where the error is originated. 
             See below for the keys in dict msgLayer.
msgLevel   : The importance level of the message. See below for the keys in dict msgLevel.
code       : The code of the message: warning, error, fatal.
msg        : The error message itself.
outMessage : The output message.

Below several possible use cases of class Error for different arguments:

Error( client=name, msgLayer='AppMsg', msgLevel='SilentMsg', msg='Message from the SAS (silent)' ).message()

Error( client=name, msgLayer='AppMsg', msgLevel='SparseMsg', msg='Message from the SAS (sparse)' ).message()

Error( client=name, msgLayer='AppMsg', msgLevel='VerboseMsg', msg='Message from the SAS (verbose)' ).message()

Error( client=name, msgLayer='AppMsg', msgLevel='NoisyMsg', msg='Message from the SAS (noisy)' ).message()

print('-------------------------------------------------------------')

Error( client=name, code='warningCode', msg='Warning message' ).warning()

Error( client=name, code='errorCode', msg='Error message' ).error()

Error( client=name, code='fatalCode', msg='Fatal message' ).fatal()
"""

# Standard library imports
import sys, subprocess

# Third party imports

# Local application imports


class Error:
    """Error Class definitions"""

    msgLayerValues = {
        'UIMsg'     : '1',
        'MetaMsg'   : '2',
        'AppMsg'    : '3',
        'AppLibMsg' : '4',
        'LibMsg'    : '5',
        'CoreMsg'   : '6',
        'KernelMsg' : '7',
        }

    msgLevelValues = {
        'SilentMsg'    : '0',
        'SparseMsg'    : '1',
        'VerboseMsg'   : '2',
        'NoisyMsg'     : '3',
        }

    def __init__(self, client=None, msgLayer=None, msgLevel=None, code=None, msg=None, outMessage=None):
        self.client         = client
        if msgLayer:
           self.msgLayer    = self.msgLayerValues[msgLayer]
        if msgLevel:
           self.msgLevel    = self.msgLevelValues[msgLevel]
        self.code           = code
        self.msg            = msg
        self.outMessage     = outMessage

    def message(self):
        opt = '-m'
        outMessage = ['saserrstr' , opt , self.client, self.msgLayer , self.msgLevel , self.msg ]
        # Spawn 'outMessage' command to the shell through 'saserrstr'
        returncode = subprocess.call(outMessage) 
        if(returncode):
          self.code = "InternalError" 
          self.msg  = "SAS::error::warning failed" 
          self.fatal()
	
    def warning(self):
        opt = '-w'
        outMessage = ['saserrstr', opt, self.client, self.code, self.msg ]
        # Spawn 'outMessage' command to the shell through 'saserrstr'
        returncode = subprocess.call(outMessage)
        if(returncode):
          self.code = "InternalError" 
          self.msg  = "SAS::error::warning failed" 
          self.fatal()
	
    def error(self):
        opt = '-e'
        outMessage = ['saserrstr', opt, self.client, self.code, self.msg ]
        # Spawn 'outMessage' command to the shell through 'saserrstr'
        returncode = subprocess.call(outMessage)
        sys.exit(1)

    def fatal(self):
        opt = '-f'
        outMessage = ['saserrstr', opt, self.client, self.code, self.msg ]
        # Spawn 'outMessage' command to the shell through 'saserrstr'
        returncode = subprocess.call(outMessage)
        sys.exit(1)
