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

# eslewchain.py

from .version import VERSION, SAS_RELEASE, SAS_AKA

__version__ = f'eslewchain (eslewchain-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 

import warnings
import sys # needed in order to check argv
import subprocess # calls command line
import os # calls system
import numpy as np # used for some operations.
import time # checks how long does this take
import math # needed for the ceil function
import pysas.pyeslewchain.pyeslewchainTime as eslewchainTime # time transforming utilities
import pysas.pyeslewchain.pyeslewchainUtils as eslewchainUtils # miscellaneous utilities
import pysas.pyutils.pyutils as pyutils
from astropy.io import fits


#################################################
# Functions
#################################################

def find_min_max_x_y(event_file):
    """
    Finds the minimum and maximum values for x and y.
    
    Args:
        event_file: the event file to be checked.
    
    Output:
        (min_x, max_x, min_y, max_y): the min and max.
    """

    print('Min and max of {}'.format(event_file))

    with fits.open(event_file) as ef:
        x = ef[1].data['X']
        y = ef[1].data['Y']

    min_x = min(x)
    min_y = min(y)
    max_x = max(x)
    max_y = max(y)

    return (min_x, max_x, min_y, max_y)


def num_events(event_file):
    """
    Find the number of events in a given event file.
    
    Args:
        event_file: name of the event file.
    Output:
        number_of_events: total number of events found.
    """

    with fits.open(event_file) as ev:
        number_of_events = ev['EVENTS'].header['NAXIS2']

    return number_of_events


def add_slew_keys(names_of_files):
    """
    Write slew specific keywords into the image and exposure map headers
    All the commented lines represent another way to work with this.
    
    Args:
        names_of_files: the list of names to be added.
    """

    # Input @_ = Names of files to use
    tstart = names_of_files[-2]
    tstop = names_of_files[-1]

    print("Times:  {} {} {}\n".format(tstart, tstop, names_of_files[-3]))

    exp = (tstop - tstart) * 86400.0

    # Find the image stem from the first filename
    image_stem = names_of_files[0][0:11] + "_" + names_of_files[0][24:24+3]

    # Add the needed content into the header of each file (PRIMARY extension).
    files = names_of_files[0:-2]
    print("Files: {}\n".format(files))

    for i in files:
    #    fitsf = fits.open(i)
    #    primary = fitsf[0]
        pyutils.pymodhdu(i, 0, "OBJECT", image_stem, "Stem of image name")
        pyutils.pymodhdu(i, 0, "OBSERVER", "XMM-Newton", "Name of PI")
        pyutils.pymodhdu(i, 0, "MJDSTART", tstart ,"The start time for this subimage (MJD)")
        pyutils.pymodhdu(i, 0, "MJDSTOP", tstop, "The end time for this subimage (MJD)")
        pyutils.pymodhdu(i, 0, "EXPOSURE", exp, "The exposure time of this subimage (sec)")


