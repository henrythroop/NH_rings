# -*- coding: utf-8 -*-
"""
Created on Mon Feb 29 14:55:00 2016

@author: throop

"""

# -*- coding: utf-8 -*-
"""
# Program display a GUI of NJ J-ring data to navigate and extract it.

# Possible features to be added:
#  o Output images as PNG
#  o Select multiple images and display them as an arrayf
#  o Slider to scale the image brightness / contrast
#  o Subtract median? Subract neighbor image?

# Widget program created 18-May-2016 based on previous text version (same name), and salt_interact.py .

@author: throop
"""

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
from   scipy.optimize import curve_fit
#from   pylab import *  # So I can change plot size.
                       # Pylab defines the 'plot' command
import spiceypy as sp
#from   itertools import izip    # To loop over groups in a table -- see astropy tables docs
from   astropy.wcs import WCS
from   astropy.vo.client import conesearch # Virtual Observatory, ie star catalogs
from   astropy import units as u           # Units library
from   astropy.coordinates import SkyCoord # To define coordinates to use in star search
#from   photutils import datasets
from   scipy.stats import mode
from   scipy.stats import linregress
import wcsaxes
import time
from scipy.interpolate import griddata

import re # Regexp
import pickle # For load/save

import cProfile # For profiling

# Imports for Tk

#import Tkinter # change Tkinter -> tkinter for py 2 - 3?
import tkinter
from tkinter import ttk
from tkinter import messagebox
tkinter.messagebox
#import tkMessageBox #for python2
from   matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from   matplotlib.figure import Figure

# HBT imports

import hbt

#pdb.set_trace()

# First we define any general-purpose functions, which are not part of the class/module.
# We can move these to a different file at some point.

        
class App:

# Now define the functions that are part of this module (or class, not sure). They are accessed with 
# self.function(), and they have access to all of the variables within self. .	

##########
# INIT CLASS
##########

    def __init__(self, master):

# Set some default values

        self.filename_save = 'nh_jring_read_params_571.pkl' # Filename to save parameters 

        self.dir_out    = '/Users/throop/data/NH_Jring/out/' # Directory for saving of parameters, backplanes, etc.
        
        dir_images = '/Users/throop/data/NH_Jring/data/jupiter/level2/lor/all'

        file_tm = "/Users/throop/gv/dev/gv_kernels_new_horizons.txt"  # SPICE metakernel

# Set the sizes of the plots -- e.g., (7,7) = large square

        self.figsize_1 = (7,7) # Setting this larger and larger still leaves whitespace...
        self.figsize_2 = (7,3)
        self.figsize_3 = (7,4)

# Set various default values
        
        option_bg_default   = 'String'
        entry_bg_default    = '0-10' # Default polynomial order XXX need to set a longer string length here!
        index_group_default = 8 # Jupiter ring phase curve
        index_image_default = 54 # Image number within the group

        self.do_autoextract     = 0             # Flag to extract radial profile when moving to new image. 
                                                # Flag is 1/0, not True/False, as per ttk.
                                                
# Do some general code initialization

        hbt.set_plot_defaults()
        
        self.bgcolor = '#ECECEC'    # ECECEC is the 'default' background for a lot of the ttk widgets.
        
        (r2d, d2r) = (hbt.r2d, hbt.d2r)

# Start up SPICE

        sp.furnsh(file_tm) # Commented out for testing while SPICE was recopying kernel pool.

# Check if there is a pickle save file found. If it is there, go ahead and read it.

        if os.path.exists(self.dir_out + self.filename_save):
            print("Loading file: " + self.filename_save)
            self.load(verbose=False) # This will load self.t
            t = self.t

        else:    

# Find and process all of the FITS header info for all of the image files
# 't' is our main data table, and has all the info for all the files.
        
            t = hbt.get_fits_info_from_files_lorri(dir_images)

# Define new columns for the main table. 
# For several of these, we want to stick an array into the table cell. We do this by defining it as a string.
         
            t['dx_opnav']  = 0 # The measured offset between pos_star_cat and pos_star_image
            t['dy_opnav']  = 0
            t['dx_offset'] = 0 # Additional user-requested offset between the two
            t['dy_offset'] = 0
            t['bg_method'] = option_bg_default # None, Previous, Next, Polynomial, Median, "Grp Num Frac Pow", etc.
            t['bg_argument'] = entry_bg_default # A number (if 'Polynomial'). A range (if 'Median')
            t['Comment']  = 'Empty comment'  # Blank -- I'm not sure how to init its length if needed
            t['is_navigated'] = False  # Flag
            t['x_pos_star_cat']   = np.array(t['Format'],dtype='U20000')   # 1 x n array, pixels, with abcorr
            t['y_pos_star_cat']   = np.array(t['Format'],dtype='U20000')   # 1 x n array, pixels, with abcorr            
            t['x_pos_star_image'] = np.array(t['Format'],dtype='U20000') # 1 x n array, pixels, with abcorr
            t['y_pos_star_image'] = np.array(t['Format'],dtype='U20000') # 1 x n array, pixels, with abcorr
            t['x_pos_ring1']      = np.array(t['Format'],dtype='U20000')  # 5000 char is not long enough!
            t['y_pos_ring1']      = np.array(t['Format'],dtype='U20000')    # 10,000 char is not long enough!
            t['x_pos_ring2']      = np.array(t['Format'],dtype='U20000')
            t['y_pos_ring2']      = np.array(t['Format'],dtype='U20000')
                      
            self.t = t
            
            # Since there was no pickle file read, go ahead and write it out. Some of the other routines
            # rely on having this file available.

            lun = open(self.dir_out + self.filename_save, 'wb')
            t = self.t
            pickle.dump(t, lun)
            lun.close()
            print("Wrote: " + self.dir_out + self.filename_save)
            
        # Get a list of unique observation descriptions (i.e., 'groups')
        
        self.groups = astropy.table.unique(t, keys=(['Desc']))['Desc']
                
        # Set initial location to first file in first group
        
        self.index_group = index_group_default
        self.index_image  = index_image_default
        
        # Extract the one group we are looking at 
        # NB: This creates an entirely new table -- *not* a view into the original table. 
        # If we modify values here, we need to explicitly write the changes back to the original.
        
        self.groupmask = t['Desc'] == self.groups[self.index_group]
        self.t_group = t[self.groupmask]
        
        self.num_images_group = np.size(self.t_group)

# Now set up a few variables for the current image only. These are not stored in the main
# table, because they are regenerated / reloaded every time, and they are potentially very large.

        self.planes             = 0         # Backplanes will be loaded into this variable
        self.has_backplane      = False     # Need to update this every time we load a new image file.
        self.profile_radius     = np.zeros((1))
        self.profile_azimuth    = np.zeros((1))
        self.bins_radius        = np.zeros((1))
        self.bins_azimuth       = np.zeros((1))
        
        self.image_raw          = np.zeros((1)) # The current image, with *no* processing done. 
                                                # Prevents re-reading from disk.
        self.image_processed    = np.zeros((1)) # Current image, after all processing is done (bg, scaling, etc)
        self.image_bg_raw       = np.zeros((1)) # The 'raw' background image. No processing done to it. 
                                                # Assume bg is single image; revisit as needed.
        
        self.file_backplane_shortname = ''      # Shortname for the currently loaded backplane.
								
        self.legend             = False         # Store pointer to plot legend here, so it can be deleted
								
        (dim, radii)            = sp.bodvrd('JUPITER', 'RADII', 3)
        self.rj                 = radii[0]  # Jupiter radius, polar, in km. Usually 71492.
        
        self.stretch_percent    = 90            # Image scaling value to use. 90 means plot from 5th to 95th %ile.
        
# Now define and startup the widgets
                
        self.path_settings = "/Users/throop/python/salt_interact_settings/"

# Create the sliders, for navigation offset
        
        self.slider_offset_dx  = ttk.Scale(master, from_=-450, to=450, orient=tkinter.HORIZONTAL, 
                                   command=self.set_offset) # Slider dx offset
        self.slider_offset_dy  = ttk.Scale(master, from_=-450, to=450, orient=tkinter.VERTICAL, 
                                   command=self.set_offset) # Slider dy offset

# Define labels

        self.var_label_info = tkinter.StringVar()
        self.var_label_info.set("init")
        self.label_info = ttk.Label(master, textvariable = self.var_label_info)
        
        self.var_label_status_io = tkinter.StringVar()
        self.var_label_status_io.set('IO STATUS')
        self.label_status_io = ttk.Label(master, textvariable = self.var_label_status_io) # For the 'save status' text
                   
# Create the buttons
   
        self.button_prev =     ttk.Button(master, text = 'Prev',     command=self.select_image_prev)
        self.button_next =     ttk.Button(master, text = 'Next',     command=self.select_image_next)
        self.button_plot   =   ttk.Button(master, text = 'Plot',     command=self.handle_plot_image)
        self.button_extract =  ttk.Button(master, text = 'Extract',  command=self.handle_extract_profiles)
        self.button_navigate = ttk.Button(master, text = 'Navigate', command=self.handle_navigate)
        self.button_repoint =  ttk.Button(master, text = 'Repoint',  command=self.repoint)
        self.button_ds9 =      ttk.Button(master, text = 'Open in DS9', command=self.open_external)
        self.button_copy =     ttk.Button(master, text = 'Copy name to clipboard', command=self.copy_name_to_clipboard)
        self.button_quit =     ttk.Button(master, text = 'Quit',     command = self.quit)
        self.button_load =     ttk.Button(master, text = 'Load',     command = self.load)
        self.button_save =     ttk.Button(master, text = 'Save',     command = self.save_file)
        self.button_export =   ttk.Button(master, text = 'Export Analysis', command = self.export_analysis)
        
        self.var_checkbutton_extract = tkinter.IntVar()
        self.var_checkbutton_extract.set(self.do_autoextract)        # Values are in fact 1,0  not  True,False. Ugh. 
        self.checkbutton_extract = ttk.Checkbutton(master, text = 'Auto-Extract', command = self.handle_checkbutton, 
                                                   var = self.var_checkbutton_extract)

        
