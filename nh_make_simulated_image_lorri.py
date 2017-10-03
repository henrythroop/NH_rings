#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  3 10:12:26 2017

@author: throop
"""


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
from   scipy.stats import linregress
from   astropy.visualization import wcsaxes
import time
from   scipy.interpolate import griddata
from   importlib import reload            # So I can do reload(module)
import imreg_dft as ird                    # Image translation

from astropy.convolution import convolve, convolve_fft, Gaussian2DKernel, Box2DKernel

import re # Regexp
import pickle # For load/save

import scipy

from   matplotlib.figure import Figure

# HBT imports

import hbt


# =============================================================================
# Compute brightness of MU69, in DN, based on distance to body and exptime.
# =============================================================================

def nh_dn_lorri_mu69(mode = '1X1', dist = 0.1*u.au, exptime = 10):

#    dist = 0.1*u.au
#    exptime = 100
#    mode = '4X4'
    
    PPLUTO_LORRI_1X1 = 8.7249995e+15 # Point Source sensitivity. Units are (DN/s)/(erg/cm^2/s/A).
    PPLUTO_LORRI_4X4 = 1.0033749e+16

    FSOLAR_LORRI  = 176.	     	    # We want to be sure to use LORRI value, not MVIC value!

    V_MU69_OPP = 26.7 + 0.65                 # MU69 V mag at opposition (ie, from Earth at 1 AU)
    
    if (mode.upper() == '1X1'):
        PPLUTO_LORRI_1X1
        PHOTZPT = 18.76

    else:
        PPLUTO = PPLUTO_LORRI_4X4
        PHOTZPT = 18.91

    CC = 0  # Color correction for solar-type stars
    AC = 0  # AC (or BC) is aperture correction "in case the flux is not integrated over the entire stellar image"
    
    # Convert opposition mag, to mag seen from NH

    V_MU69 = hbt.fac2mag( hbt.mag2fac(V_MU69_OPP) * ((1) / (dist.to('AU').value) )**2 )
     
#    V = -2.5 * alog10(S/texp) + PHOTZPT + CC – AC  # S is integrated net signal, in DN. Equation from Hal writeup
    
    # Calculate the integrated signal, in DN.
    
    S = exptime * 10** ((V_MU69 - PHOTZPT - CC + AC) / (-2.5))  # My inversion of Hal's eq

#    print('{} s, {}, {}, vmag({}) = {:.2f} -> {:.2f} DN'.format(exptime, mode, dist, dist, V_MU69, S))
    
    return(S)  # Return the total counts
    
# =============================================================================
# Compute conversion constant from I/F to DN.
#     mode = {'1X1', '4X4'}
#     dist = distance to sun, in astropy units.
#     exptime = exposure time in seconds
#     This ignores any ring-specific geometry
# =============================================================================
    
def nh_iof_2_dn_lorri_extended(mode = '1X1', dist = 43*u.au, exptime = 10):

    RSOLAR_LORRI_1X1 =  221999.98  # Diffuse sensitivity, LORRI 1X1. Units are (DN/s/pixel)/(erg/cm^2/s/A/sr)
    RSOLAR_LORRI_4X4 = 3800640.0   # Diffuse sensitivity, LORRI 1X1. Units are (DN/s/pixel)/(erg/cm^2/s/A/sr)

    FSOLAR_LORRI  = 176.	     	    # We want to be sure to use LORRI value, not MVIC value!
    
    if (mode.upper() == '1X1'):
        RSOLAR = RSOLAR_LORRI_1X1
    else:
        RSOLAR = RSOLAR_LORRI_4X4

#    I = C / TEXP / RSOLAR   # Could use RSOLAR, RJUPITER, or RPLUTO. All v similar, except for spectrum assumed.

# Apply Hal's conversion formula from p. 7, to compute I/F and print it.

#    IoF = math.pi * I * r_sun_mu69**2 / F_solar # Equation from Hal's paper

    I = 1 / math.pi / (dist.to('AU').value)**2 * FSOLAR_LORRI
    
    C = I * exptime * RSOLAR
    
    factor = C  # This is the multiplicative factor. IoF = C * DN
    
    return factor

#    # Now convert to 'normal I/F'
#    
#    # Define mu = cos(e), where e = emission angle, and e=0 is face-on.
#    
#    e = 0 # Assume ring is face-on. The sunflower orbits are. 
#    
#    mu = np.cos(e)
#    
#    #        mu_2D = np.transpose(np.tile(mu, (self.num_bins_radius(),1)))
#    
#    # Calculate the normal I/F
#    
#    IoF_normal = 4 * mu * IoF
#    
#    
# =============================================================================
# Make a simulated image.
# For now, this image has zero DN of background readnoise, stray light, etc.
# It is just the ring and/or MU69.
#
# The returned image is in DN (not I/F).
# =============================================================================
        
def nh_make_simulated_image_lorri(do_ring = False,                  # Flag: do we draw a ring? 
                                  do_mu69 = False,                  # Flag: Do we draw MU69?
                                  mode = '1X1',                     # LORRI mode: 4X4 or 1X1
                                  exptime = 10,                     # Exposure time, seconds
                                  dist_solar = 40*u.au,             # Distance from sun to MU69
                                  dist_target = 0.01*u.au,          # Distance to MU69, from s/c
                                  a_ring = (1000*u.km, 3000*u.km),  # Default ring inner, outer radii
                                  do_psf = True,                    # Flag: do we apply a PSF?
                                  albedo_mu69 = 0.5,                # Albedo of MU69
                                  radius_mu69 = 20*u.km,            # Radius of MU69
                                  iof_ring = 1e-4,                  # Default ring I/F
                                  dist_ring_smoothing = None,       # Do we smooth the edges of the ring?
                                  pos = (None, None)):              # Center position: x and y

    

    a_ring = (1000*u.km, 3000*u.km)
    exptime = 10
    mode = '1x1'
    dist_solar = 40*u.au
    dist_target = 0.01*u.au
    do_psf = True
    albedo_mu69 = 0.5
    radius_mu69 = 20*u.km
    iof_ring = 1e-4
    do_ring_edges_smooth = True
    pos = (None, None)
    do_ring = True
    dist_ring_smoothing = 500*u.km
    do_mu69 = True
    
    if (mode.upper() == '1X1'):
        naxis = 1024     # Number of pixels in the output array. Assumed to be square.
    else:
        naxis = 256      # 4X4 mode
   
    scale_pix_lorri_rad = (0.3 * hbt.d2r) / naxis   # Lorri pixels, in radians

    # Create the output array
    
    arr = np.zeros((naxis, naxis))
  
    # Compute the image center position, if needed.
    
    if pos[0] == None:
        pos = (naxis/2, naxis/2)
        
    # Compute the pixel scale, km/pix at target distance

    scale_pix_km = dist_target.to('km').value * scale_pix_lorri_rad
        
    # Construct an array showing the distance of each pixel from the target, in km
    
    xx, yy = np.mgrid[:naxis, :naxis]  # What is this syntax all about? That is weird.
                                       # A: mgrid is a generator. np.meshgrid is the normal function version.
    
    dist = np.sqrt( ((xx - pos[0]) ** 2) + ((yy - pos[1]) ** 2) ) * scale_pix_km
   
    # Create the ring, if requested
    
    if (do_ring):
    
        is_ring = np.logical_and(  (dist > a_ring[0].to('km').value),
                                   (dist < a_ring[1].to('km').value) )
    
        # Convolve the ring so as to make the edges smooth, not sharp
        # NB: This convolution causes issues at the image edges, because a value of 0 is assumed outside the array.
        # The proper way to do the covolution is to include the whole ring, convolve, and then crop. 
        
        if (dist_ring_smoothing):
            width_pix = dist_ring_smoothing.to('km').value / scale_pix_km
            kernel = Box2DKernel(width_pix) # Use the simplest possible kernel, just to give the ring smooth edges
            print('Smoothing ring edges...')
            is_ring_convolved = convolve_fft(is_ring, kernel)  # Pretty slow... but faster than the non-FFT version!
            
            is_ring = is_ring_convolved
    
        # Convert from I/F to DN
    
        arr = is_ring * iof_ring * nh_iof_2_dn_lorri_extended(exptime = exptime, dist=dist_solar, mode=mode)
    

    # Create the MU69 image
    
    if (do_mu69):
        dn_mu69 = nh_dn_lorri_mu69(dist = dist_target, exptime = exptime)
        
        # Put MU69 DN into a single pixel
        
        arr[int(pos[0]), int(pos[1])] = dn_mu69
        
# Convolve entire image with a LORRI PSF, if requested

    if (do_psf):
      if (mode.upper() == '1X1'):
          file_psf = 'psfs/1x1/lorri_1x1_psf22_v1.fits'
      if (mode.upper() == '4X4'):
          file_psf = 'psfs/4x4/lor_0368314618_psf_v1.fits'

      hdu = fits.open(file_psf)
      psf = hdu[0].data
      hdu.close()
      
      # If the PSF is an even dimension, convert to odd, as per the requirement of convolve()
      
      if ((np.shape(psf)[0] % 2) == 0):
          psf = psf[:-1, :-1]
      
      print("Convolving with PSF {}...".format(file_psf))
      arr_psf = convolve_fft(arr, psf)
      
      arr = arr_psf
      
    return arr

# =============================================================================
# Now do some tests on this
# =============================================================================

plt.set_cmap('Greys_r')

sp.furnsh('kernels_kem.tm')

hbt.figsize((12,12))
hbt.set_fontsize(15)

iof_ring = 1e-7
exptime = 30
mode = '4X4'
#mode = '1X1'
pos = (None, None)
#pos = (300, 700)
pos = (100, 200)  # y, x in normal imshow() coordinates.
#dist_target = 0.01*u.au
dist_solar  = 43.2*u.au  # MU69 dist at encounter: 43.2 AU, from KEM Wiki page 
do_psf = True            # Flag: Do we convolve result with NH LORRI PSF?26.7 + 0.65

dt_obs = -22*u.day        # Time relative to MU69 C/A

utc_ca = '2019 1 Jan 05:33:00'
et_ca  = sp.utc2et(utc_ca)
et_obs = et_ca + dt_obs.to('s').value
 
utc_obs = sp.et2utc(et_obs, 'C', 0)
utc_obs_human = 'K{:+}d'.format(dt_obs.to('day').value)

vec,lt = sp.spkezr('2014 MU69', et_obs, 'J2000', 'LT', 'New Horizons')
vec_sc_targ = vec[0:3]
dist_target = np.sqrt(np.sum(vec_sc_targ**2))*u.km.to('AU')*u.au
            
arr = nh_make_simulated_image_lorri(do_ring=True, 
                                    dist_ring_smoothing = 1000*u.km, 
                                    iof_ring = iof_ring,
                                    a_ring = (5000*u.km, 10000*u.km), 
                                    exptime = exptime, 
                                    mode = mode, 
                                    pos = pos,
                                    dist_solar = dist_solar, 
                                    dist_target = dist_target,
                                    do_mu69 = True,
                                    do_psf = True)

# Calculate the max DN value in the array. This is (more-or-less) the ring target, converted to DN.
# Though it might be diminished a bit due to the PSF.

dn_max = np.amax(arr[arr > 0])

plt.imshow(arr)
plt.title('I/F = {}, max = {:0.2f} DN, t = {} s, mode = {}, {}, {:.2f}, {}'.format(
                      iof_ring, dn_max, exptime, mode,
                      dist_solar, 
                      dist_target,
                      utc_obs_human))
plt.show()

# Do a test of the I/F -> DN conversion. This value can be compared to that from Exposure Time Calculator

iof2dn = nh_iof_2_dn_lorri_extended(mode = mode, dist = dist_solar, exptime = exptime)
print('For ring: I/F = {} -> {:0.2f} DN/pixel'.format(iof_ring, iof_ring * iof2dn))
print('For MU69: total signal = {:0.2f} DN, pre-PSF'.format(nh_dn_lorri_mu69(dist = dist_target, exptime = exptime)))

# =============================================================================
# Load the Buie MU69 frames, and add a ring to them!
# =============================================================================

stretch_percent = 95    
stretch = astropy.visualization.PercentileInterval(stretch_percent) # PI(90) scales to 5th..95th %ile.

dir_buie = '/Users/throop/Data/NH_KEM_Hazard/Sep17_Buie'
files = glob.glob(dir_buie + '/*.*')

for file in files:
      hdu = fits.open(file)
      im = hdu['PRIMARY'].data
      header = hdu['PRIMARY'].header
      w = WCS(file)
      hdu.close()

file = '/Users/throop/Data/NH_KEM_Hazard/K1LR_MU69ApprField_115d_L2_2017264/lor_0368310358_0x633_pwcs.fits'
hdu = fits.open(file)
im = hdu['PRIMARY'].data
header = hdu['PRIMARY'].header
w = WCS(file)
hdu.close()

plt.imshow(stretch(im + arr*50))

