#!/usr/bin/env python

#	ESA (C) 2000-2018 
#	This file is part of ESA's XMM-Newton Scientific Analysis System
#	(SAS).
#
#	SAS is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	SAS is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#	   
#	You should have received a copy of the GNU General Public License
#	along with SAS.  If not, see <http://www.gnu.org/licenses/>.



from xml.dom import minidom
import sys
from pysas.xmmextractorGUI.utils import Instruments

class createXML:
    
    def __init__(self,procEPNDict,procEMOS1Dict,procEMOS2Dict,\
                 procRGS1Dict,procRGS2Dict,procOMDict,obsInfoDict,\
                 tasksEPNDict,tasksEMOS1Dict,\
                 tasksEMOS2Dict,tasksRGS1Dict,\
                 tasksRGS2Dict,tasksOMDict,\
                 xmldocFile):       

        self.procEPNDict = procEPNDict
        self.procEMOS1Dict = procEMOS1Dict
        self.procEMOS2Dict = procEMOS2Dict
        self.procRGS1Dict = procRGS1Dict
        self.procRGS2Dict = procRGS2Dict
        self.procOMDict = procOMDict
        self.tasksEPNDict = tasksEPNDict
        self.tasksEMOS1Dict = tasksEMOS1Dict
        self.tasksEMOS2Dict = tasksEMOS2Dict
        self.tasksRGS1Dict = tasksRGS1Dict
        self.tasksRGS2Dict = tasksRGS2Dict
        self.tasksOMDict = tasksOMDict

        self.xmldocFile = xmldocFile
        self.xmldoc = minidom.parse(xmldocFile)
        #self.instrumentDict = {}
        self.obsInfoDict = obsInfoDict
        self.handleBody()       
        
    def handleBody(self):
        self.xmlfile = open(self.xmldocFile,'w')
        print("<!DOCTYPE BODY>",file=self.xmlfile)
        print ("<BODY>",file=self.xmlfile)
        print("<CONFIG SASVersion=\"xmmsas_20191021_1832\">",file=self.xmlfile)        
        self.handleConfig(self.xmldoc.getElementsByTagName("CONFIG")[0])        
        print ("</CONFIG>",file=self.xmlfile)
        print ("</BODY>",file=self.xmlfile)                
        self.xmlfile.close()
        
    def handleConfig(self,conf):  
        #update obsInfoDict with the results of the control panel
        for instrument in Instruments:
            if instrument == Instruments.EPN:
                self.obsInfoDict['EPN'] = self.procEPNDict['Processing']
            elif instrument == Instruments.EMOS1:
                self.obsInfoDict['EMOS1'] = self.procEMOS1Dict['Processing']
            elif instrument == Instruments.EMOS2:
                self.obsInfoDict['EMOS2'] = self.procEMOS2Dict['Processing']
            elif instrument == Instruments.RGS1:
                self.obsInfoDict['RGS1'] = self.procRGS1Dict['Processing']
            elif instrument == Instruments.RGS2:
                self.obsInfoDict['RGS2'] = self.procRGS2Dict['Processing']
            elif instrument == Instruments.OM:
                #self.obsInfoDict['OM'] = self.procOMDict['Processing']
                self.obsInfoDict['OM'] = "no"
                              
        self.instrumentDict = self.obsInfoDict        
        self.handleObservation(conf.getElementsByTagName("OBSERVATION")[0])
        self.handleInstrument(conf.getElementsByTagName("INSTRUMENT"))
        
    def handleObservation(self,observation):  
            newParams = {}  
            print("<OBSERVATION>",file=self.xmlfile)               
            self.handleParam(observation.getElementsByTagName('PARAM'),newParams,"none")
            print("</OBSERVATION>",file=self.xmlfile)
        
    def handleInstrument(self,instruments): 
        self.paramsDict = {}       
        for instrument in instruments:
            if instrument.getAttribute('value') == "EPN":                
                self.instrumentDict = self.procEPNDict
                self.paramsDict = self.tasksEPNDict
            elif instrument.getAttribute('value') == "EMOS1":
                self.instrumentDict = self.procEMOS1Dict
                self.paramsDict = self.tasksEMOS1Dict
            elif instrument.getAttribute('value') == "EMOS2":
                self.instrumentDict = self.procEMOS2Dict
                self.paramsDict = self.tasksEMOS2Dict
            elif instrument.getAttribute('value') == "RGS1":
                self.instrumentDict = self.procRGS1Dict
                self.paramsDict = self.tasksRGS1Dict
            elif instrument.getAttribute('value') == "RGS2":
                self.instrumentDict = self.procRGS2Dict
                self.paramsDict = self.tasksRGS2Dict
            elif instrument.getAttribute('value') == "OM":
                self.instrumentDict = self.procOMDict
                self.paramsDict = self.tasksOMDict

            print("<INSTRUMENT value=\""+str(instrument.getAttribute('value'))+"\"> ",file=self.xmlfile)
            self.handleExposure(instrument.getElementsByTagName("EXPOSURE"))
            print("</INSTRUMENT>",file=self.xmlfile)
    def handleExposure(self,exposures):
        for exposure in exposures:
            print ("<EXPOSURE mode=\""+str(exposure.getAttribute('mode'))+"\""+ \
                   " expid=\""+str(exposure.getAttribute('expid'))+"\""+ \
                   " duration=\""+str(exposure.getAttribute('duration'))+"\""+ \
                   " process=\""+str(self.instrumentDict[exposure.getAttribute('expid')]['Process'])+ "\">",file=self.xmlfile )            
            self.handleProduct(exposure.getElementsByTagName('PRODUCT'),exposure.getAttribute('expid'))
            print("</EXPOSURE>",file=self.xmlfile)
        
    def handleProduct(self,exposure,expid):
        expoDict = self.paramsDict[expid]
        for product in exposure:
            prodDict = expoDict[str(product.getAttribute('value'))]
            print("<PRODUCT value=\""+str(product.getAttribute('value'))+"\"", \
                  " process=\""+str(self.instrumentDict[expid][product.getAttribute('value')])+"\">",file=self.xmlfile )
            self.handleTasks(product.getElementsByTagName('TASK'), prodDict,expid)
            print("</PRODUCT>",file=self.xmlfile)
        
    def handleTasks(self,product,prodDict,expid):              
        taskCounter = 1
        for task in product:  
            newParams = prodDict["params_"+str(taskCounter)]           
            print("<TASK purpose=\""+str(task.getAttribute('purpose'))+"\""+ \
                  " name= \""+str(task.getAttribute('name'))+"\">",file=self.xmlfile)            
            self.handleParam(task.getElementsByTagName('PARAM'),newParams,expid)
            print("</TASK>",file=self.xmlfile)
            taskCounter = taskCounter + 1
    
    
    def handleParam(self,params,newParams,expid):
        #print(newParams)
        for param in params:
            if param.getAttribute('id') in self.instrumentDict: 
                val = self.instrumentDict[param.getAttribute('id')]
            else:
                #val = param.getAttribute('default')
                val = newParams[str(param.getAttribute('id'))]
                if (param.getAttribute('id') == "finalstage"):
                    if expid in self.procRGS1Dict:
                        stage = self.procRGS1Dict[expid]
                        if stage['EventList'] == 'yes':
                            val = "1:events"
                        if stage['spectra'] == 'yes':
                            val = "4:spectra"
                        if stage['fluxing'] == 'yes':
                            val = "5:fluxing"
                        if stage['lightcurve'] == 'yes':
                            val = "6:lightcurve"
                    if expid in self.procRGS2Dict:
                        stage = self.procRGS2Dict[expid]
                        if stage['EventList'] == 'yes':
                            val = "1:events"
                        if stage['spectra'] == 'yes':
                            val = "4:spectra"
                        if stage['fluxing'] == 'yes':
                            val = "5:fluxing"
                        if stage['lightcurve'] == 'yes':
                            val = "6:lightcurve"                        
                    
            val = val.replace('&','&amp;')
            val = val.replace('<','&lt;')
            val = val.replace('>','&gt;')        
            print ("<PARAM id=\""+str(param.getAttribute('id'))+\
                   "\" default=\""+str(val)+"\"/>",\
                   file=self.xmlfile)
        
        
    
        