# Create controls for the background subtraction
# NB: Sometimes the current value for OptionMenu is left as blank. If this happens, need to restart ipython console.
      
        self.var_option_bg = tkinter.StringVar()
        self.var_option_bg.set("Polynomial Order:")
        
        self.label_bg =         ttk.Label(master, text='Background Method')
        self.option_bg =        ttk.OptionMenu(master, self.var_option_bg,\
                                    option_bg_default,  # First argument is the default
                                    "Polynomial", "Previous", "Next", "Median Range", "None", "Grp Num Frac Pow", \
                                     "String", command = self.select_bg)

        self.entry_bg=          ttk.Entry(master, width=12)
        self.entry_bg.insert(0, entry_bg_default) # Set the value (e.g., order = "4")
              
# Create the Entry boxes (ie, single-line text)
# Note that for .insert(num, text), 'num' is in format line.character. Line starts at 1; char starts at 0.
# For both .text and .entry .
        
        self.entry_comment = ttk.Entry(master)
        self.entry_comment.insert(0, 'Comment')

# Create the text box to stuff the header into
# Since we are just displaying text, I'm not sure if this is the right widget to use
# http://www.tkdocs.com/tutorial/text.html
        
        self.text_header = tkinter.Text(master, height=15)

        self.text_header.insert(1.0,'HEADER goes here')

# Add the scrollbars for the header data

        self.scrollbar_text_header_y = ttk.Scrollbar(master, orient='vertical', command=self.text_header.yview)
        self.text_header['yscrollcommand'] = self.scrollbar_text_header_y.set
        
# Create the Listbox for Groups (ie, 'Desc') and load it up
# In theory I should use listvar and StringVar() for this, but they seem to not work for arrays with 
# spaces in them! So I have to load up the elments individually.
# Need to do exportselection=False. Otherwise, only one listbox will be 'active' at a time, and won't be
# able to see value of current setting in both. 
#   http://stackoverflow.com/questions/756662/using-multiple-listboxes-in-python-tkinter

        self.lbox_groups = tkinter.Listbox(master, height=5, selectmode = "browse",
                                           width=25, exportselection=False)
                                           
        for ii,item in enumerate(self.groups.data):    # "groups.data" gives the name of the group
            self.lbox_groups.insert("end", repr(ii) + ". " + item)

        self.lbox_groups.bind('<<ListboxSelect>>', self.select_group) # Define the event handler for 
# Listbox is tied to an event handler, *not* to the normal command= thing.

# Create the listbox for files

        files_short = self.t_group['Shortname']
        num_files = np.size(files_short)

        self.lbox_files = tkinter.Listbox(master, height=20, selectmode = "browse",
                                            width = 30, exportselection=False)

# Populate the listbox for files

        for i in range(np.size(files_short)):
            
             s = '{0:3}.   {1}   {2:.3f}   {3}  {4}'.format( \
                 repr(i), 
                 files_short[i], 
                 self.t_group['Exptime'][i], 
                 self.t_group['Format'][i],
                 self.t_group['UTC'][i]
                 
                 )
             self.lbox_files.insert("end", s)
                  
        self.lbox_files.bind('<<ListboxSelect>>', self.select_image) # Define event handler

# Call select_group, to load the contents of the current group (from index_group) into the file list

#        self.select_group(self)
        
# Add the scrollbars for the file listbox

        self.scrollbar_files_y = ttk.Scrollbar(master, orient='vertical', command=self.lbox_files.yview)
        self.lbox_files['yscrollcommand'] = self.scrollbar_files_y.set
        
# Set up Plot 1 : Main image window
        
# add_subplot: " kwargs are legal Axes kwargs. The Axes instance will be returned."
# http://matplotlib.org/api/figure_api.html
# http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
     
        self.fig1 = Figure(figsize = (7,7))    # <- this is in dx, dy... which is opposite from array order!
        junk = self.fig1.set_facecolor(self.bgcolor)

        self.ax1 = self.fig1.add_subplot(1,1,1, 
                                    xlabel = 'X', ylabel = 'Y', 
                                    label = 'Image',
                                    xlim = (0,1023),
                                    ylim = (1023,0)) # Return the axes
 
        self.canvas1 = FigureCanvasTkAgg(self.fig1,master=master)
        self.canvas1.show()
        self.ax1.imshow(hbt.read_lorri('')) # Put up an empty frame, if file = ''
        
# Set up Plot 2 : Radial / Azimuthal profiles
        
        self.fig2 = Figure(figsize = (7,3))
        junk = self.fig2.set_facecolor(self.bgcolor)

        self.ax2 = self.fig2.add_subplot(1,1,1, 
                                    xlabel = 'Radius or Azimuth', ylabel = 'Intensity', 
                                    label = 'Plot') # Return the axes

        self.canvas2 = FigureCanvasTkAgg(self.fig2,master=master)
        self.canvas2.show()  

# Set up Plot 3 : Unwrapped ring
        
        self.fig3 = Figure(figsize = (7,4))
        junk = self.fig3.set_facecolor(self.bgcolor)

        self.ax3 = self.fig3.add_subplot(1,1,1, 
                                    xlabel = 'Azimuth', ylabel = 'Intensity', 
                                    label = 'Plot') # Return the axes
 
        self.canvas3 = FigureCanvasTkAgg(self.fig3,master=master)
        self.ax3.imshow(hbt.read_lorri(''))
        self.canvas3.show()  

# Set up Plot 4 : Debugging / Misc window
     
        self.fig4 = Figure(figsize = (7,3))
        junk = self.fig4.set_facecolor(self.bgcolor)

        self.ax4 = self.fig4.add_subplot(1,1,1, 
                                    xlabel = 'X', ylabel = 'Y', 
                                    label = 'Image') # Return the axes
 
        self.canvas4 = FigureCanvasTkAgg(self.fig4,master=master)
        self.canvas4.show()
        plot4 = self.ax4.plot([1,2], [3,5]) # Put up an empty frame, if file = ''
        
# Put objects into appropriate grid positions

# Column 1 (LHS) -- numbered as column 1 .. 2

        self.lbox_groups.grid(  row=1, column=1, sticky = 'news', rowspan=1, padx=10)
        self.lbox_files.grid(   row=2, column=1, sticky = 'news',rowspan=2, padx=10)
        self.entry_comment.grid(row=4, column=1, sticky = 'new')
        self.label_info.grid(   row=5, column=1, sticky='new', padx=10, )
        self.text_header.grid(  row=6, column=1, rowspan=6, sticky = 'new', padx=10, pady=10)

        self.scrollbar_files_y.grid(       row=2, column=2, rowspan=2, sticky = 'ns')
        self.scrollbar_text_header_y.grid( row=6, column=2, rowspan=6, sticky = 'ns')
               
# Column 2 (Center) -- numbered as column 10 .. 14

        self.slider_offset_dy.       grid(row=1,  column=10, rowspan=3, sticky='ns') 

        self.canvas1.get_tk_widget().grid(row=1,  column=11, columnspan=4, rowspan=3, sticky = 'nsew')
        self.slider_offset_dx.       grid(row=5,  column=11, columnspan=4, sticky='new')

        self.label_bg.               grid(row=6,  column=11)
        self.option_bg.              grid(row=6,  column=13, sticky='we')
        self.entry_bg.               grid(row=6,  column=14)

        self.label_status_io.        grid(row=7,   column=11) 

        self.button_navigate.        grid(row=8,  column=11)
        self.button_plot.            grid(row=8,  column=13)
        self.button_extract.         grid(row=8, column=14)
    
        self.button_prev.            grid(row=9,  column=11, columnspan=1, sticky='we')
        self.button_next.            grid(row=9,  column=13, columnspan=1, sticky='we')
        self.checkbutton_extract.    grid(row=9,  column=14)

        self.button_load.            grid(row=10,  column=11)
        self.button_save.            grid(row=10,  column=13)
        self.button_export.          grid(row=10,  column=14)
        
        self.button_quit.            grid(row=11,  column=11)
        self.button_ds9.             grid(row=11,  column=13)
        self.button_copy.            grid(row=11,  column=14)
 
# Column 3 (RHS) -- numbered as column 20
        
        self.canvas2.get_tk_widget().grid(row=1, column=20, rowspan = 2)
        self.canvas3.get_tk_widget().grid(row=3, column=20, rowspan = 2)
        self.canvas4.get_tk_widget().grid(row=5, column=20, rowspan = 9)
        
# Define some keyboard shortcuts for the GUI
# These functions must be defined as event handlers, meaning they take two arguments (self and event), not just one.

        master.bind('q', self.quit_e)
        
# Finally, now that GUI is arranged, load the first image, and its backplane.

