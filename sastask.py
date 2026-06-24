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
"""sastask.py

All stand alone SAS tasks can be called by using MyTask.

As any other SAS task, Python based tasks are used to
perform specific data processing jobs.

The task invocation command may include several parameters
and generic options.

Parameters allow to set or to choose among specific task processing
options. SAS parameter syntax has the form param=value.
Mandatory parameters must be present in the command line.
Optional parameters might have a default value.
All task parameters with their properties
must be defined in a parameter file, which is unique for each task.
Such file provides for each paramater, its name, type (int, real,
boolean, string, etc), options (one or several choices), whether it is
mandatory or not, its default value if none is given, etc.
The parameter file is written in XML format.

Generic options, common to all SAS tasks, allow to handle
several features of the execution environment.
They can be expressed either with a single or with a double "-",
e.g. -v or --version (to show the task version and exit), -V or
--verbosity (to set the level of output verbosity between 0 and 10), etc.
Some of these options modify shell environment variables, e.g.
SAS_VERBOSITY is modified by the value given to --verbosity, etc.

Let be mytask a new SAS task. It will be an instance of MyTask
 
mytask = MyTask('mytask', args)
  
where args is a list that includes all arguments we pass to mytask
in the command line.

The specific Python code for mytask, and possibly other auxiliary Python
code which might be required by mytask to operate, will be placed all
within the directory structure of mytask.

A typical invocation of mytask could be of the form

MyTask('mytask', ['param0=value0','param1=value1', ... [Options]).run()

where param0, param1, etc, are any task parameters defined in
a file named mytask.par, and [Options] are any of the generic options
common to all SAS task. If a parameter, e.g. param0, is defined in
mytask.par as 'mandatory', it must be present.

Of course, the presence of some of the Options, will trigger specific
immediate actions: e.g. the option -v or --version will immediately
show the version of mytask and exit.
 
Arguments of the form param=value can alternate with Options. 
The only requirement is that Options with a value, e.g. -V 4, must be
adjacent.

Methods defined by MyTask (identified so far):

1. readparfile: Read and loads the task parameter file.

2. processargs: Parses arguments and acts accordingly. 

3. run: Executes the task with the proper arguments.

4. printHelp: Prints information about the task, equivalent to
              MyTask('mytask', ['-h']).run()

The readparfile method used class paramXmlInfoReader from
param.py module.

The processargs methods uses the class ParseArgs based on argparse.
"""

# Standard library imports
import os, numbers, subprocess
from importlib import import_module
import importlib.resources
from warnings import warn

# Third party imports

# Local application imports
from pysas.param import paramXmlInfoReader, SASParams
from pysas.parser import ParseArgs
from pysas.logger import get_logger

