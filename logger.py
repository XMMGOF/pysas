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

"""
Module for logging pySAS output.
"""

# Standard library imports
import logging
import sys
import os
from pathlib import Path

# Third party imports

# Local application imports

# Define the standard 5 levels explicitly
LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class LoggerStyleFormatter(logging.Formatter):
    """
    A custom formatter that provides ANSI colors for terminal output, 
    but plain text for file output.
    """
    RESET = "\x1b[0m"
    GREEN = "\x1b[32m"
    CYAN = "\x1b[36m"
    BOLD = "\x1b[1m"
    
    LEVEL_COLORS = {
        logging.DEBUG: "\x1b[34m",           # Blue
        logging.INFO: BOLD,                  # Bold White
        logging.WARNING: "\x1b[33m",         # Yellow
        logging.ERROR: "\x1b[31m",           # Red
        logging.CRITICAL: "\x1b[41m\x1b[37m" # White on Red background
    }

    def __init__(self, use_color=True):
        super().__init__()
        self.use_color = use_color

    def format(self, record):
        # Format: 2023-10-24 15:30:00 | INFO     | module:func:line - message
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level_name = f"{record.levelname:<8}"
        location = f"{record.module}:{record.funcName}:{record.lineno}"
        
        if self.use_color:
            color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
            time_part = f"{self.GREEN}{time_str}{self.RESET}"
            level_part = f"{color}{level_name}{self.RESET}"
            loc_part = f"{self.CYAN}{location}{self.RESET}"
            msg_part = f"{color}{record.getMessage()}{self.RESET}"
            return f"{time_part} | {level_part} | {loc_part} - {msg_part}"
        else:
            return f"{time_str} | {level_name} | {location} - {record.getMessage()}"


# ---------------------------------------------------------
# 1. Package-Wide Global Logger (_logger)
# ---------------------------------------------------------
PKG_LOGGER_NAME = "pysas_logger"
_logger = logging.getLogger(PKG_LOGGER_NAME)
_logger.setLevel(logging.DEBUG) # Let handlers filter the exact levels
_logger.propagate = False       # Prevent duplicate logging to root

# Internal variables to track active global handlers
_terminal_handler = None
_file_handler = None

def _log_enable_terminal(level="WARNING"):
    """Turns ON terminal output for the global _logger."""
    global _terminal_handler
    if _terminal_handler is None:
        _terminal_handler = logging.StreamHandler(sys.stdout)
        _terminal_handler.setFormatter(LoggerStyleFormatter(use_color=True))
        _logger.addHandler(_terminal_handler)
    
    _terminal_handler.setLevel(LEVELS.get(level.upper(), logging.WARNING))

def _log_disable_terminal():
    """Turns OFF terminal output for the global _logger."""
    global _terminal_handler
    if _terminal_handler is not None:
        _logger.removeHandler(_terminal_handler)
        _terminal_handler.close()
        _terminal_handler = None

def _log_enable_file(filepath, level="WARNING"):
    """Turns ON file output for the global _logger, routing it to 'filepath'."""
    global _file_handler
    
    # If a file is already open, close it before opening a new one
    if _file_handler is not None:
        _log_disable_file()
        
    os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
    _file_handler = logging.FileHandler(filepath)
    _file_handler.setFormatter(LoggerStyleFormatter(use_color=False))
    _file_handler.setLevel(LEVELS.get(level.upper(), logging.WARNING))
    _logger.addHandler(_file_handler)

def _log_disable_file():
    """Turns OFF file output for the global _logger."""
    global _file_handler
    if _file_handler is not None:
        _logger.removeHandler(_file_handler)
        _file_handler.close()
        _file_handler = None

def _log_set_level(level="WARNING"):
    """
    Changes the logging level for the global _logger dynamically.
    This updates the level for any currently active outputs (terminal or file)
    without turning them on or off.
    """
    level_num = LEVELS.get(level.upper(), logging.WARNING)
    
    global _terminal_handler
    if _terminal_handler is not None:
        _terminal_handler.setLevel(level_num)
        
    global _file_handler
    if _file_handler is not None:
        _file_handler.setLevel(level_num)

# ---------------------------------------------------------
# 2. Independent Logger Factory (For Subprocesses)
# ---------------------------------------------------------
def _create_independent_logger(name, terminal=False, log_file=None, level="DEBUG"):
    """
    Creates an isolated logger instance for tracking subprocesses/tasks.
    """
    indep_logger = logging.getLogger(name)
    indep_logger.setLevel(LEVELS.get(level.upper(), logging.DEBUG))
    
    # Clear any existing handlers (if calling this multiple times for the same name)
    if indep_logger.hasHandlers():
        indep_logger.handlers.clear()
        
    indep_logger.propagate = False # Crucial: Don't bubble up to _logger

    if terminal:
        term_h = logging.StreamHandler(sys.stdout)
        term_h.setFormatter(logging.Formatter("%(message)s"))
        term_h.setLevel(LEVELS.get(level.upper(), logging.DEBUG))
        indep_logger.addHandler(term_h)
        
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)) or ".", exist_ok=True)
        file_h = logging.FileHandler(log_file)
        file_h.setFormatter(logging.Formatter("%(message)s"))
        file_h.setLevel(LEVELS.get(level.upper(), logging.DEBUG))
        indep_logger.addHandler(file_h)
        
    return indep_logger


# Old Logger

class TaskLogger:
    """
    This is only here for legacy reasons. This was the original logger class for 
    pySAS.

    TaskLogger creates a logger for Python tasks. The name of the logger is the 
    name of the task. Such logger is known as saslogger. It includes two 
    handlers, one console handler and one file handler. The file handler will 
    put all logging messages in a file named <taskname>.log.
    
    This file is by default written in the starting directory of the task 
    (os.getcwd()). However, for each task we can set that directory by taking 
    into account the env variable SAS_TASKLOGDIR, if defined. 
    
    By default the logging file is created in mode -a- (append) to allow to use 
    the same file to log several runs of the same task. However, the 
    SAS_TASKLOGFMODE environment variable can be set to -w- (new file), to 
    change that behaviour.

    File handler has alogging level of DEBUG, so everything is logged. However, 
    console handler logging level is controlled by the SAS Verbosity 
    (SAS_VERBOSITY env. variable) which is set via the option -V.

    The logger can not be called more than once. If not, messages start 
    appearing duplicated. That is why the logging method is separarted from the 
    logger definition.
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

