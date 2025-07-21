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
"""param.py

Defines class paramXmlInfoReader with methods to parse and extract all
the information included in the task parameter file and build several
data structures which allow to handle them when entered either from the
command line or via an argument list.


Methods (Class and instance):

xmlParser:		Parses the parameter file into a Document object.
printHelp:		Prints a table with the parameters read from xmlFile.
defaultValues: 	Returns a dictionary with the default values for each parameter.

Functions:
att(p):                     Fills in the attributes of parameter p
getsub(p):                  Obtains the sub-parameters of parameter p
el2nam(p, pels):            Gets the name off parameter element p
nam2el(pname, rev_pels):    Gets the element of parameter name pname


Class Instantiation

t = paramXmlInfoReader('epproc')
t.xmlParser()

"""

# Standard library imports
from xml.dom import minidom as md
import os
import sys
import glob
from collections import UserDict

# Third party imports
from beautifultable import BeautifulTable

# Local application imports
from pysas.logger import get_logger


class paramXmlInfoReader:
    """paramXmlInfoReader

    Class which provides several methods
    to read and handle all the information contained in the
    the task parameter file. The file is formatted according
    to the DOM standard.
    Once the information is loaded, it is distributed into
    several data structures to allow proper handling
    of any parameters entered from the command line or through
    an argument list.
    """

    def __init__(self, taskname, logger = None):
        """taskname to be handled."""

        self.taskname = taskname
        self.xmlFile = ''
        if logger is None:
            # By default will only output to terminal
            self.logger = get_logger('paramXmlInfoReader')
        else:
            # Use logger that was passed in
            self.logger = logger

        sas_dir = os.environ['SAS_DIR']
        self.logger.debug(f'SAS_DIR: {sas_dir}')
        parfile = self.taskname + '.par'
        self.logger.debug(f'Parfile name: {parfile}')
        files = glob.glob(os.path.join(sas_dir, 'config', parfile))
        self.logger.debug(f'Parfile location: {files}')
        if files:
            self.xmlFile = files[0]
            self.logger.debug(f'xmlFile: {self.xmlFile}')

        if self.xmlFile == '':
            raise Exception(f'Does not exist any file named {parfile}. Wrong syntax?')

    # xmlParser instance method
    def xmlParser(self):
        """
        The first task of xmlParser is to get the whole XML file as an object 
        of type Document (For a list of all objects, look at the xml.dom documentation).
        Then, it produces a list of Element objects in the paramater file which are 
        identified by the tag 'PARAM'. This is done by means of the Element method
        getElementsByTagName.
        
        
        Outputs:
        - params                  : List of all elements with tag PARAM
        - allparams               : Dictionary { parameter: {attributes} }
        - pels                    : Dictionary { element: pname }
        - rev_pels                : Dictionary { pname : element }
        - parmap                  : Dictionary { pname: [ subparameters ...], ...}
        
        It is the map of the parameter tree as a list of dictionaries.
        Each dictionary corresponds to a paramater and all its sub-parameters
        structure as follows:
        keys are the parent parameters and values are lists with all their subparameters
        
        
        Examples:
        
        1- Parent parameter: keepfilteroutput
           Subparameters: withfilteredset, filteredset

           {'keepfilteroutput': ['withfilteredset, 'filteredset'],
           'wilthfilteredset': ['filteredset'],
           'fileteredset': [] }
           
           This dictionary corresponds to a parameter tree as follows:
           
           keepfilterouput
               └── withfilteredset
                       └── filteredset

        2- Parent parameter: filtertype
           Subparameters: dssblock, expression
           
           {'filtertype': ['dssblock', 'expression'],
           'dssblok': [],
           'expression': [] }
           
           filtertype
               ├── dssblock
               └── expression


        3- Parent parameter: table
           Subparameters: None
           
           {'table': [] }
           
           - mandpar                 : List of all parameters/subparameters defined mandatory = 'yes'.
           - mainparams              : List of main paramaters, with or without subparamaters
           - mandpar_dict            : Dictionary, key = mandatory subparamater, value=its parent parameter
           - rev_mandpar_dict        : Dictionary, keys  = parent paramater, 
                        value = list of all mandatory subparameters
           - rev_mandpar_string_dict : Dictionary, keys  = parent parameter type 'string'
                        value = list of alternatives
        """

        try:
            doc = md.parse(self.xmlFile)
        except:
            self.logger.error(f'ERROR opening par file {self.taskname}.par: {self.xmlFile}')
            sys.exit(1)

        # self.params
        self.params = doc.getElementsByTagName('PARAM')

        # Dictionary allparams
        self.allparams = {}
        for p in self.params:
            attrib = self.att(p)
            pname = attrib['id']
            self.allparams[pname] = attrib

        # pels dictionary

        self.pels = {}
        for p in self.params:
            pname = self.att(p)['id']
            self.pels[p] = pname

        # reverse pels dictionary
        self.rev_pels = {v: k for k, v in self.pels.items()}

        # parmap

        self.parmap = []
        pardict = {}
        for p in self.params:
            pname = self.el2nam(p, self.pels)
            if p.parentNode.nodeName == 'CONFIG':
                pardict = {}
            subp = self.getsub(p)
            for k in subp:
                i = subp.index(k)
                subp[i] = self.el2nam(k, self.pels)
            pardict[pname] = subp
            if p.parentNode.nodeName == 'CONFIG':
                self.parmap.append(pardict)

        # mandpar

        self.mandpar = []
        for p in self.params:
            if self.att(p)['mandatory'] == 'yes':
                self.mandpar.append(self.att(p)['id'])

        # mainparams

        self.mainparams = []
        for e in self.parmap:
            n = 0
            for k in e.keys():
                n += 1
                if n == 1:
                    self.mainparams.append(k)
                else:
                    break

        # mandpar_dict
        self.mandpar_dict = {}
        for m in self.mandpar:
            for d in self.parmap:
                for k, v in d.items():
                    if m == k and m in self.mainparams:
                        self.mandpar_dict[m] = m
                        continue
                    elif m in v:
                        self.mandpar_dict[m] = k

        # rev_mandpar_dict
        self.rev_mandpar_dict = {}
        for k, v in self.mandpar_dict.items():
            self.rev_mandpar_dict[v] = self.rev_mandpar_dict.get(v, []) + [k]

        # rev_mandpar_string_dir
        self.rev_mandpar_string_dict = {}
        for pname in self.rev_mandpar_dict.keys():
            if self.allparams[pname]['type'] != 'string':
                continue
            el = self.rev_pels[pname]
            subp = el.getElementsByTagName('CASE')
            if len(subp) >= 1:
                subp = el.getElementsByTagName('CASE')[0]
            else:
                continue
            alternatives = []
            for i in range(subp.childNodes.length):
                if subp.childNodes.item(i).nodeName == 'ITEM':
                    a = subp.childNodes.item(i).attributes['value'].value
                    alternatives.append(a)
            self.rev_mandpar_string_dict[pname] = alternatives


        # Adding the constraints attribute to the parameters attributes in parmap
        for p in self.params:
            pname = self.el2nam(p, self.pels)
            for k in p.childNodes:
                if k.nodeName == 'CONSTRAINTS':
                    constraints = p.getElementsByTagName('CONSTRAINTS')[0].firstChild.data
                    constraints = constraints.strip('\n')
                    constraints = constraints.strip()
                    self.allparams[pname]['constraints'] = constraints

    # Print table of all parameters
    def printHelp(self):
        """
        Prints a table of all parameters with columns
        """
        table = BeautifulTable()
        table.columns.header = ['name', 'mandatory', 'type', 'default', 'description']
        table.columns.width = [50, 15, 10, 30, 50]
        table.maxwidth = 160
        for a in self.allparams.values():
            table.rows.append([a['id'], a['mandatory'], a['type'], a.get('default', None), a['description']])
        print(table)

    # method defaultValues - Returns defaults
    def defaultValues(self):
        """
        Default values might be of different types with multiple values
        For the time being, we create lists for all of then,
        which can be either single or multiple values.
        """

        defaults = {}
        for p, a in self.allparams.items():
            defaults[p] = a.setdefault('default', '')
        return defaults

    # Static methods used in the class

    @staticmethod
    def att(p):
        """
        att(p) obtains the attributes of parameter p
        """
    
        attrib = {}
        for k, v in p.attributes.items():
            attrib[k] = v
        if 'mandatory' not in attrib.keys():
            attrib['mandatory'] = 'no'
        if 'list' not in attrib.keys():
            attrib['list'] = 'no'
        # All parameters have a DESCRIPTION node after them
        if p.getElementsByTagName('DESCRIPTION').length == 0:
            description = ''
        elif p.getElementsByTagName('DESCRIPTION')[0].firstChild == None:
            description = ''
        else:
            description = p.getElementsByTagName('DESCRIPTION')[0].firstChild.data
            description = description.strip('\n')
            description = description.strip()
        attrib['description'] = description
        return attrib

    @staticmethod
    def getsub(p):
        """
        getsub(p) returns the list of all subparamaters
        from a given parameter p downwards the tree structure
        """
        subp = p.getElementsByTagName('PARAM')
        return subp
    
    @staticmethod
    def nam2el(pname, rev_pels):
        """
        nam2el(pname): returns the parameter element p for a parameter name
        """
        if not rev_pels:
            raise Exception('rev_pels is undefined!')
        el = rev_pels[pname]
        return el
    
    @staticmethod
    def el2nam(p, pels):
        """
        el2nam(p): returns the name of a parameter element p
        """
        if not pels:
            raise Exception('pels is undefined!')
        pname = pels[p]
        return pname