def slew_split(obs, in_file):
    """
    Splits an slew into small images.

    Args: 
        obs: the OBS_ID.
        in_file: the initial file.
    """

    # Checks if .PNGs are wanted:
    makePNG = get_MakePNG_parameter()
    print('Making PNG files: {}'.format(makePNG))

    # Gets the time range with the proper funciton.
    times = find_time_ranges(in_file)
    t_begin = int(round(times[0]))
    t_end = int(round(times[1]))

    # Work out the number of subimages
    t_delta = 45
    nmaps = math.ceil((t_end - t_begin) / t_delta)

    # Find the range of X and Y values in the event file
    xy_list = find_min_max_x_y(in_file)
    x_min = xy_list[0]
    x_max = xy_list[1]
    y_min = xy_list[2]
    y_max = xy_list[3]

    # The hack to start from a given position
    #$ymin=$ybegin;

    print("Original sky coord ranges: {} {} {} {}.\n".format(x_min, x_max, y_min, y_max))
    print("Original time range: {} {}\n".format(t_begin, t_end))

    # Loop over the input file extracting roughly 1 degree square fields
    print("No of images to create: {}\n".format(nmaps))

    # Make the root filenames
    outroot = "P" + obs + "PNS003IMAGE_"
    exproot = "P" + obs + "PNS003EXPMAP"
    unfroot = "P" + obs + "PNS003UNFDAT"

    # Define temp files
    timfiltfile = 'timefiltfile.ds'
    largetimfiltfile = 'largetimefiltfile.ds'

    # Initialise an image count
    imcount = 0
    args = []

    for j in range(0, nmaps):
        # Find the time range for this subimage
        t_start = t_begin + j * t_delta
        t_stop = t_start + t_delta

        # Sort out the filename stems for this image count - image numbers in HEX.
        imcstring = format(f"{imcount:003x}")
        print('Current image count: {}'.format(imcstring))
        filtfile = "P" + obs + "PNS003PIEVLI0" + imcstring + ".ds"

        # Select events during this time range +/- the delta
        t_start_extra = t_start - t_delta
        t_stop_extra = t_stop + t_delta

        args = "evselect " + "table={} ".format(in_file) + "expression=\'(TIME in [{}:{}])\' ".format(int(round(t_start_extra)), int(round(t_stop_extra))) +\
            "filtertype=expression " + "writedss=yes " + "destruct=yes " + "filteredset={} ".format(largetimfiltfile) + "withfilteredset=yes " +\
            "keepfilteroutput=yes " + "ximagebinsize=55 " + "yimagebinsize=55 " + "ximagemin=1 " + "ximagemax=640 " + "withxranges=no " + "yimagemin=1 " +\
            "yimagemax=640 " + "withyranges=no " + "raimagecenter=0 " + "decimagecenter=0 " + "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " +\
            "maketimecolumn=no " + "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no "

        if os.system(args):
            print("event file filtering failed for (1) {} {}".format(t_start, t_stop))

        # attcalc this large file
        rejig_attitude(largetimfiltfile)

        # extra a new file with just the inner times
        args = "evselect " + "table={} ".format(largetimfiltfile) + "expression=\'(TIME in [{}:{}])\' ".format(int(round(t_start)), int(round(t_stop))) + "filtertype=expression " +\
            "writedss=yes " + "destruct=yes " + "filteredset={} ".format(timfiltfile) + "withfilteredset=yes " + "keepfilteroutput=yes " + "ximagebinsize=55 " +\
            "yimagebinsize=55 " + "ximagemin=1 " + "ximagemax=640 " + "withxranges=no " + "yimagemin=1 " + "yimagemax=640 " + "withyranges=no " + "raimagecenter=0 " +\
            "decimagecenter=0 " + "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " + "makeratecolumn=no " +\
            "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"


        if os.system(args):
            print("event file filtering failed for (2) {} {}".format(t_start, t_stop))

        # If no events were found, skip to the next subimage
        if (num_events(timfiltfile) == 0):
            continue

        # Find the X and Y range for these times
        xy_list = find_min_max_x_y(timfiltfile)
        x1 = xy_list[0]
        x2 = xy_list[1]
        y1 = xy_list[2]
        y2 = xy_list[3]

        print("Using times: {} {} X: {} {} Y: {} {} \n".format(t_start, t_stop, x1, x2, y1, y2))

        # Extract another event file with these X,Y ranges
        args = "evselect " + "table={} ".format(largetimfiltfile) + "expression=\'(X in [{}:{}])&&(Y in [{}:{}])\' ".format(x1, x2, y1, y2) +\
            "filtertype=expression " + "writedss=yes " + "destruct=yes " + "filteredset={} ".format(filtfile) + "withfilteredset=yes " + "keepfilteroutput=yes " +\
            "ximagebinsize=55 " + "yimagebinsize=55 " + "ximagemin=1 " + "ximagemax=640 " + "withxranges=no " + "yimagemin=1 " + "yimagemax=640 " + "withyranges=no " +\
            "raimagecenter=0 " + "decimagecenter=0 " + "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " +\
            "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"

        if os.system(args):
            print("event file filtering failed for {} {}".format(x1, y1))

        # Reconstruct the attitude for this events subfile
        ## NOT NEEDED NOW ??
        rejig_attitude(filtfile)

        # Find the new X,Y range
        xylist = find_min_max_x_y(filtfile)
        xminnew = xylist[0]
        xmaxnew = xylist[1]
        yminnew = xylist[2]
        ymaxnew = xylist[3]

        print("NEW range: {}, {}, {}, {}\n".format(xminnew, xmaxnew, yminnew, ymaxnew))

        # Get the RA and DEC of the centre from the filtfile
        line = find_celcent(filtfile)

        line_list = line.split(" ")
        print('RA, DEC, REV: ', line_list)
        ra = line_list[0]
        dec = line_list[1]
        rev = line_list[2]

        outb1 = outroot + "1" + imcstring + ".ds"
        outb2 = outroot + "2" + imcstring + ".ds"
        outb3 = outroot + "3" + imcstring + ".ds"
        outb6 = outroot + "6" + imcstring + ".ds"  # Soft band image
        outb7 = outroot + "7" + imcstring + ".ds"  # hard band image
        outb8 = outroot + "8" + imcstring + ".ds"  # Total band image
        outbW = unfroot + "8" + imcstring + ".ds"  # Warts n all image
        expb1 = exproot + "1" + imcstring + ".ds"
        expb2 = exproot + "2" + imcstring + ".ds"
        expb3 = exproot + "3" + imcstring + ".ds"
        expb6 = exproot + "6" + imcstring + ".ds"
        expb7 = exproot + "7" + imcstring + ".ds"
        expb8 = exproot + "8" + imcstring + ".ds"

        # Create an image in each band from this events file

        # First create an image with no pattern, flag or PI selection to
        # serve as a diagnostic

        args = "evselect " + "table={} ".format(filtfile) + "expression=true " + "filtertype=expression " + "writedss=yes " + "xcolumn=X " +\
            "ycolumn=Y " + "ximagebinsize=82 " + "yimagebinsize=82 " + "squarepixels=yes " + "imageset={} ".format(outbW) + "imagebinning=binSize " + "withimageset=yes " +\
            "ximagemin={} ".format(xminnew) + "ximagemax={} ".format(xmaxnew) + "withxranges=yes " + "yimagemin={} ".format(yminnew) + "yimagemax={} ".format(ymaxnew) +\
            "withyranges=yes " + "raimagecenter=0 " + "decimagecenter=0 " + "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " +\
            "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"


        if os.system(args):
            print("image creation failed for (1) {} {}".format(x1, y1))

        # 0.2-0.5 keV, patt 0
        args = "evselect " + "table={} ".format(filtfile) + "filtertype=expression " + "expression=\'(FLAG==0)&&(PI in [200:500])&&(PATTERN==0)\' " + "writedss=yes " + "xcolumn=X " +\
            "ycolumn=Y " + "ximagebinsize=82 " + "yimagebinsize=82 " + "squarepixels=yes " + "imageset={} ".format(outb1) + "imagebinning=binSize " + "withimageset=yes " + "ximagemin={} ".format(xminnew) +\
            "ximagemax={} ".format(xmaxnew) + "withxranges=yes " + "yimagemin={} ".format(yminnew) + "yimagemax={} ".format(ymaxnew) + "withyranges=yes " + "raimagecenter=0 " + "decimagecenter=0 " +\
            "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " + "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"

        if os.system(args):
            print("image creation failed for (2) {} {}".format(x1, y1))

        # 0.5-1.0 keV, patt 0-4
        args = "evselect " + "table={} ".format(filtfile) + "filtertype=expression " + "expression=\'(FLAG==0)&&(PI in [501:1000])&&(PATTERN<=4)\' " + "writedss=yes " + "xcolumn=X " + "ycolumn=Y " +\
            "ximagebinsize=82 " + "yimagebinsize=82 " + "squarepixels=yes " + "imageset={} ".format(outb2) + "imagebinning=binSize " + "withimageset=yes " + "ximagemin={} ".format(xminnew) +\
            "ximagemax={} ".format(xmaxnew) + "withxranges=yes " + "yimagemin={} ".format(yminnew) + "yimagemax={} ".format(ymaxnew) + "withyranges=yes " + "raimagecenter=0 " + "decimagecenter=0 " +\
            "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " + "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"

        if os.system(args):
            print("image creation failed for (3) {} {}".format(x1, y1))

        # 1.0-2.0 keV, patt 0-4
        args = "evselect " + "table={} ".format(filtfile) + "filtertype=expression " + "expression=\'(FLAG==0)&&(PI in [1001:2000])&&(PATTERN<=4)\' " + "writedss=yes " + "xcolumn=X "+\
            "ycolumn=Y " + "ximagebinsize=82 " + "yimagebinsize=82 " + "squarepixels=yes " + "imageset={} ".format(outb3) + "imagebinning=binSize " + "withimageset=yes " + "ximagemin={} ".format(xminnew) +\
            "ximagemax={} ".format(xmaxnew) + "withxranges=yes " + "yimagemin={} ".format(yminnew) + "yimagemax={} ".format(ymaxnew) + "withyranges=yes " + "raimagecenter=0 " + "decimagecenter=0 " +\
            "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " + "maketimecolumn=no " + "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"

        if os.system(args):
            print("image creation failed for (4) {} {}".format(x1, y1))

        # 2.0-12.0 keV, patt 0-4
        args = "evselect " + "table={} ".format(filtfile) + "filtertype=expression " + "expression=\'(FLAG==0)&&(PI in [2001:12000])&&(PATTERN<=4)\' " + "writedss=yes " + "xcolumn=X " + "ycolumn=Y " + "ximagebinsize=82 "+\
            "yimagebinsize=82 " + "squarepixels=yes " + "imageset={} ".format(outb7) + "imagebinning=binSize " + "withimageset=yes " + "ximagemin={} ".format(xminnew) + "ximagemax={} ".format(xmaxnew) + "withxranges=yes " +\
            "yimagemin={} ".format(yminnew) + "yimagemax={} ".format(ymaxnew) + "withyranges=yes " + "raimagecenter=0 " + "decimagecenter=0 " + "withcelestialcenter=no " + "timemin=0 " + "timemax=1000 " + "withtimeranges=no " +\
            "maketimecolumn=no " + "makeratecolumn=no " + "withrateset=no " + "histogrammin=0 " + "histogrammax=1000 " + "withhistoranges=no"

        if os.system(args):
            print("image creation failed for (5) {} {}".format(x1, y1))

        # Find the range of times of the events in the full file - roughly equivalent
        # to the start and end time of the exposure in the subimage
        tstartMjd = eslewchainTime.MRT_to_MJD(t_start)
        tstopMjd = eslewchainTime.MRT_to_MJD(t_stop)

        # Make the exposure maps
        atthk_chop(filtfile) # cut attitude file down to minimum

        # Save the image to a temporary file without a '+' sign
        args = "cp " + outb1 + " Idel.fits"
        if os.system(args):
            print("Failed to copy {} to temporary file Idel.fits".format(outb1))

        # Create the exposure maps - based on attitude from temp att file
        args = "eexpmap" + " imageset=Idel.fits" + " attitudeset=temp_sp_atthk_chopped.dat" + " eventset={}".format(filtfile) +\
            " expimageset=\'{} {} {}\'".format(expb7, expb6, expb8) + " pimin=\'2000 200 200\'" + " pimax=\'12000 2000 12000\'" + " attrebin=1"

        if os.system(args):
            return("Exposure map creation failed for {} {}".format(x1, y1))

        # Remove the temporary files
        if os.system("rm Idel.fits temp_sp_atthk_chopped.dat"):
            print("NoClean","Failed to remove temporary file")
        # Add together 0.2-0.5, 0.5-1.0, 1.0-2.0 and 2-12 keV images to
        # make the b8 and b6 images

        pyutils.pyadd((outb1, outb2, outb3), outb6)
        pyutils.pyadd((outb6, outb7), outb8)

        # Add standard slew keywords into output file headers
        # Make an array of final output filenames
        add_slew_keys([outb6, outb7, outb8, expb6, expb7, expb8, tstartMjd, tstopMjd])

        # Make .pngs if requested
        if makePNG:
            make_png_files((outb6, outb7, outb8))
        # Remove the EXPOSURE extensions from the filtered event file
        eslewchainUtils.delete_exposure_xtns(filtfile)

        # Increment the image count
        imcount = imcount + 1

    # End of loop over subimages

    # Delete temporary files
    if os.system("rm {}".format(timfiltfile)):
        print("NoClean","Failed to remove temporary files")


