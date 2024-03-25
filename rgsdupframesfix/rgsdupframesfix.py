# ESA (C) 2000-2022
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

# rgsdupframesfix.py

from .version import VERSION, SAS_RELEASE, SAS_AKA
from astropy.io import fits
from astropy.table import Table
import numpy as np
import matplotlib.pyplot as plt
from shutil import copyfile
import glob
from collections import Counter
import os
import argparse
from pysas.logger import TaskLogger as TL



__version__ = f'rgsdupframesfix (rgsdupframesfix-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

rgsdupframesix_log = TL('rgsdupframesfix')

def fixScience(odfdir,outdir,expoNumber,badDict,frameDict,goodDict):
        
    totalFramesRemovedFromSciFiles = 0
    #OPEN SCIENCE FILE
    scienceFilePattern = odfdir+'/*'+expoNumber+'*SPE.FIT'
    
        
    for scienceFile  in glob.glob(scienceFilePattern):
        
        fileNameSci = os.path.basename(scienceFile)
        #copyfile(file, fileName)
        newFileName = fileNameSci
        ccdidExp = fileNameSci[23:24]
        revno = fileNameSci[0:4]
        obsid = fileNameSci[5:15]
        inst = fileNameSci[16:18]


        rgsdupframesix_log.log('info','FILE NAME: '+fileNameSci)

        v = len(badDict[ccdidExp])
        if (len(badDict[ccdidExp]) != 0):
            hdul2 = fits.open(scienceFile)
            hdr0Sci = hdul2[0].header
            data2Sci = hdul2[1].data
            hdroSci = hdul2[1].header
            hdul2.close()
            
            #print('SPE Before ', obsid, ' ', expoNumber, ' ', ccdidExp, ' =  ' ,len(data2Sci))
            oldSPEdata = data2Sci

            for x,y in zip(badDict[ccdidExp],goodDict[ccdidExp]):
                frameindex = np.where(oldSPEdata['FRAME'] == x)
                frameindexgood = np.where(oldSPEdata['FRAME'] == y)
                #print('Frame value ',x, ' appears in indexes ',frameindex)
                #print(oldSPEdata[x])
                rgsdupframesix_log.log('debug','ORI[{}:{}:{}]  {}'.format(obsid,expoNumber,ccdidExp,oldSPEdata[frameindexgood].tolist()))
                rgsdupframesix_log.log('debug','DUP[{}:{}:{}]  {}'.format(obsid,expoNumber,ccdidExp,oldSPEdata[frameindex].tolist()))

                #for y in frameindex:
                
                #print("deleteing frames ",frameindex)
                newdataSPE = np.delete(oldSPEdata, frameindex)
                oldSPEdata = newdataSPE
                    
            #print('SPE After ', obsid, ' ', expoNumber, ' ', ccdidExp, ' =  ',len(newdataSPE))
            totalFramesRemovedFromSciFiles = totalFramesRemovedFromSciFiles + len(data2Sci)-len(newdataSPE)
            rgsdupframesix_log.log('info','FRAMES removed in SPE file [{} {} {} {}]: {}'.format(revno,  obsid, expoNumber,  ccdidExp , len(data2Sci)-len(newdataSPE)))
            
            for key, value in frameDict.items():
                newdataSPE['FRAME'] = np.where(newdataSPE['FRAME'] == key, value, newdataSPE['FRAME'])

            del oldSPEdata
            del data2Sci
            hduSPE1 = fits.PrimaryHDU(header=hdr0Sci)
            hduSPE2 = fits.BinTableHDU(data=newdataSPE,header=hdroSci)
            new_hduSPE = fits.HDUList([hduSPE1,hduSPE2])
            
            new_hduSPE.writeto(outdir+newFileName,overwrite=True,output_verify='silentfix')
                
    rgsdupframesix_log.log('info','Science Summary: [REVNO: {} OBSID: {} EXPO: {}]  FRAMES REMOVED IN ALL CCDS: {} '.format(revno,  obsid, expoNumber , totalFramesRemovedFromSciFiles))
        #else:
        #    if os.path.exists(fileName):
        #        os.remove(fileName)


    

