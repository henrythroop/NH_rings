#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 22 11:53:55 2018

@author: throop
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 16:20:36 2018

@author: throop
"""

import hbt
import numpy as np

def get_radial_profile_backplane(im, radius_plane, method='median', num_pts = 100):

    """
    Extract a radial profile from an image. 
    
    Uses a backplane passed in.
    
    Parameters
    -----
    
    im:
        Array of data values (e.g., the image).
        
    radius_plane:
        2D array, which is the backplane. Typically this is planes['Radius_eq'].
    
    num_pts:
        Scalar. Number of points to use in the output array.  Output radius is evenly spaced
        from 0 .. max(radius_plane).
        
    Optional parameters
    -----    
    
    method: 
        String. 'mean' or 'median'.
        
    """
    radius_1d = hbt.frange(0, int(np.amax(radius_plane)), num_pts)
    
    profile_1d    = 0. * radius_1d.copy()
        
    for i in range(len(profile_1d)-2):

    # Identify the pixels which are at the right distance
    
        is_good = np.logical_and(radius_plane >= radius_1d[i],
                                 radius_plane <= radius_1d[i+1]) 
    
        if (method == 'mean'):
            profile_1d[i]   = np.mean(im[is_good])
    
        if (method == 'median'):
            profile_1d[i] = np.median(im[is_good])
        
    return (radius_1d, profile_1d)

### END OF FUNCTION DEFINTION
    
if (__name__ == '__main__'):
    pass