def find_celcent(in_file):
    """
    Gets RA, Revolution, and obsid from the FITS File.
    
    Args:
        in_file:  name of the file.

    Output:
        ostring: string with information related to the observation.
    """

    with fits.open(in_file) as hdu:
        ra = hdu[1].header['REFXCRVL']
        dec = hdu[1].header['REFYCRVL']
        rev = hdu[1].header['REVOLUT']
        obs = hdu[1].header['OBS_ID']

    # Get the RA in the right form
    cra = round(ra, 4)
    if ra < 10.0:
        cra = "00" + str(cra)
    elif ra < 100.0:
        cra = "0" + str(cra)

    # Get the DEC in the right form
    cdec = 0.0
    if dec >= 10.0:
        cdec= '+' + str(round(dec, 4))
    elif dec >= 0.0 and dec < 10.0:
        cdec = '+0' + str(round(abs(dec), 4))
    elif dec > -10.0:
        cdec = '-0' + str(round(abs(dec), 4))
    else:
        cdec = '-' + str(round(abs(dec), 4))

    # Set revolution to 4 digits
    revolution = (f'{rev:04d}')

    # remove quotes from OBSID. Should not have need of this now, but anyways.
    obs = obs.replace('"', '')
    obs = obs.replace("'", "")

    ostring = str(cra) + ' ' + str(cdec) + ' ' + str(revolution) + ' ' + str(obs)
    print("{}\n".format(ostring))

    print('CELPOS: ', ostring)
    return ostring