def fixAUX(file,outdir):
    fileName = os.path.basename(file)   
    revno = fileName[0:4]
    obsid = fileName[5:15]
    expoNumber = fileName[16:22]

        
    hdul1 = fits.open(file)
    data1 = hdul1[1].data
    
    if len(data1) == 0:
        hdul1.close()
        rgsdupframesix_log.log('warning',"NO AUX DATA")
        if os.path.exists(fileName):
            os.remove(fileName)
        return(0,0,0,0,0)
        
    if ( "FTCOARSE" not in hdul1[1].columns.names):
        rgsdupframesix_log.log('warning', "NO FTCOARSE")
        hdul1.close()
        if os.path.exists(fileName):
            os.remove(fileName)
        return(0,0,0,0,0)

    #RGS
    frame = data1['FRAME']
    ccdid = data1['CCDID']
    ftcoarse = data1['FTCOARSE']
    ftfine =  data1['FTFINE']
    eoscoars = data1['EOSCOARS']
    eosfine = data1['EOSFINE']
    frmtime = data1['FRMTIME']
    seqindex = data1['SEQINDEX']
    nrejectc = data1['NREJECTC']
    nacceptc = data1['NACCEPTC']
    nupperc = data1['NUPPERC']
    ndpp = data1['NDPP']
    nlostevt = data1['NLOSTEVT']
    abortflg = data1['ABORTFLG']    
    hdul1.close()
    #RGS


    ntuple = tuple(zip(ftcoarse,ftfine,ccdid,eoscoars,eosfine,frmtime,seqindex,nrejectc,nacceptc,nupperc,ndpp,nlostevt,abortflg))
        
    yy = 0
    ind = 0
    counts = 0
    yy,ind,counts = np.unique(np.array(ntuple),return_index=True,axis=0, return_counts=True)
    dup = len(ntuple)-len(yy)
    
    rgsdupframesix_log.log('info','AUX summary: REVNO: {:5}  OBSID: {:10} EXPOSURE: {:6} FRAMES: {:8} DUPLICATED FRAMES: {:8}'.format(revno, obsid,expoNumber, len(ntuple) , len(ntuple)-len(yy)))
    
    ll = np.where(counts != 1)
    bad = []
    badDict = {"1": [],"2": [],"3": [],"4": [],"5": [],"6": [],"7": [],"8": [],"9": []}
    goodDict = {"1": [],"2": [],"3": [],"4": [],"5": [],"6": [],"7": [],"8": [],"9": []}
    rgsdupframesix_log.log('info','    {:12} {:17} {:18} {:9} {:10} {:19} {:8} {:4} {:6} {:6} {:6} {:6} {:6}'.format('INDEX','FRAME','FTCOARSE','FTFINE','CCDID','EOSCOARSE','EOSFINE','FRMTIME','SEQINDEX','NACCEPTC','NUPPERC','NDPP','NLOSTEVT','ABORTFLG'))
    for x in ll:
        for y in x:
            ind = np.where( (ftcoarse == yy[y][0]) & (ftfine ==  yy[y][1]) & (ccdid == yy[y][2]) & (nrejectc == yy[y][7]) & (seqindex == yy[y][6]) & (nacceptc == yy[y][8]) )

            rgsdupframesix_log.log('info','{} {} {} {} {} {} {} {} {} {} {} {} {}'.format(ind[0], frame[ind],ftcoarse[ind],ftfine[ind],ccdid[ind],eoscoars[ind],eosfine[ind],frmtime[ind],seqindex[ind],nacceptc[ind],nupperc[ind],ndpp[ind],nlostevt[ind],abortflg[ind]))

            ind = np.array(ind)
            bad.append(ind[0,1])
            badDict[str(ccdid[ind[0,1]])].append(frame[ind[0,1]])
            goodDict[str(ccdid[ind[0,1]])].append(frame[ind[0,0]])                              

    # Duplicated
    hdulaux = fits.open(file)
    hdr0 = hdulaux[0].header
    datao = hdulaux[1].data
    hdro = hdulaux[1].header
    data2  =  hdulaux[2].data
    hdr2 = hdulaux[2].header
    hdulaux.close()
    badframe =frame[bad]
    
    #print('AUX before ',len(datao))
    newdata2 = np.delete(datao, bad)
    #print('AUX after ',len(newdata2))
    jumps = np.diff(newdata2['FRAME'])
    jumpindex = np.where(jumps > 65000) 
    


    del frame
    del ccdid
    del ftcoarse
    del ftfine
    del eoscoars
    del eosfine
    del frmtime
    del seqindex
    del nrejectc
    del nacceptc
    del nupperc
    del ndpp
    del nlostevt
    del abortflg
    

    rgsdupframesix_log.log('info', 'FRAMES removed from AUX file [{} {} {}]: {} number of jumps: {}'.format(revno, obsid, expoNumber, len(datao)-len(newdata2), len(jumpindex[0])))
        
    if ( (dup > 0) and  (len(jumpindex[0]) != 0) ):
        jump = 0
        counter = 0
        jumpcounter = 0
        frameDict = {}
        for x in newdata2:
            #print ('Before ',x['FRAME'] , counter, jump, x['FRAME'] - jump)
            oldVal = x['FRAME']
            newVal = x['FRAME'] - jump
            if ( oldVal != newVal):
                frameDict[oldVal] = newVal
            x['FRAME'] = newVal

            if ((jumpcounter < len(jumpindex[0]))  and ( counter == jumpindex[0][jumpcounter])):
                jump = jump + 65536
                jumpcounter = jumpcounter + 1

            counter = counter + 1


        #CREATE OUTPUTDIR
        
        try:
            if not os.path.isdir(outdir+'/'):
                os.makedirs(outdir+'/', exist_ok=True)
        except FileExistsError:
            pass
            
        
        hdu1 = fits.PrimaryHDU(header=hdr0)
        hdu2 = fits.BinTableHDU(data=newdata2,header=hdro)
        hdu3 = fits.BinTableHDU(data=data2,header=hdr2)
        new_hdu = fits.HDUList([hdu1,hdu2,hdu3])

        new_hdu.writeto(outdir+'/'+fileName,overwrite=True,output_verify='silentfix')
        
        #copyfile(outdir+'/'+fileName+'.NEW',outdir+'/'+fileName)
        #if os.path.exists(file+'.NEW'):
        #    os.remove(file+'.NEW')

        return(dup,jumpindex,badDict,frameDict,goodDict)
    else:
        return (0,0,0,0,0)
                


