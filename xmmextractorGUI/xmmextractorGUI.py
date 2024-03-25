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

# xmmextractorGUI.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'xmmextractorGUI (xmmextractorGUI-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

# From this point onwards, all code is from xmmextractorGUI, except
# the replacement of the statement if __name__ == '__main__' which have been 
# replaced by def run(args). 
# How args are handled is also slightly changed.
import sys
import signal
import os
import stat
import re
import glob
import time
import logging
import requests
import shutil, sys 
from os import environ
from os.path import expanduser, basename
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import functools
from functools import partial
from pathlib import Path
import tarfile
import traceback
import subprocess
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QHBoxLayout, QTabWidget,QMainWindow,QPushButton, QVBoxLayout,\
    QLineEdit, QFormLayout, QMessageBox, QButtonGroup, QAbstractButton
from PyQt5.Qt import QApplication, QWidget, QPixmap, QLabel, QScrollArea,QFrame,QGroupBox,\
    QGridLayout, QSizePolicy, QLayout, QFileDialog, QObject, QDialog, QComboBox
from PyQt5.QtCore import QRect, QTimer,pyqtSlot, Qt, QFile, QTextStream
from xml.dom import minidom
from pysas.xmmextractorGUI.controlPanel import controlPanel
from pysas.xmmextractorGUI.createXML import createXML
from pysas.xmmextractorGUI.doIt import doIt
from pysas.xmmextractorGUI.showImageClass import PlotCanvas
from astropy.units import pixel
from astropy.io import fits
from astropy.table import Table
from _operator import length_hint, contains
from six import _meth_self
from fileinput import filename
from numpy import RAISE
from pyds9 import *

# The Python code for xmmextractorGUI should go inside run
class App(QMainWindow):
 
    def __init__(self,fileNameList):
        super().__init__()
        self.title = 'xmmextractor'
        self.left = 0
        self.top = 0
        self.width = 1600
        self.height = 1000
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        logger = logging.getLogger('xmmextractorGUI')
               
        DownloadODFFlag = False
        templateXMLFileName=""

        if fileNameList[0] == 'none':
           #Find the file in the SAS_DIR data directory or SAS_PATH...
            XMLFileSASDIR = Path(str(os.environ['SAS_DIR'])+'/lib/data/xmlTemplateData/xmmextractorDEFAULTParam.xml') 
            saspath = str(os.environ['SAS_PATH']).split(":")
            XMLFileSASPATH = Path(saspath[0]+'/lib/data/xmlTemplateData/xmmextractorDEFAULTParam.xml') 
            if  (XMLFileSASDIR.is_file()):
                self.xmldocFile = str(os.environ['SAS_DIR'])+'/lib/data/xmlTemplateData/xmmextractorDEFAULTParam.xml'               
            elif XMLFileSASPATH.is_file():
                self.xmldocFile = saspath[0]+'/lib/data/xmlTemplateData/xmmextractorDEFAULTParam.xml'
            else:
                logger.error("Default XML template file nor found")

            templateXMLFileName="/tmp/"+str(os.getpid())+"_xmmextractorDEFAULTParam.xml"
            shutil.copyfile( self.xmldocFile, templateXMLFileName)            
            self.xmldocFile= templateXMLFileName
            os.chmod(self.xmldocFile, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP |stat.S_IROTH | stat.S_IWOTH )
            DownloadODFFlag = True
        else:
            #Check if the file exists
            if  Path(fileNameList[0]).is_file():
                self.xmldocFile = fileNameList[0]
            else:
                logger.fatal("XML File "+fileNameList[0]+" does not exists")
                exit(1)
                    
        self.table_widget = mainPanel(self, self.xmldocFile,DownloadODFFlag,templateXMLFileName)
        self.setCentralWidget(self.table_widget)
        
        self.show()