def find_time_ranges(event_file):
    """
    Finds the maximum and minimum times present.
    
    Args:
    event_file: the event file to be used.
    
    Output:
        ostring: returns the minimum and the maximum as a tuple.
    """

    with fits.open(event_file) as ev:
        times = ev[1].data['TIME']

    min_time = int(round(min(times)))
    max_time = int(round(max(times)))
    ostring = (min_time, max_time)

    return ostring


def atthk_chop(event_list):
    """
    Used to subset an attitude file over the times present in
    an event file +/- 75 seconds> NB +/- 30 secs as before gives
    bad exposures at the beginning of the slew now.
    
    Args:
        event_list: an event list
    Output:
        (min_time, max_time): a tuple containing the minimum time and the maximum time.
    """

    with fits.open(event_list) as ev:
        times = ev[1].data['TIME']

    min_time = int(round(min(times) - 75))
    max_time = int(round(max(times) + 75))

    pyutils.pyselect('atthk.dat', 'temp_sp_atthk_chopped.dat', 1, 'TIME', max_time, min_time)

    print('Results from attik_chop: ', min_time, max_time)
    return (min_time, max_time)


def get_MakePNG_parameter():
    """
    Returns the parameter needed for MakePNG.
    
    Output:
        0 if withpng is not in argv, or not present, 1 if it's present.
    """

    make_png = makepng

    return make_png