class SASParams(UserDict):
    """
    The class 'SASParams' is a child of 'UserDict', which is 
    like a normal Python dict, but allows for special modifications.

    Upon instatiation the object will create a parallel dict which
    keeps track if the values of the main dict have been modified.

    The end user should interact with the SASParams dict like a normal
    Python dictionary.
    
    The special methods are intended for internal pySAS use only!

    How to use:
        from pysas.param import SASParams
        my_task_inputs = SASParams({})
        my_task_inputs.set_inparams_to_defaults(taskname)
    """
    def __init__(self, *args, **kwargs):
        self.inparams = {}
        super().__init__(*args, **kwargs)
        for key in self.data.keys():
            self.inparams[key] = (self.data[key],False)
    def __setitem__(self, key, value):
        self.inparams[key] = (value,True)
        super().__setitem__(key, value)

    def get_task_defaults(self,taskname):
        """
        Function to get the default parameters for a SAS task.
        """
        t = paramXmlInfoReader(taskname)
        t.xmlParser()
        self.defaults = t.defaultValues()
        self.defaults['options'] = ''

    def get_task_params(self,taskname):
        """
        Function to get ALL the parameter information
        for a SAS task.
        """
        t = paramXmlInfoReader(taskname)
        t.xmlParser()
        self.allparams = t.allparams
        self.mandparams = t.mandpar
        self.mainparams = t.mainparams
        self.parmap = t.parmap
        self.mandpar_dict = t.mandpar_dict
        self.rev_mandpar_dict = t.rev_mandpar_dict
        self.rev_mandpar_string_dict = t.rev_mandpar_string_dict

    def set_inparams_to_defaults(self, taskname):
        """
        Sets special dictionary 'inparams' to defaults without
        setting 'modified' to 'True'.

        Silently overwrites previous values!
        """
        self.get_task_defaults(taskname)
        for k, v in self.defaults.items():
            self.inparams[k] = (v,False)
            super().__setitem__(k, v)

def get_input_params(taskname):
    """
    Function to return dictionary of input parameters for a given 
    SAS task.

        Input:
        - taskname (string)

        Output:
        - Special dictionary of input parameters with defaults.
          The dictionary will be of the type 'SASParams', which
          behaves like a normal dictionary, but keeps track of 
          which parameters have been modified.
        
    """
    
    return_dict = SASParams({})
    return_dict.set_inparams_to_defaults(taskname)

    return return_dict
