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
    The SASTask class replaces the Wrapper class from
    wrapper.py.

    Inputs:
    (required)
        - taskname   : Name of the task to be run.
        - inargs     : Input arguments.
    (optional)
        - logfilename: Designated log file name. Will be used instead
                        of "{taskname}.log". Useful for putting all 
                        output from multiple tasks into the same file.
        - tasklogdir : (default: cwd) Directory where to write the log 
                        file.
                        Priority of defaults for task_logdir
                        1. tasklogdir (passed in to function)
                        2. SAS_TASKLOGDIR (envirnment variable)
                        3. cwd (final default)

        - output_to_terminal : (default: True) Output will be written to 
                                the terminal.
        - output_to_file     : (default: False) Output will be written to 
                                a log file.


    For pySAS v2.0 the inargs has switched to fundamentally being a dictionary.
    If a list is passed in it will be converted into a dictionary.
                                
    In the class initialization, the task name and
    the input args to run it are processed. 
    Task parameters as identified by the '=' sign are 
    separated of task options, to reorder them to 
    avoid conflicts at the time of parsing them.

    The instance method 'readparfile' gets a full
    picture of the task parameter file, receiving
    a bunch of information abouth subparameters and
    their relationship with its predecessors.

    The instance method 'processargs' performs the
    processing of any immediate options and filter out
    the legitimate and mandatory parameters so as
    they can be used in the 'run' instance method.
    """

    def __init__(self, taskname, 
                 inargs = {}, 
                 logfilename = None, 
                 tasklogdir  = None,
                 output_to_terminal = True, 
                 output_to_file     = False,
                 logger = None):
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

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname}, {self.inargs})'

    def readparfile(self):
        """
        Reads the parameter file (taskname.par) for the task. Returns 
        various lists and dictionaries.
            - allparams : Dictionary { parameter: {attributes} }
            - mandpar   : List of all mandatory parameters/subparameters
            - mainparams: List of main paramaters
            - parmap    : Dictionary { pname: [ subparameters ...], ...}
            - mandpar_dict: Dictionary, key = mandatory subparamater, 
                            value=its parent parameter
            - rev_mandpar_dict: Dictionary, keys = parent paramater, 
                                value = list of all mandatory subparameters
            - rev_mandpar_string_dict: Dictionary, keys = parent parameter type 'string'
                                       value = list of alternatives
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
        for p in self.argsdic.keys():
            if p.strip() not in self.allparams.keys():
                raise Exception(f'Parameter {p} is not defined in the parameter file')

        # 2nd check: Whether we have mandatory parameters and subparameters
        for k, v in self.rev_mandpar_dict.items():
            if k.strip() in v and k.strip() not in self.argsdic.keys():
                raise Exception(f'Missing, at least, mandatory parameter {k}')
            if k not in v:
                for p in self.argsdic.keys():
                    if p in v:
                        implicit = 'yes'
                        for c in v:
                            if c not in self.argsdic.keys():
                                implicit = 'no'
                                raise Exception(f'Besides {p}, mandatory subparameter {c} must also be present')
                        if implicit == 'yes':
                            defval = self.allparams[k]['default']
                            if self.allparams[k]['type'] == 'string':
                                self.rev_mandpar_string_dict[k].remove(defval)
                                alt = self.rev_mandpar_string_dict[k].pop()
                            elif self.allparams[k]['type'] == 'bool' and defval == 'no':
                                alt = 'yes'
                            elif self.allparams[k]['type'] == 'bool' and defval == 'yes':
                                alt = 'no'
                            newinarg = k + '=' + alt
                            self.argsdic[k] = alt
                            if k in self.argsdic.keys():
                                self.logger.warning(f'No need to include {k}. Assumed {newinarg}')
                            break
                    elif p in v and k not in self.argsdic.keys():
                        raise Exception(f'Mandatory sub-parameter {p} requires {k} be present')

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

        # At this point in inargs there should be only optional modifiers
        # and true task parameters

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

        # 3rd Check: Whether any subparameter is set in self.argsdic or not.
        # We assume the parent is boolean ('yes'/'no').

        for a in self.argsdic.keys():
            for k, v in implicitparams.items():
                if a in v:
                    #print(f'parent = {k}')
                    if self.allparams[k]['default'] == 'no':
                        defaults[k] = 'yes'
                    elif self.allparams[k]['default']  == 'yes':
                        defaults[k] = 'no'
                    #print(k, a,  defaults[k])
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
        self.paramXmlInfo.printHelp()
    
    def run(self):
        """
        Method run

        If taskname is a Python module, therefore it is in the
        list pysaspkgs, then import it and pass to its run
        function the dictionary of parameters, iparsdic

        If taskname is not a Python SAS task, there will not be
        a run function, so we will invoke subprocess
        """
        self.logger.debug(f'Running {self.taskname}')
        self.logger.debug(f'Reading parameter file.')
        self.readparfile()
        self.logger.debug(f'Processing input arguments')
        self.processargs()
        if self.Exit:
            self.logger.debug(f'Exit called by processargs')
            return self.Exit
        sas_path = os.environ.get('SAS_PATH')

        if not sas_path:
            raise Exception('SAS_PATH is undefined! SAS not initialised?')

        pysaspkgs = []

        my_resources = importlib.resources.files("pysas")
        for line in (my_resources / "pysaspkgs").read_text().splitlines():
            pysaspkgs.append(line)

        # For Python based SAS tasks
        if self.taskname in pysaspkgs:
            self.logger.debug(f'Using Python based SAS task: {self.taskname}')
            # Add the environment options to iparsdic
            self.logger.debug(f'Adding environment options to iparsdic')
            self.iparsdic['options'] = dict(self.env_options)
            temp_dict = {}
            for k, v in self.env_options.items():
                match(k):
                    case 'SAS_CCFPATH' | 'SAS_CCF' | 'SAS_ODF' | 'SAS_VERBOSITY':
                        temp_dict[k] = os.getenv(k)
                        self.logger.debug(f'Storing previous setting of {k}={temp_dict[k]}')
                        os.environ[k] = v
                        self.logger.debug(f'Temporarely changing {k} to {v}')
                    case 'SAS_CLOBBER' | 'CCF_files' | 'WARNING' | 'TRACE':
                        # This needs to be handled by the individual task
                        pass
                    case _:
                        pass
            
            self.logger.debug(f'Importing module {self.taskname}')
            m = import_module('pysas.' + self.taskname + '.' + self.taskname)

            self.logger.debug(f'Running module {self.taskname}')
            m.run(self.iparsdic)
            
            # Reset Environment variables
            for k, v in temp_dict.items():
                match(k):
                    case 'SAS_CCFPATH' | 'SAS_CCF' | 'SAS_ODF' | 'SAS_VERBOSITY':
                        self.logger.debug(f'Resetting {k} to {temp_dict[k]}')
                        if temp_dict[k] is None:
                            os.environ.pop(k,None)
                        else:
                            os.environ[k] = temp_dict[k]
                    case 'SAS_CLOBBER' | 'CCF_files' | 'WARNING' | 'TRACE':
                        # This needs to be handled by the individual task
                        pass
                    case _:
                        pass
            
        # For all other SAS tasks
        else:
            # Build a list of parameters based on iparsdic
            self.logger.debug(f'Using non-Python based SAS task: {self.taskname}')
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
        This method is here for legacy reasons since some Python
        based SAS tasks still create a MyTask object.
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
    Class SASTask is a child of MyTask and has access to all
    of the methods in MyTask. It's only purpose is to act as
    a placeholder for legacy code.
    """
    def __init__(self, taskname, inargs):
        super().__init__(taskname,inargs)
        warn(
             """
             The class SASTask has been depricated. Use MyTask instead.
             ex: from pysas.sastask import MyTask
             """)