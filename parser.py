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

The class initialization checks for the existence of SAS_PATH.
Then it populates the pysaspkgs list with all packages below pysas.
This is used to get the version of the package.

The instance method optparser uses module argparse to define the
two types of arguments supported: options and parameters.
Options can be classified into two categories: immediate action and
execution modifiers. Options are accessed via the a single or a 
double '-'. All SAS tasks allow for a given set of specific options.
Parameters must include the '='symbol to separate the name and its
value. Within the value there can be more '=' symbols. 

Method procopt either executes the immediate options or sets the 
environment variables that modify the execution of the task.
"""


# Standard library imports
import os
import sys
import subprocess
import argparse
from importlib import import_module
import importlib.resources

# Third party imports

# Local application imports
from pysas.param import paramXmlInfoReader
from pysas.logger import get_logger
from pysas import sas_cfg

class ParseArgs:
    """
    For pySAS v2.0 it is now assumed that the input arguments are
    passed in as a dictionary.
    """
    def __init__(self, taskname, argdict, logger = None):
        self.taskname = taskname
        self.argdict = argdict
        if logger is None:
            # By default will only output to terminal
            self.logger = get_logger('ParseArgs')
        else:
            # Use logger that was passed in
            self.logger = logger

        # Before any further processing check that SAS_PATH is defined
        sas_path = os.environ.get('SAS_PATH')
        if not sas_path:
            raise Exception('SAS_PATH is undefined. SAS not initialised?')

        pysaspkgs = []

        my_resources = importlib.resources.files("pysas")
        for line in (my_resources / "pysaspkgs").read_text().splitlines():
            pysaspkgs.append(line)

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
    def optparser(self):
        """
        This parses the 'options' from the input.
        """

        # Define the parser. No need to make it class wide.
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

        # Get default verbosity
        default_verbosity = sas_cfg.get_setting("verbosity")

        parser.add_argument('-V',
                            '--verbosity',
                            dest='verbosity',
                            type=int,
                            nargs=1,
                            default=default_verbosity,
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

        # Apply parse_args method to parser with the options being passed in. 
        # Result is put into parsedargs. The parsedargs object is not a 
        # dictionary but can be shown as such with function vars().

        self.parsedargs = parser.parse_args([self.argdict['options']])

        #print(self.parsedargs)
        #print(f'vars(self.parsedargs)          = \n{vars(self.parsedargs)}')
        #print(f'self.parsedargs.pvpairs        = {self.parsedargs.pvpairs}')

    # If these options are present, will execute a command and return Exit
    def exe_options(self):
        """
        Method to execute options or parameters that 
        require immediate action.

        These include options that execute the command 
        and exit. These are: 

            version(--version, -v)
            help(--help, -h)
            param(--param, -p)
            dialog(--dialog, -d)
            manpage(--manpage, -m)

        Returns 'Exit' which if True will send the exit 
        command up the chain. If False, then pySAS will 
        continue to execute.

        # Process options entered in command line
        #
        # Options version(--version, -v), help(--help, -h), param(--param, -p)
        # dialog(--dialog, -d) and manpage(--manpage, -m) are exclusive.  
        # Only one can be present and will set Exit to True. 
        # When exe_options is executed on the instance of ParseArgs (e.g. p), as
        # p.exe_options() the return Exit determines wheter to return immediately or
        # not. If Exit is set to True, the method will return immediately.
        #
        # Some options entered in self.argdict will launch special SAS tasks
        # designed only to provide specific result. These are:
        #
        # -d/--dialog   => sasdialog to launch task GUI
        # -m/--manpage  => sashelp to show HTML doc in the default web browser
        #

        """

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

        # Version:
        if self.parsedargs.version:
            print(f'{self.version}')
            Exit = True
        # Help:
        if self.parsedargs.help:
            print(usage)
            pf = paramXmlInfoReader(self.taskname, logger = self.logger)
            pf.xmlParser()
            pf.printHelp()
            Exit  = True
        if self.parsedargs.param:
            pf = paramXmlInfoReader(self.taskname, logger = self.logger)
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

    # If these options are present, they will be returned for handling
    def env_options(self):
        """
        Method to collect options that set environment variables 
        and then continue running the SAS task. These are:

               -V/--verbosity (SAS_VERBOSITY)
               -c/--noclobber (SAS_CLOBBER)
               -a/--ccfpath (SAS_CCFPATH)
               -i/--ccf (SAS_CCF)
               -o/--odf (SAS_ODF)
               -f/--ccffiles
               -w/--warning
               -t/--trace
        """
        # return_options is a dictionary to hold set options
        return_options = {}
        env_options_list = []

        # The options are accumulative, if they are 
        # present they are collected into a list and
        # returned to MyTask. 

        # sas_ccfpath
        if self.parsedargs.sas_ccfpath:
            envar_val = str(self.parsedargs.sas_ccfpath[0])
            env_options_list.append(f'-a {envar_val}')
            return_options['SAS_CCFPATH'] = envar_val
            self.logger.info(f'SAS_CCFPATH = {envar_val}')
        # noclobber
        if self.parsedargs.noclobber:
            envar_val = False
            env_options_list.append('-c')
            return_options['SAS_CLOBBER'] = envar_val
            self.logger.info(f'SAS_CLOBBER = {envar_val}')
        # sas_ccf
        if self.parsedargs.sas_ccf:
            envar_val = str(self.parsedargs.sas_ccf[0])
            env_options_list.append(f'-i {envar_val}')
            return_options['SAS_CCF'] = envar_val
            self.logger.info(f'SAS_CCF = {envar_val}')
        # sas_odf
        if self.parsedargs.sas_odf:
            envar_val = str(self.parsedargs.sas_odf[0])
            env_options_list.append(f'-o {envar_val}')
            return_options['SAS_ODF'] = envar_val
            self.logger.info(f'SAS_ODF = {envar_val}')
        # ccffiles
        if self.parsedargs.ccffiles:
            envar_val = str(self.parsedargs.sas_odf[0])
            env_options_list.append(f'-f {envar_val}')
            return_options['CCF_files'] = envar_val
            self.logger.info(f'CCF files = {envar_val}')
        # warning
        if self.parsedargs.warning:
            envar_val = str(self.parsedargs.warning[0])
            env_options_list.append(f'-w {envar_val}')
            return_options['WARNING'] = envar_val
            self.logger.info(f'WARNING = {envar_val}')
        # trace
        if self.parsedargs.trace:
            envar_val = True
            env_options_list.append('-t')
            return_options['TRACE'] = envar_val
            self.logger.info(f'Trace = {envar_val}')
        # verbosity
        if self.parsedargs.verbosity:
            envar_val = str(self.parsedargs.verbosity[0])
            env_options_list.append(f'-V {envar_val}')
            return_options['SAS_VERBOSITY'] = envar_val
            self.logger.info(f'SAS_VERBOSITY = {envar_val}')

        # Add the list of all options to return_options
        return_options['env_options'] = " ".join(env_options_list)

        return return_options

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname} - {self.argdict})'

    def runext(self, runcmd):
        self.runcmd = runcmd
        if self.runcmd == None:
            return
        with subprocess.Popen(self.runcmd, bufsize=1, shell=False, text=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT, universal_newlines=True) as p:
            for line in p.stdout:
                print(line, end='')
        #if p.returncode != 0:
        #    raise subprocess.CalledProcessError(p.returncode, p.args)