class mainPanel(QWidget):
    
    def __init__(self,parent,xmldocFile,downloadFlag,templateXMLFileName):
        super(QWidget, self).__init__(parent)

        self.logger = logging.getLogger('xmmextractorGUI')
        self.logger.info('Creating main panel')

        self.XMMTimer = None
              
        self.xmldocFile = xmldocFile
        self.templateXMLFileName = templateXMLFileName
        self.xmldoc = minidom.parse(self.xmldocFile)
        self.DownloadODFFlag = downloadFlag
        #observation info
        self.obsInfoDict = dict()
        #procInfo
        self.procEPNDict = dict()
        self.procEMOS1Dict = dict()
        self.procEMOS2Dict = dict()
        self.procRGS1Dict = dict()
        self.procRGS2Dict = dict()
        self.procOMDict = dict()
        
        self.EPNExpoInfoDict = dict()
        self.EMOS1ExpoInfoDict = dict()
        self.EMOS2ExpoInfoDict = dict()
        self.RGS1ExpoInfoDict = dict()
        self.RGS2ExpoInfoDict = dict()
        self.OMExpoInfoDict = dict()
        
        self.tasksEPNDict = dict()
        self.tasksEMOS1Dict = dict()
        self.tasksEMOS2Dict = dict()
        self.tasksRGS1Dict = dict()
        self.tasksRGS2Dict = dict()
        self.tasksOMDict = dict()       
        
        self.expoTabProductDict = dict()
        self.paramsDict = dict()
        self.sn = 0.0
        self.bkgCR = 0.0
        self.SNValDict = dict()
        self.SNBKGValDict = dict()
        self.prod=""
        self.thresholdDict = dict()
        self.pid = None
        self.loginWidget = None
        #...Layout directory. Needed to refresh graphics


        #Ds9 instance
        self.p = None

        #Check SAS variables....
        self.checkSASEnviromentalVariables()

        #Parse XML file        
        self.parseXMLFile("init")
        #Screen

        self.layout = QVBoxLayout(self) 

        #Left block
        leftFrame = QFrame(self)
        leftFrame.setMinimumWidth(500)
        leftLayout = QVBoxLayout()
        leftFrame.setLayout(leftLayout)
        #Download Frame
        leftLayout.addWidget(self.getDownloadFrame())
        #Observation info
        leftLayout.addWidget(self.getObservationTab())
        #Output directory widgets need to be created
        #before ccf.cif and SUM.SAS exists
        outputGroupBox = QGroupBox(leftFrame)
        outputGroupBox.setTitle("Output Directory")
        outputLayout = QFormLayout()
        outputLabel = QLabel("Output Directory")
        self.outputField = QLineEdit()
        self.outputField.setText(os.getcwd())
        outputLayout.addRow(outputLabel, self.outputField)
        fileSearchLabel = QLabel("Search")
        fileDialogButton = QPushButton("Change Dir")
        fileDialogButton.clicked.connect(self.getDirectory)
        outputLayout.addRow(fileSearchLabel, fileDialogButton)
        outputGroupBox.setLayout(outputLayout)
        
        
        #Configuration Group Box
        confGroupBox = QGroupBox(leftFrame)
        confGroupBox.setTitle("Configuration")
        confLayout = QFormLayout()

        ccfLabel = QLabel("CCF File")
        self.ccfField = QLineEdit()            
        self.ccfField.setText(self.getFileName('.cif',str(self.outputField.text())))
        confLayout.addRow(ccfLabel, self.ccfField)

        odfLabel = QLabel("SUM.SAS File")
        self.odfField = QLineEdit()        
        self.odfField.setText(self.getFileName('SUM.SAS',str(self.outputField.text())))
        confLayout.addRow(odfLabel, self.odfField)
           
        confGroupBox.setLayout(confLayout)     
        leftLayout.addWidget(confGroupBox)
        #
        # Ouptut directory Group Box                       
        leftLayout.addWidget(outputGroupBox)
        #End of output directory Group Box
        #End of Left box
        
        #Initialize tab screen
        self.tabs = QTabWidget()  


        #Main tab
        self.MainTab = QWidget()
        self.MainTab.layout = QHBoxLayout()
        self.MainTab.layout.addWidget(leftFrame,1)
        

        self.epicImageFrame =  QFrame()
        self.epicImageLayout = QVBoxLayout()
        self.epicImageFrame.setLayout(self.epicImageLayout)



        if self.obsInfoDict['obsid'] != "":
            if (self.getEPICImage() == 'NOT FOUND'):            
                err = self.xsaRequest('IMA',self.obsInfoDict['obsid'],"","")
                self.readSUMASCFile()

        #Check if there is a ODF directoy in the current dir. If yes, read the SUM.ASC file and check if there is an
        #EPIC image
        odfPath = str(self.outputField.text())+'/ODF/'
        if os.path.isdir(odfPath) and self.obsInfoDict['obsid'] == "":
            self.readSUMASCFile()
            self.AIOButton.setEnabled(False)
            self.DownloadODFFlag = False
            # Set SAS_ODF...
            os.environ["SAS_ODF"]=odfPath


        if ( self.getEPICImage() != 'NOT FOUND'):
            if len((self.odf_ra_data.text())) == 0 :
                self.readSUMASCFile()
            ra = float(self.obsInfoDict['ra'])
            dec = float(self.obsInfoDict['dec'])
            #ra=float(self.odf_ra_data.text())
            #dec=float(self.odf_dec_data.text())
            self.epicImageLayout.addWidget(PlotCanvas(self, width=20, height=20,fileName=self.getEPICImage(),type='IM',ra=ra,dec=dec),4)             
        self.MainTab.layout.addWidget(self.epicImageFrame,1)
        self.tabs.addTab(self.MainTab, "Main")
        self.MainTab.setLayout(self.MainTab.layout)
        #self.ObsTab.layout.addWidget(PlotCanvas(self, width=5, height=5),2)
        #End of Main Tab

        #Observation Tab
        self.ObsTab = QWidget()                        
        self.ObsTab.layout = QHBoxLayout()        

        #self.ObsTab.layout.addWidget(self.getObservationTab(),1)
        #self.ObsTab.layout.addWidget(leftFrame,1)    

        #Right Frame
        rightFrame = QFrame()
        self.rightLayout = QVBoxLayout()
        rightFrame.setLayout(self.rightLayout)

        self.rightLayout.addWidget(self.getProductsTitle(),1)
        self.rightLayout.addStretch(0)
        self.controlButtonsFrame =  self.createControlPanel()
        self.rightLayout.addWidget(self.controlButtonsFrame,2)
               
        self.rightLayout.addWidget(self.addInstrumentExpoInfo(),1)
    
        self.ObsTab.layout.addWidget(rightFrame,3)
        
            


        self.tabs.addTab(self.ObsTab, "Settings")
        self.ObsTab.setLayout(self.ObsTab.layout)

        if self.DownloadODFFlag == False: 
            self.createInstrumentTabs()
  
        #Add tabs to Widget
        self.layout.addWidget(self.tabs)    
        self.layout.addWidget(self.getControlButtons(self))
        #Slot to check the focus on tabs
        self.tabs.currentChanged.connect(self.tabSelected)
    

        if self.DownloadODFFlag:
            self.runButton.setDisabled(True)



    def checkSASEnviromentalVariables(self):
        if "SAS_CCFPATH" not in os.environ: 
            self.logger.error("SAS_CCFPATH undefined. Please set the enviromental variable SAS_CCFPATH")
            exit(1)
    

    def on_PNinfoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())
    def on_EMOS1infoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())
    def on_EMOS2infoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())
    def on_RGS1infoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())
    def on_RGS2infoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())
    def on_OMinfoButton_click(self,bt):
        self.logger.info("Clicked " + bt.text())

    def addInstrumentExpoInfo(self):

        self.odfBrowserFrame = QFrame()
        LabelODFB = QLabel(self.odfBrowserFrame)
        LabelODFB.setText("ODF Browser")
        odfBrowserLayout = QVBoxLayout()
        self.odfBrowserFrame.setLayout(odfBrowserLayout)
        odfBrowserLayout.addWidget(LabelODFB,0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True) 
        scroll.setVisible(True)
        #scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
       
        InstrumentFrame = QFrame()        
        #InstrumentForm = QFormLayout()
        InstrumentLayout = QVBoxLayout()
        #InstrumentForm.setFormAlignment(Qt.AlignCenter)
        InstrumentFrame.setLayout(InstrumentLayout)

        self.PNButtonGroup = QButtonGroup()
        self.PNButtonGroup.buttonClicked[QAbstractButton].connect(self.on_PNinfoButton_click)         
        PNInstrument = QPushButton("EPN")
        self.PNButtonGroup.addButton(PNInstrument) 
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(PNInstrument)
        for expid,info in self.EPNExpoInfoDict.items():  
            PNinfoButton = QPushButton(expid)
            PNinfoButton.setFixedWidth(round(float(info['duration'])/50.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            PNinfoButton.setToolTip(toolTipString)
            self.PNButtonGroup.addButton(PNinfoButton)
            buttonLayout.addWidget(PNinfoButton)
        

        InstrumentLayout.addLayout(buttonLayout)
            
        self.EMOS1ButtonGroup = QButtonGroup()
        self.EMOS1ButtonGroup.buttonClicked[QAbstractButton].connect(self.on_EMOS1infoButton_click)   
        EMOS1Instrument = QPushButton("EMOS1")
        self.EMOS1ButtonGroup.addButton(EMOS1Instrument) 
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(EMOS1Instrument)
        for expid,info in self.EMOS1ExpoInfoDict.items():                        
            EMOS1infoButton = QPushButton(expid)
            EMOS1infoButton.setFixedWidth(round(float(info['duration'])/50.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            EMOS1infoButton.setToolTip(toolTipString)
            self.EMOS1ButtonGroup.addButton(EMOS1infoButton)
            buttonLayout.addWidget(EMOS1infoButton)

        InstrumentLayout.addLayout(buttonLayout)
  
        self.EMOS2ButtonGroup = QButtonGroup()
        self.EMOS2ButtonGroup.buttonClicked[QAbstractButton].connect(self.on_EMOS2infoButton_click)   
        EMOS2Instrument = QPushButton("EMOS2")
        self.EMOS2ButtonGroup.addButton(EMOS2Instrument) 
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(EMOS2Instrument)
        for expid,info in self.EMOS2ExpoInfoDict.items():                        
            EMOS2infoButton = QPushButton(expid)
            EMOS2infoButton.setFixedWidth(round(float(info['duration'])/50.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            EMOS2infoButton.setToolTip(toolTipString)
            self.EMOS2ButtonGroup.addButton(EMOS2infoButton)
            buttonLayout.addWidget(EMOS2infoButton)            

        InstrumentLayout.addLayout(buttonLayout)

        self.RGS1ButtonGroup = QButtonGroup()
        self.RGS1ButtonGroup.buttonClicked[QAbstractButton].connect(self.on_RGS1infoButton_click)        
        RGS1Instrument = QPushButton("RGS1")
        self.RGS1ButtonGroup.addButton(RGS1Instrument) 
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(RGS1Instrument)
        for expid,info in self.RGS1ExpoInfoDict.items():                        
            RGS1infoButton = QPushButton(expid)
            RGS1infoButton.setFixedWidth(round(float(info['duration'])/50.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            RGS1infoButton.setToolTip(toolTipString)
            self.RGS1ButtonGroup.addButton(RGS1infoButton)
            buttonLayout.addWidget(RGS1infoButton)

        InstrumentLayout.addLayout(buttonLayout)

        self.RGS2ButtonGroup = QButtonGroup()
        self.RGS2ButtonGroup.buttonClicked[QAbstractButton].connect(self.on_RGS2infoButton_click)
        RGS2Instrument = QPushButton("RGS2")
        self.RGS2ButtonGroup.addButton(RGS2Instrument)
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(RGS2Instrument)
        for expid,info in self.RGS2ExpoInfoDict.items():                        
            RGS2infoButton = QPushButton(expid)
            RGS2infoButton.setFixedWidth(round(float(info['duration'])/50.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            RGS2infoButton.setToolTip(toolTipString)
            self.RGS2ButtonGroup.addButton(RGS2infoButton)
            buttonLayout.addWidget(RGS2infoButton)
        
        InstrumentLayout.addLayout(buttonLayout)

        self.OMButtonGroup = QButtonGroup()
        self.OMButtonGroup.buttonClicked[QAbstractButton].connect(self.on_OMinfoButton_click)
        OMInstrument = QPushButton("OM")
        self.OMButtonGroup.addButton(OMInstrument)
        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignLeft)
        buttonLayout.addWidget(OMInstrument)
        for expid,info in self.OMExpoInfoDict.items():                        
            OMinfoButton = QPushButton(expid)
            OMinfoButton.setFixedWidth(round(float(info['duration'])/30.))
            toolTipString = "Duration: " +info['duration'] +"\n"+"Mode: "+info['mode']
            OMinfoButton.setToolTip(toolTipString)
            self.OMButtonGroup.addButton(OMinfoButton)
            buttonLayout.addWidget(OMinfoButton)
            

        InstrumentLayout.addLayout(buttonLayout)
        scroll.setWidget(InstrumentFrame)
        
        #return scroll
        odfBrowserLayout.addWidget(scroll,4)
        return self.odfBrowserFrame
      
    def getProductsTitle(self):
        controlFrame = QFrame()
        controlFrame.setObjectName("control")
        controlFrame.setMaximumSize(1000, 40)            
        btnWidth = 110
        btnHeight = 24
        btnStartXPos = 220
        btnStartYPos = 5
        #Product titles
        self.eventListProductTitle = QLineEdit(controlFrame)
        self.eventListProductTitle.setText("EventList")
        self.eventListProductTitle.setAlignment(Qt.AlignCenter)
        self.eventListProductTitle.setGeometry(QRect(btnStartXPos,btnStartYPos,btnWidth,btnHeight))
        self.eventListProductTitle.setReadOnly(True)
        self.GTIProductTitle = QLineEdit(controlFrame)
        self.GTIProductTitle.setText("GTI Filtering")
        self.GTIProductTitle.setGeometry(QRect(btnStartXPos+btnWidth,btnStartYPos,btnWidth,btnHeight))
        self.GTIProductTitle.setAlignment(Qt.AlignCenter)
        self.GTIProductTitle.setReadOnly(True)
        #self.pileupProductTitle = QLineEdit(controlFrame)
        #self.pileupProductTitle.setText("Pileup")
        #self.pileupProductTitle.setAlignment(Qt.AlignCenter)
        #self.pileupProductTitle.setGeometry(QRect(btnStartXPos+(2*btnWidth),btnStartYPos,btnWidth,btnHeight))
        #self.pileupProductTitle.setReadOnly(True)
        self.srcDetectProductTitle = QLineEdit(controlFrame)
        self.srcDetectProductTitle.setText("Src Detect")
        self.srcDetectProductTitle.setAlignment(Qt.AlignCenter)        
        self.srcDetectProductTitle.setGeometry(QRect(btnStartXPos+(2*btnWidth),btnStartYPos,btnWidth,btnHeight))
        self.srcDetectProductTitle.setReadOnly(True)
        self.spectraProductTitle = QLineEdit(controlFrame)
        self.spectraProductTitle.setText("Spectra")
        self.spectraProductTitle.setAlignment(Qt.AlignCenter)
        self.spectraProductTitle.setGeometry(QRect(btnStartXPos+(3*btnWidth),btnStartYPos,btnWidth,btnHeight))
        self.spectraProductTitle.setReadOnly(True)
        self.lightCurveProductTitle = QLineEdit(controlFrame)
        self.lightCurveProductTitle.setText("LightCurve")
        self.lightCurveProductTitle.setAlignment(Qt.AlignCenter)
        self.lightCurveProductTitle.setGeometry(QRect(btnStartXPos+(4*btnWidth),btnStartYPos,btnWidth,btnHeight))
        self.lightCurveProductTitle.setReadOnly(True)       
        self.fluxedProductTitle = QLineEdit(controlFrame)
        self.fluxedProductTitle.setText("Fluxed")
        self.fluxedProductTitle.setAlignment(Qt.AlignCenter)
        self.fluxedProductTitle.setGeometry(QRect(btnStartXPos+(5*btnWidth),btnStartYPos,btnWidth,btnHeight))
        self.fluxedProductTitle.setReadOnly(True)       
        
        return controlFrame
    
 
    def createInstrumentTabs(self):

        #EPN tab        
        if len(self.tasksEPNDict) != 0:
            self.EPNTab = QTabWidget()        
            self.createExpTab(self.EPNTab,self.tasksEPNDict,'EPN')                      
            self.tabs.addTab(self.EPNTab, "EPN")

        #EMOS1 tab
        if len(self.tasksEMOS1Dict) != 0:
            self.EMOS1Tab = QTabWidget()
            self.createExpTab(self.EMOS1Tab,self.tasksEMOS1Dict,'EMOS1')
            self.tabs.addTab(self.EMOS1Tab, "EMOS1")
        
        #EMOS2 tab
        if len(self.tasksEMOS2Dict) != 0:
            self.EMOS2Tab = QTabWidget()
            self.createExpTab(self.EMOS2Tab,self.tasksEMOS2Dict, 'EMOS2')
            self.tabs.addTab(self.EMOS2Tab, "EMOS2")

        #RGS1 tab
        if len(self.tasksRGS1Dict) !=0:
            self.RGS1Tab = QTabWidget()
            self.createExpTab(self.RGS1Tab,self.tasksRGS1Dict, 'RGS1')
            self.tabs.addTab(self.RGS1Tab, "RGS1")

        #RGS2 tab
        if len(self.tasksRGS2Dict) != 0:
            self.RGS2Tab = QTabWidget()
            self.createExpTab(self.RGS2Tab,self.tasksRGS2Dict,'RGS2')
            self.tabs.addTab(self.RGS2Tab, "RGS2")

        #OM tab
        if len(self.tasksOMDict) != 0:
            self.OMTab = QTabWidget()
            self.createExpTab(self.OMTab,self.tasksOMDict,'OM')
            self.OMTab.currentChanged.connect(self.ExpoTabSelected)
            self.tabs.addTab(self.OMTab, "OM")  
        
        #Add all instrument tabs        
        self.ObsTab.setLayout(self.ObsTab.layout)
        
        

    def getDirectory(self):
        searchDialog = QFileDialog()
        currDir = self.outputField.text()
        newDir = searchDialog.getExistingDirectory(self, 'Open a Folder', expanduser("~"),QFileDialog.ShowDirsOnly)
        if len(newDir) == 0:
            self.outputField.setText(currDir)            
        else:
            self.outputField.setText(newDir)            
            self.logger.info("New directory selected "+newDir)

    
    def getFileName(self,fileExtension,dirPath):
        self.logger.info("Search file name with pattern... "+ fileExtension)
        files = os.listdir(dirPath)
        fileName = [i for i in files if i.endswith(fileExtension)]
        if len(fileName) == 0:
            file = "NOT FOUND"
        else:
            file = dirPath+'/'+str(fileName[0])
        
        self.logger.info("Retrieving file with name "+ file)
        
        return file
    
    def findFileName(self,pattern,dirPath):
        filename="NOT FOUND"
        self.logger.info("Searching for files with pattern.... "+dirPath+pattern)
        for filename in glob.iglob(dirPath+"/"+pattern, recursive=True):
            self.logger.info("file found: " + filename)
        return filename;

    def checkFiles(self):
        self.logger.info("Checking files...")
        files = os.listdir(str(self.outputField.text()))
        
        fileToCheck = ['.cif','SUM.SAS','Param.xml']
        for fileExtension in fileToCheck:
            self.logger.info("file extension "+ fileExtension)           
            fileNames = [i for i in files if i.endswith(fileExtension)]                    
        
            if len(fileNames) == 0:                
                file = "NOT FOUND"
            elif len(fileNames) != 0 and fileExtension == '.cif':
                file = self.getFileName('.cif',str(self.outputField.text()))
                self.logger.info("Setting CCF file " + file)
                self.ccfField.setText(file)
            elif len(fileNames) != 0 and fileExtension == 'SUM.SAS':
                file = self.getFileName('SUM.SAS',str(self.outputField.text()))
                self.logger.info("Setting SUM.SAS file " + file)
                self.odfField.setText(file)
        
            self.logger.info("file name: "+ file)
            
    
    def f(self,executeJob,okButton,pid):
        #print("TEST "+str(executeJob.checkJobStatus()))
        #try:
            self.logger.info("Running product: "+ self.prod + " PID: " + str(pid))
            if (okButton.text() != "Running..."):
                self.prod =  okButton.text()
                self.logger.info("Current Product Button info " + self.prod)     

            if executeJob.checkJobStatus(pid):
                self.logger.info("Thread running")
                executeJob.updatePID(0) 
                okButton.setText("Running...")
                okButton.setEnabled(False)
            else:
                self.logger.info("Job with PID " + str(pid) + " ended")

                executeJob.updatePID(-1) 
                #currentProductLabel="UNDEF"
                self.XMMTimer.stop()
                self.XMMTime = None
                executeJob.closeLogFile()
                # Get the infor of the current Tab
                expoTab = self.tabs.currentWidget()                      

                if (self.tabs.currentIndex() > 1):
                    expoID = expoTab.tabText(expoTab.currentIndex())
                    currentExpoTab = self.expoTabProductDict[str(expoID)]
                    currentProductLabel=currentExpoTab.tabText(currentExpoTab.currentIndex()) 
                else:
                    currentProductLabel = self.tabs.tabText(self.tabs.currentIndex())

               
                self.checkFiles() 
                
                # if Current Tab is GTIFiltering, check for new output values

                if (currentProductLabel == "GTIFiltering"):
                   #... Read xmmextractor.info file to extract the PG filetering info
                    self.logger.info(currentProductLabel + " product finished.  EXPO " + str(expoID) )
                    self.get_SNand_BKG_CR(expoID,currentProductLabel)

                    okButton.setText(self.prod)

                    #... Plot the new SN and C/R                    
                    pattern = 'PG_*lightcurve_bkg_newgti.fit'
                    imageDirectory = str(self.outputField.text())+"/gti/"

                    #... Get the PlotCanvas frame
                    #... Refresh plot
                    expoTab = self.tabs.currentWidget()                      
                    expoID = expoTab.tabText(expoTab.currentIndex())
                    currentExpoTab = self.expoTabProductDict[str(expoID)]
                    currentProductLabel=currentExpoTab.tabText(currentExpoTab.currentIndex()) 
                
                    w = currentExpoTab.currentWidget()
                    plotCanvasWidget = w.layout().itemAt(0).widget().widget().layout().itemAt(1).widget()

                    #... Check for PG files
                    fileName = self.findFileName(pattern,imageDirectory)

                    #.. Refresh both!!!! LC and PG!!!                   
                    lcType = 'LC'
                    #if (fileName == "NOT FOUND"):
                    inst = expoID[:2]
                    expo = expoID[2:]
                    pattern = "PG_"+inst.lower()+"_"+expo+"*lightcurve_bkg*"
                    fileName = self.findFileName(pattern,imageDirectory)
                                        
                    key = str(expoID)+"_"+str(currentProductLabel)+"_BKG"    
                    PGKey = str(expoID)+"_GTIFiltering_params_5_PG_optimize_SN"
                    instrument = self.tabs.tabText(self.tabs.currentIndex())
                    if (instrument == 'EPN' and (self.paramsDict[PGKey].text() == "yes" or self.paramsDict[PGKey].text() == "YES" \
                                                     or self.paramsDict[PGKey].text() == "Y") ):                                                         
                        self.thresholdDict[self.tabs.tabText(self.tabs.currentIndex())] = float(self.SNBKGValDict[key].text())  
                    else:                        
                        paramValue = expoID+"_GTIFiltering_params_3_expression"
                        val =self.paramsDict[paramValue].text().split("<=")
                        self.thresholdDict[self.tabs.tabText(self.tabs.currentIndex())] = val[1]
                    
                    self.addCutValue2Fits(fileName,self.thresholdDict[self.tabs.tabText(self.tabs.currentIndex())])
                    plotCanvasWidget.plotLC(self.thresholdDict[self.tabs.tabText(self.tabs.currentIndex())],fileName)
                    self.resetApp("process")

                elif self.getFileName('.cif',str(self.outputField.text())) == "NOT FOUND":            
                    okButton.setText("Run cifbuild")
                elif self.getFileName('SUM.SAS',str(self.outputField.text())) == "NOT FOUND":
                    if self.getFileName('.cif',str(self.outputField.text())) != "NOT FOUND":       
                        os.environ['SAS_CCF']=self.getFileName('.cif',str(self.outputField.text()))                      
                    okButton.setText("Run odfingest")
                elif self.getFileName('Param.xml',str(self.outputField.text())) == "NOT FOUND":   
                    if self.getFileName('SUM.SAS',str(self.outputField.text())) != "NOT FOUND":
                        os.environ['SAS_ODF']=self.getFileName('SUM.SAS',str(self.outputField.text())) 
                    okButton.setText("Run odfParamCreator")
#                elif okButton.text() == "Run xmmextractor":
#                    print("DO NOTHING...")
                else:                        
                    okButton.setText("Run xmmextractor")
                    self.xmldocFile = self.getFileName("Param.xml", self.outputField.text())
                    self.xmldoc = minidom.parse(self.xmldocFile)
                    self.resetApp("process")

                #okButton.setText("Run")
                okButton.setEnabled(True)
        #except:
        #    print("ERROR checking job status") 


    # Create the actions
    @pyqtSlot()    
    def on_click(self):
        self.logger.info("Exiting...")
        #delete XML template file
        
        if  Path(self.templateXMLFileName).is_file():
           os.remove(self.templateXMLFileName)

        if self.pid is not None:
            try:
                self.logger.info("Killing process "+str(self.pid))     
                
                os.kill(self.pid, signal.SIGTERM)
            except OSError:
                self.logger.info("No process to stop...")     

        if self.p is not None:
            if self.p.pid.poll() is None :
                self.p.set('exit')

        QApplication.instance().exit()

    @pyqtSlot()
    def on_click_ok(self):     
        
        #prepare the processing paramaters for each specific analysis.
        #If user is in the "Setting" tab, it will execute xmmextractor as a whole
        #If user is in a particular tab, it will execute xmmextractor tailored for 
        #an specfic product.
        instrument = "" 
        expoID = ""
        currentProductLabel = "" 

        if (self.tabs.currentIndex() > 1 ):
            instrument = self.tabs.tabText(self.tabs.currentIndex())
            expoID =  self.tabs.currentWidget().tabText( self.tabs.currentWidget().currentIndex())
            currentExpoTab = self.expoTabProductDict[str(expoID)]
            currentProductLabel=self.expoTabProductDict[str(expoID)].tabText(self.expoTabProductDict[str(expoID)].currentIndex()) 

            #... AI Check this calls. Maybe not necessaries any longer 
            self.setCurrentProcessingParam(self.procEPNDict,expoID,currentProductLabel,instrument)
            self.setCurrentProcessingParam( self.procEMOS1Dict,expoID,currentProductLabel,instrument)
            self.setCurrentProcessingParam( self.procEMOS2Dict,expoID,currentProductLabel,instrument)
            self.setCurrentProcessingParam( self.procRGS1Dict,expoID,currentProductLabel,instrument)
            self.setCurrentProcessingParam( self.procRGS2Dict,expoID,currentProductLabel,instrument)
            self.setCurrentProcessingParam( self.procOMDict,expoID,currentProductLabel,instrument)


        self.XMMTimer = QTimer()

        self.logger.info("Create XML file")
        #... Control log...
        #Parse the epicsrc field and write 'yes' or 'no;
        if  self.odf_epicsr_data.currentText() == 'Proposal Central Target' or self.odf_epicsr_data.currentText() == 'User\'s Defined':
            if len(self.odf_ra_data.text()) == 0 or len(self.odf_dec_data.text()) == 0:
                msg = QMessageBox()
                msg.setWindowTitle("Coordinates")
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Empty RA or Dec fields")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.buttonClicked.connect(self.msgbtn)
                msg.exec_()
                return

            self.obsInfoDict['epicsrc'] = 'yes'                
        else:
            self.obsInfoDict['epicsrc'] = 'no'
        self.obsInfoDict['ra'] = self.odf_ra_data.text()
        self.obsInfoDict['dec'] = self.odf_dec_data.text()
        xmlfile = createXML(self.procEPNDict,self.procEMOS1Dict,\
                            self.procEMOS2Dict,self.procRGS1Dict,\
                            self.procRGS2Dict,self.procOMDict,self.obsInfoDict,\
                            self.tasksEPNDict,self.tasksEMOS1Dict,\
                            self.tasksEMOS2Dict,self.tasksRGS1Dict,\
                            self.tasksRGS2Dict,self.tasksOMDict,\
                            self.xmldocFile)

        os.chdir(self.outputField.text())
        if str(self.runButton.text()).find('cifbuild') != -1:
            self.logger.info("Ready to run cifbuild")
            executeJob = doIt('')
            executeJob.runSASCommand('cifbuild')
        elif str(self.runButton.text()).find('odfingest') != -1:
            self.logger.info("Ready to run odfingest")
            executeJob = doIt('')            
            executeJob.runSASCommand('odfingest')
        elif str(self.runButton.text()).find('odfParamCreator') != -1:
            self.logger.info("Ready to run odfParamCreator")
            executeJob = doIt('')
            executeJob.runSASCommand('odfParamCreator')
        else:
            self.logger.info("Ready to run xmmextractor")
            executeJob = doIt("xmmextractorParam.xml")
            executeJob.runSASCommand('xmmextractor')

        #executeJob.checkJobStatus()    
        self.logger.info("Starting New Job...")
        self.runButton.setEnabled(False)
        
        self.prod=""
        #get PID 
        self.pid = executeJob.getPID()
        self.logger.info("Current PID number " + str(self.pid))
        executeJob.setPID(self.pid)

        timerCallback = functools.partial(self.f, executeJob,self.runButton,self.pid)
        self.XMMTimer.timeout.connect(timerCallback)
        self.XMMTimer.start(1000)

        #self.f( executeJob,self.runButton, pid)

    def get_SNand_BKG_CR(self,expoID,product):
        self.logger.info("Retrieving S/N ration...")
        #... AI check for the file name
        self.logger.info("Reading output log...")
        filepath = self.outputField.text()+"/xmmextractor.info" 
        
        key = str(expoID)+"_"+product+"_SN"
        keyBKG = str(expoID)+"_"+product+"_BKG"

        #Wait until the file exists...
        while not os.path.exists(filepath):
            time.sleep(1)

        with open(filepath) as fp:  
            for cnt, line in enumerate(fp):
                if (line.find("Max S/N") != -1):
                    tmp = line.split(":")
                    self.sn = tmp[1]
                    self.logger.info("S/N value "+self.sn)        
                    self.SNValDict[key].setText(str(self.sn))
                if (line.find("Optimum Background Count Rate Cut") != -1):
                    tmp = line.split(":")
                    self.bkgCR = tmp[1]
                    self.logger.info("BKG value "+str(self.bkgCR))
                    self.SNBKGValDict[keyBKG].setText(str(self.bkgCR))
                    

    def parseXMLFile(self,level):
        self.logger.info("Parsing XML file")
        if level == "process":
            self.xmldocFile = self.getFileName("xmmextractorParam.xml", str(self.outputField.text()))
            self.xmldoc = minidom.parse(self.xmldocFile)
            itemlist = self.xmldoc.getElementsByTagName('OBSERVATION')
        else:
            itemlist = self.xmldoc.getElementsByTagName('OBSERVATION')
        #obsItemList = itemlist[0].getElementsByTagName('PARAM')
        obsItemList = itemlist[0].getElementsByTagName('PARAM')
        for element in obsItemList:
            self.obsInfoDict[element.getAttribute('id')] = element.getAttribute('default') 
            if element.getAttribute('id') == "EPN":
                self.procEPNDict['Instrument'] = element.getAttribute('id')
                self.procEPNDict['Processing'] = element.getAttribute('default')                    
            elif element.getAttribute('id') == "EMOS1":
                self.procEMOS1Dict['Instrument'] = element.getAttribute('id')
                self.procEMOS1Dict['Processing'] = element.getAttribute('default')                
            elif element.getAttribute('id') == "EMOS2":
                self.procEMOS2Dict['Instrument'] = element.getAttribute('id')
                self.procEMOS2Dict['Processing'] = element.getAttribute('default')
            elif element.getAttribute('id') == "RGS1":
                self.procRGS1Dict['Instrument'] = element.getAttribute('id')
                self.procRGS1Dict['Processing'] = element.getAttribute('default')
            elif element.getAttribute('id') == "RGS2":
                self.procRGS2Dict['Instrument'] = element.getAttribute('id')
                self.procRGS2Dict['Processing'] = element.getAttribute('default')
            elif  element.getAttribute('id') == "OM":
                self.procOMDict['Instrument'] = element.getAttribute('id')
                self.procOMDict['Processing'] = element.getAttribute('default')       
            else:
                self.logger.warning("Keyword not found "+element.getAttribute('id'));
        
        instItemList = self.xmldoc.getElementsByTagName('INSTRUMENT')
        i = 0
        j = 0
        for element in instItemList:
            instrument = element.getAttribute('value')
            expItemList = instItemList[i].getElementsByTagName('EXPOSURE')
            i = i + 1
            for expElement in  expItemList:
                expInfo = dict()
                expBrowserInfo = dict()       
                expId = expElement.getAttribute('expid')
                expBrowserInfo['duration'] = expElement.getAttribute('duration') 
                expBrowserInfo['mode'] = expElement.getAttribute('mode')
                
                expInfo['Process'] = expElement.getAttribute('process')  
                   
                productItemList = expElement.getElementsByTagName('PRODUCT')
                productInfo = dict()
                j = j + 1        
                for taskElement in productItemList:
                    product = taskElement.getAttribute('value')
                    taskProc = taskElement.getAttribute('process')   
                    expInfo[product] = taskProc
                    taskList = taskElement.getElementsByTagName('TASK')   
                    productDict = dict()  
                    #productPurpose = dict()  
                    taskCounter = 1  
                    for task in taskList:
                        #print("TASK_"+str(taskCounter)+" "+task.getAttribute('name'))
                        productDict["task_"+str(taskCounter)] = task.getAttribute('name')+"%"+task.getAttribute('purpose')
                        
                        paramList = task.getElementsByTagName('PARAM')
                        paramInfo = dict()
                        for param in paramList:
                            #print(param.getAttribute('id')+'='+param.getAttribute('default'))
                            paramInfo[param.getAttribute('id')] = param.getAttribute('default')
                        productDict["params_"+str(taskCounter)] = paramInfo 
                        taskCounter = taskCounter+1
                        #print(paramInfo) 
                    #print(productDict)
                        #productPurpose[task.getAttribute('purpose')] =  productDict   
                    productInfo[product] = productDict

                    #productInfo[product] =   productPurpose  
                #print(productInfo)                                

                if instrument == "EPN":
                    #print(expInfo)
                    #print(productInfo)
                    #print(expId)
                    self.procEPNDict[expId] =  expInfo
                    self.tasksEPNDict[expId] = productInfo
                    self.EPNExpoInfoDict[expId] = expBrowserInfo
                if instrument == "EMOS1":
                    self.procEMOS1Dict[expId] =  expInfo
                    self.tasksEMOS1Dict[expId] = productInfo
                    self.EMOS1ExpoInfoDict[expId] = expBrowserInfo
                if instrument == "EMOS2":
                    self.procEMOS2Dict[expId] =  expInfo
                    self.tasksEMOS2Dict[expId] = productInfo
                    self.EMOS2ExpoInfoDict[expId] = expBrowserInfo                                  
                if instrument == "RGS1":
                    self.procRGS1Dict[expId] =  expInfo
                    self.tasksRGS1Dict[expId] = productInfo
                    self.RGS1ExpoInfoDict[expId] = expBrowserInfo                                        
                if instrument == "RGS2":
                    self.procRGS2Dict[expId] =  expInfo
                    self.tasksRGS2Dict[expId] = productInfo
                    self.RGS2ExpoInfoDict[expId] = expBrowserInfo                                        
                if instrument == "OM":
                    self.procOMDict[expId] =  expInfo
                    self.tasksOMDict[expId] = productInfo
                    self.OMExpoInfoDict[expId] = expBrowserInfo                      
        
        
    def updateObsTab(self):
        self.logger.info('Update Observation Tab info')
        
        for key,val in self.obsInfoDict.items():
            if key != "analysisoption"  and \
                key != "OM_sourcematch" and key != "EPN" and key != "EMOS1" and\
                key != "EMOS2" and key != "RGS1" and key != "RGS2" and key != "OM":
                if key == "obsid":
                    self.odf_obsid_data.setText(val) 
                if key == "sourcename":
                    self.odf_sourcename_data.setText(val) 
                if key == "ra":
                    self.odf_ra_data.setText(val)                    
                if key == "dec":
                    self.odf_dec_data.setText(val)
                

    def getDownloadFrame(self):
    
        horizontalGroupBox = QGroupBox("Download ODF")
        odf_download_layout = QFormLayout() 
        odf_download_info = QFrame()
        tagDownloadLayout = QHBoxLayout()
        self.obsidLabel = QLabel('obsid')
        self.AIOButton = QPushButton()
        self.AIOButton.setText("Download ODF")      
        if self.DownloadODFFlag == False:
            self.AIOButton.setDisabled(True)
                    #tagLayout.addRow(label,AIOButton)
        tagDownloadLayout.addWidget(self.obsidLabel)
        self.odf_obsid_data = QLineEdit();
        self.odf_obsid_data.setToolTip("Current Observation ID to be processed")                                    
        self.AIOButton.clicked.connect(self.downloadODF)
        tagDownloadLayout.addWidget(self.odf_obsid_data)
        tagDownloadLayout.addWidget(self.AIOButton)
        odf_download_info.setLayout(tagDownloadLayout)  
        odf_download_layout.addRow(odf_download_info)       
        horizontalGroupBox.setLayout(odf_download_layout)        
        
        #Check if there is internet connection.
        if self.online(4) == False:
            self.AIOButton.setEnabled(False)
        
        
        return horizontalGroupBox


    def online(self,timeout):
        req = Request("http://www.google.com")
        try:
            response = urlopen(req)
        except HTTPError as e:
            self.logger.info('No internet connection')
            self.logger.error('Error code: ', e.code)
            return False
        except URLError as e:
            self.logger.info('No internet connection.')
            self.logger.error('Reason: ', e.reason)
            return False
        else:
            self.logger.info('Internet connection fine')
            return True
                        
    def getObservationTab(self):
        self.logger.info("Creating Observation Tab....")        
                        
        
        horizontalGroupBox = QGroupBox("ODF")

        odf_layout = QFormLayout() 
        for key,val in self.obsInfoDict.items():
            if key != "analysisoption"  and \
            key != "OM_sourcematch" and key != "EPN" and key != "EMOS1" and\
            key != "EMOS2" and key != "RGS1" and key != "RGS2" and key != "OM":                 
                #odf_info = QLabel(key); 
                #odf_info = QObject()
                if key == "obsid":
                    odf_info = QFrame()
                    if self.DownloadODFFlag == False:
                        self.AIOButton.setDisabled(True)

                    self.odf_obsid_data.setText(val);
                else:
                    odf_info = QLabel(key)
                      
                
                if key == "epicsrc":
                    self.odf_epicsr_data = QComboBox();
                    #self.odf_epicsr_data.addItem(val);
                    self.odf_epicsr_data.addItem('Proposal Central Target');
                    self.odf_epicsr_data.addItem('Central Target');
                    self.odf_epicsr_data.addItem('User\'s Defined');
                    if val == "no":
                        self.odf_epicsr_data.setCurrentIndex(1)   
                    self.odf_epicsr_data.currentIndexChanged.connect(self.EpicSrcSelectionchange)
                    self.odf_epicsr_data.setToolTip("Use proposal target coordinates")                    
                    self.odf_epicsr_data.setMinimumWidth(200)     
                    odf_layout.addRow(odf_info,self.odf_epicsr_data)
                elif key == "ra":
                    self.odf_ra_data = QLineEdit(val);
                    self.odf_ra_data.setToolTip("Source coordinates (RA,DEC) to extract products")
                    self.odf_ra_data.setMinimumWidth(200)
                    odf_layout.addRow(odf_info,self.odf_ra_data)
                    self.odf_ra_data.setEnabled(False)
                elif key == "dec":
                    self.odf_dec_data = QLineEdit(val);
                    self.odf_dec_data.setToolTip("Source coordinates (RA,DEC) to extract products")
                    self.odf_dec_data.setMinimumWidth(200)
                    odf_layout.addRow(odf_info,self.odf_dec_data)
                    self.odf_dec_data.setEnabled(False)
                elif key == "sourcename":
                    self.odf_sourcename_data = QLineEdit(val);
                    self.odf_sourcename_data.setToolTip("Label to tag all xmmextractor source products")
                    self.odf_sourcename_data.setMinimumWidth(200)
                    odf_layout.addRow(odf_info,self.odf_sourcename_data)                                                                                                                        
            else:
                self.logger.warning("Keyword not found "+val);                
                
        horizontalGroupBox.setLayout(odf_layout)        
        
        return horizontalGroupBox

    

    def EpicSrcSelectionchange(self):

        #for count in range(self.odf_epicsr_data.count()):
        #    print (self.odf_epicsr_data.itemText(count))
        #self.logger.info("Current index "+str(count)+" selection changed "+self.odf_epicsr_data.currentText() )
        if self.odf_epicsr_data.currentText() == 'Proposal Central Target':
            self.odf_epicsr_data.setToolTip("Use proposal target coordinates")     
            self.cp.activateSrcDetection(True)
            self.odf_ra_data.setText(str(self.obsInfoDict['ra']))
            self.odf_dec_data.setText(str(self.obsInfoDict['dec']))
            self.odf_ra_data.setEnabled(False)
            self.odf_dec_data.setEnabled(False)
        elif self.odf_epicsr_data.currentText() == 'User\'s Defined':
            self.odf_epicsr_data.setToolTip("Use User's coordinates")     
            self.cp.activateSrcDetection(True)  
            self.odf_ra_data.setText("")
            self.odf_dec_data.setText("")            
            self.odf_ra_data.setEnabled(True)
            self.odf_dec_data.setEnabled(True)
        else:
            self.odf_epicsr_data.setToolTip("Run source detection and automatically identify the central source ")           
            self.cp.activateSrcDetection(False)
            self.cp.changeButtonState(self.procEPNDict,False)
            self.cp.changeButtonState(self.procEMOS1Dict,False)
            self.cp.changeButtonState(self.procEMOS2Dict,False)
            self.odf_ra_data.setText("")
            self.odf_dec_data.setText("")            
            self.odf_ra_data.setEnabled(False)
            self.odf_dec_data.setEnabled(False)

         



    def getEPICImage(self):
        #First Check if the file exists...
        obsid = self.odf_obsid_data.text() 
        epicImageFileName = str(self.outputField.text())+"/P"+str(obsid)+"EPX000OIMAGE8000.FTZ"

        if (Path(epicImageFileName).is_file()):
            return epicImageFileName
        else:
            return 'NOT FOUND'
        
        
    def readSUMASCFile(self):
        odfDir = None
        if environ.get('SAS_ODF') is not None and Path(environ.get('SAS_ODF')).is_file():
            odfDir =self.getODFPathFromSUMSAS( os.environ['SAS_ODF'])       
        else:
            odfDir = str(self.outputField.text())+'/ODF/'

        sumASCFile = str(self.getFileName('SUM.ASC',odfDir.rstrip()))

        f = open(sumASCFile, 'r') # 'r' = read
        for line in f:
            if ('Observation/Slew Identifier' in line):
                val = line.split('/')
                val[0] = val[0].rstrip()
                self.odf_obsid_data.setText(val[0]) 
            if ('Target Name' in line):
                val = line.split('/')
                val[0] = val[0].rstrip()
                self.odf_sourcename_data.setText(val[0]) 
            if ('Target Right Ascension' in line):
                val = line.split('/')
                ra = round((float(val[0])*180.)/12.,5)
                #self.odf_ra_data.setText(str(ra))
                self.obsInfoDict['ra']=ra
                self.odf_epicsr_data.setItemText(0,"Proposal Central Target")
            if ('Target Declination' in line):
                val = line.split('/')
                dec = float(val[0])
                dec = round(dec,5)
                #self.odf_dec_data.setText(str(dec))
                self.obsInfoDict['dec']=dec
        f.close()

    def getODFPathFromSUMSAS(self,sasodfFile):
        odfDir = None
        f = open(sasodfFile, 'r') # 'r' = read
        for line in f:
            if ('PATH' in line):
                val = line.split(' ')
                odfDir = val[1]
        f.close()

        return odfDir
   

    def downloadODF(self):
        self.logger.info("Downloading ODF file")
        obsid = self.odf_obsid_data.text()        
        
        if not obsid:        
            msg = QMessageBox()
            msg.setWindowTitle("Observation ID")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("ObsID empty")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.buttonClicked.connect(self.msgbtn)
            msg.exec_()
        else:
            self.loginWidget = QDialog(self)
            self.loginWidget.setWindowTitle("ODF Download")
            xsaDetails = QFrame()
            uNameLayout = QFormLayout()
            xsaDetails.setLayout(uNameLayout)
            uName = QLabel("XSA login")
            self.userName = QLineEdit(self.loginWidget)
            uNameLayout.addRow(uName, self.userName)
            passw= QLabel("password")
            self.passWord = QLineEdit(self.loginWidget)
            uNameLayout.addRow(passw, self.passWord)
            self.passWord.setEchoMode(QLineEdit.Password)
            self.buttonLogin = QPushButton('Login', self)
            self.buttonLogin.clicked.connect(self.handleLogin)       
            self.buttonCancel = QPushButton('Cancel', self)
            self.buttonCancel.clicked.connect(self.handleCancel)       
            loginLayout = QVBoxLayout(self.loginWidget)
            #loginLayout.addWidget(self.userName)
            loginLayout.addWidget(xsaDetails)
            #loginLayout.addWidget(self.passWord)
            loginLayout.addWidget(self.buttonLogin)  
            loginLayout.addWidget(self.buttonCancel)  
            val = self.loginWidget.exec_()    
            err = 1
            if val == 1:
                err = self.xsaRequest('ODF',obsid,self.userName.text(),self.passWord.text())
                if err == 1 and val == 1:       
                    self.unpackODF()            
                    self.readSUMASCFile()
                    err = self.xsaRequest('IMA',obsid,self.userName.text(),self.passWord.text())

                    if  self.obsInfoDict['ra']:
                        ra=float(self.obsInfoDict['ra'])
                        if  self.obsInfoDict['dec']:
                            dec=float( self.obsInfoDict['dec'])
                            self.epicImageLayout.addWidget(PlotCanvas(self, width=20, height=20,fileName=self.getEPICImage(),type='IM',ra=ra,dec=dec),4) 
                            

    def msgbtn(i):
        print ("Button pressed is:"+str(i))

    def xsaRequest(self,product,obsid,userName, psw):
        err = 1
        try:
            command = None
            outFile = None
            self.logger.info("Downloading ODF....")

            if (userName != ""):                    
                if product == 'ODF':
                    command = "http://nxsa.esac.esa.int/nxsa-sl/servlet/data-action-aio?obsno="+str(obsid)+"&level=ODF&AIOUSER="+userName+"&AIOPWD="+psw                
                else:
                    command = "http://nxsa.esac.esa.int/nxsa-sl/servlet/data-action-aio?obsno="+str(obsid)+"&name=OIMAGE&level=PPS&extension=FTZ&AIOUSER="+userName+"&AIOPWD="+psw
            else:
                if product == 'ODF':
                    command = "http://nxsa.esac.esa.int/nxsa-sl/servlet/data-action-aio?obsno="+str(obsid)+"&level=ODF"               
                else:
                    command = "http://nxsa.esac.esa.int/nxsa-sl/servlet/data-action-aio?obsno="+str(obsid)+"&name=OIMAGE&level=PPS&extension=FTZ"
                
            if product == 'ODF':
                tarFileName = str(self.outputField.text())+"/"+str(obsid)+'.tar.gz'
                outFile = tarFileName
            else:
                outFile = str(self.outputField.text())+"/P"+str(obsid)+"EPX000OIMAGE8000.FTZ"

            r = requests.get(command,stream=True)

            if  r.status_code == 401 or r.status_code == 404 or r.status_code == 500:
                self.loginError = QDialog()
                self.loginError.setWindowTitle("ODF Download Error")                    
                loginMessages = QLineEdit(self.loginError)
                text = "Proprietary Data"
                
                if product == 'ODF':
                    if  r.status_code == 404:
                        text="Check ObsID number"
                    if  r.status_code == 401:
                        text="Check credentials"

                if product == 'IMA':
                    if  r.status_code == 404:
                        text="EPIC Image not found"

                if r.status_code == 500:
                    text="internal Error. Please try later"
                
                   
                loginMessages.setText(text)
                #loginMessages.setMinimumWidth(100)
                buttonLoginErrorOK = QPushButton('OK', self)
                buttonLoginErrorOK.clicked.connect(self.handleError)       
                loginLayout = QVBoxLayout(self.loginError)
                loginLayout.addWidget(loginMessages)
                loginLayout.addWidget(buttonLoginErrorOK)  
                err = self.loginError.exec_()    

                    
            if r.status_code == 200:
                with open(outFile, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                    self.logger.info("STATUS "+str(r.status_code))   

            # Check if the file is empty or does not exists....
            try:
                if os.path.getsize(outFile) > 0:
                    self.logger.info("Donwloading EPIC Iamge...")                
                else:
                    msg = QMessageBox()
                    msg.setWindowTitle("XSA Response")
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText("XSA File Empty. Please, check credentials")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.buttonClicked.connect(self.msgbtn)
                    msg.exec_()
                    self.status = -1
                    err = self.status
            except OSError as e:
                self.logger.error ("FILE DOES NOT EXIST")
                self.status = -1
                err = self.status
     
        except:
            self.error = traceback.format_exc()
            self.status = -1
            self.logger.error("Error downloading ODF file "+ str(self.error))
            err = self.status
            
        return err

    def handleError(self):
        self.loginError.reject()
        if  self.loginWidget :
            self.loginWidget.reject()

    def runInitialTasks(self, SASTask):
        self.logger.info("Running "+SASTask+" for data set "+str(os.environ['SAS_ODF']))
        os.chdir(str(self.outputField.text()))
        try:
            self.logger.info("Running cifbuild...")
            command = SASTask
            cifbuildProcess = subprocess.Popen(command,bufsize=64,
                                               stderr=subprocess.STDOUT,
                                               shell=True)
            cifbuildProcess.wait()
        except:
            self.error = traceback.format_exc()
            self.error = -1
            self.logger.error("Error running cifbuild..."+str(self.error))
        
        
    
    def unpackODF(self):
        self.logger.info("Unpacking ODF...")
        #Create ODF directory
        dirPath = str(self.outputField.text())
        self.logger.info("Creating ObsId directory... " + dirPath)
        path = Path(dirPath)
        path.mkdir(exist_ok=True)
        odfDir = dirPath+'/ODF' 
        self.logger.info("Creating ODF directory... " + odfDir)
        path = Path(dirPath)
        path.mkdir(exist_ok=True) 
        

        self.logger.info("untar ODF file...")
        tgzName = str(self.outputField.text())+'/'+str(self.odf_obsid_data.text())+'.tar.gz'

        try:            
            tar_file = tarfile.open(tgzName,'r:gz')
        except:
            message = "Could not open tar file: \n"\
                " The file probably does not have the correct format.\n"\
                " --> Inner message:"
            raise Exception(message)
                          
        tar_file.extractall(odfDir)
        #os.chdir(odfDir)        
        tarName= str(self.getFileName(".TAR",odfDir))
        self.logger.info("TAR File "+ tarName)
        tar_file = tarfile.open(tarName,'r')
        tar_file.extractall(odfDir)
        tar_file.close()
        os.environ["SAS_ODF"]=odfDir
        self.logger.info("ODF unpacked")
        self.runButton.setDisabled(False)                
        if os.path.isfile(tarName):
            os.remove(tarName)
            os.remove(tgzName)
        else:
            self.logger.info("Cannot Remove"+tarName+" file")


    def handleLogin(self):
        self.logger.info("USER "+ str(self.userName.text()))
        if self.userName.text() != "":
            os.environ["AIOUSER"]=str(self.userName.text())
            os.environ["AIOPWD"]=str(self.passWord.text())
        
        self.loginWidget.accept()

    def handleCancel(self):
        self.loginWidget.reject()
        
    def createControlPanel(self):
        self.cp = None
        self.cp = controlPanel(self.procEPNDict,self.procEMOS1Dict,\
                          self.procEMOS2Dict,self.procRGS1Dict,\
                          self.procRGS2Dict,self.procOMDict)       
        
        
        return self.cp.getFrame()


    def getControlButtons(self,bf):      
        buttonsFrame = QtWidgets.QFrame(bf)
        buttonsFrame.setObjectName("frame")
        buttonsBox = QHBoxLayout(buttonsFrame);        
        buttonsBox.addWidget(self.createRunButton(buttonsFrame));
        buttonsBox.addWidget(self.createCancelButton(buttonsFrame));

        return buttonsFrame

    def createRunButton(self,bf):
        self.runButton = QtWidgets.QPushButton(bf);
        self.runButton.setObjectName("Run");
        if self.getFileName('.cif',str(self.outputField.text())) == "NOT FOUND":            
            self.runButton.setText("Run cifbuild")
        elif self.getFileName('SUM.SAS',str(self.outputField.text())) == "NOT FOUND":
            if self.getFileName('.cif',str(self.outputField.text())) != "NOT FOUND":       
                os.environ['SAS_CCF']=self.getFileName('.cif',str(self.outputField.text()))
                if environ.get('SAS_ODF') is  None:
                    os.environ['SAS_ODF']= str(self.outputField.text())+"/ODF"
            self.runButton.setText("Run odfingest")
        elif self.getFileName('SUM.SAS',str(self.outputField.text())) != "NOT FOUND" \
                and self.getFileName('Param.xml',str(self.outputField.text())) == "NOT FOUND":
            os.environ['SAS_ODF']=self.getFileName('SUM.SAS',str(self.outputField.text())) 
            self.runButton.setText("Run odfParamCreator")        
        #elif self.getFileName('Param.xml',str(self.outputField.text())) == "NOT FOUND":
        #    self.runButton.setText("Run odfParamCreator")        
        else:                                   
            self.runButton.setText("Run xmmextractor")
            self.xmldocFile = self.getFileName("Param.xml", str(self.outputField.text()))
            self.xmldoc = minidom.parse(self.xmldocFile)
            if self.DownloadODFFlag == True:
                self.resetApp("init")
                        
        self.runButton.clicked.connect(self.on_click_ok)
        return self.runButton
    
 
    def resetApp(self,level):
        self.parseXMLFile(level)
        self.updateObsTab()
        self.ObsTab.layout.removeWidget(self.controlButtonsFrame)
        self.controlButtonsFrame.deleteLater()
        self.controlButtonsFrame = None
        
        self.ObsTab.layout.removeWidget(self.odfBrowserFrame)
        self.odfBrowserFrame.deleteLater()
        self.odfBrowserFrame = QFrame()
        self.rightLayout.addStretch(0)
        self.cp = None
        self.controlButtonsFrame =  self.createControlPanel()
        self.rightLayout.addWidget(self.controlButtonsFrame,3)
        self.rightLayout.addWidget(self.addInstrumentExpoInfo(),1)
        
        #removing Instrument Tabs
        if self.tabs.count() > 2:
            self.tabs.removeTab(2)
        #removing EMOS1&EMOS2
            self.tabs.removeTab(2)
            self.tabs.removeTab(2)
        #removing RGS1&RGS2
            self.tabs.removeTab(2)
            self.tabs.removeTab(2)
        #removing OM
            self.tabs.removeTab(2)
        self.createInstrumentTabs()  



    def createCancelButton(self,bf):
        self.cancelButton = QtWidgets.QPushButton(bf);
        self.cancelButton.setObjectName("Exit");
        #cancelButton.setGeometry(QRect(600, 30, 80, 22))
        self.cancelButton.setText("Exit");
        #cancelButton.clicked.connect(QCoreApplication.instance().quit);
        self.cancelButton.clicked.connect(self.on_click);
        return self.cancelButton
     
    def createExpTab(self,tab,expoInfo,instrument): 
        self.logger.info("Creating Exposure tabs... ")
        
        for expo,products in expoInfo.items():
            uniqueExpo = expo
            expo = expo[2:]
            self.logger.info("Creating EXPOSURE "+ uniqueExpo+ " tab")
            expTab = QTabWidget()
            #expTab.currentChanged.connect(partial(self.productTabSelected,productTab.currentIndex(), expo))            
            tab.addTab(expTab, uniqueExpo)
            
            for product, productss in products.items():
                self.logger.info("Creating PRODUCT "+product + " tab")
                #print (productss)
                productTab = QTabWidget()
                #prodLayout = QVBoxLayout()                                             
                #productTab.setLayout(prodLayout) 
                if product != "pileup":
                    expTab.addTab(productTab, product)
        
                totalFrame = QFrame(productTab)
                totalLayout = QHBoxLayout()
                totalFrame.setLayout(totalLayout)                
                frame4GroupBox = QFrame(totalFrame)
                #frame4GroupBox = QFrame(productTab)
                frameLayout = QVBoxLayout()
                frame4GroupBox.setLayout(frameLayout)
                taskName = ''
                param2Show = True

                #Add the switch for using standard High particle bkg filtering or PG_script
                if product == "GTIFiltering":
                    self.taskGroupBox = QGroupBox(frame4GroupBox) 
                    self.param_layout = QFormLayout()
                    self.taskGroupBox.setTitle("Flaring particle background method:")
                    param_info = QLabel("PG_script") 
                    param_info_data = QComboBox();
                    param_info_data.addItem(value);
                    param_info_data.addItem('yes');
                    param_info_data.currentTextChanged.connect(self.PGScriptSelectionchange)
                    self.param_layout.addRow(param_info, param_info_data)
                    self.taskGroupBox.setLayout(self.param_layout)  
                    frameLayout.addWidget(self.taskGroupBox)  

                for taskOrParamOrder,tasks in productss.items():
                    expressionParamKey = ''   

                    if isinstance(tasks,dict):                        
                        for param,value in tasks.items():                                
                            param_info = QLabel(param) 

                            ## Add to the evselect call in the GTIFiltering product the correct 
                            ## gti file name in case it exists....
                            if product == "GTIFiltering" and taskName == "evselect" and param == "expression":
                                #Check if there is a GTI corresponding with this exposure
                                if instrument == "EPN": inst="pn"
                                if instrument == "EMOS1": inst="m1"
                                if instrument == "EMOS2": inst="m2"
                                gtiFile = '*'+inst+"_gti_"+expo+"*.fits"
                                gtiFile = self. findFileName(gtiFile,str(self.outputField.text())+'/gti')
                                if Path(gtiFile).is_file():
                                    value = value.replace('gti.fits',gtiFile)

                                tasks[param] = value

                            ## Add to the evselct spectra call the GTI file generated 
                            ## in the GTIFiltering phase
                            if product == "spectra" and taskName == "evselect" and param == "expression":
                                #Check if there is a GTI corresponding with this exposure
                                if instrument == "EPN": inst="pn"
                                if instrument == "EMOS1": inst="m1"
                                if instrument == "EMOS2": inst="m2"
                                gtiFile = '*'+inst+"_gti_"+expo+"*.fits"
                                gtiFile = self. findFileName(gtiFile,str(self.outputField.text())+'/gti')
                                if Path(gtiFile).is_file():
                                    value = value.replace('gti.fits',gtiFile)
                                else:
                                    value = value.replace('gti(gti.fits,TIME) &&','')
                                
                                tasks[param] = value

                            #param_info_data.textChanged[str].connect(self.onChanged)
                            paramKey=uniqueExpo+"_"+product+"_"+taskOrParamOrder+"_"+param

                            if paramKey.find('srcexp') != -1:
                                srcParamKey = paramKey
                            elif paramKey.find('backexp') != -1:
                                bkgParamKey = paramKey
                            if paramKey.find('expression') != -1:
                                expressionParamKey = paramKey
                                                                
                            if taskName == 'tabgtigen' and param == 'expression':                               
                                tmp = value.split('=')                                
                                self.thresholdDict[instrument] = tmp[1]
                                
                            #param_info_data.editingFinished.\textChanged
                            #param_info_data.editingFinished.\

                            #param_info_data = None
                            #if param == "PG_optimize_SN":
                            #    param_info_data = QComboBox();
                            #    param_info_data.addItem(value);
                            #    param_info_data.addItem('yes');
                                #param_info_data.currentTextChanged.connect(self.PGScriptSelectionchange)
                                #param_info_data.setToolTip("Use proposal target coordinates")                    
                            #    param_info_data.setMinimumWidth(200)
                            #else:
                            param_info_data = QLineEdit();
                            font = QFont("SansSerif", 12)
                            #fm = QFontMetrics(font)
                            #pixelsWide = fm.width(value)
                            #if pixelsWide == 0:
                            #    pixelsWide = 20
                            #param_info_data.setFixedWidth(pixelsWide+4)
                            param_info_data.setText(value)                            

                            param_info_data.textChanged.\
                                connect(partial(self.handleEditingFinished,product,\
                                                    tasks,param,value,paramKey))

                            #used internally in xmmextractor PG_filer scrpt. It is not worht to set it here.
                            if param == "areafactor":
                                param_info_data.setEnabled(False)

                            self.param_layout.addRow(param_info, param_info_data)  
                            self.paramsDict[paramKey] =  param_info_data

                            if taskName == "xmmextractor" and (param == "interactivity" or param == "areafactor" ):
                                 param2Show = False
                            else:
                                param2Show = True

                        if param2Show == True:
                            self.taskGroupBox.setLayout(self.param_layout)  
                            frameLayout.addWidget(self.taskGroupBox)   
                        else:
                            self.taskGroupBox.hide()                        

                        imageDirectory = str(self.outputField.text())+"/images/"
                        #Check if there is a Timing file. In this case, open in 
                        pattern = '*'+instrument+"*"+expo+'*'+'Timing'+'*'+'Image.ds'
                        fileName = self.findFileName(pattern,imageDirectory)
                        if fileName == 'NOT FOUND':
                            pattern = '*'+instrument+"*"+expo+'*'+'Image.ds'
                            fileName = self.findFileName(pattern,imageDirectory)

                        if ( (product == 'spectra' and taskName == 'especget') or
                            (product == 'GTIFiltering' and taskName == 'PG_script')):                             
                            ds9Frame = QFrame()
                            ds9Layout = QHBoxLayout()                            
                            ds9Button = QPushButton(ds9Frame)
                            ds9Button.setText('ds9')
                            ds9Button.clicked.connect(partial(self.ds9InAction,fileName))
                            ds9Layout.addWidget(ds9Button)  
                            ds9GetSrcButton = QPushButton(ds9Frame)
                            ds9GetSrcButton.setText("Get Source region")
                            expr=self.getImageMode(fileName)
                            ds9GetSrcButton.clicked.connect(partial(self.ds9GetSrcRegion,srcParamKey,expr) )
                            ds9Layout.addWidget(ds9GetSrcButton)
                            ds9GetBkgButton = QPushButton(ds9Frame)
                            ds9GetBkgButton.setText("Get Background region")
                            ds9GetBkgButton.clicked.connect(partial(self.ds9GetBkgRegion,bkgParamKey,expr))
                            ds9Layout.addWidget(ds9GetBkgButton)
                            ds9Frame.setLayout(ds9Layout)
                            self.param_layout.addRow(ds9Frame)
                        if ( product == 'GTIFiltering' and taskName == 'PG_script' and instrument == "EPN" ):
                            resultFrame = QFrame()
                            resultLayout = QFormLayout()
                            SNLabel = QLabel()
                            self.SNVal = QLineEdit()
                            SNLabel.setText("MAX S/N")
                            self.SNVal.setText(str(self.sn))
                            paramSNKey=uniqueExpo+"_"+product+"_SN"
                            self.SNValDict[paramSNKey] = self.SNVal
                            BKGLabel = QLabel()
                            BKGVal =  QLineEdit()
                            BKGLabel.setText("Optimum Background Count Rate Cut (cts/sec)")
                            BKGVal.setText(str(self.bkgCR))
                            paramBKGKey=uniqueExpo+"_"+product+"_BKG"
                            self.SNBKGValDict[paramBKGKey]=BKGVal
                            resultLayout.addRow(SNLabel, self.SNVal)
                            resultLayout.addRow(BKGLabel,BKGVal)
                            resultFrame.setLayout(resultLayout)
                            self.param_layout.addRow(resultFrame)
                        if  ( product == 'lightcurve' and taskName == 'evselect' and param == 'timebinsize' ):
                            ds9Frame = QFrame()
                            ds9Layout = QHBoxLayout()                            
                            ds9Button = QPushButton(ds9Frame)
                            ds9Button.setText('ds9')
                            ds9Button.clicked.connect(partial(self.ds9InAction,fileName))
                            ds9Layout.addWidget(ds9Button)  
                            ds9GetButton = QPushButton(ds9Frame)
                            ds9GetButton.setText("Get region")
                            expr=self.getImageMode(fileName)
                            ds9GetButton.clicked.connect(partial(self.ds9GetSrcRegion,expressionParamKey,expr) )
                            ds9Layout.addWidget(ds9GetButton)
                            ds9Frame.setLayout(ds9Layout)
                            self.param_layout.addRow(ds9Frame)                          
                        '''
                        if expressionParamKey.find('expression') != -1:
                                ds9Frame = QFrame()
                                ds9Layout = QHBoxLayout()                            
                                ds9ExpressionButton = QPushButton(ds9Frame)
                                ds9ExpressionButton.setText("Apply new expression")
                                print ("PARAM "+paramKey)                            
                                ds9ExpressionButton.clicked.connect(partial(self.ds9ExpressionButton,expressionParamKey) )
                                ds9Layout.addWidget(ds9ExpressionButton)
                                ds9Frame.setLayout(ds9Layout)
                                self.param_layout.addRow(ds9Frame)
                        '''                                                                                                                 
                    else:                            
                        #Tasks....
                        self.taskGroupBox = QGroupBox(frame4GroupBox) 
                        self.param_layout = QFormLayout()
                        tmp = tasks.split("%")
                        tasks = tmp[0]
                        purpose = tmp[1]
                        self.taskGroupBox.setTitle(tasks+" ("+purpose+")")
                        taskName = tasks
                        if taskName == "PG_script":
                            self.taskGroupBox.setEnabled(False)
            
                ##Add result panel. It returns a dictionary with file names and purpose
                self.resultFrame = QGroupBox()
                #XMLFileSASDIR = Path(str(os.environ['SAS_DIR'])+'/lib/data/xmlTemplateData/xmmextractorDEFAULTParam.xml') 
                
                styleSheet = 'none'
                if ("SAS_PATH" in os.environ):
                    qssdir = str(os.environ['SAS_PATH'])
                    qssdirs = re.split(':',qssdir)
                    for k in qssdirs:
                        f = Path(k+"/lib/python/pysas/xmmextractorGUI/resultsStyles.qss")
                        if (f.exists() ):
                            styleSheet= str(f)
                            break
                else:
                    styleSheet= Path(str(os.environ['SAS_DIR'])+"/lib/python/pysas/xmmextractorGUI/resultsStyles.qss") 
                            
                #styleSheet= Path(str(os.environ['SAS_DIR'])+"/lib/python/pysas/xmmextractorGUI/resultsStyles.qss")
                
                self.resultFrame.setStyleSheet(self.getStyleSheet(str(styleSheet)))
                self.resultFrame.setTitle("RESULT PANEL")
                self.resultLayout = QFormLayout()
                testLabel = QLabel()
                productInfoDict = self.getProductResults(instrument,expo,product)                
                for k,v in productInfoDict.items():
                    testLabel.setText("RESULT EXAMPLE")
                    label1 = QLabel(k)
                    label2 = QLineEdit(v)
                    label2.setFixedWidth(420)
                    #label2.setEnabled(False)
                    label2.setReadOnly(True)
                    self.resultLayout.addRow(label1,label2)

                self.resultFrame.setLayout(self.resultLayout)
                frameLayout.addWidget(self.resultFrame)
                ##ADDED
                self.logger.info("Creating and adding scroll area...")
                scroll = QScrollArea()        
                scroll.setWidgetResizable(True)
                #scroll.setFixedHeight(400)
                if instrument == "EPN": inst="pn"
                if instrument == "EMOS1": inst="m1"
                if instrument == "EMOS2": inst="m2"
                if (instrument == 'EPN' or instrument == 'EMOS1' or instrument == 'EMOS2')\
                    and product == 'EventList':
                    totalLayout.addWidget(frame4GroupBox,1)
                    imageDirectory = str(self.outputField.text())+"/images/"
                    #Check if a Timing image exists and if exists use it
                    pattern = '*'+instrument+"*"+expo+'*'+'Timing'+'*'+'Image.ds'
                    fileName = self.findFileName(pattern,imageDirectory)
                    if fileName == 'NOT FOUND':
                        pattern = '*'+instrument+"*"+expo+'*'+'Image.ds'
                        fileName = self.findFileName(pattern,imageDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=20, height=20,fileName=fileName,type='IM'),4) 
                    scroll.setWidget(totalFrame)
                elif (instrument == 'EPN' or instrument == 'EMOS1' or instrument == 'EMOS2')\
                    and product == 'GTIFiltering':
                    totalLayout.addWidget(frame4GroupBox,1)
                    imageDirectory = str(self.outputField.text())+"/gti/"

                    pattern = "*"+inst+'*'+expo+'*lightcurve_bkg_newgti.fit'

                    fileName = self.findFileName(pattern,imageDirectory)
                    lcType = 'LC'

                    if fileName == "NOT FOUND" and instrument == "EPN":
                       # pattern = 'PG_sn*.fits'
                       # fileName = self.findFileName(pattern,imageDirectory)
                       # lcType='PG'
                       # if (fileName == "NOT FOUND"):
                        pattern = 'PG_'+inst+"*"+expo+'*lightcurve_bkg_newgti.fit'
                        fileName = self.findFileName(pattern,imageDirectory)
                        #lcType = 'LC'                           
                        #else:
                        key = str(uniqueExpo)+"_"+str(product)+"_BKG"
                        PGKey = str(uniqueExpo)+"_GTIFiltering_params_5_PG_optimize_SN"
                        if (instrument == 'EPN' and (self.paramsDict[PGKey] == "yes" or self.paramsDict[PGKey] == "YES" \
                           or self.paramsDict[PGKey] == "Y") ):                                                         
                             self.thresholdDict[instrument] = float(self.SNBKGValDict[key].text())                  


                    totalLayout.addWidget(PlotCanvas(self, width=5, height=5,fileName=fileName,type=lcType,threshold=self.thresholdDict[instrument]),3)

                    #... Add the Frame to the Prodcut tab
                    scroll.setWidget(totalFrame)
                elif (instrument == 'EPN' or instrument == 'EMOS1' or instrument == 'EMOS2')\
                    and product == 'spectra':
                    totalLayout.addWidget(frame4GroupBox,1)
                    imageDirectory = str(self.outputField.text())+"/spectra/"
                    pattern = '*'+inst+"*"+expo+'*'+'_source_spectrum*'
                    fileName = self.findFileName(pattern,imageDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=5, height=5,fileName=fileName,type='SP'),3)
                    scroll.setWidget(totalFrame)
                elif (instrument == 'EPN' or instrument == 'EMOS1' or instrument == 'EMOS2')\
                    and product == 'lightcurve':
                    totalLayout.addWidget(frame4GroupBox,1)
                    imageDirectory = str(self.outputField.text())+"/lcurve/"
                    pattern = '*'+inst+"*"+expo+'*'+'_sourcebkgsubtracted*'
                    fileName = self.findFileName(pattern,imageDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=5, height=5,fileName=fileName,type='LC'),3)
                    scroll.setWidget(totalFrame)
                elif (instrument == 'EPN' or instrument == 'EMOS1' or instrument == 'EMOS2')\
                    and product == 'edetectchain':
                    totalLayout.addWidget(frame4GroupBox,1)
                    imageDirectory = str(self.outputField.text())+"/images/"
                    pattern = '*'+inst+"*"+expo+'*'+'image_full.fits'
                    fileName = self.findFileName(pattern,imageDirectory)
                    pattern = '*'+inst+'*'+expo+'*'+'_ImagingEvts_emllist.fits'
                    emlFileName = self.findFileName(pattern,imageDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=20, height=20,fileName=fileName,type='DT',emllistFileName=emlFileName),4) 
                    scroll.setWidget(totalFrame)                
                elif (instrument == 'RGS1' or instrument == 'RGS2') and product == 'EventList':
                    totalLayout.addWidget(frame4GroupBox,1)
                    rgsDirectory = str(self.outputField.text())+"/rgs/"
                    pattern = 'spatial_'+instrument.lower()+'_'+expo+'.fit'
                    fileName = self.findFileName(pattern,rgsDirectory)
                    pattern = 'pi_'+instrument.lower()+'_'+expo+'.fit'
                    enerFileName = self.findFileName(pattern,rgsDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=2, height=2,fileName=fileName,type='RGS',rgsEnerFileName=enerFileName),2) 
                    scroll.setWidget(totalFrame)
                elif (instrument == 'RGS1' or instrument == 'RGS2') and  product == 'spectra':
                    totalLayout.addWidget(frame4GroupBox,1)
                    rgsDirectory = str(self.outputField.text())+"/rgs/"
                    shortInstrument = 'R1'

                    if instrument != 'RGS1':
                        shortInstrument = 'R2'
                    pattern = '*'+shortInstrument+expo+'SRSPEC1001.FIT'

                    fileName = self.findFileName(pattern,rgsDirectory)        
                    totalLayout.addWidget(PlotCanvas(self, width=2, height=2,fileName=fileName,type='RGSSpectra'),2) 
                    scroll.setWidget(totalFrame)
                elif (instrument == 'RGS1' or instrument == 'RGS2') and product == 'fluxing':
                    totalLayout.addWidget(frame4GroupBox,1)
                    rgsDirectory = str(self.outputField.text())+"/rgs/"

                    pattern = '*fluxed1000.FIT'                    
                    fileName = self.findFileName(pattern,rgsDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=2, height=2,fileName=fileName,type='RGSFlux'),2) 
                    scroll.setWidget(totalFrame)
                elif (instrument == 'RGS1' or instrument == 'RGS2') and product == 'lightcurve':
                    totalLayout.addWidget(frame4GroupBox,1)
                    rgsDirectory = str(self.outputField.text())+"/rgs/"
                    shortInstrument = 'R1'
                    if instrument != 'RGS1':
                        shortInstrument = 'R2'
                    #pattern = '*'+shortInstrument+expo+'SBTSR_1001.FIT'             
                    pattern = '*'+shortInstrument+expo+"*SRTSR*.FIT"             
                    fileName = self.findFileName(pattern,rgsDirectory)
                    totalLayout.addWidget(PlotCanvas(self, width=2, height=2,fileName=fileName,type='RGSLC'),2) 
                    scroll.setWidget(totalFrame)
                else:
                    scroll.setWidget(frame4GroupBox)
                

                layout = QVBoxLayout(productTab)
                layout.addWidget(scroll)              
            self.expoTabProductDict[uniqueExpo] = expTab 
            expTab.currentChanged.connect(partial(self.productTabSelected,instrument,uniqueExpo))                                               
        self.logger.info("Exposure Tab created")       


    def PGScriptSelectionchange(self,value):
        #print ("Items in the list are : " +value)
        expoID = self.tabs.currentWidget().tabText(self.tabs.currentWidget().currentIndex())
        currentExpoTab = self.expoTabProductDict[str(expoID)]	
        w = currentExpoTab.currentWidget()
        #w.layout().itemAt(0).widget().widget().layout().itemAt(1).widget()
        frameTab = w.layout().itemAt(0).widget().widget().layout().itemAt(0).widget()
        #kk.layout().itemAt(3).setEnabled(True)    
        for i in range(1,frameTab.layout().count()-1):
            if value == 'yes':
                if  frameTab.layout().itemAt(i).widget().title() == "PG_script":                
                    frameTab.layout().itemAt(i).widget().setEnabled(True)
                    frameTab.layout().itemAt(i).widget().layout().itemAt(1).widget().setText("yes")
                else:
                    frameTab.layout().itemAt(i).widget().setEnabled(False)
            else:
                if  frameTab.layout().itemAt(i).widget().title() == "PG_script":        
                    frameTab.layout().itemAt(i).widget().setEnabled(False)
                    frameTab.layout().itemAt(i).widget().layout().itemAt(1).widget().setText("no")
                else:
                    frameTab.layout().itemAt(i).widget().setEnabled(True)


#        if value == 'yes':
#            frameTab.layout().itemAt(1).widget().setEnabled(False)
#            frameTab.layout().itemAt(2).widget().setEnabled(False)
#            frameTab.layout().itemAt(3).widget().setEnabled(False)
#            frameTab.layout().itemAt(4).widget().setEnabled(True)
#        else:
#            frameTab.layout().itemAt(1).widget().setEnabled(True)
#            frameTab.layout().itemAt(2).widget().setEnabled(True)
#            frameTab.layout().itemAt(3).widget().setEnabled(True)
#            frameTab.layout().itemAt(4).widget().setEnabled(False)




    def getProductResults(self,instrument,expo,product):

        productInfoDict = {}

        ##EPIC:EventList -> EventList Files and images
        ##EPIC:GTIFiltering -> GTI file
        ##EPIC:Pileup -> epatplot output  <-- TEMPORARILY REMOVED
        ##EPIC:edetectchain -> Source List and image
        ##EPIC:spectra -> src+bkg spectra files, arf and rmf
        ##EPIC:lightcurve -> bkg substracted src light curve
        ###Remove the INST name....
        if instrument == "EPN": inst="pn"
        if instrument == "EMOS1": inst="m1"
        if instrument == "EMOS2": inst="m2"

        #expo = expo[2:]        
        if (instrument == "EPN" or instrument == "EMOS1" or instrument == "EMOS2"):
            if (product == "EventList"):                
                if (instrument == "EPN"):
                    productInfoDict = self.getProductsFileNames("pn",expo,product,instrument+"_"+expo+"*Evts.ds","EPN Event File for exposure "+expo)
                else:
                    productInfoDict = self.getProductsFileNames("mos",expo,product,instrument+"_"+expo+"*Evts.ds","EMOS Event File for exposure "+expo)
            if (product == "GTIFiltering"):
                productInfoDict = self.getProductsFileNames("gti",expo,product,inst+"_gti_"+expo,"GTI file for exposure "+expo)
            #if (product == "Pileup"):                
            #    self.logger.info("Pileup")
            if (product == "edetectchain"):                
                productInfoDict = self.getProductsFileNames("images",expo,product,inst+"_"+expo+"*emllist*","Detection source list for exposure "+expo)
            if (product == "spectra"):
                productInfoDict = self.getProductsFileNames("spectra",expo,product,inst+"_"+expo+"*_source_spectrum*","Source spectra for exposure"+expo)
                productInfoDict.update(self.getProductsFileNames("spectra",expo,product,inst+"_"+expo+"*_background_spectrum*","Background spectra for exposure "+expo))
                productInfoDict.update(self.getProductsFileNames("spectra",expo,product,inst+"_"+expo+"*src.arf","Effective Area file for exposure "+expo))
                productInfoDict.update(self.getProductsFileNames("spectra",expo,product,inst+"_"+expo+"*src.rmf","Response Matrix file for exposure "+expo))

            if (product == "lightcurve"):
                productInfoDict = self.getProductsFileNames("lcurve",expo,product,inst+"_"+expo+"*_sourcebkgsubtracted*","Lightcurve file for exposure "+expo)   


        if (instrument == "RGS1" or instrument == "RGS2"):
            if (product == "EventList"):                
                productInfoDict = self.getProductsFileNames("rgs",expo,product,expo+"*EVENLI*.FIT","RGS Event file for exposure "+expo)
            if (product == "spectra"):                
                productInfoDict = self.getProductsFileNames("rgs",expo,product,expo+"*SRSPEC1*.FIT","RGS Source spectra for exposure "+expo)
                productInfoDict.update(self.getProductsFileNames("rgs",expo,product,expo+"*BGSPEC1*.FIT","RGS Background spectra for exposure "+expo))
                productInfoDict.update(self.getProductsFileNames("rgs",expo,product,expo+"*RSPMAT1*.FIT","RGS Response Matrix for exposure "+expo))
            if (product == "fluxing"):                
                productInfoDict = self.getProductsFileNames("rgs",'OBX',product,'OBX'+"*fluxed1*.FIT","RGS Fluxed file for exposure "+expo)
            if (product == "lightcurve"):
                productInfoDict = self.getProductsFileNames("rgs",expo,product,expo+"*SRTSR*.FIT","RGS Lightcurve file for exposure "+expo)
                #productInfoDict = self.getProductsFileNames("lcurve",expo,product,expo+"*.lc","RGS Lightcurve file for exposure "+expo)

            
        if (instrument == "OM"):
            self.logger.info("OM")
        
        
        ##RGS:EventList -> Event file
        ##RGS:LightCurve -> RGS lightcurve
        ##OM: -> OMproducts
        return productInfoDict


    def getProductsFileNames(self,path,expo,product,pattern,comment):
        res = {}
        dirPath = str(self.outputField.text())+"/"+path+"/"
        pattern = "*"+pattern+"*"

        for filename in glob.iglob(dirPath+"/"+pattern, recursive=True):
            res[comment] = basename(filename)
        return res

    def getStyleSheet(self, path):
        f = QFile(path)
        f.open(QFile.ReadOnly | QFile.Text)
        stylesheet = QTextStream(f).readAll()
        f.close()
        return stylesheet             

    def tabSelected(self,arg=None):
        self.logger.info("Current Tab Title " + str(self.tabs.tabText( arg)))

        if arg > 1:
            self.logger.info("Current Tab Index: "+str(arg))       
            instName = self.tabs.tabText( self.tabs.currentIndex())
            expoTab = self.tabs.currentWidget()           

            expoID = expoTab.tabText(expoTab.currentIndex())
            currentExpoTab = self.expoTabProductDict[str(expoID)]
            currentProductLabel=currentExpoTab.tabText(currentExpoTab.currentIndex()) 

            text = "Create "+currentProductLabel+" for " + instName+ " exposure "+str(expoID)
            self.runButton.setText(text)           
            if (self.checkProductGeneration(currentProductLabel,instName,str(expoID)) == False):
                self.runButton.setEnabled(False)
        else:
            self.logger.info("Settings tab.... "+ str(arg))          
            if self.getFileName('.cif',str(self.outputField.text())) == "NOT FOUND":            
                    self.runButton.setText("Run cifbuild")
            elif self.getFileName('SUM.SAS',str(self.outputField.text())) == "NOT FOUND":
                if self.getFileName('.cif',str(self.outputField.text())) != "NOT FOUND":       
                    os.environ['SAS_CCF']=self.getFileName('.cif',str(self.outputField.text()))                      
                self.runButton.setText("Run odfingest")
            elif self.getFileName('Param.xml',str(self.outputField.text())) == "NOT FOUND":   
                if self.getFileName('SUM.SAS',str(self.outputField.text())) != "NOT FOUND":
                    os.environ['SAS_ODF']=self.getFileName('SUM.SAS',str(self.outputField.text())) 
                self.runButton.setText("Run odfParamCreator")
            else:
                self.runButton.setText("Run xmmextractor")
            self.runButton.setEnabled(True)
            


    def ExpoTabSelected(self,expo=None):
        instName = self.tabs.tabText( self.tabs.currentIndex())
        expoID = self.OMTab.tabText(self.OMTab.currentIndex())
        currWidget = self.OMTab.currentWidget()
        self.logger.info("EXPO ID "+ expoID+" PRODUCT " + currWidget.tabText(currWidget.currentIndex()))
       
        myTab = self.expoTabProductDict[str(expoID)]
        currentExpoTab = self.expoTabProductDict[str(expoID)]
        currentProductLabel=currentExpoTab.tabText(currentExpoTab.currentIndex()) 
        text = "Create "+currentProductLabel+" for " + instName + " exposure "+str(expoID)
        self.runButton.setText(text)
        if (self.checkProductGeneration(currentProductLabel,instName,str(expoID)) == False):
            self.runButton.setEnabled(False)
            
    def productTabSelected(self,instrument=None, expo=None, product=None):
        
        myTab = self.expoTabProductDict[str(expo)]
        text = "Create "+myTab.tabText(product)+" for " + instrument + " exposure "+str(expo)

        self.logger.info ("Product changed "+str(expo)+" "+myTab.tabText(product)+ " " + instrument)
        #Arrange the parameter keywords to only execute the product of the current tab
        currProd = myTab.tabText(product)

        myTab = self.expoTabProductDict[str(expo)]
        ##text = "Create "+myTab.tabText(product)+" for " + instrument  + " exposure "+str(expo)
        self.runButton.setText(text)
        if (self.checkProductGeneration(myTab.tabText(product),instrument,str(expo)) == False):
            self.runButton.setEnabled(False)


    def checkProductGeneration(self,currentProductLabel,instName,expoID):
        self.logger.info("checkProductGeneration "+currentProductLabel+" " +instName+ " " +expoID)
        return True

    def setCurrentProcessingParam(self, instProcParams,expo,currProd,instrument):

        self.logger.info("Setting current processing product " + expo + "  " + currProd + " " +instrument)
        if  instrument  == instProcParams['Instrument']:
           instProcParams['Processing'] = "yes"
        else:
           instProcParams['Processing'] = "no"               

        for key,val in instProcParams.items():  
            self.logger.info("Processing params... " + key + " " + expo + "  " + instrument)      
      
            if key == expo:
                if isinstance(val,dict):   
                    for k,v in instProcParams[key].items():
                        instProcParams[key]['Process'] = "yes"
                        if currProd == k:
                            instProcParams[key][currProd] = "yes"
                        else:
                            instProcParams[key][k] = "no"
            elif isinstance(val,dict)  :
                instProcParams[key]['Process'] = "no"
                for k,v in instProcParams[key].items():
                      instProcParams[key][k] = "no"
       

    def ds9InAction(self,fileName=None):
        self.logger.info("Displaying ds9... "+ fileName)
        self.p = DS9("xmmextractor_ds9")
        self.p.set("file "+fileName)
        self.p.set("scale log")
        self.p.set("cmap heat")
        self.p.set("mode region")
        self.p.set("regions system physical")
        
    def ds9GetSrcRegion(self,key,expr):
        self.logger.info("ds9 source info and key val: "+key)
        srcCoords = self.p.get("regions source","system physical sky fk5")

        res = re.split('\n',srcCoords)        
        physicalFlag = False
        regionFlag = False
        for line in res:
            if line.find('physical') != -1:
                expr = expr
                physicalFlag = True
            if line.find('circle') != -1 or line.find('annulus') != -1 or line.find('box') != -1:
                regionFlag = True
                srcexpr = re.split('#',line)
                if key.find('spectra') != -1 or key.find('lightcurve') != -1 :
                        expr = expr+srcexpr[0]
                else:
                        expr = srcexpr[0]

        if physicalFlag == False:
            choice = QMessageBox.question(self, 'DS9 Coordinates' ,
                                            "Only physical (X,Y) coordinates allowed",
                                            QMessageBox.Ok)
            if choice == QMessageBox.Ok:
                expr = ""
                self.p.set('exit')

        if regionFlag == False:
            choice = QMessageBox.question(self, 'DS9 regions' ,
                                            "Only Circle, Annulus or Box regions are allowed",
                                            QMessageBox.Ok)
            if choice == QMessageBox.Ok:
                expr = ""
                self.p.set('exit')


        self.paramsDict[key].setText(expr)
        self.paramsDict[key].setFixedWidth(320)        

        #Set the same region to the lightcurve extraction
        if key.find('spectra'):
            lightCurveKey = key.replace('spectra','lightcurve')
            lightCurveKey = lightCurveKey.replace('srcexp','expression')
            self.paramsDict[lightCurveKey].setText(expr)
        
        self.logger.info("ds9 source coordinates "+srcCoords)
  
    def ds9GetBkgRegion(self,key,expr):
        self.logger.info("ds9 background info....")
        bkgCoords = self.p.get("regions bakground","system physical sky fk5")

        res = re.split('\n', bkgCoords)        
        physicalFlag = False
        regionFlag = False
        for line in res:
            if line.find('physical') != -1:
                expr = expr
                physicalFlag = True 
            if line.find('background') != -1 and (line.find('circle') != -1 or line.find('annulus') != -1 \
                                                      or line.find('box') != -1 ):
                    regionFlag = True
                    bkgexpr = re.split('#',line)
                    if key.find('spectra') != -1:
                        expr = expr+bkgexpr[0]
                    else:
                        expr = bkgexpr[0]

        if physicalFlag == False:
            choice = QMessageBox.question(self, 'DS9 Coordinates' ,
                                            "Only physical (X,Y) coordinates allowed",
                                            QMessageBox.Ok)
            if choice == QMessageBox.Ok:
                expr = ""
                self.p.set('exit')

        if regionFlag == False:
            choice = QMessageBox.question(self, 'DS9 regions' ,
                                            "Only Circle and Annulus regions are allowed",
                                            QMessageBox.Ok)
            if choice == QMessageBox.Ok:
                expr = ""
                self.p.set('exit')

        self.paramsDict[key].setText(expr)
        self.paramsDict[key].setFixedWidth(320)


        #Set the same region to the lightcurve extraction
        if key.find('spectra'):
            lightCurveKey = key.replace('spectra','lightcurve')
            lightCurveKey = lightCurveKey.replace('4_backexp','5_expression')
            self.paramsDict[lightCurveKey].setText(expr)
        


        self.logger.info("ds9 background coordinates: "+bkgCoords)

        

#    def ds9ExpressionButton(self,key):
#        self.logger.info("RUNNING EVSELECT.... "+ key ) 
#        self.logger.info("NEW EXPRESSION... "+ self.paramsDict[key].text())

#    def onChanged(self,text):
#        self.logger.info("INIT VAL "+ str(self.SNVal.text()))
#        self.logger.info("NEW TEXT... "+text)
#        #self.SNVal.clear
#        self.SNVal.setText(text)



    def  getImageMode(self,fileName):
         self.logger.info("Openning fileName to read keyword "+fileName)
         expr = ""
         if fileName != 'NOT FOUND':
             hdulist = fits.open(fileName, mode='update')
         
             prihdr = hdulist[0].header
             val = prihdr['DATAMODE']
             hdulist.close()
             if val == 'TIMING' or val == 'BURST':
                 expr = '(RAWX,RAWY) IN '
             else:
                 expr = '(X,Y) IN '
         return expr

    def  addCutValue2Fits(self,fileName,cutVal=0.0):
         self.logger.info("Openning fileName to write keyword "+fileName+" CUT "+str(cutVal))

         if Path(fileName).is_file():
             hdulist = fits.open(fileName, mode='update')
         
             prihdr = hdulist[1].header
             if ('CUTVAL' in prihdr):
                 prihdr.update({'CUTVAL': str(cutVal)})
             else:
                 prihdr.append(('CUTVAL', str(cutVal), 'Cts/s' ),end=True)
             hdulist.close()
         

    def handleEditingFinished(self,product,tasks,param,old,key):
        
        #print (self.paramsDict[key].text())

        # do interesting stuff ...
        #print("PRODUCT "+ product)
        #print(tasks)
        #print("OLD Value "+old+ " NEW "+ self.paramsDict[key].text())
        
        tasks[param]= self.paramsDict[key].text()

        #print (key)
        
        #self.paramsDict[key]=self.paramsDict[key].text()
        #print(tasks)
        #print ('Editing Finished')
        #param_info_data.setModified(False)  

# iparsdic is a dictionary with all the task parameters, where their
# respective values are either those entered from the command line 
# or those taken from par file defaults.

def run(iparsdic):
    print(f'Executing {__file__} {iparsdic}')
    # Create loger with 'xmmextractorGUI'
    logger = logging.getLogger('xmmextractorGUI')
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    fh = logging.FileHandler('xmmextractorGUI.log')
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR) 
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    # Handle args
    #
    # At this point, args from the command line can include only std. parameters
    # and options that were set to modify the environment. Any others have been
    # executed already. 
    
    xmldocFile = ["none"]
    #if len(sys.argv) == 1:
    #    xmldocFile[0] = 'none'
    #else:
    #    if len(sys.argv) > 2:
    #        logger.error("Only \'xmlparamfile\' parameter is allowed ")

    #    params = sys.argv[1].split("=")
    #    if params[0] != "xmlparamfile":
    #        logger.error("Parameter "+params[0]+" not found")
    #    xmldocFile[0] = params[1]
   
    # In args besides other things there could be either xmlparamfile=file or 
    # nothing. Therefore, we look in args for it. Otherwise xmldocFile = ['none']
    for key, value in iparsdic.items():
        if (key == 'xmlparamfile'):
            xmldocFile[0] = value
        
    app = QApplication(xmldocFile)

    #XMMTimer = QTimer()

    ex = App(xmldocFile)
    sys.exit(app.exec_())
        
    
