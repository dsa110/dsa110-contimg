"""Generate AEP frequency scan movies."""

import os

import pylab as plt
from tqdm import tqdm

from ska_ost_low_uv.postx.aeps import orthview_aep

if not os.path.exists('aeps'):
    os.mkdir('aeps')

if not os.path.exists('aeps/linear'):
    os.mkdir('aeps/linear')

if not os.path.exists('aeps/stokes'):
    os.mkdir('aeps/stokes')

for ii in tqdm(range(0, 301)):
    ff = ii + 50
    orthview_aep(ff)
    plt.savefig(f'aeps/linear/orthview_{ii:03d}.png')
    plt.close()

for ii in tqdm(range(0, 301)):
    ff = ii + 50
    orthview_aep(ff, mode='stokes')
    plt.savefig(f'aeps/stokes/orthview_{ii:03d}.png')
    plt.close()

# Make videos with ffmpeg
os.system(
    'cd aeps/stokes; ffmpeg -framerate 10 -i orthview_%03d.png -vf scale=1080:-2,format=yuv420p ../stokes.mp4'
)
os.system(
    'cd aeps/linear; ffmpeg -framerate 10 -i orthview_%03d.png -vf scale=1080:-2,format=yuv420p ../linear.mp4'
)
