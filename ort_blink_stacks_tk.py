#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 22 09:58:37 2018

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
import astropy.visualization
from   astropy.io import fits
from   astropy.table import Table
import astropy.table   # I need the unique() function here. Why is in in table and not Table??
import matplotlib
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
import time
from   importlib import reload            # So I can do reload(module)

import re # Regexp
import pickle # For load/save
import time

# Imports for Tk

#import Tkinter # change Tkinter -> tkinter for py 2 - 3?
import tkinter
import tkinter.messagebox
#import tkMessageBox #for python2
from   matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from   matplotlib.figure import Figure

from   astropy.stats import sigma_clip

from   image_stack import image_stack

# HBT imports

import hbt

class App:

##########
# INIT CLASS
##########

    def __init__(self, master):

        self.master = master
        
        # Open the image stack
        
        self.stretch_percent = 90    
        self.stretch = astropy.visualization.PercentileInterval(self.stretch_percent) # PI(90) scales to 5th..95th %ile.
        
        self.reqids_haz  = ['K1LR_HAZ00', 'K1LR_HAZ01', 'K1LR_HAZ02', 'K1LR_HAZ03', 'K1LR_HAZ04']
#        self.reqids_haz  = ['K1LR_HAZ03', 'K1LR_HAZ01', 'K1LR_HAZ02']
        self.reqid_field = 'K1LR_MU69ApprField_115d_L2_2017264'
        
        self.dir_data    = '/Users/throop/Data/ORT1/throop/backplaned/'
            
        # Set the edge padding large enough s.t. all output stacks will be the same size.
        # This value is easy to compute: loop over all stacks, and take max of stack.calc_padding()[0]
        
        self.padding     = 61 # Amount to pad the images by. This is the same as the max drift btwn all images in stacks
        self.zoom        = 4  # Sub-pixel zoom to apply when shifting images
        self.num_image   = 0  # Which stack number to start on.
        self.zoom_screen = 1  # 'Screen zoom' amount to apply. This can be changed interactively.
        
        self.is_blink    = False  # Blinking mode is turned off by default
        self.dt_blink    = 300    # Blink time in ms
        
        # Start up SPICE if needed
        
        if (sp.ktotal('ALL') == 0):
            sp.furnsh('kernels_kem_prime.tm')
            
        # Set the RA/Dec of MU69. We could look this up from SPICE but it changes slowly, so just keep it fixed for now.
        
        self.radec_mu69 = (4.794979838984583, -0.3641418801015417)
        
        # Boolean. For the current image, do we subtract the field frame, or not?
        
        self.do_subtract = True

        hbt.figsize((12,12))
        hbt.figsize((5,5))
        hbt.set_fontsize(20)

        # Set the stretch range, for imshow. These values are mapped to black and white, respectively.
        
        self.vmin_diff = -1   # Range for subtracted images
        self.vmax_diff =  2
        
        self.vmin_raw = -1    # Range for raw images (non-subtracted)
        self.vmax_raw = 1000
        
# Restore the stacks directly from archived pickle file, if it exists
        
        self.file_save = os.path.join(self.dir_data, f'stacks_blink_n{len(self.reqids_haz)}_z{self.zoom}.pkl')
        
        if os.path.isfile(self.file_save):
            self.restore()
        else:

# If no pickle file, load the stacks from raw images and re-align them
            
            # Load and stack the field images
    
            print("Stacking field images")        
            self.stack_field = image_stack(os.path.join(self.dir_data, self.reqid_field))    # The individual stack
            self.stack_field.align(method = 'wcs', center = self.radec_mu69)
            self.img_field  = self.stack_field.flatten(zoom=self.zoom, padding=self.padding) # Save the stacked image
        
            # Load and stack the Hazard images
            
            self.img_haz   = {} # Output dictionary for the stacked images
            self.stack_haz = {} # Output dictionary for the stacks themselves
            
            for reqid in self.reqids_haz:
                self.stack_haz[reqid] = image_stack(os.path.join(self.dir_data, reqid))    # The individual stack
                self.stack_haz[reqid].align(method = 'wcs', center = self.radec_mu69)
                self.img_haz[reqid]  = self.stack_haz[reqid].flatten(zoom=self.zoom, padding=self.padding) 
                # Put them in a dictionary

            # Save the stacks to a pickle file, if requested
            
            yn = input("Save stacks to a pickle file? ")
            if ('y' in yn):
                self.save()
                