#        self.save_gui()  # Small bug: for the first image, t[] is set, but not gui, so plot is not made properly.
                
        self.refresh_gui()
        self.load_image()
        self.process_image()
        self.plot_image()

        if (self.do_autoextract == 1):
            self.extract_profiles()
            
#==============================================================================
# Unwrap ring image in ra + dec to new image in lon + radius.
#==============================================================================

    def unwrap_ring_image(self):

        (numrad, rj_array) = sp.bodvrd('JUPITER', 'RADII', 3) # 71492 km
        rj = rj_array[0]
        r_ring_inner = 1.6 * rj   # Follow same limits as in Throop 2004 J-ring paper fig. 7
        r_ring_outer = 1.9 * rj

        num_bins_azimuth = 300    # 500 is OK. 1000 is too many -- we get bins ~0 pixels
        num_bins_radius  = 300
        
        # Read the current variables and backplane, and makes a plot / imshow.
        
        ####################
 
# Check if the backplane is loaded already. Load it iff it is not loaded
    
        if (self.file_backplane_shortname != self.t_group['Shortname'][self.index_image]):
            self.load_backplane()

        if (self.t_group['is_navigated'][self.index_image] == False):
            print("Image not navigated -- returning")
            return

# Create the satellite mask for the current image and pointing. It has already been rolled properly.

        mask_satellites = self.get_mask_satellites()
        mask_stars      = self.get_mask_stars()

# Create the masked pixels maps

        image_processed_mask = self.image_processed.copy()
        image_processed_mask[mask_satellites] = np.nan
        image_processed_mask[mask_stars]      = np.nan 
            
# Calculate the amount by which to roll image

        dx_total =  -( self.t_group['dx_opnav'][self.index_image] +  int(self.slider_offset_dx.get()) )
        dy_total =  -( self.t_group['dy_opnav'][self.index_image] +  int(self.slider_offset_dy.get()) )

# Roll the image

        self.image_roll      = np.roll(np.roll(self.image_processed, dx_total, axis=1), dy_total, axis=0)
        self.image_roll_mask = np.roll(np.roll(image_processed_mask, dx_total, axis=1), dy_total, axis=0)
                
#==============================================================================
# Examine backplane to figure out azimuthal limits of the ring image
#==============================================================================

        # Read in values from the backplane. Note that self. just keeps the backplanes of the *current* image.

        radius  = self.planes['Radius_eq']    # Radius in km
        azimuth = self.planes['Longitude_eq'] # Azimuth in radians
        phase   = self.planes['Phase']        # Phase angle, radians

        bins_radius = hbt.frange(r_ring_inner, r_ring_outer, num_bins_radius)
            
        # Select the ring points -- that is, everything inside the mask
        
        is_ring_all = ( np.array(radius > r_ring_inner) & np.array(radius < r_ring_outer))
        
        radius_all  = radius[is_ring_all]     # Make a list of all of the radius values
        azimuth_all = azimuth[is_ring_all]  # Make a list of all of the azimuth points for all pixels
        phase_all   = phase[is_ring_all]

        # Now apply the satellite mask. 
        # If it is 0, let the value through
        # If it is 1, turn to NaN
        
        DO_SAT_MASK = True
        
        if (DO_SAT_MASK):
            dn_all = self.image_roll_mask[is_ring_all]
        else:
            dn_all = self.image_roll[is_ring_all]          # DN values, from the rolled image
        
        phase_mean  = np.mean(phase_all)     # Get the mean phase angle across the ring.
        
        # Now take these raw data, and rearrange them so that we can take the longest continuous segment
        # We do this by appending the timeseries to itself, looking for the largest gap (of no az data), 
        # and then the data will start immediately after that.
        
        # _2 indicates a double-length array (ie, with [azimuth, azimuth + 2pi])
        # _s indicates sorted
        # _d indicates delta
        
        azimuth_all_3 = np.concatenate((azimuth_all, azimuth_all + 2*math.pi, azimuth_all + 4*math.pi))
        dn_all_3      = np.concatenate((dn_all, dn_all, dn_all))
        radius_all_3  = np.concatenate((radius_all, radius_all, radius_all))
        
        azimuth_all_3_s = np.sort(azimuth_all_3, kind = 'heapsort')
        azimuth_all_3_s_d = azimuth_all_3_s - np.roll(azimuth_all_3_s, 1)
        
        # Look for the indices where the largest gaps (in azimuth) start
        
        index_seg_start_3_s = (np.where(azimuth_all_3_s_d > 0.999* np.max(azimuth_all_3_s_d)))[0][0]
        index_seg_end_3_s = (np.where(azimuth_all_3_s_d > 0.999* np.max(azimuth_all_3_s_d)))[0][1]-1
        
        # Get proper azimithal limits. We want them to be a single clump of monotonic points.
        # Initial point is in [0, 2pi) and values increase from there.
                                                           
        azimuth_seg_start = azimuth_all_3_s[index_seg_start_3_s] # Azimuth value at the segment start
        azimuth_seg_end   = azimuth_all_3_s[index_seg_end_3_s]   # Azimuth value at the segment end
        
        indices_3_good = (azimuth_all_3 >= azimuth_seg_start) & (azimuth_all_3 < azimuth_seg_end)
        
        azimuth_all_good = azimuth_all_3[indices_3_good]
        radius_all_good  = radius_all_3[indices_3_good]
        dn_all_good      = dn_all_3[indices_3_good]
        
        # Extract arrays with the proper pixel values, and proper azimuthal values
        
        azimuth_all = azimuth_all_good
        radius_all  = radius_all_good
        dn_all      = dn_all_good
        
#==============================================================================
#  Now regrid the data from xy position, to an unrolled map in (azimuth, radius)
#==============================================================================

# Method #1: Construct the gridded image line-by-line

        dn_grid         = np.zeros((num_bins_radius, num_bins_azimuth))  # Row, column
        bins_azimuth    = hbt.frange(azimuth_seg_start, azimuth_seg_end, num_bins_azimuth)
        bins_radius     = hbt.frange(r_ring_inner, r_ring_outer, num_bins_radius)        
        
        for i in range(num_bins_radius-1):  # Loop over radius -- inner to outer
            
            # Select only bins with right radius and azimuth
            is_ring_i = np.array(radius_all > bins_radius[i]) & np.array(radius_all < bins_radius[i+1]) & \
                        np.array(azimuth_all > azimuth_seg_start) & np.array(azimuth_all < azimuth_seg_end) 
            
            if np.sum(is_ring_i) > 0:
                dn_i         = dn_all[is_ring_i]  # Get the DN values from the image (adjusted by nav pos error)
                radius_i     = radius_all[is_ring_i]
                azimuth_i    = azimuth_all[is_ring_i]
                grid_lin_i   = griddata(azimuth_i, dn_i, bins_azimuth, method='linear')
                
                dn_grid[i,:] = grid_lin_i

# Save the variables, and return

# We do *not* plot the unwrapped image for now
        
        self.image_unwrapped = dn_grid
        self.radius_unwrapped = bins_radius
        self.azimuth_unwrapped = bins_azimuth

        return
        
########################3

## Method #2: Construct the gridded image all at once 
#
#        az_arr  = np.linspace(azimuth_seg_start, azimuth_seg_end,     num_bins_azimuth)
#        rad_arr = np.linspace(np.min(radius_all), np.max(radius_all), num_bins_radius)
#
## In order for griddata to work, d_radius and d_azimuth values should be basically equal.
## In Jupiter data, they are not at all. Easy soln: tweak azimuth values by multiplying
## by a constant to make them large.
##
#        f = (np.max(radius_all) - np.min(radius_all)) / (np.max(azimuth_all) - np.min(azimuth_all))
#        aspect = 1/f
#
## NB: griddata() returns an array in opposite row,column order than I would naively think.
## I want results in order (radius, azimuth) = (y, x)
#
#        dn_grid2 = griddata((f*azimuth_all, radius_all), dn_all, 
#                           (f*az_arr[None,:], rad_arr[:,None]), method='linear')
#        
#        plt.imshow(dn_grid2)
#        plt.title('dn_grid, method 2')
#        plt.show()
#        

#==============================================================================
# Extract ring profiles from the data image
#==============================================================================
        
    def extract_profiles(self):

        # Compute additional quantities we need

        (vec, lt)        = sp.spkezr('New Horizons', 
                            self.t_group['ET'][self.index_image], 'IAU_JUPITER', 'LT', 'Jupiter')
        (junk, lon, lat) = sp.reclat(vec[0:3])
        ang_elev         = np.abs(lat)          # Elevation angle (aka 'B')  
        ang_emis         = math.pi/2 - ang_elev     # Emission angle (ie, angle down from normal) 
        mu               = abs(math.cos(ang_emis))  # mu. See definitions of all these Throop 2004 @ 63 

        width_ring  = 6500 # in km. This is a constant to normalize by -- not the same as actual boundaries.
        
        ew_edge     = [120000, 130000]  # Integrate over this range. This is wider than the official ring width.

        self.unwrap_ring_image()  # creates self.image_unwrapped, etc.
        self.ang_elev   = ang_elev
        
        # Load the unwrapped image. ** I should rename the local vars to be same as the self.vars! Only historical.
        
        dn_grid       = self.image_unwrapped # This is only set if this image was navigated, and could be extracted.
        bins_radius   = self.radius_unwrapped
        bins_azimuth  = self.azimuth_unwrapped
        
        # Remove cosmic rays, stars, or anything else that might be left in the unwrapped image.
        # We have already done this, but maybe the unwrapping creates sharp edges -- so do it again.
        
        dn_grid       = hbt.decosmic(dn_grid)
        
