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

Defines a template SASTask Python class
based on the ABC (Abstract Base Classes) module.

All SAS Pyhton based tasks will derive from SASTask.
However, they will not instantiate it but instead a
subclass of it, MyTask. There could be other similar
to MyTask, but for the time being we simply define this one.

The methods defined in SASTask (decorated with
the @abstractmethod decorator), must be redefined in MyTask.
Otherwise, the instantiation of MyTask will fail.
By particularizing the methods defined in SASTask
we ensure all SAS Python based tasks have unified methods.

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

Let be mytask a new Python based task. It will be an instance of MyTask
 
mytask = MyTask('mytask', args)
  
where args is a list that includes all arguments we pass to mytask
in the command line. As we will see this is not the only way to
pass arguments to the task.

mytask mandatory files and directories will be created by pkgmaker,
a Python script responsible of creating any type of SAS task, including
also those based on C++, Fortran 90 and Perl.

The specific Python code for mytask, and possibly othe auxiliary Python
code which might be required by mytask to operate, will be placed all
within the directory structure of mytask.

A typical invocation of mytask could be of the form

mytask param0=value0 [param1=value1] ... [Options]

where param0, param1, etc, are any task parameters defined in
a file named mytask.par, and [Options] are any of the generic options
common to all SAS task. If a parameter, e.g. param0, is defined in
mytask.par as 'mandatory', it must be present in the command line.

Of course, the presence of some of the Options, will trigger specific
immediate actions: e.g. the option -v or --version will immediately
show the version of mytask and exit.
 
Arguments of the form param=value can alternate with Options. 
The only requirement is that Options with a value, e.g. -V 4, must be
adjacent.

Methods defined by SASTask (identified so far):

1. readparfile: Read and loads the task parameter file.

2. processargs : Parses arguments and acts accordingly. 

3. runtask: Executes the task with the proper arguments.

MyTask will actually implement these three methods.

The readparfile method used class paramXmlInfoReader from
param.py module.

The processargs methdos uses the class ParseArgs based on argparse.
 
The runtask method uses class RunTask.
"""

# Standard library imports
from abc import ABC, abstractmethod
import os

# Third party imports

# Local application imports
from pysas.param import paramXmlInfoReader
from pysas.parser import ParseArgs
from pysas.runtask import RunTask


# Class SASTask

class SASTask(ABC):
    """This is the abstract base class for all SAS Python tasks"""

    def __init__(self, taskname, inargs):
        self.name = taskname
        self.inargs = inargs

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname} - {self.inargs})'

    @abstractmethod
    def readparfile(self):
        pass

    @abstractmethod
    def processargs(self):
        pass

    @abstractmethod
    def runtask(self):
        pass



class MyTask(SASTask):
    """
    Class MyTask is a children of SASTask which 
    implements all its abstract methods.

    In the class initialization, the task name and
    the input args to run it are passed from the 
    instatiation of MyTask. Task parameters as
    identified by the '=' sign are separated of 
    task options, to reorder them to avoid conflicts 
    at the time of parsing them.

    The instance method 'readparfile' gets a full
    picture of the task parameter file, receiving
    a bunch of information abouth subparameters and
    their relationship with its predecessors.

    The instance method 'processargs' performs the
    processing of any immediate options and filter out
    the legitimate and mandatory parameters so as
    they can be used in the ' runtask' instance method.
    """

    def __init__(self, taskname, inargs,logFile='DEFAULT'):
        super().__init__(taskname, inargs)
        self.taskname = taskname
        self.inargs = inargs
        self.logFile = logFile

        # Reorder self.inargs to group together all options and 
        # all args of type param=value, in that order.
        sasparams = []
        options = []
        for a in self.inargs:
            if '=' in a.split('=',1):
                sasparams.append(a)
            else:
                options.append(a)
        self.inargs = [*options, *sasparams]

    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname} - {self.inargs})'

    def readparfile(self):
        t = paramXmlInfoReader(self.taskname)
        t.xmlParser()
        self.allparams = t.allparams
        self.mandparams = t.mandpar
        self.mainparams = t.mainparams
        self.parmap = t.parmap
        self.mandpar_dict = t.mandpar_dict
        self.rev_mandpar_dict = t.rev_mandpar_dict
        self.rev_mandpar_string_dict = t.rev_mandpar_string_dict


    def processargs(self):
        p = ParseArgs(self.taskname, self.inargs)
        p.taskparser()
        # tparams is a list with the left hands of param=value, if any
        self.tparams = p.tparams

        # Execute options which require immediate action
        # Options which are for environment (which are cumulative) 
        # do not change default False value of Exit.
        self.Exit = p.procopt()
        if self.Exit:
            return self.Exit

        # 1st check: Whether or not parameters in inargs are defined in the parameter file
        for p in self.tparams:
            if p.strip() not in self.allparams.keys():
                raise Exception(f'Parameter {p} is not defined in the parameter file')

 
        # 2nd check: Whether we have mandatory parameters and subparameters
        for k, v in self.rev_mandpar_dict.items():
            if k.strip() in v and k.strip() not in self.tparams:
                raise Exception(f'Missing, at least, mandatory parameter {k}')
            if k not in v:
                for p in self.tparams:
                    if p in v:
                        implicit = 'yes'
                        for c in v:
                            if c not in self.tparams:
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
                            self.inargs.append(newinarg)
                            if k in self.tparams:
                                print(f'Warning: No need to include {k}. Assumed {newinarg}')
                            break
                    elif p in v and k not in self.tparams:
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
	    # all the parameters) and the argsdic to pass all task  
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

        # argsdic is a dictionary with the pairs param, value 
        # as entered from the command line from 'param=value'

        argsdic = {}
        for a in self.inargs:
            if '=' in a:
                k, v = a.split('=', 1)
                argsdic[k] = v

        # Load defaults with all parameters default values.
        # Use dictionary method 'setdefault' to set the value for a given key;
        # here the key is 'default'.
        # If the value for that key is not defined, fill it with ''.

        defaults = {}
        for a in self.allparams.values():
            defaults[a['id']] = a.setdefault('default', '')

        # 3rd Check: Whether any subparameter is set in argsdic or not.
        # We assume the parent is boolean ('yes'/'no').

        for a in argsdic.keys():
            for k, v in implicitparams.items():
                if a in v:
                    #print(f'parent = {k}')
                    if self.allparams[k]['default'] == 'no':
                        defaults[k] = 'yes'
                    elif self.allparams[k]['default']  == 'yes':
                        defaults[k] = 'no'
                    #print(k, a,  defaults[k])
                    break

        # Merge argsdic onto parsdic. Those values set in command line, 
        # from argsdic, will overwrite the defaults obtained from the par file, 
        # from parsdic. The resulting dictionary, self.iparsdic, is what we will 
        # pass to method runtask.

        self.iparsdic = {**defaults, **argsdic}


    def runtask(self):
        if self.Exit:
            return self.Exit
        r = RunTask(self.taskname, self.iparsdic,self.logFile)
        r.run()