# Set the sizes of the plots -- e.g., (7,7) = large square
        
        figsize_image = (10,10)
        
        self.fig1 = Figure(figsize = figsize_image)    # <- this is in dx, dy... which is opposite from array order!

        self.ax1 = self.fig1.add_subplot(1,1,1, 
                                    xlabel = 'X', ylabel = 'Y', 
                                    label = 'Image') # Return the axes
        plt.set_cmap('Greys_r')
        
        self.canvas1 = FigureCanvasTkAgg(self.fig1,master=master)
        self.canvas1.show()
        
# Set up Plot 2 : Radial / Azimuthal profiles
        
        do_canvas2 = False

        if do_canvas2:
            
            self.bgcolor = 'red'
    
            self.fig2 = Figure(figsize = (7,3))
            _ = self.fig2.set_facecolor(self.bgcolor)
    
            self.ax2 = self.fig2.add_subplot(1,1,1, 
                                        xlabel = 'Radius or Azimuth', ylabel = 'Intensity', 
                                        label = 'Plot') # Return the axes
            
            self.canvas2 = FigureCanvasTkAgg(self.fig2,master=master)
            self.canvas2.show()  
            self.canvas2.get_tk_widget().grid(row=2, column=1, rowspan = 1)

# Put objects into appropriate grid positions

        self.canvas1.get_tk_widget().grid(row=1, column=1, rowspan = 1)
        
# Define some keyboard shortcuts for the GUI
# These functions must be defined as event handlers, meaning they take two arguments (self and event), not just one.

        master.bind('q',       self.quit_e)
        master.bind('<space>', self.toggle_subtract_e)
        master.bind('=',       self.prev_e)
        master.bind('-',       self.next_e)
        master.bind('h',       self.help_e)
        master.bind('<Left>',  self.prev_e)
        master.bind('<Right>', self.next_e)
        master.bind('s',       self.stretch_e)
        master.bind('b',       self.blink_e)
        
        master.bind('z',       self.zoom_screen_up_e)
        master.bind('Z',       self.zoom_screen_down_e)

# Set the initial image index
        
        self.reqid_haz = self.reqids_haz[self.num_image]  # Set it to 'K1LR_HAZ00', for instance.
        
# Plot the image
        
        self.plot()

# =============================================================================
# Restore all stacks from a single saved pickle array
# =============================================================================

    def restore(self):
        
        """
        Load state from a pickle file. No arguments.
        """

        print("Reading: " + self.file_save)           
        lun = open(self.file_save, 'rb')
        (self.stack_field, self.img_field, self.stack_haz, self.img_haz) = pickle.load(lun)
        lun.close()

        return
    
# =============================================================================
# Save current state into a pickle file.
# =============================================================================

    def save(self):
        
        """
        Save stacks into a .pkl file. No arguments.
        """

        lun = open(self.file_save, 'wb')
        pickle.dump((self.stack_field, self.img_field, self.stack_haz, self.img_haz), lun)
        lun.close()
        print("Wrote: " + self.file_save)
        
        return
        
# =============================================================================
# Plot the current image, updating axes etc.
# =============================================================================
        
    def plot(self):

        # Load the current image
        