#==============================================================================
# Extract radial and azimuthal profiles. Method #1: From the full remapped images.
#==============================================================================

        profile_azimuth_full = np.nanmean(dn_grid, 0)
        profile_radius_full  = np.nanmean(dn_grid, 1)       
        
        plt.rcParams['figure.figsize'] = 16,10

# Method 2: from a limited region of the remapped images

        # Set limits for where the extraction should happen
        
        # For the radial profile, we take only a portion of the unwrapped frame. 
        # e.g., the inner 30%. We exclude the region on the edges, since it is smeared, and has contamination.
        # We are not starved for photons. Take the best portion of the signal and use it.
        
        frac_profile_radial = 0.3  # Of the available azimuth range, what fraction 
                                   # do we use for extracting radial profile?
                                   # Azimuthal limits, used for radial profile
                                   
        # For azimuthal profile, focus on the main ring. Don't focus on the diffuse inner region.
        # It is harder to do that photometry, more artifacts, fainter, and probalby more spread out anyhow.
        
        # Define distances of [outer box, outer ring, inner ring, inner box] in km
        # These four radii define the position of the inner and outer regions to subtract as bg, 
        # and the inner region to use for the signal.
        
        limits_profile_azimuth = np.array([131e3,130e3,127e3,126e3]) # Radial limits, used for az profile
        
        limits_profile_azimuth_bins = limits_profile_azimuth.astype(int).copy() * 0

        # XXX I think ths should be rewritten with hbt.x2bin()
        
        for i,r in enumerate(limits_profile_azimuth):
            limits_profile_azimuth_bins[i] = int(hbt.wheremin(abs(bins_radius - r)))
        
        limits_profile_radial_bins = int(np.shape(dn_grid)[1]) * \
            np.array([0.5-frac_profile_radial/2, 0.5+frac_profile_radial/2])

        limits_profile_radial_bins = limits_profile_radial_bins.astype(int)     
              
#        lprb = hbt.x2bin(np.array((0.5-frac_profile_radial/2, 0.5+frac_profile_radial/2)), bins_radius)
#        lpab = hbt.x2bin(limits_profile_azimuth, bins_azimuth)
#        
#        print "limits_profile_radial_bins:"
#        print limits_profile_radial_bins
#        print lprb
#        
#        print "limits_profile_azimuth_bins:"
#        print limits_profile_azimuth_bins
#        print lpab
        
        #==============================================================================
        # Extract radial and azimuthal profiles, using subsections
        #==============================================================================
        
        # I am using the *mean* here along each row and column. That means that the final value
        # in the profiles is 
        # Azimuthal
        
        #profile_azimuth_bg_inner = np.nansum(dn_grid[limits_profile_azimuth_bins[1]:limits_profile_azimuth_bins[0],:],0)
        
        plt.rcParams['figure.figsize'] = 10,5
        
        profile_azimuth_bg_inner = np.nanmean(dn_grid[limits_profile_azimuth_bins[1]:limits_profile_azimuth_bins[0],:],
                                              axis=0)
        profile_azimuth_core     = np.nanmean(dn_grid[limits_profile_azimuth_bins[2]:limits_profile_azimuth_bins[1],:],
                                              axis=0)
        profile_azimuth_bg_outer = np.nanmean(dn_grid[limits_profile_azimuth_bins[3]:limits_profile_azimuth_bins[2],:],
                                              axis=0)

        # Get profile in DN
        profile_azimuth_central  = profile_azimuth_core - (profile_azimuth_bg_inner + profile_azimuth_bg_outer)/2
        profile_radius_central   = np.nanmean(dn_grid[:,limits_profile_radial_bins[0]:limits_profile_radial_bins[1]],1)
        
#==============================================================================
# Converted extracted values from DN, into photometric quantities
#==============================================================================

#        rsolar_i = t_group['RSolar'][self.index_image]

        rsolar = 266400.  #   RSOLAR  =  266400.000000 / Conv to radiance for solar source. From LORRI FITS file.

        pixfov = 0.3 * hbt.d2r * 1e6 / 1024  # This keyword is missing. "Plate scale in microrad/pix "

# Convert into I/F
         
        profile_radius_full_iof = self.dn2iof(profile_radius_full, self.t_group['Exptime'][self.index_image],\
                                     pixfov, rsolar )

        profile_radius_full_iof_norm = profile_radius_full_iof * mu

        ew_edge_bin = hbt.x2bin(ew_edge,bins_radius)
            
        dr = np.roll(bins_radius,-1) - bins_radius # Bin width, in km
        dr[-1] = 0
        
#        ioprofile_radius_iof_norm  # Just a shorter alias
        ew_norm  = np.sum((profile_radius_full_iof_norm * dr)[ew_edge_bin[0] : ew_edge_bin[1]]) # Normalized EW from top
        ew_mean  = ew_norm / width_ring                                           # Mean normalized EW
        
        taupp    = profile_radius_full_iof_norm * 4 * mu  # Radially averaged tau_omega0_P

## Plot it. First just to screen. 
#        plt.plot([3,4,7])
#        plt.xlabel('Radius [1000 km]', fontsize=20)
#        plt.ylabel(r'$\tau \, \varpi_0 \, P$', fontsize=20)
#        plt.show()
         
#==============================================================================
#  Plot the remapped 2D images
#==============================================================================

        extent = [bins_azimuth[0], bins_azimuth[-1], bins_radius[0], bins_radius[-1]]

        f = (np.max(bins_radius) - np.min(bins_radius)) / (np.max(bins_azimuth) - np.min(bins_azimuth))
        aspect = 0.5/f * 2 # Set the aspect ratio

#        stretch = astropy. ization.PercentileInterval(self.stretch_percent)  # PI(90) scales array to 5th .. 95th %ile. 

        # For now, we are scaling this vertically by hand. Might have to revisit that.

        self.ax3.clear()        
        self.ax3.imshow(dn_grid, extent=extent, aspect=aspect, vmin=-15, vmax=20, origin='lower') # aspect='auto'a


#        self.ax3.hlines(limits_profile_azimuth[0], -10, 10, color='purple')
#        self.ax3.hlines(limits_profile_azimuth[1], -10, 10, color='purple')
#        self.ax3.hlines(limits_profile_azimuth[2], -10, 10, color='purple')
#        self.ax3.hlines(limits_profile_azimuth[3], -10, 10, color='purple')
#        self.ax3.set_xlim(hbt.mm(bins_azimuth))
        
#        self.ax3.vlines(bins_azimuth[limits_profile_radial_bins[0]],-1e10, 1e10)
#        self.ax3.vlines(bins_azimuth[limits_profile_radial_bins[1]],-1e10, 1e10)

        self.ax3.set_ylim([124000, 134000])
        self.ax3.set_xlim([bins_azimuth[0], bins_azimuth[-1]])
        
        self.ax3.set_xlabel('Azimuth [radians]')
        self.ax3.set_ylabel('Radius [$R_J$]')
        
        self.canvas3.show()
            
#==============================================================================
# Plot the radial and azimuthal profiles
#==============================================================================

# Plot azimuthal profile

        self.ax2.clear()  # Clear lines from the current plot. 

        dy = 2            # Vertical offset between curves
                          # Set the y limit to go from minimum, to a bit more than 90th %ile
                          # The idea here is to clip off flux from a moon, if it is there.
                          
                
        self.ax2.plot(bins_azimuth, profile_azimuth_full, label = 'Full')
        self.ax2.plot(bins_azimuth, profile_azimuth_central, label = 'Central - bg')
        
#        self.ax2.plot(bins_azimuth, profile_azimuth_2 + dy, label='Raw')
        self.ax2.set_title('Azimuthal Profile')
        self.ax2.set_xlabel('Azimuth [radians]')
        self.ax2.set_xlim([bins_azimuth[0], bins_azimuth[-1]])
        self.ax2.legend(loc = 'upper left')

        self.ax2.plot(bins_radius, profile_radius_full)
        self.ax2.plot(bins_radius, profile_radius_central)
        
        self.canvas2.show()
        
        dy = 1

#        ylim = [np.amin(0.9 * profile_radius), dy + 1.5 * np.percentile(profile_radius, 90)]

        self.ax4.clear()  # Clear lines from the current plot.
        
        plt.rcParams['figure.figsize'] = 16,10

        DO_PLOT_IOF = False # Do we plot I/F, or DN

# Plot radial profile
        
        if (DO_PLOT_IOF == False):

#            self.ax4.plot(bins_radius/1000, profile_radius_full, label = 'Full')
            self.ax4.plot(bins_radius/1000, profile_radius_central, label = 'Central')
            
            self.ax4.set_xlabel(r'Radial Profile      Radius [1000 km]    phase = {:.1f} deg'
                                .format(hbt.r2d * np.mean(self.planes['Phase'])))
#            self.ax4.set_xlim(list(hbt.mm(bins_radius/1000)))
            self.ax4.set_xlim([120,130])
            self.ax4.legend(loc='upper left')
            
            # Plot a second axis, in RJ    
            
            ax41 = self.ax4.twiny()
            ax41.set_xlim(list(hbt.mm(bins_radius/1000/71.4)))

        if (DO_PLOT_IOF == True):     
            
            self.ax4.plot(bins_radius / 1000, taupp, label = 'Method 1')
            self.ax4.set_xlabel('Radius [1000 km]')
            self.ax4.set_ylabel(r'$\tau \varpi_0 P(\alpha)$')
             

