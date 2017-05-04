#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  4 16:59:29 2017

@author: throop
"""

# This is a driver routine that calls NH_JRING_CREATE_MASKFILE() many times.
# That function works on individual files. This function reads and interactively 
# plots an entire directory.

# General python imports

import pdb
import glob
import math       # We use this to get pi. Documentation says math is 'always available' 
                  # but apparently it still must be imported.
from   subprocess import call
import warnings
import pdb
import os.path
import os
import subprocess

import astropy
from   astropy.io import fits
from   astropy.table import Table
import astropy.table   # I need the unique() function here. Why is in in table and not Table??
import matplotlib.pyplot as plt # pyplot
from   matplotlib.figure import Figure
import numpy as np
import astropy.modeling
from   astropy.utils import data

from   scipy.optimize import curve_fit
                       # Pylab defines the 'plot' command
import spiceypy as sp
from   astropy.wcs import WCS
from   astropy.vo.client import conesearch # Virtual Observatory, ie star catalogs
from   astropy import units as u           # Units library
from   astropy.coordinates import SkyCoord # To define coordinates to use in star search
from   scipy.stats import mode
from   scipy.stats import linregress
import wcsaxes
import time
from   scipy.interpolate import griddata
#import cv2

import re # Regexp
import pickle # For load/save

import cProfile # For profiling

from   matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from   matplotlib.figure import Figure
import warnings
from   importlib import reload
from   time import gmtime, strftime

# HBT imports

import hbt

#==============================================================================
# Now the driver routine that calls the individual routine
#==============================================================================

files = glob.glob(dir + '*_opnav.fit')  # Only worth doing this for files that have been opnav'd

plt.set_cmap('Greys_r')            
hbt.figsize((15,15))
do_plot           = True
DO_SKIP_NAVIGATED = True
DO_SKIP_4X4       = False
DO_INTERACTIVE    = True
method_opnav      = 'fft'
is_success        = False

i = 0   # i must be the current image number
        # ii is index within the list
        # k is the keyboard string

sats = ['Adrastea', 'Thebe', 'Metis', 'Io', 'Europa', 'Amalthea']


# Now start a keyboard loop and run with input from the user

while True:
    
    file_short = files[i].split('/')[-1]
    
    if DO_INTERACTIVE:
        k = input("File {}-{} ({} = {}): ".format(0, np.size(files)-1, i, file_short))
    else:
        k = repr(list_batch[ii])         # Load the next element, as a string
        if (ii == np.size(list_batch)-1):  # If we've hit the last element
            DO_INTERACTIVE = True    # And go back to interactive mode

    if (k in ['x', 'q']):            # QUIT
        sys.exit(0)

    if ('-' in k):
       (i1, i2) = np.array(k.split('-')).astype('int')
       list_batch = hbt.frange(int(i1), int(i2)).astype('int')
       ii = 0                        # Current element number, within our list
       k = repr(list_batch[ii])      # Extract one element from it
       print ("Running from {} to {}...".format(i1, i2))
       DO_INTERACTIVE = False

    if ('*' in k):                   # Wildcard search
        searchstr = k.replace('*', '')
        for ii,file in enumerate(files):
            if (searchstr in file):
                print("{}. {}".format(ii, file.split('/')[-1]))
                
    if (k == 'l'):                  # List all files
        for ii,file in enumerate(files):
            print("{}. {}".format(ii, file.split('/')[-1]))
    
    if (k == '?'):                  # Get help
        print(" <#> = navigate, <#-#> = navigate range, l = list, n = next, x = exit, sn = toggle Skip_Navigated, " + 
                 "s4 = toggle Skip_4x4")
    
    if (k == 'sn'):
        DO_SKIP_NAVIGATED = not(DO_SKIP_NAVIGATED)
        print("DO_SKIP_NAVIGATED = {}".format(DO_SKIP_NAVIGATED))

    if (k == 's4'):
        DO_SKIP_4X4 = not(DO_SKIP_4X4)
        print("DO_SKIP_4X4 = {}".format(DO_SKIP_4X4))
        
    if (k == 'n') :                 # Next
        k = repr(i)

    if (k == ''):                   # Next
        k = repr(i)
    
    if hbt.is_number(k):            # If a number was entered () 
        i = int(k)
        file = files[i]
        file_short = file.split('/')[-1]
        file_out   = file.replace('.fit', '_opnav.fit')
        
        im = hbt.read_lorri(file) # Read the image, and process it a bit I think

        print
        print("Reading {}/{}: {}".format(int(k), np.size(files), file_short))
        hdulist = fits.open(file) 
        header  = hdulist['PRIMARY'].header
        mode    = header['SFORMAT']
        exptime = header['EXPTIME']
        hdulist.close()           
        
        is_navigated = os.path.isfile(file_out)

# If it's a 4x4 file, it's probably saturated and lots of things don't work. So doing navigation 
# it hopeless. But we don't want to lose track of the file (for the numbering scheme), 
# so we tag it and copy anyhow.
        
        if (mode == '4X4') and (DO_SKIP_4X4):
            print("{}/{}: Skipping OpNav due to 4x4".format(i, np.size(files)))
            print("Copying to {}".format(file_out))
            shutil.copyfile(file, file_out)

        elif (is_navigated and DO_SKIP_NAVIGATED):
            print ("{}/{}: Skipping since already navigated".format(i, np.size(files)))
    
        else:
    
    # Do the masking call
                    
            objects = nh_jring_create_maskfile(file, bodies = sats)
            
            is_success = True
            
    else:
        print("Error!")
        is_success = False
        
    if (DO_INTERACTIVE and is_success):
        i += 1        # Go to next image in master list
    else:
        ii += 1       # Go to next image in the sublist

            