# Class MyTask
class MyTask:
    """
    Class for SAS tasks. 

    When a class instance is generated the corresponding parameter file is read. 
    If input arguments are passed in as a list or string then they are converted 
    into a dictionary, but input arguments are not processed until either 'run' 
    or 'processargs' is called.
    """    

    def __init__(self, taskname: str, 
                 inargs: dict | list | str = {}, 
                 logfilename: str = None, 
                 tasklogdir: str  = None,
                 output_to_terminal: bool = True, 
                 output_to_file: bool     = False,
                 logger = None):
        """
        Class constructor for MyTask.

        Parameters
        ----------
        taskname : str
            SAS task name.
        inargs : dict | list | str, optional
            SAS input arguments, by default {}.
        logfilename : str, optional
            Designated log file name. Useful for putting all output from 
            multiple tasks into the same file. By default "{taskname}.log".
        tasklogdir : str, optional
            Output directory for the log file, by default None.
            Priority of defaults for task_logdir
                1. tasklogdir (passed in)
                2. SAS_TASKLOGDIR (envirnment variable)
                3. cwd (final default)
        output_to_terminal : bool, optional
            Whether to print output to the terminal, by default True.
        output_to_file : bool, optional
            Whether to print output to file, by default False.
        logger : logger, optional
            Logger object, by default None.
        """
        self.taskname    = taskname
        self.inargs      = inargs
        self.logfilename = logfilename
        self.tasklogdir  = tasklogdir
        self.output_to_terminal = output_to_terminal
        self.output_to_file     = output_to_file
        
        # The logger object assigned here will only be used for log information
        # generated by pySAS. Log information generated by SAS tasks will not 
        # be controled by this logger object.
        # If a logger object was not passed in, then generate one
        if logger is None:
            if logfilename is None:
                # If no logfilename is given, then only write out to terminal
                self.logger = get_logger('MyTask',
                                         toterminal  = self.output_to_terminal)
            else:
                # If a logfilename was given then use that
                self.logger = get_logger('MyTask',
                                         toterminal  = self.output_to_terminal, 
                                         tofile      = self.output_to_file, 
                                         logfilename = self.logfilename,
                                         tasklogdir  = self.tasklogdir)
        else:
            # If a logger object was passed in, then use that.
            self.logger = logger

        # Check if inargs is a 'dict'.
        if isinstance(self.inargs, dict):
            # Insert empty string for options if not present
            if not 'options' in self.inargs.keys():
                self.inargs['options'] = ''
            for key in self.inargs.keys():
                # Safety check to see if a number was passed in.
                if isinstance(self.inargs[key], numbers.Number):
                        self.inargs[key] = str(self.inargs[key])
                # Convert booleans to 'yes' and 'no'
                if self.inargs[key] is bool:
                    if self.inargs[key]:
                        self.inargs[key] = 'yes'
                    else:
                        self.inargs[key] = 'no'

        # Check if inargs is a 'SASParams' dict.
        if isinstance(self.inargs, SASParams):
            argsdic = {}
            # Pull off the parameters that have been modified
            for k, v in self.inargs.inparams.items():
                if v[1]:
                    argsdic[k] = v[0]
            self.inargs = dict(argsdic)
            if not 'options' in self.inargs.keys():
                self.inargs['options'] = ''

        # Check if inargs is a single string. If it is, then split
        # it at all spaces. This is not fool proof!
        # ***STRONGLY*** NOT RECOMMENDED
        # (unless the input is very simple, such as '-h')
        if isinstance(self.inargs, str):
            self.inargs = self.inargs.split()

        # If inargs is a list, pick off all the options, then put
        # all other arguments into key-value pairs in the dictionary.
        if isinstance(self.inargs, list):
            argsdic = {}
            options = []
            for a in self.inargs:
                if '=' in a:
                    k, v = a.split('=', 1)
                    argsdic[k] = v
                else:
                    options.append(a)
            argsdic['options'] = " ".join(options)
            self.inargs = argsdic
        
        self.logger.debug(f'Reading parameter file.')
        self.readparfile()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname}, {self.inargs})'

    def readparfile(self):
        """
        Reads the parameter file (taskname.par) for the task. Adds various lists 
        and dictionaries to the object.
            - allparams : Dictionary { parameter: {attributes} }
            - mandpar   : List of all mandatory parameters/subparameters
            - mainparams: List of main paramaters
            - parmap    : Dictionary { pname: [ subparameters ...], ...}
            - mandpar_dict: Dictionary, key = mandatory subparamater, 
                            value=its parent parameter
            - rev_mandpar_dict: Dictionary, keys = parent paramater, 
                                value = list of all mandatory subparameters
            - rev_mandpar_string_dict: Dictionary, keys = parent parameter type 
                                       'string' value = list of alternatives
        """
        t = paramXmlInfoReader(self.taskname, logger = self.logger)
        t.xmlParser()
        self.allparams = t.allparams
        self.mandparams = t.mandpar
        self.mainparams = t.mainparams
        self.parmap = t.parmap
        self.mandpar_dict = t.mandpar_dict
        self.rev_mandpar_dict = t.rev_mandpar_dict
        self.rev_mandpar_string_dict = t.rev_mandpar_string_dict

    def processargs(self):
        """
        Processes the input arguments and compares them with the parameter file.

        Returns
        -------
        bool
            Whether to exit without running the task based on the inputs.

        Raises
        ------
        Exception
            Parameter '{p}' is not recognized!
        Exception
            Missing, at least, mandatory parameter "{p}".
        Exception
            If subparameter {p} is used then {parent} must be set to "{cond_par_val}"!
        Exception
            Missing mandatory subparameter {child}.
        """
        # Only if options are passed in
        if 'option' in self.inargs.keys():
            self.logger.warning("Input arguments include the key 'option'. Use 'options' (with an 's') instead.")
                    
        self.Exit = False
        if len(self.inargs['options']) > 0:
            pararg = ParseArgs(self.taskname, self.inargs, logger = self.logger)
            pararg.optparser()

            # Execute options which require immediate action
            self.Exit = pararg.exe_options()
            if self.Exit:
                return self.Exit
            
            # Deal with options that set environment variables
            # For non-Python based tasks these will be passed in
            # as part of the command for the subprocess call.
            # For Python based tasks, they will have to be handled
            # in the .run() function.
            env_opts = pararg.env_options()

        # Remove the options from argsdic
        self.argsdic = dict(self.inargs)
        self.argsdic.pop('options',None)

        # 1st check: Whether or not parameters in inargs are defined in the parameter file
        self.logger.debug('1st parameter check: Check if parameters are valid.')
        for p in self.argsdic.keys():
            if p.strip() not in self.allparams.keys():
                self.logger.error(f"Parameter '{p}' is not defined in the parameter file.")
                raise Exception(f"Parameter '{p}' is not recognized!")

        # 2nd check: Whether we have any missing mandatory **main** parameters
        self.logger.debug('2nd parameter check: Check if missing any mandatory main parameters.')
        for p in self.mainparams:
            if p in self.mandparams and p not in self.argsdic.keys():
                self.logger.error('Missing a mandatory main parameter.')
                raise Exception(f'Missing, at least, mandatory parameter "{p}".')

        # 3rd check: Check if any subparameters passed in have parents with a required value ("conditionally mandatory")
        # Check that parent value passed in matches required value
        # If parent not passed in then implicitly set the "default" parent value
        self.logger.debug('3rd parameter check: Check if any subparameters passed in have parents with a required value.')
        for p in self.argsdic.keys(): # Loop over all parameters passed in
            if self.allparams[p]['cond_mand']: # If the parameter is conditionally mandatory
                parent = self.allparams[p]['parent']
                cond_par_val = self.allparams[p]['cond_par_val'] # Required parent value
                if parent in self.argsdic.keys(): # If parent was passed in
                    parent_value = self.argsdic[parent].strip()
                    if parent_value != cond_par_val: # Check if passed in parent value matches required value
                        raise Exception(f'If subparameter {p} is used then {parent} must be set to "{cond_par_val}"!')
                else: # Parent not passed in
                    if self.allparams[parent]['default'] != cond_par_val:
                        self.logger.info(f'Parameter {parent} implied by {p}.')
                        self.logger.info(f'Setting {parent} default to "{cond_par_val}".')
                        self.allparams[parent]['default'] = cond_par_val

        # 4th check: Whether we are missing any conditionally mandatory **sub**parameters
        # Mandatory subparameters are dependant on the value of their parent parameter.
        self.logger.debug('4th parameter check: Check if any conditionally mandatory subparameters are missing.')
        for parent, children in self.rev_mandpar_dict.items(): # Loop over dictionary containing mandatory subparameters
            if parent in self.argsdic.keys(): # If parent was passed in
                for child in children:
                    cond_par_val = self.allparams[child]['cond_par_val']
                    parent_value = self.argsdic[parent].strip()
                    if parent_value == cond_par_val and child not in self.argsdic.keys():
                        # If parent value matches necessary condition and mandatory child not passed in
                        self.logger.error(f'When {parent} has value "{parent_value}", {child} is a mandatory subparameter.')
                        raise Exception(f'Missing mandatory subparameter {child}.')

        # If any subparameters of a parent parameter are set in the command
	    # line or the arguments list, the parent can not keep its default
	    # value. This is typical for parent parameters of type 'boolean' whose
	    # default value is 'no' (or 'yes'). In such a case the parent value must 
        # be changed to 'yes' (or 'no'). This is known as 'implicit' behaviour. 
	    # The previous code takes this behaviour in consideration but
	    # only for mandatory parameters. Now it will be applied to all
	    # parameters having subparameters. 
	    # The final effect of this will be visible below when merging 
	    # the parsdic (the dictionary with the default values for 
	    # all the parameters) and the inargs to pass all task  
	    # parameters for execution.

	    # Now compute a dictionary for all implicit parameters. 
	    # keys are the parent parameters having any subparameters and
	    # values are lists with these subparameters as elements.
	    # Neither the keys nor the elements of the lists can be mandatory.

        implicitparams = {}
        for d in self.parmap:
            for k, v in d.items():
                if v != [] and k not in self.mandparams:
                    for sp in v:
                        if sp not in self.mandparams:
                            implicitparams[k] = v

        # At this point in inargs there should be only true task parameters

        # Given that we know all parameters for the task (self.allparams) with
        # their default values, and the parameters and their values entered 
        # in the command line, let us produce now a single object with all 
        # parameters which we can pass to the module to run.

        # Load defaults with all parameters default values.
        # Use dictionary method 'setdefault' to set the value for a given key;
        # here the key is 'default'.
        # If the value for that key is not defined, fill it with ''.

        defaults = {}
        for a in self.allparams.values():
            defaults[a['id']] = a.setdefault('default', '')

        # 5th Check: Whether any non-mandatory subparameter is set in self.argsdic or not.
        # We assume the parent is boolean ('yes'/'no').
        self.logger.debug('5th parameter check: Check if any non-mandatory subparameter is set in self.argsdic or not.')
        for a in self.argsdic.keys():
            for k, v in implicitparams.items():
                if a in v:
                    # print(f'parent = {k}')
                    if self.allparams[k]['default'] == 'no':
                        defaults[k] = 'yes'
                    elif self.allparams[k]['default']  == 'yes':
                        defaults[k] = 'no'
                    # print(k, a,  defaults[k])
                    break

        # Return options that modify the environment to argdic
        self.env_options = {}
        if len(self.inargs['options']) > 0:
            for k, v in env_opts.items():
                if k == 'env_options':
                    self.argsdic['options'] = env_opts['env_options']
                else:
                    self.env_options[k] = v

        # Merge self.argsdic onto parsdic. Those values set in command line, 
        # from self.argsdic, will overwrite the defaults obtained from the par file, 
        # from parsdic. The resulting dictionary, self.iparsdic, is what we will 
        # pass to method runtask.

        self.iparsdic = {**defaults, **self.argsdic}

    def printHelp(self):
        """
        Wrapper for paramXmlInfo.printHelp. Prints information on the SAS task.
        """
        self.paramXmlInfo.printHelp()
    
    def run(self):
        """
        Runs the SAS task with the inputs stored in the dictionary iparsdic. 

        SAS tasks are invoked through a subprocess call.

        Returns
        -------
        bool
            Whether to exit without running the task based on the inputs.

        Raises
        ------
        EnvironmentError
            SAS_PATH is undefined!
        """
        
        
        self.logger.debug(f'Running {self.taskname}')
        self.logger.debug(f'Processing input arguments')
        self.processargs()
        if self.Exit:
            self.logger.debug(f'Exit called by processargs')
            return self.Exit
        sas_path = os.environ.get('SAS_PATH')

        if not sas_path:
            raise EnvironmentError('SAS_PATH is undefined! SAS not initialised?')

        # Build a list of parameters based on iparsdic
        self.logger.debug(f'Calling SAS task: {self.taskname}')
        cmd_list = []
        cmd_list.append(self.taskname)
        for k, v in self.iparsdic.items():
            if k == 'options':
                cmd_list.append(v)
                continue
            #Remove single quotes a double quotes from the python input parameters
            #SOC-SPR-7684
            if v.startswith("\"") or v.endswith("\""):
                v = v.replace('"','')
            if v.startswith("'") or v.endswith("'"):
                v = v.replace('\'','')
            
            if ' ' or '|' in v:
                singparam = k + '=' + "'"
                vc = v.split(' ')
                for i in range(len(vc)):
                    if i == len(vc) - 1:
                        singparam += vc[i]
                    else:
                        singparam += vc[i] + ' '
                singparam += "'"
                cmd_list.append(singparam)
            else:
                cmd_list.append(k + '=' + v)

        # Join all the parameters into a single command
        cmd = " ".join(cmd_list)
        if self.output_to_terminal:    
            print(f'Executing: \n{cmd}')

        try:
            logger = get_logger(self.taskname,
                                toterminal  = self.output_to_terminal, 
                                tofile      = self.output_to_file, 
                                logfilename = self.logfilename,
                                tasklogdir  = self.tasklogdir,
                                pylogger    = False)
                                # The only place pylogger should be set to false
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
            for line in process.stdout:
                logger.info(f"{line.strip()}")

            # Wait for the process to complete and get the return code
            process.wait()

        except Exception as e:
            logger.exception(f"An error occurred while running the command: {e}")

        if process.returncode == 0:
            logger.success(f"{self.taskname} executed successfully!")
        else:
            logger.critical(f"{self.taskname} failed!")

    def runtask(self):
        """
        This method is here for legacy reasons since some Python based SAS tasks 
        still create a MyTask object.
        e.g.
            # Instatntiate MyTask for the task
            t = MyTask('sasver', args)
            t.readparfile()
            t.processargs()
            t.runtask()
        """
        self.run()


class SASTask(MyTask):
    """
    Class SASTask is a child of MyTask and has access to all of the methods in 
    MyTask. It's only purpose is to act as a placeholder for legacy code.
    """
    def __init__(self, taskname, inargs):
        super().__init__(taskname,inargs)
        warn(
             """
             The class SASTask has been depricated. Use MyTask instead.
             ex: from pysas.sastask import MyTask
             """)