def find_ra_dec(fits_file, out_image):
    """
    Obtains the RA and DEC for a given fits file.
    
    Args:
        fits_file: the fits file to use.
        out_image: the output image.
    
    Output:
        celpos: a tuple containing the RA and DEC.
    """

    # First we find the mean.

    with fits.open(fits_file) as ev:
        x = ev[1].data['X']
        y = ev[1].data['Y']

    mean_x = np.mean(x)
    mean_y = np.mean(y)

    x_minbit = int(round(mean_x - 3200))
    y_minbit = int(round(mean_y - 3200))
    x_maxbit = int(round(mean_x + 3200))
    y_maxbit = int(round(mean_y + 3200))


    if os.system("evselect table={} filtertype=expression expression=true writedss=yes ".format(fits_file) +\
        "xcolumn=X ycolumn=Y ximagebinsize=800 yimagebinsize=800 squarepixels=yes imageset={} ".format(out_image) +\
        "imagebinning=binSize withimageset=yes specchannelmin=0 specchannelmax=20479 ximagemin={} ".format(x_minbit) +\
        "ximagemax={} withxranges=yes yimagemin={} yimagemax={} withyranges=yes ".format(x_maxbit, y_minbit, y_maxbit) +\
        "raimagecenter=0 decimagecenter=0 withcelestialcenter=no timemin=0 timemax=1000 withtimeranges=no " +\
        "maketimecolumn=no makeratecolumn=no withrateset=no histogrammin=0 histogrammax=1000 withhistoranges=no"):

        return 'Error in evselect (find_ra_dec).'


    cmd = 'ecoordconv imageset={} withcoords=yes x={} y={} pos2eqpos=yes | grep \'RA: DEC:\''.format(out_image, mean_x, mean_y)
    ps = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    out = ps.communicate()[0]
    celpos = [None, None]

    line = out.rstrip()
    line_list = line.decode().split(' ')
    print('time list: ', line_list)
    celpos[0] = float(line_list[3])
    celpos[1] = float(line_list[4])

    # Extract the RA, DEC from the input region centre line

    return celpos


