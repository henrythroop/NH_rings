-----
MU69 Flyby Kernel Set, for Hazard Team use at MU69 ORT1 (January 2018).
-----

This metakernel file is a copy of NHGV's default kernel set for the NH MU69
Prime trajectory flyby. It includes all SPICE files used by NHGV, including
frames kernels, trajectories for s/c and many planets and satellites, MU69,
frames kernels, instrument kernels, etc. This is a larger set than necessary
for KEM (e.g., it includes kernels for the Pluto system and other planets), but
it is guaranteed to be complete.

All of these files exist on ixion, in GV's kernel respository at
/home/html/nh/gv-dev/kernels. For code run on ixion, this metakernel can be
incorporated using FURNSH() with nothing else necessary.

Henry Throop 12-Jan-2018

-----

\begindata

PATH_SYMBOLS = ('DIR', 'DIR2')

PATH_VALUES  = ('/Users/throop/gv/dev/kernels', '/Users/throop/git/NH_rings')

KERNELS_TO_LOAD = (
'$DIR/pck00009.tpc',
'$DIR/naif0012.tls',
'$DIR/new-horizons_1698.tsc',
'$DIR/gv_pck.tpc',
'$DIR/gv_naif_ids.txt',
'$DIR/gv_pluto_smallsats.tf',
'$DIR/gv_smallbodies.tf',
'$DIR/gv_pluto_smallsats_lhr.tf',
'$DIR2/mu69_ring_frames.tf',
'$DIR/nh_ref_20150801_20210714_od128_tcm29_alt.bsp'
'$DIR/NavPE_de433_od128.bsp',
'$DIR/NavSBE_2014MU69_od138.bsp',
'$DIR/NavSBE_2014MU69_od128.bsp',
)