#        self.img_haz = self.stack_haz.image_single(self.num_image, padding = self.padding, zoom = self.zoom)
        
        img_haz = self.img_haz[self.reqids_haz[self.num_image]]
        
        # Calculate and apply the 'screen zoom'
        
        dx = hbt.sizex(img_haz)
        dx_zoomed = dx / self.zoom_screen
        min = int(dx/2 - dx_zoomed/2)
        max = int(dx/2 + dx_zoomed/2)
        
        # Subtract the bg image, if requested, and display it
        
        if (self.do_subtract):
            im_disp = img_haz[min:max, min:max] - self.img_field[min:max, min:max]
            self.plt1 = self.ax1.imshow(im_disp, interpolation=None, vmin=self.vmin_diff, vmax=self.vmax_diff)
            self.range_stretch = hbt.mm(self.stretch(im_disp))  # Get the 
            
        else:
            self.plt1 = self.ax1.imshow(img_haz[min:max, min:max], interpolation=None, 
                                        vmin=self.vmin_raw, vmax=self.vmax_raw)
            
        # Set the title, etc.
        
        self.ax1.set_title('{}, {}/{}, zoom = {}'.format(self.reqid_haz,
                       'N', len(self.reqids_haz), self.zoom))
#        self.ax1.set_xlim(range)
#        self.ax1.set_ylim(range)
        
        # Make it as compact as possible
        
#        plt.tight_layout()
        self.canvas1.show()

#        self.ax2.plot(self.img_haz[500,:])
#        self.canvas2.show()
 
# =============================================================================
# Update just the data in the current image, leaving all the rest untouched.
# =============================================================================
        
    def replot(self):

        # Load the current image

        # Figure out key for newest image to plot
        self.reqid_haz = self.reqids_haz[self.num_image]  # Set it to 'K1LR_HAZ00', for instance.

        print(f'Plotting num_image={self.num_image} : self.reqid_haz={self.reqid_haz}')            
        
        # Load the image
        img = self.img_haz[self.reqid_haz]
        
#        self.img_haz = self.stack_haz.image_single(self.num_image, padding = self.padding, zoom = self.zoom)

        dx = hbt.sizex(img)
        dx_zoomed = dx / self.zoom_screen
        min = int(dx/2 - dx_zoomed/2)
        max = int(dx/2 + dx_zoomed/2)
        
        # Subtract the bg image, if requested, and display it
        
        if (self.do_subtract):
            im_disp = img[min:max, min:max] - self.img_field[min:max, min:max]
            self.plt1.set_data(im_disp)
        else:
            self.plt1.set_data(img[min:max, min:max]) # Like imshow, but faster

        self.canvas1.draw()
        self.canvas1.show()  # Q: Do I need this:? A: Yes, even when using set_data().

        
        
# =============================================================================
# Key: Help
# =============================================================================

    def help_e(self, event):
        print('Help!')
        print('<space>      : Toggle field subtraction on/off')
        print('Z / z        : Zoom in/out' )
        print('<left> or =  : Previous')
        print('<right> or - : Next')
        print('-            : Next')
        print('h or ?       : Help')
        print('q            : Quit')
        print('s            : change Stretch')
        print('b            : Toggle blinking on/off')
        print('t            : Change blink time')
        print('e            ; Enter blink sequence as a string')
        print('-----')
        print('CURRENT STATUS:')
        print(f'Stretch:     {self.stretch_percent}')
        print(f'Blink sequence: ')
        print(f'Blink status: XX, dt = X')
        print(f'Zoom:        {self.zoom}')
        print(f'Zoom_screen: {self.zoom_screen}')
        print(f'v1, v2 diff: {self.vmin_diff},  {self.vmax_diff}')
        print(f'v1, v2 raw:  {self.vmin_raw},   {self.vmax_raw}')
        
# =============================================================================
# Key: Next image
# =============================================================================

    def next_e(self, event):
        self.num_image_prior = self.num_image  # Save it so we can blink to it.
        self.num_image += 1
        self.num_image = np.clip(self.num_image, 0, len(self.reqids_haz)-1)
        print(f'Next: num_image = {self.num_image}')
        print(f'Next: stack = {self.reqids_haz[self.num_image]}')
        self.replot()

