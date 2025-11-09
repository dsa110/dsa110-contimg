#!/bin/bash
# Command to run gaincal on 2025-10-29T13:54:17.phased.ms

conda run -n casa6 python3 -c "
from casatasks import gaincal
import os

ms_path = '/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.phased.ms'
refant = '59'
# Use .gcal extension for gain calibration table (standard CASA convention)
# This table can be passed to bandpass() via gaintable parameter
caltable = f'{ms_path}.gaincal_p30s.gcal'

# Remove existing table if present
if os.path.exists(caltable):
    import shutil
    shutil.rmtree(caltable)

print('Running gaincal...')
gaincal(
    vis=ms_path,
    caltable=caltable,
    field='0',
    solint='30s',
    refant=refant,
    gaintype='G',
    calmode='p',
    minsnr=3.0,
    selectdata=True,
)

if os.path.exists(caltable):
    print(f'SUCCESS: {caltable}')
else:
    print('FAILED')
"
