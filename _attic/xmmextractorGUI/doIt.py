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


import sys
import os
import subprocess
import traceback
import threading
import time
import logging

class doIt:
    def __init__(self,fileName):

        
        self.logger = logging.getLogger('xmmextractorGUI')
        self.logger.info("Creating Canvas")
        if len(fileName) == 0:
            self.fileName = ''
        else:
            self.fileName = fileName                
        
        error = ''
        status = None        
        timeout = 100
        thread_count = 2
        self.threads = []
        self.threadName = 'xmmextractor'
        self.job = None
        self.pid = None
        self.jobPIDDict = dict()
        self.stdoutFile=open("xmmextractor.log",'w')
     
    def runSASCommand(self, SASTask):
        #child_env = os.environ.copy()  
        os.remove("xmmextractor.info") if os.path.exists("xmmextractor.info") else None
        
        #stderrFile=open("xmmextractor.error",w)
        try:
            self.logger.info("running command.... "+ SASTask)
            if SASTask == "xmmextractor":
                self.job = subprocess.Popen("xmmextractor paramfile=%s " % self.fileName, \
                                        universal_newlines = True,\
                                        bufsize = -1, \
                                        stdout = self.stdoutFile, \
                                        stderr = subprocess.STDOUT, shell=True)
##                                        env=child_env,\
              
                self.logger.info("NEW PID " + self.job.pid)
                
            else:
                self.job = subprocess.Popen(SASTask, \
                            universal_newlines = True,\
                            bufsize = 64,\
                            stdout = self.stdoutFile, \
                            stderr = subprocess.STDOUT, shell=True)
    
            
            self.job._internal_poll(_deadstate='dead')
            self.pid = self.job.pid
            #print ("NEW PID " + self.pid)
            self.jobPIDDict[ self.pid] = self.job.poll()
            #self.logger.info("done ",self.job.poll())
        except:
            self.error = traceback.format_exc()
            self.status = -1
                    

            
    def checkJobStatus(self, val):
        
        self.logger.debug ("Checking JobStatus.......... "+ str(self.job.poll()) + "  PID " + str(val) + " getPID " + str(self.getPID()) )
      
        if  self.job.poll() == None:
            return True

        return False
      
       
    def deleteJob(self):
        self.logger.info("DELETING JOB...." )
        val = self.job.pid
        self.pid = None
        self.logger.info("JobStatus after KILL.......... "+ str(self.job.poll()) + "  PID " + str(val))

    def getPID(self):
        return self.job.pid

    def closeLogFile(self):
        self.logger.info("Closing log file." )
        self.stdoutFile.close()
        
    def setPID(self,currentPID):
        self.pid = currentPID

    def updatePID(self,pid):
         self.logger.info ("Updating pid "+str(self.job.pid))
         self.jobPIDDict[self.job.pid] =  -1

    def checkJob(self):
        t = threading.Thread(target=checkJobStatus(),name=self.threadName)
        t.setDaemon(True)

        t.start()
        self.logger.info("Thread launched ")
             
