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

# rgsbkgsmoothing.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'rgsbkgsmoothing (rgsbkgsmoothing-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

from pysas.error import Error
import pysas.rgsbkgsmoothing.expTime as  e
import numpy as np
from astropy.io import fits
from astropy.table import Table
import sys
import os
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import pysas.rgsbkgsmoothing.expTime as e
from shutil import copyfile

# Global constant to be used in the curve_fit method
C = 0

def func(x, N, a):
    return C + N * x ** (a)

# The Python code for rgsbkgsmoothing should go inside run
# args passed from the rgsbkgsmoothing script should be
# handled inside the code.

def run(args):
    print(f'Executing {__file__} {args}')
    name = os.path.basename(__file__)

    # Constant and parameter that need to be revised. Some of these parameters should go to the param file
    nmax = 32768
    nccdmax = 9
    nccd = 9
    io = None # order
    irgs = None # RGS instrument identifier
    lim = 30
    errsq = False
    #If we use our method to determine the CCD boundaries, we do not need these arrays
    wr1 = np.asarray([0.00,7.69,10.55,13.68,17.09,20.77,24.72,28.96,33.46,99.99])
    wr2 = np.asarray([0.00,7.16, 9.98,13.07,16.43,20.06,23.97,28.14,32.60,99.99])
    wlim = np.asarray([0.,1000.])
    colors = ["red", "blue" , "green", "orange", "purple","cyan","magenta","yellow","red"]


    expmapfilename = None
    resmatfilename = None
    srcspecfilename = None
    bkgspecfilename = None
    srcbkgsuboutputfile = None
    bkgsmoothoutputfile = None
    plotbkg = bool(False)
    SRONFlag = bool(False)
    SRONoutput = None
    
    for key, value in args.items():
        if (key == 'srcspectrum'):
            srcspecfilename = value
        if ( key == 'bkgspectrum'):
            bkgspecfilename = value
        if ( key == 'expmap'):
            expmapfilename = value
        if ( key == 'response'):
            resmatfilename = value
        if ( key == 'intermediateFileFlag'):
            intermediateFileFlag = value
        if ( key == 'intermediateFile'):
            intermediateFile = value
        if (key == 'srcbkgsuboutputfile'):
            srcbkgsuboutputfile = value
        if (key == 'bkgsmoothoutputfile'):
            bkgsmoothoutputfile = value
        if ( key == 'plotbkg'):
            if (value.upper() == 'Y' or value.upper() == 'YES' ):
                plotbkg = bool(True)
            elif (value.upper() == 'N' or value.upper() == 'NO'):
                plotbkg = bool(False)
            elif (value.upper() == 'TRUE'):
                plotbkg = bool(True)
            elif (value.upper() == 'FALSE'):
                plotbkg = bool(False)
            else:
                plotbkg = bool(value)

        if ( key == 'sronflag'):
            if (value.upper() == 'Y' or value.upper() == 'YES' ):
                SRONFlag = bool(True)
            elif (value.upper() == 'N' or value.upper() == 'NO'):
                SRONFlag = bool(False)
            elif (value.upper() == 'TRUE'):
                SRONFlag = bool(True)
            elif (value.upper() == 'FALSE'):
                SRONFlag = bool(False)
            else:
                SRONFlag = bool(value)

        if (key == 'sronoutput'):
            SRONoutput = value


    irgs,io,lener,uener,exptim,src_counts,bkg_counts,goodchannels,lam,ccdChannels = e.getData(srcspecfilename,bkgspecfilename,expmapfilename,resmatfilename,intermediateFileFlag,intermediateFile)


    ener = 0.5 * (lener+uener)
    w =  12.398424 / ener
    wl =  12.398424 / uener
    wu = 12.398424 / lener
    data = src_counts
    back = bkg_counts
    
    
    f = back
    so = data

    #  
    # Initialization of final array 
    #              
    fs = np.zeros(len(f))
    n = w.size
    

    # Split data into CCD segments          
    #Algortihm to find the CCD gaps for this observation             
    nogapmin = sys.float_info.max
    
    w1 = np.zeros(9)
    w2 = np.zeros(9)
    for ia in range(99):
        for ias in range(-1,1,2):
            delt = float(ias)*float(ia)*0.01
            if (irgs == 1):
                wra = (wr1 + delt)/float(io)
            if (irgs == 2):
                wra = (wr2 + delt)/float(io)
            nogap = 0
            for j in range(2,10):
                for i in range(1,n):
                    if ((wra[j] >= wl[i]) and (wra[j] <= wu[i])):
                        nogap = nogap + 1
                        exit
            if(nogap < nogapmin):
                nogapmin = nogap
                dmin = delt
            if (nogap == 0):
                break
        if(nogap == 0):
            break
    if (ia >= 100):
        delt = dmin
        if (irgs == 1):
            wra = (wr1 + delt) / float(io)
            wra = (wr2 + delt) / float(io)
                                        
    for j in range(0,9):
        w1[j] = wra[j]
        w2[j] = wra[j+1]
                                            
    # AI expmap lambda values for each CCD
    #w1 = lam[:,0]
    #w2 = lam[:,1]
    # AI


    # 
    # Loop over ccds     
    #
    ncolor = 0
    for iccd in range(0,nccd):
        #              
        # Set data   
        #         
        
        j = 0
        nj = 0
        g = np.zeros(nmax)
        i1 = sys.maxsize
        i2 = 0

        for i in range(0,n):
            if (w[i] >= w1[iccd] and w[i] < w2[iccd]):
                if (w[i] >= wlim[0] and w[i] <= wlim[1]):
                    i1 = min(i1,i)
                    i2 = max(i2,i)
                    g[j] = f[i]
                    j = j + 1
        nj = j
        if (nj == 0):
            continue
        j = 2
        for i in range(10000):
            j = j * 2
            if (j > nj):
                break
        nuse = 2 * j
        suma =  sum(g[0:nj])
        #       
        # pad the data with appropriate value      
        #      
        gaver = sum(g[0:nj]) / float(nj)
        #print ('sum nj nuse gaver ',suma, nj, nuse, gaver)
        #fill remainder with average to avoid edge effects  
        g[nj:nuse] = gaver
        # subtract average value   
        g = g - gaver
        
        kk0 = ccdChannels[:,0]
        kk1 = ccdChannels[:,1]
        Error(client=name, msgLayer='AppMsg', msgLevel='SilentMsg', msg=f'CCD {iccd+1},{lam[iccd]},{ccdChannels[iccd]},{kk0[iccd]},{kk1[iccd]},{kk1[iccd]-kk0[iccd]} ').message()
        #Error(client=name, code='openFileError', msg=f'ERROR opening par file {name}: ').error()
        kk = np.where((goodchannels[0] >= kk0[iccd]) & (goodchannels[0] <= kk1[iccd]))

        #AI old value res = np.fft.rfft(g,512)     
        res = np.fft.rfft(g,nuse)
        g2 = res.real**2 + res.imag**2

        xData = np.asarray(np.linspace(1,1440,1440))
           
        #Why the number of energy channels are the same if we now that the are not equaly spaced...       
        lxData = xData[1:30]
        uxData = xData[30:512]
        lyData = g2[1:30]
        uyData = g2[30:512]
        
        C = np.average(uyData)
        # optimize using the appropriate bounds 
        #popt, pcov = curve_fit(func, lxData, lyData, bounds=([1000.,-2.],[1e10,0.]))               
        popt, pcov = curve_fit(func, lxData, lyData, bounds=([0.,-3.],[1e10,-.1]))
        if (popt[1] < -5 or popt[1]  > -0.1):
            popt[1] = -1.
            popt[0] = 0.

        if (np.abs(popt[0] ) < 0.0001):
            popt[0] = 0.

        Error(client=name, msgLayer='AppMsg', msgLevel='SilentMsg', msg=f'Power Law fitting values C, a b (y = C + a*e^xb) {C} {popt[0]} {popt[1]}').message()
        vals = np.arange(1, nmax, dtype=np.float)

        gmod = C
        cmod = C + popt[0]*vals**popt[1]

        realp = np.zeros(len(res))
        imagp = np.zeros(len(res))

        #AI old value!!! phivec = np.zeros(257)                    
        phivec = np.zeros(len(res))

        for i in range(len(res)):
            c2 = g2[i]
            s2 = cmod[i] - gmod
            phi = s2 / cmod[i]
            phivec[i] = phi
            realp[i] = res[i].real*phi
            imagp[i] = res[i].imag*phi


        z = np.array(realp, dtype=complex)
        # Now define the imaginary part:
        
        z.imag = imagp
        toplot = z.real**2+z.imag**2

        # Transform back
        resi = np.fft.irfft(z)
        resi = resi*len(res)
        resi = resi * (2./nuse) + gaver
        j = 0

        Error(client=name, msgLayer='AppMsg', msgLevel='SilentMsg', msg=f'CCD edge values {i1} {i2}').message()
        for i in range(i1,i2):
            fs[i] = resi[j]

            j = j + 1

        xnew4 = np.linspace(0., len(res),len(res))

        if (plotbkg == True):
            #plot wavelength and counts
            #plt.subplot(3,3,iccd+1)
            plt.plot(w[i1:i2], f[i1:i2], 'k')
            plt.plot(w[i1:i2], fs[i1:i2], color=colors[ncolor])
            ncolor += 1

    if (plotbkg == True):
        plt.xlabel("Wavelength \u00c5")
        plt.ylabel('Counts')
        plt.show()

    #     
    # flush any remaining (non-filtered) data for the plot  
    #          

    #for i in range(0,n):  
    #    for iccd in range(0,nccd):        
    #        if (w[i] >= w1[iccd] and w[i] < w2[iccd]):
    #            if (w[i] >= wlim[0] and w[i] <= wlim[1]):  
    #                continue             
    #    myfile.write("%s %s %s\n" % (w[i],fs[i],f[i]))  
    #myfile.close()


    #Plot of the bkg smooth results

    
    #       
    # Recalculate the source and background    
    # 
    df = np.zeros(len(f))
    c1 = np.zeros(len(f))
    c2 = np.zeros(len(f))
    c3 = np.zeros(len(f))
    

    backincounts = np.zeros(len(f))
    srcincounts = np.zeros(len(f))
    for i in range(0,len(f)):
        val = np.sqrt(so[i])
        dspec = val / exptim[i]
        spec = (so[i] - fs[i]) / exptim[i]
        back = fs[i] / exptim[i]
        backincounts[i] = fs[i]
        df[i] = f[i] - fs[i]
        c1[i] = spec
        c2[i] = dspec
        c3[i] = back


    backrates3600 = np.zeros(3600)
    src3600  = np.zeros(3600)
    srcrate3600 = np.zeros(3600)
    srccounts3600 = np.zeros(3600)
    for i in range(len(backrates3600)):
        for j in range(len(goodchannels[0])):
            if (i == goodchannels[0][j]):
                #print("i,j ",i,goodchannels[0][j])     
                backrates3600[i] = c3[j]
                srcrate3600[i] = c1[j]
                srccounts3600[i] = c1[j]*exptim[j]
                break
    #xnew2 = np.linspace(4., 40., 3600)
    #plt.plot(xnew2, srcrate3600, 'b')
    #plt.show()

    #                     
    # Swap to energy     
    #          
    # AI (uncomment for AI input) For JK input data we do not have to flip the lener and uener vectors  
    lener = np.flipud(lener)
    uener = np.flipud(uener)
    # AI                     
    c1 =  np.flipud(c1)
    c2 =  np.flipud(c2)
    c4 =  c3*exptim
    c3 =  np.flipud(c3)
    
    #                   
    # Create fit file            
    #                    
    #du = fits.PrimaryHDU(len(c1))        
    #hdul = fits.HDUList([hdu])            
    if (SRONFlag == True):
        col1 = fits.Column(name='Elow', format='D', array=lener)
        col2 = fits.Column(name='EHigh', format='D', array=uener)
        col3 = fits.Column(name='Source_Rate', format='D', array=c1)
        col4 = fits.Column(name='Err_Source_Rate', format='D', array=c2)
        col5 = fits.Column(name='Back_Rate', format='D', array=c3)
        col6 = fits.Column(name='Back_Counts', format='D', array=c4)
        #t = fits.BinTableHDU.from_columns([col1, col2, col3],header=myheader)                                                      
        t = fits.BinTableHDU.from_columns([col1, col2, col3,col4,col5,col6])
        t.writeto(SRONoutput,overwrite=True)



    #channels = np.arange(1,3600,1)
    #ncol1 = fits.Column(name='CHANNELS', format='E', array=channels)
    #ncol2 = fits.Column(name='RATE', format='D', array=backrates3600)
    #t = fits.BinTableHDU.from_columns([ncol1, ncol2])
    #t.writeto('AI_BACK_output.fits',overwrite=True)


    copyfile(bkgspecfilename, bkgsmoothoutputfile)
    outhdul = fits.open(bkgsmoothoutputfile,mode='update')
    hdrbkg = outhdul[1].header
    cols = outhdul[1].data
    outhdul[1].columns.del_col('COUNTS')
    colbkg = fits.Column(name='RATES', format='D', array=backrates3600)
    coldefbkg =outhdul[1].columns.add_col(colbkg)
    hdrbkg['HDUCLAS3'] = "RATE"
    outhdul[1] = fits.BinTableHDU.from_columns(coldefbkg, header=hdrbkg)


    #cols['COUNTS'][:] = np.rint(back3600)

    #spectrum.add_column(back3600, name='COUNTS', rename_duplicate=True)                                                        
    outhdul.writeto(bkgsmoothoutputfile,overwrite=True)
    outhdul.close()                                                                                                            

    copyfile(srcspecfilename, srcbkgsuboutputfile)
    outhduls = fits.open(srcbkgsuboutputfile,mode='update')
    hdr = outhduls[1].header
    colssrc = outhduls[1].data
    
    outhduls[1].columns.del_col('COUNTS')
    outhduls[1].columns.del_col('BACKSCAL')
    colsrc = fits.Column(name='RATES', format='D', array=srccounts3600)
    coldef =outhduls[1].columns.add_col(colsrc)
    hdr['HDUCLAS2'] = "NET"
    hdr['HDUCLAS3'] = "RATE"
    
    outhduls[1] = fits.BinTableHDU.from_columns(coldef, header=hdr)
    
    outhduls.writeto(srcbkgsuboutputfile,overwrite=True)
    outhduls.close()
