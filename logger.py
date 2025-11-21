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


# Standard library imports
import copy
import logging
import os
import sys
from pathlib import Path

# Third party imports
from loguru import logger
# This cleans up any loguru loggers that
# might be hanging around.
logger.remove()

# Local application imports
from pysas import sas_cfg

# Functions

def get_logger(taskname: str, 
               toterminal  = True, 
               tofile      = False, 
               logfilename = None, 
               tasklogdir  = None,
               pylogger    = True):
    """
    Function to get a loguru logger object.

    Inputs:
    (required)
        - taskname   : Name of the task to be run. By default will
                       name log file "{taskname}.log"
    (optional)
        - toterminal : (default: True) Output will be written to 
                        the terminal.
        - tofile     : (default: False) Output will be written to 
                        a log file.
        - logfilename: Designated log file name. Will be used instead
                       of "{taskname}.log". Useful for putting all 
                       output from multiple tasks into the same file.
        - tasklogdir : (default: cwd) Directory where to write the log 
                       file.
                       Priority of defaults for task_logdir
                         1. tasklogdir (passed in to function)
                         2. SAS_TASKLOGDIR (envirnment variable)
                         3. cwd (final default)
        - pylogger   : True: Use logger settings for Python logging
                       False: Use logger settings for subprocess logging
                       Only set to 'False' in sastask.py -> MyTask.run()
                       when running a non Python SAS task using 
                       subprocess.
    """
    task_logger = copy.deepcopy(logger)
    
    # SAS_TASKLOGDIR allows to set the directory for the logging file
    # Priority of defaults for task_logdir
    #   1. tasklogdir (passed in to function)
    #   2. SAS_TASKLOGDIR (envirnment variable)
    #   3. cwd (final default)
    sas_tasklogdir = os.getenv('SAS_TASKLOGDIR')

    if (tasklogdir and os.path.isdir(tasklogdir)):
        task_logdir = Path(tasklogdir)
    else:
        if(sas_tasklogdir and os.path.isdir(sas_tasklogdir)):
            task_logdir = Path(sas_tasklogdir)
        else:
            task_logdir = Path.cwd()

    if logfilename:
        task_logfile = task_logdir / logfilename
    else:
        task_logfile = task_logdir / f"{taskname}.log"

    # SAS_TASKLOGFMODE allows to set the write mode for the logging file
    # Allowed modes are : w (new file each invocation of logger),
    # a (append to any existing file)A That is the default mode.
    sastasklogfmode = os.getenv("SAS_TASKLOGFMODE", "a")
    if sastasklogfmode != 'a' and sastasklogfmode != 'w':
        sastasklogfmode = 'a'

    if pylogger:
        # For Python based logging
        # Set verbosity
        verbosity = int(os.getenv('SAS_VERBOSITY'))
        match(verbosity):
            case 1:
                level = "CRITICAL"
            case 2 | 3:
                level = "ERROR"
            case 4 | 5:
                level = "WARNING"
            case 6 | 7:
                level = "INFO"
            case 8 | 9 | 10:
                level = "DEBUG"
            case _:
                level = "INFO"
        
        # 98% of the time pysas_verbosity == SAS_VERBOSITY.
        # But for debugging purposes it is convienent to have
        # a separate verbosity for pySAS.
        # This does not affect the verbosity for non-Python
        # based SAS tasks.
        pysas_verbosity = sas_cfg.get_setting('pysas_verbosity')

        # Take the lower of sas_level or pysas_level
        sas_level   = logger.level(level).no
        pysas_level = logger.level(pysas_verbosity).no
        if sas_level < pysas_level: pysas_verbosity = level

        level = pysas_verbosity
        
        # Add file sink
        if tofile:
            task_logger.add(
                sink=task_logfile,
                level=level,
                mode=sastasklogfmode,
                enqueue=True,
                format="{time:DD-MM-YYYY HH:mm:ss.SSS Z} - {name} - {level: <8} - {message}"
            )

        # Add console sink
        if toterminal:
            task_logger.add(
                sink=sys.stdout,
                level=level,
                enqueue=True,
                format="<g>{name}</g> - <level>{level: <8}</level> - <level>{message}</level>"
            )
    else:
        # For non-Python based logging (i.e. subprocess)
        # Set verbosity
        # For non-Python SAS tasks the verbosity is set separately
        level = "INFO"
        
        # Add file sink
        if tofile:
            task_logger.add(
                sink=task_logfile,
                level=level,
                mode=sastasklogfmode,
                enqueue=True,
                format="<green>{time:DD-MM-YYYY HH:mm:ss.SSS Z}</green> - {message}"
            )

        # Add console sink
        if toterminal:
            task_logger.add(
                sink=sys.stdout,
                level=level,
                enqueue=True,
                format="{message}",
            )

    return task_logger

