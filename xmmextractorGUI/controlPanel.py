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


from PyQt5.QtWidgets import QFrame
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QWidget,QLineEdit
from PyQt5.QtCore import QRect,Qt,pyqtSlot
from functools import partial
from PyQt5.Qt import QScrollArea, QGroupBox
import logging

class controlPanel:
    #on_click = pyqtSignal()
    
    def __init__(self,procEPNDict,procEMOS1Dict,procEMOS2Dict,procRGS1Dict,\
                 procRGS2Dict,procOMDict):

        self.logger = logging.getLogger('xmmextractorGUI')
        self.logger.info("Creating Control Panel")

        self.procEPNDict = procEPNDict
        self.procEMOS1Dict = procEMOS1Dict
        self.procEMOS2Dict = procEMOS2Dict
        self.procRGS1Dict = procRGS1Dict
        self.procRGS2Dict = procRGS2Dict
        self.procOMDict = procOMDict
        #self.tabObservationWidget = tabObservationWidget
        self.EPNExpButtonDict= {}
        self.height = 0
        self.btnWidth = 110
        self.btnHeight = 24
    
    def createPanel(self): 
        self.logger.info("Creating Control Panel")
    
    def getFrame(self):        
               
        self.EPNControlFrame = QtWidgets.QFrame()
        self.EPNFrameLayout = QVBoxLayout()
        self.EPNControlFrame.setMinimumSize(100,1000)
        self.EPNControlFrame.setLayout(self.EPNFrameLayout)
        self.EPNControlFrame.setGeometry(QRect(0,25,650,300))
        
        
        self.createEPNControlPanel(self.procEPNDict)
        
        self.createEPNControlPanel(self.procEMOS1Dict)
        self.createEPNControlPanel(self.procEMOS2Dict)
        self.createEPNControlPanel(self.procRGS1Dict)
        self.createEPNControlPanel(self.procRGS2Dict)
        self.createEPNControlPanel(self.procOMDict)
                
        self.scroll = QScrollArea()        
        self.scroll.setWidgetResizable(True) 
        self.scroll.setVisible(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.scroll.setWidget(self.EPNControlFrame)
        #self.scroll.setWidget(self.totalFrame)        
        return self.scroll
        #return self.controlFrame
    
    

    def createEPNControlPanel(self,instDict):
        
        if len(instDict) == 2:
            return

        j = (((len(instDict ) - 2)*20)/2. - 10) + self.height               
        self.EPNButton = QtWidgets.QPushButton(self.EPNControlFrame)
        self.EPNButton.setGeometry(QRect(0,round(j),self.btnWidth,self.btnHeight))
        inst = instDict['Instrument']
        instButtonName = inst+'Button'
        self.EPNButton.setObjectName(instButtonName)
        self.EPNButton.setText(inst)
        self.EPNButton.setCheckable(True);        
        if instDict['Processing'] == "yes":
            self.EPNButton.setChecked(True)
            instrumentFlag = True
        else:
            self.EPNButton.setChecked(False)
            instrumentFlag = False            
        self.EPNButton.toggle()
        self.EPNButton.clicked.connect(partial(self.EPN_on_click,inst,instDict))
        self.EPNExpButtonDict[inst] = self.EPNButton
        #EPNButtongList = []
       
        
        j = self.height
        for key,val in instDict.items():
            RGSFlag = True
            OMFlag = True
            i = self.btnWidth
            EPNExpButtonDict = {}                            
            if isinstance(val,dict):
                self.ExpButton = QtWidgets.QPushButton(key, self.EPNControlFrame)
                self.ExpButton.setGeometry(QRect(i,j,self.btnWidth,self.btnHeight))                
                self.ExpButton.setObjectName(key)
                self.ExpButton.setText(key)                
                self.ExpButton.setCheckable(True);
                
                if instDict[key]['Process'] == "yes" and instrumentFlag == True:
                    self.ExpButton.setChecked(True)
                else:
                    self.ExpButton.setChecked(False)
                self.ExpButton.toggle()
                self.ExpButton.clicked.connect(partial(self.Exp_on_click,key,instDict))
                self.EPNExpButtonDict[key] = self.ExpButton
                #print ('EXPOSURE ', key)
                for expKey,expInfo in val.items():
                    if expKey != "Process":
                        i = i + self.btnWidth                        

                    if expKey == "pileup":
                        i = i - self.btnWidth

                    #For RGS we do not have "yet" the possibility to create GTI
                    if (inst == "RGS1" or inst == "RGS2")  and  (expKey != "Process" and\
                      expKey != "EventList"  and RGSFlag == True):                        
                        for x in range(0,2):                            
                            self.ExpInfoButton = QtWidgets.QPushButton(self.EPNControlFrame)
                            self.ExpInfoButton.setGeometry(QRect(i,j,self.btnWidth,self.btnHeight))
                            self.ExpInfoButton.setObjectName(expInfo)
                            self.ExpInfoButton.setText("N/A")                            
                            self.ExpInfoButton.setEnabled(False);
                            i = i + self.btnWidth
                            RGSFlag = False

                    if inst == "OM"  and  (expKey != "Process" and\
                    expKey != "EventList" and OMFlag == True):
                        
                        for x in range(0,4):                            
                            self.ExpInfoButton = QtWidgets.QPushButton(self.EPNControlFrame)
                            self.ExpInfoButton.setGeometry(QRect(i,j,self.btnWidth,self.btnHeight))
                            self.ExpInfoButton.setObjectName(expInfo)
                            self.ExpInfoButton.setText("N/A")                            
                            self.ExpInfoButton.setEnabled(False);
                            i = i + self.btnWidth
                            OMFlag = False
                            

                    
                    #print(expKey, ' ',expInfo)
                    self.ExpInfoButton = QtWidgets.QPushButton(self.EPNControlFrame)
                    self.ExpInfoButton.setGeometry(QRect(i,j,self.btnWidth,self.btnHeight))
                    self.ExpInfoButton.setObjectName(expInfo)
                    self.ExpInfoButton.setText(expInfo)
                    self.ExpInfoButton.setCheckable(True);


                    if instDict[key][expKey] == "yes" and instrumentFlag == True:
                        self.ExpInfoButton.setChecked(True)                        
                    else:
                        self.ExpInfoButton.setChecked(False)
                        self.ExpInfoButton.setText("no")
                        instDict[key][expKey] = "no"


                    self.ExpInfoButton.toggle()
                    self.ExpInfoButton.clicked.connect(partial(self.ExpInfo_on_click,key,expKey,instDict))
                    expVal = key+"_"+expKey
                    self.EPNExpButtonDict[expVal] = self.ExpInfoButton
                    if expKey == "omchain":
                        self.ExpInfoButton.setText("N/A")
                        self.ExpInfoButton.setEnabled(False);
                        
                    if expKey == "Process" or expKey == "pileup" :
                        self.ExpInfoButton.hide()
                    
                    
                #EPNButtongList.append(EPNExpButtonDict)
                j=j+self.btnHeight
            #else:               
                #print (key,' ',val)
        
        self.height = j
               
    
    def getEPNDict(self):
        return self.procEPNDict
    
    def setFrame(self,newFrame):
        self.logger.info("UPDATING CONTROL FRAME")
        self.controlFrame = newFrame
        self.controlFrame.update()
        
    def getFrame2(self):
        return self.controlFrame
        
    def updateControlPanel(self,procEPNDict,procEMOS1Dict,procEMOS2Dict,
                           procRGS1Dict,procRGS2Dict,procOMDict):
        self.logger.info("Updating Buttons...")
        self.procEPNDict = procEPNDict
        self.procEMOS1Dict = procEMOS1Dict
        self.procEMOS2Dict = procEMOS2Dict
        self.procRGS1Dict = procRGS1Dict
        self.procRGS2Dict = procRGS2Dict
        self.procOMDict = procOMDict
        '''
        for instrument in Instruments:
            print ("Instrument "+str(instrument.name))
            #if instrument == Instruments.EPN:
            if self.procEPNDict['Processing'] == 'yes':
                self.EPNExpButtonDict[instrument.name].setChecked(False)
        self.changeButtonState(self.procEPNDict,False)
        self.changeButtonState(self.procEMOS1Dict,False)
        self.changeButtonState(self.procEMOS2Dict,False)
        self.changeButtonState(self.procRGS1Dict,False)
        self.changeButtonState(self.procRGS2Dict,False)
        #self.changeButtonState(self.procOMDict,False)
        
        if self.procEPNDict['Processing'] == 'yes':
            self.EPNExpButtonDict['EPN'].setChecked(False)        
        self.changeButtonState(self.procEPNDict,False)
        '''
        #print(self.procEPNDict)
    # Create the actions
    @pyqtSlot()
    def EPN_on_click(self,inst,instrumentDict):
        self.logger.info("EPN button clicked")
        self.logger.info("Status: "+str(self.EPNExpButtonDict[inst].isChecked()))    
        #Get all exposures               
        if self.EPNExpButtonDict[inst].isChecked() == True :
            instrumentDict["Processing"] = "no"
            self.changeButtonState(instrumentDict,True)
        else:
            instrumentDict["Processing"] = "yes"
            self.changeButtonState(instrumentDict,False)
    
    def Exp_on_click(self,a,instrumentDict):        
        self.logger.info("Exp on-click "+a)
        self.logger.info("Status "+str(self.EPNExpButtonDict[a].isChecked()))
        if self.EPNExpButtonDict[a].isChecked() == True :
            instrumentDict[a]["Process"] = "no"
            self.changeExpButtonState(instrumentDict,a,True)
        else:
            instrumentDict[a]["Process"] = "yes"
            self.changeExpButtonState(instrumentDict,a,False)
        
    def ExpInfo_on_click(self,key,val,instrumentDict):
        self.logger.info("Exp Info on-click "+key+" "+val)

        expVal=key+"_"+val
        self.logger.info("Status: "+str(self.EPNExpButtonDict[expVal].isChecked()))
        if self.EPNExpButtonDict[expVal].isChecked() == True:
            instrumentDict[key][val] = "no"
            self.EPNExpButtonDict[expVal].setText("no")
        else:            
            instrumentDict[key][val] = "yes"
            self.EPNExpButtonDict[expVal].setText("yes")
            instrumentDict[key]['Process'] = "yes"
            instrumentDict['Processing'] = "yes"
            self.EPNExpButtonDict[key].setChecked(False)
            self.EPNExpButtonDict[instrumentDict['Instrument']].setChecked(False)
    
    def changeButtonState(self,instrumentDict,valState):
        self.logger.info("VAL STATE "+ str(valState))
        for key,val in instrumentDict.items(): 
            if isinstance(val,dict):
                if valState == True:
                    instrumentDict[key]["Process"] = "no"                    
                else:
                    instrumentDict[key]["Process"] = "yes"
                    
                self.EPNExpButtonDict[key].setChecked(valState)
                for expKey,expInfo in val.items():
                    expVal = key+"_"+expKey  
                    if valState == True:
                        instrumentDict[key][expKey] = "no"
                        self.EPNExpButtonDict[expVal].setText("no")
                    else:
                        instrumentDict[key][expKey] = "yes"
                        self.EPNExpButtonDict[expVal].setText("yes")                    
                    self.EPNExpButtonDict[expVal].setChecked(valState)
            #else:
                #print(key,' ',val)
    def changeExpButtonState(self,instrumentDict,a,valState):                    
        for key,val in instrumentDict.items(): 
            if isinstance(val,dict):
                for expKey,expInfo in val.items():
                    expVal = a+"_"+expKey
                    if valState == True:
                        instrumentDict[a][expKey] = "no"
                        self.EPNExpButtonDict[expVal].setText("no")                        
                    else:
                        instrumentDict[a][expKey] = "yes"
                        instrumentDict['Processing'] = "yes"
                        self.EPNExpButtonDict[expVal].setText("yes")
                        self.EPNExpButtonDict[instrumentDict['Instrument']].setChecked(valState)
                    
                    self.EPNExpButtonDict[expVal].setChecked(valState)
                
        
    def activateSrcDetection(self,state):
        self.logger.info("Activate Source Detection to state "+str(state))
        
        for k,v in self.EPNExpButtonDict.items():            
            if "edetectchain" in k:
                if state is False:
                    self.EPNExpButtonDict[k].setChecked(False)
                    self.EPNExpButtonDict[k].setText("yes")
                else:
                    self.EPNExpButtonDict[k].setChecked(True)
                    self.EPNExpButtonDict[k].setText("no")
                    