#            self.ax4.plot(bins_radius/1000, profile_radius_1, label = 'Regrid')
#            self.ax4.plot(bins_radius/1000, profile_radius_2 + dy, label='Raw')
            self.ax4.set_xlabel('Radial Profile      Radius [1000 km]')
#            self.ax4.set_ylim(ylim)
            self.ax4.set_xlim(list(hbt.mm(bins_radius/1000)))
            self.ax4.legend(loc='upper left')
    
            self.ax4.plot(self.bins_radius, self.profile_radius)
            ax41 = self.ax4.twiny()
            ax41.set_xlim(list(hbt.mm(bins_radius/1000/71.4)))
            
        self.canvas4.show()
        
        # Save the profiles where we can access them later
        
        self.profile_radius_full   = profile_radius_full
        self.profile_radius_central = profile_radius_central
        
        self.profile_azimuth_full   = profile_azimuth_full
        self.profile_azimuth_central = profile_azimuth_central
        
                       
##########
# Navigate the image and plot it
##########

    """
    Handle the 'navigate image' button. Plots image when done.
    Extracts profile if that is default.
    """
				
    def handle_navigate(self):
        self.navigate()
        self.refresh_statusbar()  # Put the new nav info into the statusbar
        self.plot_image()								
							
#########
# Navigate the image
#########

    def navigate(self):        

        t = self.t_group # We use this a lot, so make it shorter
        d2r = hbt.d2r
        r2d = hbt.r2d
        
        index_image = self.index_image       
        
# Now look up positions of stars in this field, from a star catalog

        w = WCS(t['Filename'][index_image])                  # Look up the WCS coordinates for this frame
        et = t['ET'][index_image]

        print('ET[i] =  ' + repr(et))
        print('UTC[i] = ' + repr(t['UTC'][index_image]))
        print('crval[i] = ' + repr(w.wcs.crval))              # crval is a two-element array of [RA, Dec], in degrees
        
        center  = w.wcs.crval  # degrees
        DO_GSC1     = False    # Stopped working 2-Oct-2016
        DO_GSC2     = True
        DO_USNOA2   = False
        
        if (DO_GSC1):
            name_cat = u'The HST Guide Star Catalog, Version 1.1 (Lasker+ 1992) 1' # works, but 1' errors; investigating
            radius_search = 0.15
            stars = conesearch.conesearch(w.wcs.crval, radius_search, cache=False, catalog_db = name_cat)
            ra_stars  = np.array(stars.array['RAJ2000'])*d2r # Convert to radians
            dec_stars = np.array(stars.array['DEJ2000'])*d2r # Convert to radians
#            table_stars = Table(stars.array.data)

        if (DO_GSC2):
            name_cat = u'Guide Star Catalog v2 1'
#            name_cat = u'The HST Guide Star Catalog, Version 1.1 (Lasker+ 1992) 1' # works, but 1' errors; investigating

#            stars = conesearch.conesearch(w.wcs.crval, 0.3, cache=False, catalog_db = name_cat)
            from astropy.utils import data
            
            with data.conf.set_temp('remote_timeout', 30): # This is the very strange syntax to set a timeout delay.
                                                           # The default is 3 seconds, and that times out often.
                stars = conesearch.conesearch(w.wcs.crval, 0.3, cache=False, catalog_db = name_cat)

            ra_stars  = np.array(stars.array['ra'])*d2r # Convert to radians
            dec_stars = np.array(stars.array['dec'])*d2r # Convert to radians

            mag       = np.array(stars.array['Mag'])
            
            print("Stars downloaded: {}; mag = {} .. {}".format(np.size(mag), np.nanmin(mag), np.nanmax(mag)))
            print("RA = {} .. {}".format(np.nanmin(ra_stars)*r2d, np.nanmax(ra_stars)*r2d))
            
            # Now sort by magnitude, and keep the 100 brightest
            # This is because this GSC catalog is huge -- typically 2000 stars in LORRI FOV.
            # We need to reduce its size to fit in our fixed astropy table string length.

            num_stars_max = 100            
            order = np.argsort(mag)
            order = np.array(order)[0:num_stars_max]

            ra_stars = ra_stars[order]
            dec_stars = dec_stars[order]
  
#            table_stars = Table(stars.array.data)

        if (DO_USNOA2):        
            name_cat = u'The USNO-A2.0 Catalogue (Monet+ 1998) 1' # Works but gives stars down to v=17; I want to v=13 
            stars = conesearch.conesearch(w.wcs.crval, 0.3, cache=False, catalog_db = name_cat)
            table_stars = Table(stars.array.data)
            mask = table_stars['Bmag'] < 13
            table_stars_m = table_stars[mask]            

            ra_stars  = table_stars_m['RAJ2000']*d2r # Convert to radians
            dec_stars = table_stars_m['DEJ2000']*d2r # Convert to radians
        
# Get an array of points along the ring

        ra_ring1, dec_ring1 = hbt.get_pos_ring(et, name_body='Jupiter', radius=122000, units='radec', wcs=w)
        ra_ring2, dec_ring2 = hbt.get_pos_ring(et, name_body='Jupiter', radius=129000, units='radec', wcs=w)

                    # Return as radians              
        x_ring1, y_ring1    = w.wcs_world2pix(ra_ring1*r2d, dec_ring1*r2d, 0) # Convert to pixels
        x_ring2, y_ring2    = w.wcs_world2pix(ra_ring2*r2d, dec_ring2*r2d, 0) # Convert to pixels

# Get position of Jupiter, in pixels

#        ra_io, dec_io = get_pos_body(et, name_body='Io', units = 'radec', wcs=w)
        
# Look up velocity of NH, for stellar aberration
        
        abcorr = 'LT+S'
        frame = 'J2000'
        st,ltime = sp.spkezr('New Horizons', et, frame, abcorr, 'Sun') # Get velocity of NH 
        vel_sun_nh_j2k = st[3:6]
        
# Correct stellar RA/Dec for stellar aberration

        radec_stars        = np.transpose(np.array((ra_stars,dec_stars)))
        radec_stars_abcorr = hbt.correct_stellab(radec_stars, vel_sun_nh_j2k) # Store as radians

# Convert ring RA/Dec for stellar aberration

        radec_ring1        = np.transpose(np.array((ra_ring1,dec_ring1)))
        radec_ring1_abcorr = hbt.correct_stellab(radec_ring1, vel_sun_nh_j2k) # radians
        radec_ring2        = np.transpose(np.array((ra_ring2,dec_ring2)))
        radec_ring2_abcorr = hbt.correct_stellab(radec_ring2, vel_sun_nh_j2k) # radians
        
# Convert RA/Dec values back into pixels
        
        x_stars,        y_stars          = w.wcs_world2pix(radec_stars[:,0]*r2d,   radec_stars[:,1]*r2d, 0)        
        x_stars_abcorr, y_stars_abcorr   = w.wcs_world2pix(radec_stars_abcorr[:,0]*r2d, radec_stars_abcorr[:,1]*r2d, 0)
        x_ring1_abcorr, y_ring1_abcorr   = w.wcs_world2pix(radec_ring1_abcorr[:,0]*r2d, radec_ring1_abcorr[:,1]*r2d, 0)
        x_ring2_abcorr, y_ring2_abcorr   = w.wcs_world2pix(radec_ring2_abcorr[:,0]*r2d, radec_ring2_abcorr[:,1]*r2d, 0)

        points_stars        = np.transpose((x_stars, y_stars))
        points_stars_abcorr = np.transpose((x_stars_abcorr, y_stars_abcorr))

# Read the image file from disk

        image_polyfit = hbt.read_lorri(t['Filename'][index_image], frac_clip = 1.,  
                                     bg_method = 'Polynomial', bg_argument = 4)
        image_raw     = hbt.read_lorri(t['Filename'][index_image], frac_clip = 0.9, 
                                     bg_method = 'None')

# Use DAOphot to search the image for stars. It works really well.

        points_phot = hbt.find_stars(image_polyfit)
        
# Now look up the shift between the photometry and the star catalog. 
# Do this by making a pair of fake images, and then looking up image registration on them.
# I call this 'opnav'. It is returned in order (y,x) because that is what imreg_dft uses, even though it is a bit weird.
#
# For this, I can use either abcorr stars or normal stars -- whatever I am going to compute the offset from.        

        (dy_opnav, dx_opnav) = hbt.calc_offset_points(points_phot, points_stars, np.shape(image_raw), plot=False)

# Save the newly computed values to variables that we can access externally
# For the star locations, we can't put an array into an element of an astropy table.
# But we *can* put a string into astropy table! Do that: wrap with repr(), unwrap with eval('np.' + ).
       
        self.t_group['dx_opnav'][self.index_image] = dx_opnav
        self.t_group['dy_opnav'][self.index_image] = dy_opnav
        
        self.t_group['x_pos_star_cat'][self.index_image] = hbt.reprfix(x_stars_abcorr)
        self.t_group['y_pos_star_cat'][self.index_image] = hbt.reprfix(y_stars_abcorr)
        
