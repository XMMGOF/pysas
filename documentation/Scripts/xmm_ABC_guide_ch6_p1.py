#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 13 12:20:26 2023

@author: ryan.tanner@nasa.gov

Script to replicate the XMM-Newton ABC Guide, chapter 6.
https://heasarc.gsfc.nasa.gov/docs/xmm/abc/node8.html
Part 1
"""

# pySAS imports
import gofpysas as pysas
from gofpysas.wrapper import Wrapper as w

# Useful imports
import os

# Imports for plotting
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import Table
plt.style.use(astropy_mpl_style)

# Make FITS image file and plot
def make_fits_image(event_list_file, image_file='image.fits'):
    
    inargs = {}
    inargs['table']        = '{0}'.format(event_list_file)
    inargs['withimageset'] = 'yes'
    inargs['imageset']     = '{0}'.format(image_file)
    inargs['xcolumn']      = 'X'
    inargs['ycolumn']      = 'Y'
    inargs['imagebinning'] = 'imageSize'
    inargs['ximagesize']   = '600'
    inargs['yimagesize']   = '600'

    w('evselect', inargs).run()

    hdu = fits.open(image_file)[0]
    wcs = WCS(hdu.header)

    ax = plt.subplot(projection=wcs)
    plt.imshow(hdu.data, origin='lower', norm='log', vmin=1.0, vmax=1e2)
    ax.set_facecolor("black")
    plt.grid(color='blue', ls='solid')
    plt.xlabel('RA')
    plt.ylabel('Dec')
    plt.colorbar()
    plt.show()
    
# Make light curve file and plot
def plot_light_curve(event_list_file, light_curve_file='ltcrv.fits'):
                     
    inargs = ['table={0}'.format(event_list_file), 
              'withrateset=yes', 
              'rateset={0}'.format(light_curve_file), 
              'maketimecolumn=yes', 
              'timecolumn=TIME', 
              'timebinsize=100', 
              'makeratecolumn=yes']

    w('evselect', inargs).run()

    ts = Table.read(light_curve_file,hdu=1)
    plt.plot(ts['TIME'],ts['RATE'])
    plt.xlabel('Time (s)')
    plt.ylabel('Count Rate (ct/s)')
    plt.show()

# 6.1 : Rerun basic processing
obsid = '0123700101'
odf = pysas.odfcontrol.ODFobject(obsid)
odf.basic_setup(overwrite=False,repo='heasarc',
                rerun=False, epproc_args=['withoutoftime=yes'])

# Event list file names and paths are in the odf object
file_names = list(odf.files.keys())
print(file_names)
for name in file_names: print(odf.files[name])

# The data, odf, and work directory paths are in the odf object
print("Data directory: {0}".format(odf.data_dir))
print("ODF  directory: {0}".format(odf.odf_dir))
print("Work directory: {0}".format(odf.work_dir))


# 6.2 : Plot unfiltered image

os.chdir(odf.work_dir)
mos1 = odf.files['m1evt_list'][0]
make_fits_image(mos1)


# 6.3 : Apply Standard Filter
# A lot of that is just background noise. We need to filter it out.
filtered_event_list = 'mos1_filt.fits'

inargs = ['table={0}'.format(mos1), 
          'withfilteredset=yes', 
          "expression='(PATTERN <= 12)&&(PI in [200:4000])&&#XMMEA_EM'", 
          'filteredset={0}'.format(filtered_event_list), 
          'filtertype=expression', 
          'keepfilteroutput=yes', 
          'updateexposure=yes', 
          'filterexposure=yes']

w('evselect', inargs).run()

# Create image file from filtered event list "outfilter"
make_fits_image(filtered_event_list)


# 6.4 : Create Light Curve
# Helps us see if there is particle flaring so we can filter it out.

light_curve_file='mos1_ltcrv.fits'
plot_light_curve(filtered_event_list, light_curve_file=light_curve_file)


# 6.5 : Applying Time Filters
# 6.5.1 : Filter on RATE with tabgtigen

gti_rate_file = 'gti_rate.fits'
mos1_filt_rate = 'mos1_filt_rate.fits'

inargs = ['table={0}'.format(light_curve_file), 
          'gtiset={0}'.format(gti_rate_file),
          'timecolumn=TIME', 
          "expression='(RATE <= 6)'"]

w('tabgtigen', inargs).run()

inargs = ['table={0}'.format(filtered_event_list),
          'withfilteredset=yes', 
          "expression='GTI({0},TIME)'".format(gti_rate_file), 
          'filteredset={0}'.format(mos1_filt_rate),
          'filtertype=expression', 
          'keepfilteroutput=yes',
          'updateexposure=yes', 
          'filterexposure=yes']

w('evselect', inargs).run()

# Create new image file from filtered event list.
# Point sources are left.

make_fits_image(mos1_filt_rate, image_file='final_image1.fits')

# Create new light curve and plot.

plot_light_curve(mos1_filt_rate)


# 6.5.2 : Filter on TIME with tabgtigen

gti_time_file = 'gti_rate.fits'
mos1_filt_time = 'mos1_filt_time.fits'

inargs = ['table={0}'.format(light_curve_file), 
          'gtiset={0}'.format(gti_time_file),
          'timecolumn=TIME', 
          "expression='(TIME <= 73227600)&&!(TIME IN [7.32118e7:7.3212e7])&&!(TIME IN [7.32204e7:7.32206e7])'"]

w('tabgtigen', inargs).run()

inargs = ['table={0}'.format(filtered_event_list),
          'withfilteredset=yes', 
          "expression='GTI({0},TIME)'".format(gti_time_file), 
          'filteredset={0}'.format(mos1_filt_time),
          'filtertype=expression', 
          'keepfilteroutput=yes',
          'updateexposure=yes', 
          'filterexposure=yes']

w('evselect', inargs).run()

make_fits_image(mos1_filt_time, image_file='final_image2.fits')
plot_light_curve(mos1_filt_time)


# 6.5.3 : Filter on TIME with gtibuild

gti_lines = ['0        73227600 + # Good time from the start of the observation',
             '73211800 73212000 - # But without a small flare here.',
             '73211800 73212000 - # And here.']

with open('gti.txt', 'w') as f:
    f.writelines(gti_lines)
    
gti_txt_file = 'gti.txt'
new_gti_file = 'new_gti.fits'
mos1_new_gti = 'mos1_new_gti.fits'

inargs = ['file={0}'.format(gti_txt_file),
          'table={0}'.format(new_gti_file)]

w('gtibuild', inargs).run()

inargs = ['table={0}'.format(filtered_event_list),
          'withfilteredset=yes', 
          "expression='GTI({0},TIME)'".format(new_gti_file), 
          'filteredset={0}'.format(mos1_new_gti),
          'filtertype=expression', 
          'keepfilteroutput=yes',
          'updateexposure=yes', 
          'filterexposure=yes']

w('evselect', inargs).run()

make_fits_image(mos1_new_gti, image_file='final_image3.fits')
plot_light_curve(mos1_new_gti)


# 6.5.4 : Filter on TIME by Explicit Reference

expression = "expression='(PATTERN <= 12)&&(PI in [200:12000])&&#XMMEA_EM&&(TIME <= 73227600) &&!(TIME IN [7.32118e7:7.3212e7])&&!(TIME IN [7.32204e7:7.32206e7])'"

full_filt_event_list = 'mos1_filt.fits'

inargs = ['table={0}'.format(mos1), 
          'withfilteredset=yes', 
          expression, 
          'filteredset={0}'.format(full_filt_event_list), 
          'filtertype=expression', 
          'keepfilteroutput=yes', 
          'updateexposure=yes', 
          'filterexposure=yes']

w('evselect', inargs).run()

make_fits_image(full_filt_event_list, image_file='final_image4.fits')
plot_light_curve(full_filt_event_list)