# =============================================================================
# Key: Previous image
# =============================================================================
        
    def prev_e(self, event):
        self.num_image_prior = self.num_image
        self.num_image -=1
        self.num_image = np.clip(self.num_image, 0, len(self.reqids_haz)-1)
        
        print(f'Prev: num_image = {self.num_image}')
        print(f'Prev: stack = {self.reqids_haz[self.num_image]}')
        self.replot()

# =============================================================================
# Key: Change Stretch
# =============================================================================
        
    def stretch_e(self, event):
        str = input(f'Enter new stretch range ({self.vmin} {self.vmax}): ')
        
        self.vmin = int(str.split(' ')[0])  # Mapped to black
        self.vmax = int(str.split(' ')[1])  # Mapped to white 
        
        self.replot()   # We have to do plot and not replot, since the latter doesn't take vmin args.

# =============================================================================
# Key: zoom screen Up
# =============================================================================

    def zoom_screen_up_e(self, event):
        self.zoom_screen += 1
        print(self.zoom_screen)
        self.plot()

# =============================================================================
# Key: zoom screen Down
# =============================================================================

    def zoom_screen_down_e(self, event):
        self.zoom_screen -= 1
        if (self.zoom_screen < 1):
            self.zoom_screen = 1
        print(self.zoom_screen)
        self.plot()

# =============================================================================
# Key: change Stretch
# =============================================================================

    def restretch_e(self, event):
        print('Enter new stretch value:')
        self.plot()
        
# =============================================================================
# Key: Blink On/Off
# =============================================================================

    def blink_e(self, event):
        
        if (self.is_blink):
            self.is_blink = False
            print("Blinking now off")
        
        else:
            self.is_blink = True
            print("Blinking now on")
            self.show_next_frame()            # To turn on animation, set the flag, and call func to display next frame
    
# =============================================================================
# Show next frame -- animation
# =============================================================================

    def show_next_frame(self):
        
        """
        This function when called advances to the next frame in the animation.
        It then sets an 'idle event handler' with a timeout, so that it gets called
        again automatically by Tk. Other than setting this event handler, the animation
        is entirely done in the background, and the app responds fully to all events.
        """
        
        self.num_image += 1
        if (self.num_image >= len(self.reqids_haz)):
            self.num_image = 0
        print(f"Animating frame {self.num_image}")    
        self.replot()    
        if (self.is_blink):
            self.master.after(self.dt_blink, self.show_next_frame)
        
# =============================================================================
# Key: Blink (advanced)
# =============================================================================

    def blink_advanced_e(self, event):
        print('Blink advanced now!')
        self.plot()  
        
# =============================================================================
# Key: Toggle bg subtraction
# =============================================================================
        
    def toggle_subtract_e(self, event):
        self.do_subtract = not(self.do_subtract)
        self.plot()
        
# =============================================================================
# Key: Quit
# =============================================================================
        
    def quit_e(self, event):
        self.quit()        

# =============================================================================
# Quit app
# =============================================================================
    
    def quit(self):
        root.destroy() # Q: How does root. get automatically imported here? Not sure.
        root.quit()        
                
###########
# Now start the main app
###########

# Start up the widget

root = tkinter.Tk()
app  = App(root)

# set the dimensions and position of the window

root.geometry('%dx%d+%d+%d' % (810, 800, 2, 2))
root.configure(background='#ECECEC')                # ECECEC is the 'default' background
               
os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

while True:
    try:
        root.mainloop()
        break
    except UnicodeDecodeError:  # Fix a TK + py3 bug, which causes Unicode errors on events. 
                # http://stackoverflow.com/questions/16995969/inertial-scrolling-in-mac-os-x-with-tkinter-and-python
        pass
    
    
#def other:

# https://stackoverflow.com/questions/292095/polling-the-keyboard-detect-a-keypress-in-python   
#        https://stackoverflow.com/questions/29158220/tkinter-understanding-mainloop