#        self.t_group['x_pos_star_cat'][self.index_image] = repr(x_stars) # For test purposes, ignore the abcorr
#        self.t_group['y_pos_star_cat'][self.index_image] = repr(y_stars)
                
        self.t_group['x_pos_star_image'][self.index_image] = hbt.reprfix(points_phot[:,0]).replace(' ', '') # Shorten it
        self.t_group['y_pos_star_image'][self.index_image] = hbt.reprfix(points_phot[:,1]).replace(' ', '')
        self.t_group['is_navigated'][self.index_image] = True             # Set the flag saying we have navigated image

        self.t_group['x_pos_ring1'][self.index_image] = hbt.reprfix(x_ring1_abcorr)
        self.t_group['y_pos_ring1'][self.index_image] = hbt.reprfix(y_ring1_abcorr)
        self.t_group['x_pos_ring2'][self.index_image] = hbt.reprfix(x_ring2_abcorr)
        self.t_group['y_pos_ring2'][self.index_image] = hbt.reprfix(y_ring2_abcorr)
        
#        self.t_group['x_pos_bodies'][self.index_image] = repr(x_pos_bodies)
#        self.t_group['y_pos_bodies'][self.index_image] = repr(y_pos_bodies)
#        self.t_group['ra_bodies'][self.index_image]  = repr(ra_bodies)
#        self.t_group['dec_bodies'][self.index_image] = repr(dec_bodies)
#        self.t_group['name_bodies'][self.index_image] = repr(name_bodies)

#        print("Opnav computed: {dx,dy}_opnav = " + repr(dx_opnav) + ', ' + repr(dy_opnav))
#
#        print('ra_stars      : ' + repr(ra_stars*r2d) + ' deg')
               
        # Now that we have navigated it, replot the image!
               
        return 0


##########
# Save GUI settings. 
##########
    """
    Take all settings from the GUI, and put them into the proper table variables
    This does *not* save to disk. It saves the Tk widget settings into variables, 
    which can then be saved later.
    """
 
    def save_gui(self):

#        print("save_gui()")
        
# Save the current values
         
        comment = self.entry_comment.get()
        self.t_group['Comment'][self.index_image] = comment

        # Get the slider positions
        
        self.t_group['dx_offset'][self.index_image] = self.slider_offset_dx.get()
        self.t_group['dy_offset'][self.index_image] = self.slider_offset_dy.get()

        # Get the background subtraction settings

        self.t_group['bg_method'][self.index_image] = self.var_option_bg.get()
        self.t_group['bg_argument'][self.index_image] = self.entry_bg.get()
        
# Copy the entire current 'group' back to the main table

        self.t[self.groupmask] = self.t_group
        
##########
# Change Image, and go to a new one
##########
#
# index_image     : old image has the current image (within the current group)
# index_image_new : new image
                                # has the new image we want to show (within the current group)
# This does not change the group -- just the image      

    def change_image(self, refresh=True):
   
#        print("change_image")

        # Save current GUI settings into variables
        
        self.save_gui()
        
# Update the index, to show that new image is active
        
        self.index_image = self.index_image_new
        self.index_group = self.index_group_new

#  Update the frequently used 't_group' list to reflect new group

        name_group = self.groups[self.index_group]
        self.groupmask = self.t['Desc'] == name_group        
        self.t_group = self.t[self.groupmask]
        self.num_images_group = np.size(self.t_group)							
								
# Redraw the GUI for the new settings

        self.refresh_gui()

# Load, process, and display the image
								
        self.load_image()
					
        self.process_image()
								
        self.plot_image()
                
# Extract radial / azimuthal profiles, if desired

        if (self.do_autoextract == 1):
            self.extract_profiles()        



#==============================================================================
# Load new image from disk
#==============================================================================

    """
    Load current image from disk
    """
    
    def load_image(self):

#        print("load_image()")

# autozoom: if set, and we are loading a 4x4 image, then scale it up to a full 1x1.

        file = self.t_group[self.index_image]['Filename']                    
        self.image_raw = hbt.read_lorri(file, frac_clip = 1., bg_method = 'None', autozoom=True)
        print("Loaded image: " + file)

# Load the backplane as well. We need it to flag satellite locations during the extraction.
        
        DO_LOAD_BACKPLANE = True
        if DO_LOAD_BACKPLANE:
            self.load_backplane()

#        print("Loaded backplane.")
                                                

#==============================================================================
# Change Group
#==============================================================================

    def select_group(self, event):

        print("select_group")

        index = (self.lbox_groups.curselection())[0]
        name_group = self.groups[index]

# Create the listbox for files, and load it up
# NB: We are using a local copy of t_group here -- not self.t_group, 
# which still reflects the old group, not new one.

        groupmask = self.t['Desc'] == name_group        
        t_group = self.t[groupmask]
        num_images_group = np.size(t_group)
        print("Group #{} = {} of size {} hit!".format(index, name_group, self.num_images_group))

# Now look up the new group name. Extract those elements.        
								
#        name = self.t_group['Shortname'][index]
#        print("selected = " + repr(index) + ' ' + name)


        files_short = t_group['Shortname']

        self.lbox_files.delete(0, "end")
 
        for i in range(np.size(files_short)):
            
             s = '{0:3}.   {1}   {2:.3f}   {3}  {4}'.format( \
                 repr(i), 
                 files_short[i], 
                 t_group['Exptime'][i], 
                 t_group['Format'][i],                 
                 t_group['UTC'][i])

             self.lbox_files.insert("end", s)
                 
# Then set the group number, and refresh screen.

        self.index_image_new = 0      # Set image number to zero
        self.index_group_new = index  # Set the new group number
#        print(" ** Calling change")
        self.change_image()

##########
# Select new image, based on user click
##########
# This is called when user clicks on a new image number in list.

    def select_image(self, event):

        print("select_image")
        
        index = (self.lbox_files.curselection())[0]
        name = self.t_group['Shortname'][index]
        print("selected = " + repr(index) + ' ' + name)
        self.index_image_new = index
        self.index_group_new = self.index_group  # Keep the same group
        self.change_image()

##########
# Refresh the status bar
##########

    def refresh_statusbar(self):

# Set the Label widget value with a useful string
# Note that this is sometimes just not printed at all.  This is usually caused by a non-closed Tk window.
# To fix, quit IPython console from within spyder. Then restart.
								
        num_in_group = np.size(self.t_group)
        num_groups = np.size(self.groups)
                
        s = 'Group ' + repr(self.index_group) + '/' + repr(num_groups) + \
            ', Image ' + repr(self.index_image) + '/' + repr(num_in_group) + ': ' + \
          self.t_group['Shortname'][self.index_image] + '\n'
        
        if (self.t_group['is_navigated'][self.index_image]):
            s += ('Nav, ' + \
            'd{xy}_opnav = (' + repr(self.t_group['dx_opnav'][self.index_image]) + ', ' + \
                                repr(self.t_group['dy_opnav'][self.index_image]) + '), ' + \
            'd{xy}_user =  (' + repr(int(self.slider_offset_dx.get())) + ', ' \
                              + repr(int(self.slider_offset_dy.get())) + ')')
            
        self.var_label_info.set(s)

        return 0
        
##########
# Update UI for new settings.
##########
        """
A general-purpose routine that is sometimes called after (e.g.) switching images.
the image number. This updates all of the GUI elements to reflect the new image, based on 
the internal state which is already correct. This does *not* refresh the image itself.
        """

    def refresh_gui(self):
         
# Load and display the proper header

        filename = self.t_group['Filename'][self.index_image]
        
        header = hbt.get_image_header(filename, single=True)
        self.text_header.delete(1.0, "end")
        h2 = re.sub('\s+\n', '\n', header)  # Remove extra whitespace -- wraps around and looks bad
        self.text_header.insert(1.0, h2)

# Make sure the proper comment is displayed. (It won't be if we have just changed images.)

        self.entry_comment.delete(0, 'end') # Clear existing comment
        self.entry_comment.insert(0, self.t_group['Comment'][self.index_image])
        
# Set the proper Listbox 'Group' settings. Make sure the current item is visible, and selected.
# It's pretty easy for the Listbox to get confused, and highlight two-at-once, or underline one and highlight
# another, etc. This just cleans it up. Maybe there are settings to change here too.
    
        self.lbox_groups.see(self.index_group)
        self.lbox_groups.selection_clear(0, 'end')
        self.lbox_groups.selection_set(self.index_group) # This seems to not work always
        self.lbox_groups.activate(self.index_group)

# Set the proper Listbox 'image' settings.

        self.lbox_files.see(self.index_image)
        self.lbox_files.selection_clear(0, 'end')
        self.lbox_files.selection_set(self.index_image)
        self.lbox_files.activate(self.index_image)

# Set the slider positions

        self.slider_offset_dx.set(self.t_group['dx_offset'][self.index_image])
        self.slider_offset_dy.set(self.t_group['dy_offset'][self.index_image])

#        self.slider_offset_dy.set(self.t_group['dy_offset'][self.index_image_new]) # Set dy

# Set the background subtraction settings

        self.var_option_bg.set(self.t_group['bg_method'][self.index_image])
        self.entry_bg.delete(0, 'end') # Clear existing value
        self.entry_bg.insert(0, self.t_group['bg_argument'][self.index_image]) # Set the value (e.g., order = "4")
        
# Set the statusbar

        self.refresh_statusbar()
        
        return 0