class TaskLogger:
    """
    TaskLogger creates a logger for Python tasks.
    The name of the logger is the name of the task.
    Such logger is known as saslogger. 
    It includes two handlers, one console handler
    and one file handler. The file handler will put
    all logging messages in a file named <taskname>.log.
    
    This file is by default written in the starting directory
    of the task (os.getcwd()). However, for each task we can 
    set that directory by taking into account the env variable 
    SAS_TASKLOGDIR, if defined. 
    
    By default the logging file is created in  mode -a- (append)
    to allow to use the same file to log several runs of the
    same task. However, the SAS_TASKLOGFMODE environment variable
    can be set to -w- (new file), to change that behaviour.

    File handler has alogging level of DEBUG, so everything
    is logged. However, console handler logging level is 
    controlled by the SAS Verbosity (SAS_VERBOSITY env. variable)
    which is set via the option -V.

    The logger can not be called more than once. If not, 
    messages start appearing duplicated. That is why the
    logging method is separarted from the logger definition.
    """

    def __init__(self, taskname):
        self.taskname = taskname
       
        self.dictlevels = {
                'notset':0,
                'debug': 10,
                'info': 20,
                'warning': 30,
                'error': 40,
                'critical': 50
                }

        self.saslogger = logging.getLogger(self.taskname)
        self.saslogger.setLevel('DEBUG')

        # SAS_TASKLOGDIR allows to set the directory for tyhe logging file
        sastasklogdir = os.getenv('SAS_TASKLOGDIR')
        startdir = os.getcwd()
        #print(f'{self.taskname} was initiated from {startdir}')
       
        if not sastasklogdir:
            #print(f'\nTask logging directory is unset. \nUsing {startdir} instead.')
            sastasklogdir = startdir
        if not os.path.isdir(sastasklogdir):
            #print(f'\n{sastasklogdir} does not exist. \nUsing {startdir} instead.')
            sastasklogdir = startdir

        self.logfile = os.path.join(sastasklogdir, self.taskname + '.log')
        #print(f'\n{self.taskname} log file: {self.logfile}\n')

        # Clear any previous handlers
        if self.saslogger.hasHandlers:
            self.saslogger.handlers.clear()

        # SAS_TASKLOGFMODE allows to set the write mode for the logging file
        # Allowed modes are : w (new file each invocation of logger),
        # a (append to any existing file)A That is the default mode.

        sastasklogfmode = os.getenv('SAS_TASKLOGFMODE')
        if not sastasklogfmode:
            sastasklogfmode = 'a'
        if sastasklogfmode != 'a' and sastasklogfmode != 'w':
            sastasklogfmode = 'a'
        #print(f'\nTask logging file mode = {sastasklogfmode}')

        # File handler (fh). Level fixed to DEBUG
        self.fh = logging.FileHandler(self.logfile, mode=sastasklogfmode)
        self.fh.setLevel('DEBUG')

        # Console handler (ch). Default level set to WARNING
        self.ch = logging.StreamHandler()
        self.ch.setLevel('WARNING')

        # Add handlers to the logger
        self.saslogger.addHandler(self.ch)
        self.saslogger.addHandler(self.fh)

        # Create formatters and add them to handlers
        cformat = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        fformat = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

        self.ch.setFormatter(cformat)
        self.fh.setFormatter(fformat)


    def __repr__(self):
        return f'{self.__class__.__name__}({self.taskname})'


    def log(self, level, msg):
        """
        A log message will be issued according to the logging level.
        The logging level is fixed for the log file but 
        on the console will depend on SAS_VERBOSITY.
        SAS_VERBOSITY can be set between 1 (min) and 10 (max).
        Correspondence between SAS_VERBOSITY levels and logging levels
        DEBUG      ->   verbosity  = 8, 9, 10
        INFO       ->   verbosity  = 6, 7
        WARNING    ->   verbosity  = 4, 5
        ERROR      ->   verbosity  = 2, 3
        CRITICAL   ->   verbosity  = 1
        """

        v = os.getenv('SAS_VERBOSITY')
        if v == None:
            v = '4'
        verbosity = int(v)

        if   verbosity >= 8 and verbosity <= 10:
            self.ch.setLevel('DEBUG')
        elif verbosity >= 6 and verbosity <= 7:
            self.ch.setLevel('INFO')
        elif verbosity >= 4 and verbosity <= 5:
            self.ch.setLevel('WARNING')
        elif verbosity >= 2 and verbosity <= 3:
            self.ch.setLevel('ERROR')
        elif verbosity == 1:
            self.ch.setLevel('CRITICAL')

        nlevel = self.dictlevels[level]
        self.saslogger.log(nlevel, msg)

