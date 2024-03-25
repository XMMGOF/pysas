#!/usr/bin/python

from pysas.error import Error
from astropy.io import fits
import numpy as np
import sys
import os
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def getData(srcspecfilename,bkgspecfilename,expmapfilename,resmatfilename,intermediateFileFlag,intermediateFile):
    
    expmapfilename  = expmapfilename
    resmatfilename  = resmatfilename
    srcspecfilename = srcspecfilename
    bkgspecfilename = bkgspecfilename

    # Exposure map data and coordinate system values
    expmaphdul = fits.open(expmapfilename)
    
    naxis = expmaphdul[0].header['NAXIS1'] 
    crpix = expmaphdul[0].header['CRPIX1'] 
    crval = expmaphdul[0].header['CRVAL1']
    cdelt = expmaphdul[0].header['CDELT1']
    expmap = expmaphdul[0].data
    expmaphdul.close()
    
    #Read Response Matrix
    
    resmathdul = fits.open(resmatfilename)
    ebounds =resmathdul[2].data
    elow = ebounds['E_MIN']
    ehigh = ebounds['E_MAX']
    resmathdul.close()

    # Energy values
    enermat = 0.5 * (elow+ehigh)
    # Lambda grid
    minlow = crval-(cdelt/2.)
    maxlow = crval-(cdelt/2.)+(naxis*cdelt)
    minhigh = crval+(cdelt/2.)
    maxhigh = crval+(cdelt/2.)+(naxis*cdelt)
    bins = naxis
    llow = np.linspace(minlow, maxlow ,naxis)
    lhigh = np.linspace(minhigh, maxhigh ,naxis)
    lam = (llow+lhigh)/2.
    
    # Maximum expoure time per lambda channel
    exparray = np.max(expmap,0)
    # Maximum exposure time value
    maxexp = np.max(expmap)
 
    # Indexes where the expoosure time is less than 100 seconds and not equal to zero
    badcolumns  =  np.where((exparray != 0.) & (exparray <= 100.) )
    firstChannel = 0
    lastChannel  = 0
    # Loop to avoid channels at the begining and end with no exposure
    for i in range(len(exparray)):
        if (exparray[i] != 0) and (exparray[i] > maxexp*0.5):
            firstChannel = i
            break

    for i in  range( np.size(exparray) - 1, -1, -1):
        if (exparray[i] != 0) and (exparray[i] > maxexp*0.5):
            lastChannel = i
            break

    Error(client=os.path.basename(__file__), msgLayer='AppMsg', msgLevel='SilentMsg', msg=f'First channel with exposure time not equal to zero {firstChannel}').message()
    Error(client=os.path.basename(__file__), msgLayer='AppMsg', msgLevel='SilentMsg', msg=f'Last channel with exposure time not equal to zero {lastChannel}').message()
    
    # Indexes with 0s exposure time (chip gaps and bad columns)
    badchannels =  np.where( exparray[firstChannel:lastChannel] == 0)
    # shift the channels to the original grid
    badchannels = badchannels[0]+firstChannel
    
    jumps = np.diff(badchannels)
    jumpsind = np.where(jumps != 1)

    ccdChannels = np.empty((9,2),dtype=int)
 
    ccdChannels = np.insert(ccdChannels, 0, [firstChannel,badchannels[0]],axis=0)
    ccdChannels = np.delete(ccdChannels, (1), axis=0)
    gap = 1
    instrument = 1
    for i in range(np.size(jumpsind)):
        if instrument == 1 and i == 1:
            ccdChannels = np.insert(ccdChannels, i+gap, [650,965],axis=0)
            ccdChannels = np.delete(ccdChannels, (i+gap+1), axis=0)
            gap = 2
        ccdChannels = np.insert(ccdChannels, i+gap, [badchannels[jumpsind[0][i]],badchannels[jumpsind[0][i]+1]],axis=0)
        ccdChannels = np.delete(ccdChannels, (i+gap+1), axis=0)


    ccdChannels = np.insert(ccdChannels, 8, [badchannels[np.size(badchannels)-1],lastChannel],axis=0)  
    ccdChannels = np.delete(ccdChannels, (9), axis=0)
  

    goodchannels = np.where(exparray > (maxexp*0.85))
    lowexpchannels = np.where((exparray <= (maxexp*0.99)) & (exparray >= (maxexp*0.85)) )
    #print("GOOD CHANNELS ",np.size(goodchannels),np.size(badchannels))
    #print("Low level channels ",lowexpchannels)
    
    enerhigh =  12.398424 / llow
    enerlow = 12.398424 / lhigh

    x = np.linspace(0., np.size(goodchannels), np.size(goodchannels))
    #plt.plot(x, goodchannels[0], 'sb')
    #plt.show()
    #exit(1)
    #plt.imshow(expmap)
    #plt.xlim(1010,1080)
    #plt.ylim(0,160)
    #plt.show()
    #plt.plot(llow[badcolumns], exparray[badcolumns], 'sb')
    #plt.show()

    # I do not know what Jelle does with this channel...
    #print(np.where(np.isclose(exparray , 6793.85)))
    
    
    #Open Src Spec file
    srcspechdul = fits.open(srcspecfilename)
    irgs = srcspechdul[1].header['INSTRUME']
    irgs = int(irgs[-1])
    io = srcspechdul[1].header['RFLORDER']
    src = srcspechdul[1].data
    srccounts = src['COUNTS']
    srcbkgscale = src['BACKSCAL']
    #Open bkg Spec file
    bkgspechdul = fits.open(bkgspecfilename)
    bkg = bkgspechdul[1].data
    bkgcounts = bkg['COUNTS']
    bkgbkgscale = bkg['BACKSCAL']
    #bkgcounts = (bkgcounts*srcbkgscale)/bkgbkgscale
    a = (bkgcounts*srcbkgscale)
    kkk = np.zeros(len(bkgcounts))
    np.true_divide(a,bkgbkgscale, out=kkk, where=bkgbkgscale!=0) #only divide nonzeros
    bkgcounts = kkk

    bkgspechdul.close()
    srcspechdul.close()

    newsrccounts = (maxexp*srccounts[lowexpchannels])/exparray[lowexpchannels]
    newbkgcounts = (maxexp*bkgcounts[lowexpchannels])/exparray[lowexpchannels]
    #print("SRC BKG COUNTS ", srccounts[lowexpchannels],bkgcounts[lowexpchannels],exparray[lowexpchannels],maxexp,newbkgcounts)
    #plt.plot(elow, exparray, 'r')
    #plt.show()
    #plt.plot(elow[goodchannels], exparray[goodchannels], 'sr')
    #plt.plot(elow[lowexpchannels], exparray[lowexpchannels], 'sb')
    #plt.show()

    # Does not work... i do not know
    # pretend low exp channels are channels with maxexp
    bkgcounts[lowexpchannels] = newbkgcounts
    exparray[lowexpchannels]  = maxexp
    for i in range(np.size(lowexpchannels)):
        val1 = exparray[lowexpchannels[0][i]-1]
        val2 = exparray[lowexpchannels[0][i]+1]
        val = max(val1,val2)
        ind = lowexpchannels[0][i]
        exparray[ind] =  val
    #exparray[lowexpchannels] = maxexp
    #plt.plot(elow[goodchannels], exparray[goodchannels], 'sg')
    #plt.show()
    #plt.plot(elow, srccounts, 'sr')
    #plt.show()
    #plt.plot(elow[goodchannels], srccounts[goodchannels], 'sb')
    #plt.show()
    #plt.plot(elow, bkgcounts, 'sr')
    #plt.show()
    #plt.plot(elow[goodchannels], bkgcounts[goodchannels], 'sb')
    #plt.show()
    #print(elow[goodchannels],exparray[goodchannels],srccounts[goodchannels],bkgcounts[goodchannels])


    if (intermediateFileFlag == True):
        c1 = elow[goodchannels]
        c2 = ehigh[goodchannels]
        c3 = exparray[goodchannels]
        c4 = srccounts[goodchannels]/exparray[goodchannels]
        c5 = bkgcounts[goodchannels]/exparray[goodchannels]
        c4 = srccounts[goodchannels]
        c5 = bkgcounts[goodchannels]    
        c1 =  np.flipud(c1)
        c2 =  np.flipud(c2)
        c3 =  np.flipud(c3)
        c4 =  np.flipud(c4)
        c5 =  np.flipud(c5)
        col1 = fits.Column(name='ELow', format='D', array=c1)
        col2 = fits.Column(name='EHigh', format='D', array=c2)
        col3 = fits.Column(name='Exp_Time', format='D', array=c3)
        col4 = fits.Column(name='Source_Rate', format='D', array=c4)
        col5 = fits.Column(name='Back_Rate', format='D', array=c5)
    
        t = fits.BinTableHDU.from_columns([col1, col2, col3,col4,col5])
        t.writeto(intermediateFile,overwrite=True)

    
    return (irgs,io,elow[goodchannels],ehigh[goodchannels],exparray[goodchannels],srccounts[goodchannels],bkgcounts[goodchannels],goodchannels,lam[ccdChannels],ccdChannels)



