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
#
# 
"""parser.py

The parser module implements the class ParseArgs which includes
all the methods required to parse any arguments entered either 
via the command line or through a list.

The class initialization  checks for the existence of SAS_PATH.
Then it populates the pysaspkgs list with all packages below pysas.
This is used to get the version of the package.

The instance method taskparser uses module argparse to define the
two types of arguments supported: options and parameters.
Options can be classified into two categories: immediate action and
execution modifiers. Options are accessed via the a single or a 
double '-'. All SAS tasks allow for a given set of specific options.
Parameters must include the '='symbol to separate the name and its
value. Within the value there can be more '=' symbols. 

Method procopt either executes the immediate options or sets the 
environment variables that modify the execution of the task.

Task parameters entered are returned in list tparams.
"""


# Standard library imports
import os
import sys
import subprocess
import argparse
import pkgutil
from importlib import import_module
from contextlib import suppress

# Third party imports

# Local application imports
from pysas.param import paramXmlInfoReader

class ParseArgs:
    def __init__(self, taskname, arglist):
        self.taskname = taskname
        self.arglist = arglist

        # Before any further processing check that SAS_PATH is defined
        sas_path = os.environ.get('SAS_PATH')
        if not sas_path:
            raise Exception('SAS_PATH is undefined. SAS not initialised?')

        saspath = sas_path.split(':')
        sasdev = saspath[0]
        pysasdevdir = os.path.join(sasdev, 'lib', 'python', 'pysas')
        pysaspkgs = []

        # pysaspkgs will list all Python packages
        for p in pkgutil.walk_packages([pysasdevdir]):
            if p.ispkg:
                pysaspkgs.append(p.name)

        # If taskname is not in pysaspkgs it is a non Python SAS task
        # then its version must be obtained differently.
        # If it is a Python task, version is available from __version__ object
        if self.taskname in pysaspkgs:
            m = import_module('pysas.' + self.taskname + '.' + self.taskname)
            self.version = m.__version__
        else:
            # Do not use --version because some SAS perl tasks like epchain do not 
            # accept this option but only -v
            cmd = self.taskname + ' -v'
            self.version = subprocess.check_output(cmd, shell=True, text=True)

    # This is the task parser constructor
    def taskparser(self):

        # Define the parser. Not need to make it class wide.
        parser = argparse.ArgumentParser(
            prog = self.taskname,
            description = 'Parses command parameters and options',
            add_help = False
        )

        # Add the options with add_argument
        #
        # Two groups:
        # a) Immediate action:
        #    If the option is present, it must be processed immediately and exit.
        #    These are: -v/--version, -d/--dialog, -m/--manpage, -h/--help, -p/--param.

        parser.add_argument('-v', '--version', dest='version', action='store_true', default=False)
        parser.add_argument('-d', '--dialog', dest='dialog', action='store_true',default=False)
        parser.add_argument('-m', '--manpage', dest='manpage', action='store_true',default=False)
        parser.add_argument('-h', '--help', dest='help', action='store_true', default=False)
        parser.add_argument('-p', '--param', dest='param', action='store_true', default=False)

        # b) Modifiers:
        #    If the option is present, it modifies the
        #    execution of the command and/or the environment, usually
        #    by setting an environment variable.
        #    These are: -V/--verbosity (SAS_VERBOSITY), -c/--noclobber
        #    (SAS_CLOBBER), -a/--ccfpath (SAS_CCFPATH),
        #    -i/--ccf (SAS_CCF), -o/--odf (SAS_ODF), -f/--ccffiles,
        #    -w/--warning, -t/--trace.

        parser.add_argument('-V',
                            '--verbosity',
                            dest='verbosity',
                            type=int,
                            default=4,
                            choices=range(11),
                            action='store')

        parser.add_argument('-c',
                            '--noclobber',
                            dest='noclobber',
                            action='store_true',
                            default=False)

        parser.add_argument('-a',
                            '--ccfpath',
                            dest='sas_ccfpath',
                            type=str,
                            nargs=1,
                            action='store')

        parser.add_argument('-i',
                            '--ccf',
                            dest='sas_ccf',
                            action='store',
                            nargs=1)

        parser.add_argument('-o',
                            '--odf',
                            dest='sas_odf',
                            type=str,
                            nargs=1)

        parser.add_argument('-f',
                            '--ccffiles',
                            dest='ccffiles',
                            type=str,
                            nargs=1)

        parser.add_argument('-w',
                            '--warning',
                            dest='warning',
                            type=str,
                            nargs=1,
                            action='store')

        parser.add_argument('-t',
                            '--trace',
                            dest='trace',
                            action='store_true',
                            default=False)

        # To give access to real SAS style params in the form param=value,
        # we add a positional string argument, which can be repeated any
        # number of times, but always contiguously.
        # Notice that this is already achieved due to the initial processing
        # made in self.arglist, where these strings have been grouped together
        # at the end of self.arglist. We call this argument pvpairs.

        parser.add_argument('pvpairs', type=str, nargs='*')

        # Apply parse_args method to parser. Result is put into parsedargs.
        # The parsedargs object is not a dictionary but can be shown as such
        # with function vars().

        self.parsedargs = parser.parse_args(self.arglist)

        #print(self.parsedargs)
        #print(f'vars(self.parsedargs)          = \n{vars(self.parsedargs)}')
        #print(f'self.parsedargs.pvpairs        = {self.parsedargs.pvpairs}')


        # Put into list tparams only the real parameters entered in the command line
        # as pairs param=value
        self.tparams = []
        pp = ''
        for p in self.parsedargs.pvpairs:
            a, b = p.split('=', 1)
            self.tparams.append(a)

        #print(f'self.tparams                   = {self.tparams}')



    # Depending on the options entered, performs actions
    def procopt(self):

        # Exit is set to False
        Exit = False

        # Define header text for option -h/--help
        usage = f"""
        Usage: {self.taskname} [Options] param0=value0 [param1=value1] ...

        Options:
        -a | --ccfpath <dir1>:<dir2>...   Sets SAS_CCFPATH to <dir1>:<dir2>...
        -c | --noclobber                  Set SAS_CLOBBER=0
        -d | --dialog                     Launchs task GUI
        -f | --ccffiles <f1> <f2> ...     CCF files
        -h | --help                       Shows this message, display param file contents and exits
        -i | --ccf <cif>                  Sets SAS_CCF=<cif> (ccf.cif)
        -m | --manpage                    Opens web browser with task documentation
        -o | --odf <sumfile>              Sets SAS_ODF to SAS summary file
        -p | --param                      List of all available task parameters with default values
        -t | --trace                      Trace task execution
        -V | --verbosity <level>          Sets verbosity level and sets SAS_VERBOSITY
        -v | --version                    Shows task name and version, and exits
        -w | --warning [code|n]           Set warning code to [code|n]

        Parameters:
        param0=value0                     A mandatory parameter. If not present, exits.
        [param1=value1]                   An optional parameter. If not present, it might have a default value
        ...
        """


        # Process options entered in command line
        #
        # Options version(--version, -v), help(--help, -h), param(--param, -p)
        # dialog(--dialog, -d) and manpage(--manpage, -m) are exclusive.  
        # Only one can be present and will set Exit to True. 
        # When procopt is executed on the instance of ParseArgs (e.g. p), as
        # p.procopt() the return Exit determines wheter to return immediately or
        # not. If Exit is set to True, the method will return immediately.
        #
        # Some options entered in self.arglist will launch special SAS tasks
        # designed only to provide  specific result. These are:
        #
        # -d/--dialog   => sasdialog to launch task GUI
        # -m/--manpage  => sashelp to show HTML doc in the default web browser
        #


        # Version:
        if self.parsedargs.version:
            print(f'{self.version}')
            Exit = True
        # Help:
        if self.parsedargs.help:
            print(usage)
            pf = paramXmlInfoReader(self.taskname)
            pf.xmlParser()
            pf.printHelp()
            Exit  = True
        if self.parsedargs.param:
            pf = paramXmlInfoReader(self.taskname)
            pf.xmlParser()
            pf.printHelp()
            Exit = True
        # dialog (GUI)
        if self.parsedargs.dialog:
            print(f'\nLaunching {self.taskname} GUI ...')
            cmd = ['sasdialog', self.taskname]
            self.runext(cmd)
            Exit = True
        # manpage (HTML doc)
        if self.parsedargs.manpage:
            print(f'\nLaunching web browser to display HTML documentation on {self.taskname} ...')
            cmd = ['sashelp', 'doc=' + self.taskname]
            self.runext(cmd)
            Exit = True

        if Exit:
            return Exit

        # 
        # Excluding warning, which I do not know how to handle yet, 
        # the next five options are accumulative, if they are present they change 
        # environment variables. 
        # They do not return control  to caller.
        #
        # sas_ccfpath
        if self.parsedargs.sas_ccfpath:
            print('SAS_CCFPATH = {}'.format(str(self.parsedargs.sas_ccfpath[0])))
            os.environ['SAS_CCFPATH'] = str(self.parsedargs.sas_ccfpath[0])
        # noclobber
        if self.parsedargs.noclobber:
            os.environ['SAS_CLOBBER'] = '0'
            print('SAS_CLOBBER = {}'.format(str(os.environ.get('SAS_CLOBBER'))))
        # sas_ccf
        if self.parsedargs.sas_ccf:
            print('SAS_CCF = {}'.format(str(self.parsedargs.sas_ccf[0])))
            os.environ['SAS_CCF'] = str(self.parsedargs.sas_ccf[0])
        # sas_odf
        if self.parsedargs.sas_odf:
            print('SAS_ODF = {}'.format(str(self.parsedargs.sas_odf[0])))
            os.environ['SAS_ODF'] = str(self.parsedargs.sas_odf[0])
        # ccffiles
        if self.parsedargs.ccffiles:
            print('CCF files = {}'.format(str(self.parsedargs.ccffiles[0])))
        # warning
        if self.parsedargs.warning:
            warning = self.parsedargs.warning
        # verbosity
        if self.parsedargs.verbosity:
            os.environ['SAS_VERBOSITY'] = str(self.parsedargs.verbosity)
            if str(os.environ.get('SAS_VERBOSITY')) != '4':
                print('SAS_VERBOSITY = {}'.format(str(os.environ.get('SAS_VERBOSITY'))))

        return Exit

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname} - {self.arglist})'

    def runext(self, runcmd):
        self.runcmd = runcmd
        if self.runcmd == None:
            return
        with subprocess.Popen(self.runcmd, bufsize=1, shell=False, text=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT, universal_newlines=True) as p:
            for line in p.stdout:
                print(line, end='')
        #if p.returncode != 0:
        #    raise subprocess.CalledProcessError(p.returncode, p.args)