#==============================================================================
# Extract profiles - button handler
#==============================================================================

    def handle_extract_profiles(self):
        """
        Extract and plot radial / azimuthal profiles. Because plotting params
        have likely changed, we replot as well.
        Identical to handle_plot_image, but forces the extraction.								
        """
        
        self.save_gui()
        self.process_image()
        self.plot_image()

        self.extract_profiles()	

#==============================================================================
# Apply image processing to image. Stray light, polynomial subtraction, etc.
#==============================================================================

    def process_image(self):
        
#        print("process_image()")
        
        method = self.var_option_bg.get()
        argument = self.entry_bg.get()
        
        self.image_processed = hbt.nh_jring_process_image(self.image_raw, \
                                                          method, argument, self.index_group, self.index_image)

        # Remove cosmic rays
        
        self.image_processed = hbt.decosmic(self.image_processed)
        
#==============================================================================
# Plot image - button handler
#==============================================================================

    def handle_plot_image(self):
        """
        Plot the image. Reprocess to reflect any changes from GUI.
        Plots objects and extracts profiles, as available.								
        """
        
        self.save_gui()
        self.process_image()
        self.plot_image()

        if (self.do_autoextract):
            self.extract_profiles()								

#==============================================================================
# Plot image
#==============================================================================

    def plot_image(self):
        """
        Plot the image. It has already been loaded and processed.
        This is an internal routine, which does not process.	
        This plots the image itself, *and* the objects, if navigated.							
        """
                
        # Clear the image

        self.ax1.clear()
        
        # Set the color map
        
        plt.rc('image', cmap='Greys_r')
        
# Plot the image itself.
        
        # Render the main LORRI frame
        # *** In order to get things to plot in main plot window, 
        # use self.ax1.<command>, not plt.<command>
        # ax1 is an instance of Axes, and I can call it with most other methods (legend(), imshow(), plot(), etc)

        stretch = astropy.visualization.PercentileInterval(self.stretch_percent)  # PI(90) scales to 5th..95th %ile. 

# Get the satellite position mask, and roll it into position
                       
        self.ax1.imshow(stretch(self.image_processed))
        
        # Disable the tickmarks from plotting

        self.ax1.get_xaxis().set_visible(False)
        self.ax1.get_yaxis().set_visible(False)

        # Set image size (so off-edge stars are clipped, rather than plot resizing)

        self.ax1.set_xlim([0,1023])  # This is an array and not a tuple. Beats me, like so many things with mpl.
        self.ax1.set_ylim([1023,0])
  
#        self.ax1.Axes(fig, [0,0,1,1])
        
        # Draw the figure on the Tk canvas
        
        self.fig1.tight_layout() # Remove all the extra whitespace -- nice!
        self.canvas1.draw()
                
        if (self.t_group['is_navigated'][self.index_image]):
            self.plot_objects()									

        
        plt.imshow(stretch(self.image_processed))
        plt.show()
        
        return 0

##########
# Plot Objects
##########

    def plot_objects(self):
        """
           Plot rings and stars, etc, if we have them.
      """
        
        # If we have them, draw the stars on top

        t = self.t_group[self.index_image]  # Grab this, read-only, since we use it a lot.
                                            # We can reference table['col'][n] or table[n]['col'] - either OK
        w = WCS(t['Filename'])                  # Look up the WCS coordinates for this frame
         
        filename = self.t_group['Filename'][self.index_image]
        filename = str(filename)
        
#        print("is_navigated: " + repr(self.t_group['is_navigated'][self.index_image])  )                      
								
        if (self.t_group['is_navigated'][self.index_image]):

            # Remove all of the current 'lines' (aka points) from the plot. This leaves the axis and the image
            # preserved, but just removes the lines. Awesome. Using ax1.cla() will clear entire 'axis', including image.
            # Q: Does this remove legend? Not sure.
		
            lines = self.ax1.get_lines()
            for line in lines:
                line.remove()		# Not vectorized -- have to do it one-by-one											

# Get ring position
												
            x_pos_ring1 = eval('np.' + t['x_pos_ring1']) # Convert from string (which can go in table) to array
            y_pos_ring1 = eval('np.' + t['y_pos_ring1'])
            x_pos_ring2 = eval('np.' + t['x_pos_ring2'])
            y_pos_ring2 = eval('np.' + t['y_pos_ring2'])           

# Get the user offset position
            
            dx = t['dx_opnav'] + self.slider_offset_dx.get()
            dy = t['dy_opnav'] + self.slider_offset_dy.get()

# Plot the stars -- catalog, and DAO

            self.ax1.plot(eval('np.' + t['x_pos_star_cat']) + t['dx_opnav'], 
                     eval('np.' + t['y_pos_star_cat']) + t['dy_opnav'], 
                     marker='o', ls='None', 
                     color='lightgreen', ms=12, mew=1, label = 'Cat Stars, OpNav')
                     
            self.ax1.plot(eval('np.' + t['x_pos_star_cat']), 
                     eval('np.' + t['y_pos_star_cat']), 
                     marker='o', ls='None', 
                     color='lightgreen', label = 'Cat Stars, WCS')

            self.ax1.plot(eval('np.' + t['x_pos_star_image']), 
                     eval('np.' + t['y_pos_star_image']), 
                     marker='o', ls='None', 
                     color='pink', label = 'DAOfind Stars')               

            # Get position of satellites

            name_bodies = np.array(['Metis', 'Adrastea', 'Thebe', 'Amalthea', 'Io'])        
            x_bodies,  y_bodies   = hbt.get_pos_bodies(t['ET'], name_bodies, units='pixels', wcs=w)
            ra_bodies, dec_bodies = hbt.get_pos_bodies(t['ET'], name_bodies, units='radec', wcs=w)

            # Plot satellites
              
            self.ax1.plot(x_bodies+dx, y_bodies+dy, marker = '+', color='red', markersize=20, linestyle='none')
            
            # Plot the ring
                
            DO_PLOT_RING_INNER = False
            DO_PLOT_RING_OUTER = True
            
            if (DO_PLOT_RING_OUTER):
                self.ax1.plot(x_pos_ring2, y_pos_ring2, marker='o', color = 'blue', ls = '--',
                              label = 'Ring, OpNav only')

                self.ax1.plot(x_pos_ring2 + dx, y_pos_ring2 + dy, marker='o', color = 'lightblue', ls = '--',
                              label = 'Ring, OpNav+User')
                    
            if (DO_PLOT_RING_INNER):
                self.ax1.plot(x_pos_ring1, y_pos_ring1, marker='o', color='green', ls = '-', \
                    ms=8, label='Ring, LT')

                self.ax1.plot(x_pos_ring1 + dx, y_pos_ring1 + dy, \
                    marker='o', color='purple', ls = '-', ms=8, label='Ring, LT, Shifted')

            self.legend = self.ax1.legend()  # Draw legend. Might be irrel since remove() might keep it; not sure.

            self.canvas1.draw()


#==============================================================================
# Generate a mask of all the stars in field
#==============================================================================
            
    def get_mask_stars(self):
        """
        Returns a boolean image, set to True at pixels within r_pix_mask of a satellite.
        """

        # XXX This routine needs to be rewritten. It is a bottleneck. I think it can 
        # be done by calling np.roll() on a boolean mask of one star, rather than taking
        # sqrt of every pixel.
        
        t = self.t_group[self.index_image]  # Grab this, read-only, since we use it a lot.
                                            # We can reference table['col'][n] or table[n]['col'] - either OK
                                            
        r_pix_mask = 15                     # Exclude pixels this distance from the satellite center.

        x_star = eval('np.' + t['x_pos_star_cat']) + t['dx_opnav']
        y_star = eval('np.' + t['y_pos_star_cat']) + t['dy_opnav']
 
        mask = 0 * self.image_processed

        (x_arr, y_arr) = np.meshgrid(range(np.shape(mask)[0]), range(np.shape(mask)[1]))
        
        for x_i, y_i in zip(x_star, y_star):

            d = np.sqrt((x_arr - (x_i))**2 + (y_arr - (y_i))**2)

            mask_i = (d < r_pix_mask)
        
            mask = mask + mask_i
            
#        plt.imshow(mask > 0)
#        plt.title('Stellar Mask')
#        plt.show()

#        print("Masked {} stars.".format(np.size(x_star)))
        
        return mask > 0
        
            
#==============================================================================
# Generate a satellite mask
#==============================================================================

# The image is 'properly navigated' -- that is, reflects WCS pointing, plus any of 
# the user's navigation settings, and lines up with the read-in image, with no rolling required.

# *** We should also mask out stars, such as seen in 8/41.

    def get_mask_satellites(self):
        """
        Returns a boolean image, set to True at pixels within r_pix_mask of a satellite.
        """
    
        r_pix_mask = 30                     # Exclude pixels this distance from the satellite center.

        t = self.t_group[self.index_image]  # Grab this, read-only, since we use it a lot.
                                            # We can reference table['col'][n] or table[n]['col'] - either OK
        w = WCS(t['Filename'])  
                
        name_bodies = np.array(['Metis', 'Adrastea', 'Thebe', 'Amalthea', 'Io'])        
        x_bodies,  y_bodies   = hbt.get_pos_bodies(t['ET'], name_bodies, units='pixels', wcs=w)

        dx = t['dx_opnav'] + self.slider_offset_dx.get()
        dy = t['dy_opnav'] + self.slider_offset_dy.get()

        mask = 0 * self.image_processed
        for i,body in enumerate(name_bodies):
            (x_arr, y_arr) = np.meshgrid(range(np.shape(mask)[0]), range(np.shape(mask)[1]))
            d = np.sqrt((x_arr - (x_bodies[i] + dx))**2 + (y_arr - (y_bodies[i] + dy))**2)
            mask_i = (d < r_pix_mask)
            
            if np.sum(mask_i) > 0:
                print("Satellite {} masked.".format(body))
            
            mask = mask + mask_i
        
        return mask > 0  # Return boolean array: True if satellite within r_pix_mask pixels
        
