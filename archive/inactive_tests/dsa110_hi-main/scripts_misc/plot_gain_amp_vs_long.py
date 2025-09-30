import os
import astropy.units as u
from astropy.coordinates import SkyCoord, SkyOffsetFrame
import matplotlib.pyplot as plt

#setup
name = '2024-03-28_0319+415_setjy'
out  = '/lustre/aoc/users/mrugel/projects/dsa110/red/'
outcal = os.path.join(out,name,name)
vis = os.path.join(outcal)+'.ms'

# normalize the complex gain calibration manually (here the minimum)
tb.open(outcal+'.G1LONGNORM', nomodify = True)
cparam = tb.getcol('CPARAM')
ants = tb.getcol('ANTENNA1')
times = tb.getcol('TIME')
tb.close()

# convert times in RA
## obsframe
me.doframe(me.observatory('OVRO_MMA'))
## zenith
zenith = me.direction('AZEL', '0deg','90deg')

ras  = times.copy()
for i in range(len(ras)):
    me.doframe(me.epoch('MJD',qa.quantity(times[i],'s')))
    ras[i] = me.getvalue(me.measure(zenith, 'j2000'))['m0']['value']

# declination
msmd.open(vis)
phasecenter = msmd.phasecenter()
msmd.close()

# pointing coordinates
ptgs = []
for i in range(len(ras)):
    ptgs.append(SkyCoord(ra=ras[i]*u.rad,dec = phasecenter['m1']['value']*u.rad, frame='fk5'))
ptgs = np.array(ptgs)

# define sky offset frame
pc = SkyCoord(ra=phasecenter['m0']['value']*u.rad,dec = phasecenter['m1']['value']*u.rad, frame='fk5')
pcframe = SkyOffsetFrame(origin=pc)

# plot all antennae
for i in np.arange(cparam.shape[0]):
    for k in np.unique(ants):
        plt.scatter([_ptg.transform_to(pcframe).lon.value for _ptg in ptgs[(ants==k)]], np.abs(cparam[i,:,(ants==k)]))