def make_png_files(files):
    """
    Makes png files for each given image.
    
    Args:
        files: list of image files.
    """

    for i in range(0, len(files)):
        # Creates the name of the file based on the original name
        outfile = files[i][0:27] + '.png'
        image_plot_cmd = 'implot ' + 'colourmap=1 ' 'withzclip=no ' + 'set={} '.format(files[i]) +\
            'trimborder=no ' + 'device={}/png '.format(outfile)
        if os.system(image_plot_cmd):
            return 'Error in implot'

        print('Produced: {}'.format(outfile))


def rejig_attitude_internal(filtfile):
    """
    Operates alongside rejig_attitude.
    
    Args:
        filtfile: the filtered file.
    """

    tempfits = "temp_sp_tempfits"
    celpos = find_ra_dec(filtfile, tempfits)
    newra = celpos[0]
    newdec = celpos[1]

    print("POSITIONS are: {} {}\n".format(newra, newdec))

    # Reset the attitude
    c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(filtfile) +\
        "refpointlabel=user nominalra={} ".format(newra) +\
        "nominaldec={} withatthkset=yes ".format(newdec)

    if os.system(c_attcalc):
        return{'Error running attcalc.'}

    celpos = find_ra_dec(filtfile, tempfits)
    newra = celpos[0]
    newdec = celpos[1]

    print("Rederived position: {}, {}\n".format(newra, newdec))

    c_attcalc = ("attcalc eventset={} imagesize=200.0 ".format(filtfile) +\
        "refpointlabel=user nominalra={} ".format(newra) +\
        "nominaldec={} withatthkset=yes ".format(newdec))


    if os.system(c_attcalc):
        return('Error while running attcalc (2).')

    celpos = find_ra_dec(filtfile, tempfits)
    newra = celpos[0]
    newdec = celpos[1]

    print('Rederived position 2: {} {}'.format(newra, newdec))

    c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(filtfile) +\
        "refpointlabel=user nominalra={} ".format(newra) +\
        "nominaldec={} withatthkset=yes ".format(newdec)

    if os.system(c_attcalc):
        return('Error while running attcalc (3)')


    # Now we will check whether the CRPIX values are within acceptable
    # limits. If not then we are probably in the situation where the
    # initial pointing position of the slew is ~180 degs away from the
    # current position AND we are near one of the poles
    crpix1 = pyutils.get_key_word(tempfits, 'CRPIX1')
    crpix2 = pyutils.get_key_word(tempfits, 'CRPIX2')
    print(crpix1, crpix2, "\n")

    newraout = newra
    newdecout = newdec

    # Shift RA by 180 degs and see if the CRPIX values get tighter

    newra = newra + 180.0
    if newra > 360.0:
        newra = newra - 360.0

    print("Retry using position: {} {}\n".format(newra, newdec))

    filtfile2 = "filt_temp.fits"
    if os.system("cp {} {}".format(filtfile, filtfile2)):
        return("CopyFail","Couldn't copy filtered file")

    c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(filtfile2) +\
        "refpointlabel=user nominalra={} ".format(newra) +\
        "nominaldec={} withatthkset=yes ".format(newdec)


    if os.system(c_attcalc):
        return ('Error while running attcalc (4)')

    celpos = find_ra_dec(filtfile2, tempfits)
    newra = celpos[0]
    newdec = celpos[1]

    crpix1b = pyutils.get_key_word(tempfits, 'CRPIX1')
    crpix2b = pyutils.get_key_word(tempfits, 'CRPIX2')

    # calculate the diff from centre for first and second attempts
    d1 = np.sqrt(crpix1 * crpix1 + crpix2 * crpix2)
    d2 = np.sqrt(crpix1b * crpix1b + crpix2b * crpix2b)

    if d1 > d2:
        print("Retry - Rederived position: {} {}\n".format(newra, newdec))

        c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(filtfile2) +\
            "refpointlabel=user nominalra={} ".format(newra) +\
            "nominaldec={} withatthkset=yes ".format(newdec)

        if os.system(c_attcalc):
            return('Error while running attcalc (5)')

        celpos = find_ra_dec(filtfile2, tempfits)
        newra = celpos[0]
        newdec = celpos[1]

        print("Retry - Rederived position 2: {} {}\n".format(newra, newdec))

        c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(filtfile2) +\
            "refpointlabel=user nominalra={} ".format(newra) +\
            "nominaldec={} withatthkset=yes ".format(newdec)

        if os.systemr(c_attcalc):
            return('Error while running attcalc (6)')

        if os.system("cp {} {}".format(filtfile2, filtfile)):
            return("CopyFail","Couldn't copy filtered file")

        newraout = newra
        newdecout = newdec

        # End of if d1>d2 block

    # Update the RA_PNT, DEC_PNT keywords as well to avoid problems with
    # eboxdetect

    with fits.open(filtfile, 'update') as ec:
        hdr = ec[0].header
        hdr.set('RA_PNT', newraout)
        hdr.set('DEC_PNT', newdecout)

    # Clear up
    if os.system("rm {} {}".format(filtfile2, tempfits)):
        return('Error while trying to remove used files.')

    # End of rejig_attitude_internal


