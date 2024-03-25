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

import logging
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import unique, Table
from PyQt5.QtWidgets import QSizePolicy
#import pylab as plt
from matplotlib.colors import LogNorm
import matplotlib.gridspec as gridspec
from matplotlib.ticker import  MaxNLocator, FormatStrFormatter, MultipleLocator, FuncFormatter, ScalarFormatter, NullFormatter,StrMethodFormatter

class PlotCanvas(FigureCanvas):
 
    def __init__(self, parent=None, width=648, height=648, dpi=100,fileName='test.ds',type=None,threshold=None,emllistFileName='test.ds',rgsEnerFileName='test.ds',ra=None, dec=None):
        #self.fig = Figure(figsize=(width, height), dpi=1)

        self.logger = logging.getLogger('xmmextractorGUI')
        self.logger.info("Creating Canvas")
        self.fig = Figure(figsize=(width, height), dpi=dpi,frameon=False)    

        self.fig.subplots_adjust(0.15,0.07,0.95,0.92,0.1,0.1)
        self.fileName = fileName
        self.emlistFileName = emllistFileName
        self.rgsEnerFileName = rgsEnerFileName
        self.lines = []
        self.plotCurve = []
        self.wcs = None
        self.ra = ra
        self.dec = dec
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        #FigureCanvas.setSizePolicy(self,
        #        QSizePolicy.Expanding,
        #        QSizePolicy.Expanding)
        #FigureCanvas.updateGeometry(self)
        #self.fig.frameon = False

        self.fig.set_size_inches((280,60))
        if type == 'IM':
            self.plot()
        elif type == 'LC':
            self.plotLC(threshold,self.fileName)
        elif type == 'PG':
            self.plotPG(threshold,self.fileName)            
        elif type == 'DT':
            self.plotSrcDetection()
        elif type == 'RGS':
            self.plotRGS()
        elif type == 'RGSFlux':
            self.plotRGSFlux()
        elif type == 'RGSLC':
            self.plotRGSLC()
        else:
            self.plotSP()
        


    def plotSrcDetection(self):

        self.logger.info("plotting image")
        if self.fileName != "NOT FOUND":

            #Read the source detection list 
            table = Table.read(self.emlistFileName, hdu=1)  

            uTable = unique(table, keys='ML_ID_SRC')
                     
            image_data,hdu = fits.getdata(self.fileName, ext=0, header=True)
            self.wcs = WCS(hdu)
            #print(image_data.shape)

            ax = self.fig.add_subplot(111,projection=self.wcs)
            ra = ax.coords[0]
            dec = ax.coords[1]
            ra.set_major_formatter('d.ddd')
            dec.set_major_formatter('d.ddd')

            ax.clear()
            ax.imshow(image_data,cmap='hot', norm=LogNorm())  
 
            ax.set_title('Full Image')
            ax.set_xlabel("RA")
            ax.set_ylabel("DEC")


            for row in uTable:                
                ax.add_artist(plt.Circle((row['X_IMA'], row['Y_IMA']), 5.5, color='red',lw=2, fill=False))

            self.fig.canvas.mpl_connect('button_press_event',self.onclick)

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)

            
            #This call takes lot of time...
            #self.draw()
         

    def plot(self):

        self.logger.info("plotting image")
        if self.fileName != "NOT FOUND":

            ax = None
            image_data,hdu = fits.getdata(self.fileName, ext=0, header=True)
            if hdu['DATAMODE'] != "TIMING":
                self.wcs = WCS(hdu)
                ax = self.fig.add_subplot(111,projection=self.wcs)
            else:
                ax = self.fig.add_subplot(111)
                            
            if hdu['DATAMODE'] != "TIMING":
                ra = ax.coords[0]
                dec = ax.coords[1]
                ra.set_major_formatter('d.ddd')
                dec.set_major_formatter('d.ddd')

            ax.clear()
            ax.imshow(image_data,cmap='hot', norm=LogNorm())  
          

            if self.ra is not None:
                if hdu['DATAMODE'] != "TIMING":               
                    px, py = self.wcs.wcs_world2pix(self.ra,self.dec, 1)
                    ax.add_artist(plt.Circle((px, py), 5.5, color='white',lw=2, fill=False))

            ax.set_title('Full Image')

            if hdu['DATAMODE'] != "TIMING":
                ax.set_xlabel("RA")
                ax.set_ylabel("DEC")                
                self.fig.canvas.mpl_connect('button_press_event',self.onclick)

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            #This call takes lot of time...
            #self.draw()
        
    def format_fn(tick_val, tick_pos):
            labels = list('abcdefghijklmnopqrstuvwxyz')
            if int(tick_val) in xs:
                return labels[int(tick_val)]
            else:
                return ''

    def major_formatter(x, pos):
            return "[%.2f]" % x

    def plotRGS(self):
        self.logger.info("plotting image")
        if self.fileName != "NOT FOUND" or self.rgsEnerFileName != "NOT FOUND": 

            image_data,hdu = fits.getdata(self.fileName, ext=0, header=True)
            ener_image_data,hdu2 = fits.getdata(self.rgsEnerFileName, ext=0, header=True)
            gs = gridspec.GridSpec(2, 1,height_ratios=[1, 1],width_ratios=[1])
            ax1= self.fig.add_subplot(gs[0])
            #ax1 = self.fig.add_subplot(221)
            ax1.clear()
            ax1.imshow(image_data,cmap='hot', norm=LogNorm(),origin='lower',aspect='auto')  
            text = hdu['INSTRUME']+" Spatial and Orders Image"
            ax1.set_title(text)
            #ax1.set_xlabel("LAMBDA")
            ax1.set_ylabel("Cross Dispersion Angle (radians)")
            ax2= self.fig.add_subplot(gs[1],sharex=ax1)
            #ax2 = self.fig.add_subplot(121)
            ax2.clear()

            
            ax2.imshow(ener_image_data,cmap='hot', norm=LogNorm(),origin='lower',aspect='auto')  
            ax2.set_xlabel("LAMBDA")

            crval1 = hdu2['CRVAL1']
            delta1 = hdu2['CDELT1']
            val = crval1

            xticks = range(0, len( ener_image_data[1]), 1)
            labels=[0]*int(len( ener_image_data[1])/1)
            counter = 0
            for lTick in xticks:
                labels[counter]=  ("%.1f" % (crval1+(lTick*delta1)))
                counter = counter + 1
           
            #ax2.xaxis.set_major_locator(MultipleLocator(50.00))     
                
            ax2.xaxis.set_major_formatter(FuncFormatter(lambda x,pos: "%.2f" % (crval1+(x*delta1))))
            #ax2.set_xticklabels(labels,minor=False)
            #ax2.set_xticks(xticks)
            ax2.set_ylabel("PI (Channel)")
                
            self.fig.canvas.mpl_connect('button_press_event',self.onclickRGS)

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            #This call takes lot of time...
            #self.draw()
            
        
    def onclick(self,event):        
        if event.xdata is not None and event.ydata is not None:
            print('x=%d, y=%d, xdata=%f, ydata=%f' %
                   (event.x, event.y, event.xdata, event.ydata))
            wx,wy=self.wcs.wcs_pix2world(event.xdata,event.ydata,1)
            print('RA: {0} DEC: {1}'.format(wx,wy))

    def onclickRGS(self,event):
        if event.xdata is not None and event.ydata is not None:
            print('x=%d, y=%d, xdata=%f, ydata=%f' %
                  (event.x, event.y, event.xdata, event.ydata))
        
        
 
    def plotLC(self,threshold,fileName):        
        self.logger.info("plotting lightcurve") 
        self.fileName = fileName
        if self.fileName != "NOT FOUND":
            fitsFile = fits.open(self.fileName)   
            prihdu = fitsFile[1].header
            if ('CUTVAL' in prihdu):
                threshold = prihdu['CUTVAL']

            cols = fitsFile[1].columns
            colName = None
            for i,x  in enumerate(cols.names):
                if "RATE" in x:
                    colName = cols.names[i]
                if "COUNTS" in x:
                    colName = cols.names[i]        

            data = fitsFile[1].data   
            
            xdata = data.field('TIME')           # extract the x data column
            ydata = data.field(colName)

            ax = self.fig.add_subplot(111)
            ax.clear()
            start, end = ax.get_xlim()
            ax.xaxis.get_major_formatter().set_useOffset(False)
            ax.plot(xdata,ydata)               # plot the data

            if colName == 'RATE' and "gti.fit" not in self.fileName :
                ax.set_title("Background substracted lightcurve")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Cts/s")
            else:
                ax.set_title("High-particle flaring lightcurve")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Counts")

            
            if (threshold != 'None'):
                if (colName == 'COUNTS'):
                    threshold=float(threshold)*100.

                y2data = [threshold]*len(xdata)            
                ax.plot(xdata,y2data)
            
            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            
            fitsFile.close()
            
        #self.draw()

    def plotPG(self,threshold,fileName):
        self.logger.info("plotting S/N curve")
        self.fileName = fileName

        if self.fileName != "NOT FOUND":

            fitsFile = fits.open(self.fileName)   
            data = fitsFile[1].data   
            
            xdata = data.field('BKG')           # extract the x data column
            ydata = data.field('SN')

            ax = self.fig.add_subplot(111)
            #ax.clear()
            #Remove current plot 
            for i, line in enumerate(self.plotCurve):                
                self.plotCurve.pop(i)
                line.remove()
            
            #Remove exisiting lines (if any)            
            for i, line in enumerate(self.lines):
                self.lines.pop(i)
                line.remove()
                
            self.plotCurve = ax.plot(xdata,ydata)               # plot the data

            if threshold == 'None':
                ax.set_title("Background substracted lightcurve")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Cts/s")
            else:
                ax.set_title("High-particle flaring lightcurve")
                ax.set_xlabel("BKG Counts")
                ax.set_ylabel("S/N")
                x2data = [threshold]*len(xdata)
                self.lines = ax.plot(x2data,ydata)
            

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            fitsFile.close()
            #self.draw()
   
    def plotSP(self):
        self.logger.info("plotting spectra")
        if self.fileName != "NOT FOUND":
            fitsFile = fits.open(self.fileName)   
            data = fitsFile[1].data   
            
            xdata = data.field('CHANNEL')           # extract the x data column
            ydata = data.field('COUNTS')

            ax = self.fig.add_subplot(111)
            ax.clear()
            ax.plot(xdata,ydata)               # plot the data
            ax.set_title("Spectrum")
            ax.set_xlabel("Channel")
            ax.set_ylabel("Counts")

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            fitsFile.close()

    def plotRGSFlux(self):
        self.logger.info("plotting RGS Flux spectra " +self.fileName )
        if self.fileName != "NOT FOUND":
            fitsFile = fits.open(self.fileName)   
            data = fitsFile[1].data   
            
            xdata = data.field('CHANNEL')           # extract the x data column
            ydata = data.field('FLUX')

            ax = self.fig.add_subplot(111)
            ax.clear()
            ax.plot(xdata,ydata)               # plot the data
            ax.set_title("Fluxed Spectrum")
            ax.set_xlabel("Channel")
            ax.set_ylabel("Flux")

            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            fitsFile.close()


    def plotRGSLC(self):
        self.logger.info("plotting RGS lightcurve") 

        if self.fileName != "NOT FOUND":
            fitsFile = fits.open(self.fileName)   
            prihdu = fitsFile[1].header
            instrument = prihdu['INSTRUME']
            data = fitsFile[1].data   
            
            xdata = data.field('TIME')           # extract the x data column
            ydata = data.field('RATE')

            ax = self.fig.add_subplot(111)
            ax.clear()
            start, end = ax.get_xlim()
            ax.xaxis.get_major_formatter().set_useOffset(False)
            ax.plot(xdata,ydata)               # plot the data

            title = instrument +" Background substracted lightcurve"
            ax.set_title(title)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Cts/s")
            
            self.toolbar = NavigationToolbar(self.fig.canvas, self,coordinates=False)
            self.toolbar.setMinimumWidth(300)
            
            fitsFile.close()
            