# The Python code for rgsdupframesfix should go inside run

# iparsdic is a dictionary with all the task parameters, where their
# respective values are either those entered from the command line 
# or those taken from par file defaults.

def run(iparsdic):
    print(f'Executing {__file__} {iparsdic}')
    odfdir = iparsdic['odfdir']
    outdir = iparsdic['outputdir']


    #Create a copy of the original ODF file in new directory
    #try:
    #    os.mkdir(odfdir)
    #except FileExistsError:
    #    pass


    instrument = iparsdic['instrument']
    expr=''

    if instrument == 'RGS':
        expr = 'R'
    elif instrument == 'RGS1':
        expr = 'R1'
    elif instrument == 'RGS2':
        expr = 'R2'
    else:
        rgsdupframesix_log.log('error','Wrong instrument')
        
        
        
    rgsAUX = os.path.abspath(odfdir+'/*'+expr+'*AUX*')
    #cwd = os.getcwd()
    #os.chdir(odfdir)

    for file in glob.glob(rgsAUX):
        fileName = os.path.basename(file)


        #copyfile(file, fileName)
        #COPY AUX

        expoNumber = fileName[16:22]


        dup,jumpindex,badDict,frameDict,goodDict = fixAUX(file,outdir)

        if ( (dup > 0) and  (len(jumpindex[0]) != 0) ):
            fixScience(odfdir,outdir,expoNumber,badDict,frameDict,goodDict)

    
    #os.chdir(cwd)