def rejig_attitude(filtfile):
    """
    Finds the RA, DEC of a given X,Y position in an event file.
    
    Args: 
        filtfile: the filtered file.
    """

    rejig_attitude_internal(filtfile);

    # Check how well it worked
    refx = pyutils.get_key_word(filtfile, 'REFXCRPX')
    refxmin = pyutils.get_key_word(filtfile, 'REFXDMIN')
    refxmax = pyutils.get_key_word(filtfile, 'REFXDMAX')
    refy = pyutils.get_key_word(filtfile, 'REFYCRPX')
    refymin = pyutils.get_key_word(filtfile, 'REFYDMIN')
    refymax = pyutils.get_key_word(filtfile, 'REFYDMAX')

    print("Ref1 X: {} {} {}\n".format(refx, refxmin, refxmax))
    print("Ref1 Y: {} {} {}\n".format(refy, refymin, refymax))

    # If either ref point is outside range - try again

    if refx < refxmin or refx > refxmax or refy < refymin or refy > refymax:
        rejig_attitude_internal(filtfile)

        refx = pyutils.get_key_word(filtfile, 'REFXCRPX')
        refxmin = pyutils.get_key_word(filtfile, 'REFXDMIN')
        refxmax = pyutils.get_key_word(filtfile, 'REFXDMAX')
        refy = pyutils.get_key_word(filtfile, 'REFYCRPX')
        refymin = pyutils.get_key_word(filtfile, 'REFYDMIN')
        refymax = pyutils.get_key_word(filtfile, 'REFYDMAX')

        print("Ref2 X: {} {} {}\n".format(refx, refxmin, refxmax))
        print("Ref2 Y: {} {} {}\n".format(refy, refymin, refymax))