##########
# Load backplane
##########
# Returns True if loaded successfully; False if not
        
    def load_backplane(self):

        dir_backplanes = '/Users/throop/data/NH_Jring/out/'
        file_backplane = dir_backplanes + self.t_group['Shortname'][self.index_image].replace('.fit', '_planes.pkl')

        # Save the shortname associated with the current backplane. 
        # That lets us verify if the backplane for current image is indeed loaded.

        self.file_backplane_shortname = self.t_group['Shortname'][self.index_image]
				
        if (os.path.isfile(file_backplane)):
#            print('load_backplane: loading ' + file_backplane) 
            lun = open(file_backplane, 'rb')
            planes = pickle.load(lun)
            self.planes = planes # This will load self.t
            lun.close()
            return True

        else:
            print("Can't load backplane " + file_backplane)
            return False

##########
# Repoint an image
##########
# Placeholder -- not sure what it will do

    def repoint(self):

        return 0

##########
# Open a file in external viewer such as DS9
##########

    def open_external(self):

        app = '/Applications/SAOImage DS9.app/Contents/MacOS/ds9'
        file = self.t_group['Filename'][self.index_image]

        subprocess.call(['/usr/bin/open', app, file]) # Non-blocking (but puts up a terminal window)
#        subprocess.call([app, file]) # Blocking
        
        return 0

##########
# Choose the background model
##########

    def select_bg(self, event):
        
#        print("bg method = " + self.var_option_bg.get())

        # Grab the GUI settings for the background, and save them into proper variables.

        self.t_group['bg_method'][self.index_group] = self.var_option_bg.get()
        self.t_group['bg_argument'][self.index_group] = self.entry_bg.get()

##########
# Copy current filename (short) to clipboard
##########

    def copy_name_to_clipboard(self):

        str = self.t_group['Shortname'][self.index_image]
        hbt.write_to_clipboard(str)
        print("{} copied to clipboard".format(str))
        
        return 0
        
##########
# Close app and quit
##########
# Define this with one argument if we press a button, or two if we trigger an event like a keypress
# Get error if called with more than it can handle. So we define it here with two.

    def quit_e(self, event):
        self.quit()        
    
    def quit(self):
        root.destroy() # Q: How does root. get automatically imported here? Not sure.
        root.quit()

##########
# Handle change to a checkbox
##########

    def handle_checkbutton(self):
        
        print("Button = " + repr(self.var_checkbutton_extract.get()))
        self.do_autoextract = self.var_checkbutton_extract.get() # Returns 1 or 0
        
##########
# Load settings
##########
# Load them from the pre-set filename

    def load(self, verbose=True):
        
        lun = open(self.filename_save, 'rb')
        t = pickle.load(lun)
        self.t = t # All of the variables we need are in the 't' table.
        lun.close()

        if (verbose):
            tkMessageBox.showinfo("Loaded", "File " + self.filename_save + " loaded.")

##########
# Save everything to disk
##########

    def save_file(self, verbose=True):

#    """ 
#    Save all settings to the pre-set filename 
#    """
        # First save the current GUI settings to local variables in case they've not beeen saved yet.
  
        self.save_gui()

        # Put up a message for the user. A dialog is too intrusive.

        self.var_label_status_io.set('SAVING...') # This one doens't work for some reason...
    
        # Write one variable to a file    
    
        print("Writing to {}".format(self.dir_out + self.filename_save))
        
        lun = open(self.filename_save, 'wb')
        t = self.t
        pickle.dump(t, lun)
        lun.close()
        
        print("finished")
               
#        time.sleep(1)
        self.var_label_status_io.set('')  # This one works

##########
# Export results disk
##########

    def export_analysis(self, verbose=True):

        t = self.t_group[self.index_image]  # Grab this, read-only, since we use it a lot.

        dir_export = '/Users/throop/data/NH_Jring/out/'
        file_export = dir_export + t['Shortname'].replace('.fit', '_export.pkl')
        
        image    = self.image_unwrapped
        radius   = self.radius_unwrapped
        azimuth  = self.azimuth_unwrapped
        
        profile_radius_dn  = self.profile_radius_central
        profile_azimuth_dn = self.profile_azimuth_central
        
        ang_elev = self.ang_elev
        
        ang_phase = np.mean(self.planes['Phase'])
        
        index_image = self.index_image
        index_group = self.index_group
        
        et = t['ET']
        
        vals = (image, et, radius, azimuth, profile_radius_dn, profile_azimuth_dn, \
                ang_elev, ang_phase, index_image, index_group)
        
        lun = open(file_export, 'wb')
        pickle.dump(vals, lun)
        lun.close()
        
        print("Wrote results: {}".format(file_export))
        
##########
# (p)revious image
##########
      
    def select_image_prev(self):
        
        self.index_image_new = (self.index_image - 1) % self.num_images_group
        self.index_group_new = self.index_group
								
        self.change_image()

##########
# (n)ext image
##########
    
    def select_image_next(self):
          
        self.index_image_new = (self.index_image + 1) % self.num_images_group
        self.index_group_new = self.index_group
        self.change_image()

##########
# Process slider positions
##########

    def set_offset(self, event): # Because this is an event, it it passed two arguments
        
# Get the slider positions, for the dx and dy nav offset positions, and put them into a variable we can use

#        print("set_offset()")

        self.offset_dx = self.slider_offset_dx.get() #
        self.offset_dy = self.slider_offset_dy.get() #
        
        self.plot_objects()       
        
        return 0


#==============================================================================
# Convert from DN to I/F
#==============================================================================
        
    def dn2iof(self, dn, exptime, pixfov, rsolar):
        
    # Convert DN to I/F. 
    # This is not a general routine -- it's specific to LORRI 1x1 @ Jupiter.
    
        # Calculate LORRI pixel size, in sr

        pixfov = 0.3 * hbt.d2r * 1e6 / 1024  # This keyword is missing. "Plate scale in microrad/pix "

        sr_pix       = (pixfov*(1e-6))**2  # Angular size of each MVIC pixel, in sr
    
        # Look up the solar flux at 1 AU, using the solar spectral irradiance at 
        #    http://rredc.nrel.gov/solar/spectra/am1.5/astmg173/astmg173.html
        # or http://www.pas.rochester.edu/~emamajek/AST453/AST453_stellarprops.pdf
    
        f_solar_1au_si     = 1.77                 # W/m2/nm. At 600 nm. 
        f_solar_1au_cgs    = f_solar_1au_si * 100 # Convert from W/m2/nm to erg/sec/cm2/Angstrom
    
        f_solar_1au        = f_solar_1au_cgs
    
        # Calculate the solar flux at Pluto's distance. [Actual distance is 33.8 AU]
    
        f_solar_jup       = f_solar_1au / (5**2)  # Use 1/r^2, not 1/(4pi r^2)
    
        # Use constants (from Level-2 files) to convert from DN, to intensity at detector.
    
        # This is the equation in ICD @ 62.
    
        i_per_sr    = dn / exptime / rsolar # Convert into erg/cm2/s/sr/Angstrom.
    
        # Because the ring is spatially extended, it fills the pixel, so we mult by pixel size
        # to get the full irradiance on the pixel.
        # *** But, somehow, this is not working. I get the right answer only if I ignore this 'per sr' factor.
    
        DO_OVERRIDE = True  # If true, ignore the missing factor of 'per sr' that seems to be in the conversion
    
        i           = i_per_sr * sr_pix     # Convert into erg/cm2/s/Angstrom
    
        if (DO_OVERRIDE):
            i = i_per_sr
    
        # Calculate "I/F". This is not simply the ratio of I over F, because F in the eq is not actually Flux.
        # "pi F is the incident solar flux density" -- ie, "F = solar flux density / pi"
        # SC93 @ 125
    
        iof = i / (f_solar_jup / math.pi)
        
        return iof
        
###########
# Now start the main app
###########

# Start up the widget

root = tkinter.Tk()
app  = App(root)

# set the dimensions and position of the window


root.geometry('%dx%d+%d+%d' % (1750, 900, 2, 2))
root.configure(background='#ECECEC')                # ECECEC is the 'default' background for a lot of ttk widgets, which
                                                    # I figured out using photoshop. Not sure how to change that.

#  window.attributes('-topmost', 1)
#  window.attributes('-topmost', 0)

os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

# Start a profiler, if requested

DO_PROFILE = False

if DO_PROFILE:
    
    file_out_profile = 'profile.bin'
    
    cProfile.run('root.mainloop()', filename=file_out_profile)  # This will call the __init__ function
    
    print("Profiling with cProfile, output to " + file_out_profile)
    
else:    

    while True:
        try:
            root.mainloop()
            break
        except UnicodeDecodeError:  # Fix a TK + py3 bug, which causes Unicode errors on events. 
                    # http://stackoverflow.com/questions/16995969/inertial-scrolling-in-mac-os-x-with-tkinter-and-python
            pass
    
    



