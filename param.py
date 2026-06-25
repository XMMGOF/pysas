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
# param.py
"""
Defines class paramXmlInfoReader with methods to parse and extract all
the information included in the task parameter file and build several
data structures which allow to handle them when entered either from the
command line or via an argument dict.
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
    """
    Class which provides several methods to read and handle all the information 
    contained in the the task parameter file. The file is formatted according to 
    the DOM standard. Once the information is loaded, it is distributed into 
    several data structures to allow proper handling of any parameters entered 
    from the command line or through an argument list.
    """

    def __init__(self, taskname: str, logger = None):
        """
        Class constructor for ParseArgs.

        Parameters
        ----------
        taskname : str
            Name of SAS task.
        logger : _type_, optional
            Logger object, by default None.

        Raises
        ------
        FileNotFoundError
            Parameter file for {taskname} not found.
        """

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
            raise FileNotFoundError(f'Parameter file for {taskname} not found.')

    # xmlParser instance method
    def xmlParser(self):
        """
        Parses the parameter file into a Document object.

        The first task of xmlParser is to get the whole XML file as an object 
        of type Document (For a list of all objects, look at the xml.dom 
        documentation). Then, it produces a list of Element objects in the 
        paramater file which are identified by the tag 'PARAM'. This is done by 
        means of the Element method getElementsByTagName.
        
        Outputs:

        - params                  : List of all elements with tag PARAM

        - allparams               : Dictionary { parameter: {attributes} }

        - pels                    : Dictionary { element: pname }

        - rev_pels                : Dictionary { pname : element }

        - parmap                  : Dictionary { pname: [ subparameters ...], ...}
        
        It is the map of the parameter tree as a list of dictionaries.
        Each dictionary corresponds to a paramater and all its sub-parameters
        structure as follows:

        keys are the parent parameters and values are lists with all their 
        subparameters
        
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
            raise Exception(f'ERROR opening par file {self.taskname}.par: {self.xmlFile}')

        # self.params
        self.params = doc.getElementsByTagName('PARAM')

        # Dictionary allparams
        # A dictionary where each key is the name of a parameter.
        # Each item in the dictionary is a dictionary with the 
        # following items:
        #     - id (string)
        #     - type (string)
        #     - default (string)
        #     - mandatory (string)
        #     - description (string)
        # The following items are added later:
        #     - parent (string/None)
        #     - children (list)
        #     - cond_mand (boolean) "conditionally mandatory"
        #     - cond_par_val (string/None) "conditional parent value"

        self.allparams = {}
        for p in self.params:
            attrib = self.att(p)
            pname = attrib['id']
            self.allparams[pname] = attrib
            # Will be set later
            self.allparams[pname]['parent'] = None
            self.allparams[pname]['children'] = []
            self.allparams[pname]['cond_mand'] = False
            self.allparams[pname]['cond_par_val'] = None

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
        # List of mandatory parameters

        self.mandpar = []
        for pname,paramdict in self.allparams.items():
            if paramdict['mandatory']:
                self.mandpar.append(paramdict['id'])

        # mainparams
        # List of main parameters

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
                        # self.mandpar_dict[m] = m
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

        # Adding more information to the allparams dictionary
        #     - parent (string/None)
        #     - children (list)
        #     - cond_mand (boolean) "conditionally mandatory"
        #     - cond_par_val (string) "conditional parent value"
        #     - constraints (string)

        # Adding the constraints attribute to the parameters attributes in parmap
        for p in self.params:
            pname = self.el2nam(p, self.pels)
            for k in p.childNodes:
                if k.nodeName == 'CONSTRAINTS':
                    constraints = p.getElementsByTagName('CONSTRAINTS')[0].firstChild.data
                    constraints = constraints.strip('\n')
                    constraints = constraints.strip()
                    self.allparams[pname]['constraints'] = constraints
        
        # Adding list of children and parent value
        for d in self.parmap:
            for parent, child_list in d.items():
                self.allparams[parent]['children'] = child_list
                for child in child_list:
                    self.allparams[child]['parent'] = parent
                    p = self.rev_pels[child]
                    if p.parentNode.hasAttribute('value'):
                        self.allparams[child]['cond_par_val'] = p.parentNode.getAttribute('value')

        # Adding whether the parameter is "conditionally mandatory", and
        # the parent value needed if "conditionally mandatory".
        for parent,child_list in self.rev_mandpar_dict.items():
            for child in child_list:
                if child in self.mandpar:
                    self.allparams[child]['cond_mand'] = True                

        # Clean up and close file
        doc.unlink()

    # Print table of all parameters
    def printHelp(self):
        """
        Prints a table with the parameters read from xmlFile.
        """
        table = BeautifulTable()
        table.columns.header = ['name', 'mandatory', 'type', 'default', 'description']
        table.columns.width = [50, 15, 10, 30, 50]
        table.maxwidth = 160
        for a in self.allparams.values():
            table.rows.append([a['id'], a['mandatory'], a['type'], 
                              a.get('default', None), a['description']])
        print(table)

    # method defaultValues - Returns defaults
    def defaultValues(self):
        """
        Returns a dictionary with the default values for each parameter.

        Default values might be of different types with multiple values.
        For the time being, we create lists for all of then, which can be either 
        single or multiple values.

        Returns
        -------
        dict
            Dictionary of the default values for the SAS task.
        """

        defaults = {}
        for p, a in self.allparams.items():
            defaults[p] = a.setdefault('default', '')
        return defaults

    # Static methods used in the class

    @staticmethod
    def att(p):
        """
        Obtains the attributes of parameter p from the parameter file.

        Parameters
        ----------
        p : NodeList
            XML NodeList from xml.dom.

        Returns
        -------
        dict
            Dictionary with the parameter attributes.
        """
    
        attrib = {}
        for k, v in p.attributes.items():
            attrib[k] = v
        if 'mandatory' not in attrib.keys():
            attrib['mandatory'] = False
        else:
            if attrib['mandatory'] == 'yes':
                attrib['mandatory'] = True
            else:
                attrib['mandatory'] = False
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
        Returns the list of all subparamaters from a given parameter p downwards 
        the tree structure.

        Parameters
        ----------
        p : NodeList
            XML NodeList from xml.dom.
        
        Returns
        -------
        NodeList
            Returns the NodeList for the subparameters for parameter p.
        """
        subp = p.getElementsByTagName('PARAM')
        return subp
    
    @staticmethod
    def nam2el(pname, rev_pels):
        """
        Returns the parameter element p for a parameter name.

        Parameters
        ----------
        pname : str
            Parameter name.
        rev_pels : dict
            Dictionary of NodeLists for the parameters.

        Returns
        -------
        NodeList
            The NodeList for the parameter name.

        Raises
        ------
        Exception
            rev_pels is undefined.
        """
        
        if not rev_pels:
            raise Exception('rev_pels is undefined!')
        el = rev_pels[pname]
        return el
    
    @staticmethod
    def el2nam(p, pels):
        """
        Returns the name of a parameter element p.

        Parameters
        ----------
        p : NodeList
            NodeList of parameter to find.
        pels : dict
            Dictionary of parameter names based on parameter elements.

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        Exception
            pels is undefined.
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

    def _get_task_defaults(self,taskname):
        """
        Function to get the default parameters for a SAS task.

        Parameters
        ----------
        taskname : str
            SAS task name.
        """

        t = paramXmlInfoReader(taskname)
        t.xmlParser()
        self.defaults = t.defaultValues()
        self.defaults['options'] = ''

    def _get_task_params(self,taskname):
        """
        Function to get ALL the parameter information for a SAS task.

        Parameters
        ----------
        taskname : str
            SAS task name.
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
        Sets special dictionary 'inparams' to defaults without setting 
        'modified' to 'True'. Silently overwrites previous values!

        Parameters
        ----------
        taskname : str
            SAS task name.
        """
        self._get_task_defaults(taskname)
        for k, v in self.defaults.items():
            self.inparams[k] = (v,False)
            super().__setitem__(k, v)

def get_input_params(taskname):
    """
    Function to return SASParams dictionary of input parameters for a 
    given SAS task.

    Parameters
    ----------
    taskname : str
        SAS task name.

    Returns
    -------
    SASParams
        SASParams dictionary. Special dictionary of input parameters with 
        defaults. Behaves like a normal dictionary, but keeps track of which 
        parameters have been modified.
    """
    
    return_dict = SASParams({})
    return_dict.set_inparams_to_defaults(taskname)

    return return_dict