def eslewchain():
    """
    The main program. Execute this as eslewchain.eslewchain() inside a
    Python environment. Can take up to 2 hours, depending on the slew file.

    Needs: the content expected from running epproc.
    PythonUtils, as well as eslewchainTime and eslewchainTime.
    Patience.

    The output is based on the number of images (see slew_chain).
    """

    # Checking some basic stuff:
    start = time.time()

    try:
        if os.environ['SAS_ATTITUDE'] != 'RAF':
            warnings.warn('The SAS_ATTITUDE environment variable should be set to RAF when processing slew data')
    except KeyError:
        warnings.warn('The SAS_ATTITUDE environment variable should be set to RAF when processing slew data')

    if not 'SAS_ODF' in os.environ:
        print('SAS_ODF not set. Quitting...')
        eys.exit(0)

    # Find the name of the event file in the current directory
    evf = 0

    for f in os.listdir(os.getcwd()): # assuming the event files are in the cwd:
        if 'EVL' in f or 'Imag' in f:
            evfile = f
            # evfile = file.split('.')[0] # removes extension
            evf = evf + 1

    if evf == 0:
        return("evfile", "No event file found in current directory")
    elif evf > 1:
        return("evfile", "More than one event file found in current directory")
    else:
        print("Using event file: {}\n".format(evfile))

    eslewchainUtils.check_exp_extrns(evfile)


    # Find the rough start position of the slew and check that the ftools are set-up ok
    nomra = pyutils.get_key_word(evfile, 'RA_PNT')
    nomdec = pyutils.get_key_word(evfile, 'DEC_PNT')
    nompa = pyutils.get_key_word(evfile, 'PA_PNT')

    # Find the start and stop time of the first slew frame in s/c time units

    evfblk1 = evfile
    slew_start = pyutils.get_key_word(evfblk1, 'TSTART')
    slew_stop = pyutils.get_key_word(evfblk1, 'TSTOP')

    print("RA: {} DEC: {} PA: {} START: {}\n".format(nomra, nomdec, nompa, slew_start))

    # Run atthkgen to produce an ATTITUDE file - this is used to get the
    # pointing RA_PNT, DEC_PNT info.

    c_atthkgen = "atthkgen atthkset=atthk.dat"

    if os.system(c_atthkgen):
        return ('Error running atthkgen')

    # Set the attitude relative to the slew start position
    c_attcalc = "attcalc eventset={} imagesize=200.0 ".format(evfile) +\
        "refpointlabel=user nominalra=\'{}\' ".format(nomra) +\
        "nominaldec=\'{}\' withatthkset=no ".format(nomdec)

    if os.system(c_attcalc):
        return('Error while running attcalc')

    # Find the X and Y pixel ranges
    ranges = find_min_max_x_y(evfile)
    print("MINMAX: {}".format(ranges))
    xdiff = ranges[1] - ranges[0]
    ydiff = ranges[3] - ranges[2]

    # Find the observation number and remove quotes
    obs = pyutils.get_key_word(evfile, 'OBS_ID')

    # Split the slew into small event files and make images
    # depending on whether the slew is predominantly in the X or Y direction
    slew_split(obs, evfile)

    # Rename and Clean
    print('Cleaning up...')
    eslewchainUtils.rename_and_clean(obs, evfile)
    end = time.time()

    print("eslewchain processing finished.\nThis took {} seconds.".format(round(end - start, 2)))



def run(iparsdic):
    print(f'Executing {__file__} {iparsdic}')
    global makepng
    makepng = iparsdic['withpng']
    if makepng == 'no':
        makepng = 0
    elif makepng == 'yes':
        makepng = 1
    else:
        return 'Not a valid parameter for makepng'
    eslewchain()
