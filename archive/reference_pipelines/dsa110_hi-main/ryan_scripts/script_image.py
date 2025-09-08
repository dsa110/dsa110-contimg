import os
import shutil
import time
from fnmatch import fnmatch

import numpy as np

from dsa110hi.pipeline_calsolver import flag, apply_cal
from dsa110hi.pipeline_video_maker import animate
from casatasks import rmtables, split, tclean, exportfits, gaincal, applycal, mstransform
from casatools import table
# from imutils import stitch_images_simple

# Delete this once I've transfered imutils
from astropy.io import fits
def stitch_images_simple(
        file_in: str, \
        reffreq: float = None, \
        inds: list = None, \
        check_uniform_freqs: bool = True, \
        ):
    """Gather channel images from wsclean into a single cube
    
    Parameters
    ----------
    file_base
        name base of images
    reffreq
        reference frequency to put into (optional)
    inds
        input manual selection of indices  (optional)
    """
    path = '/'.join(file_in.split('/')[:-1])
    file_base = file_in.split('/')[-1]
    
    for imtype in ['image','dirty','model','residual','psf']:
        if inds is None:
            files = os.listdir(path)
            files = [f for f in files if fnmatch(f,f'{file_base}-*-{imtype}.fits')]
            files = [f for f in files if f != f'{file_base}-MFS-{imtype}.fits']
            files = [f for f in files if f != f'{file_base}-CUBE-{imtype}.fits']
            if len(files) == 0:
                raise ValueError(f"No {imtype} files found")
        else:
            files = [f'{file_base}-{i:04.0f}-{imtype}.fits' for i in inds]
            for f in files:
                if not os.path.exists(os.path.join(path,f)):
                    raise ValueError(f"File {path+f} not found")

        files = sorted(files)
        if imtype == 'image':
            nimage = len(files)
        else:
            if len(files) != nimage:
                raise ValueError(f"Number of {imtype} and image files doesn't match")

        # collect data
        data = []
        hdrs = []
        fs = []
        dfs = []
        for f in files:
            hdu = fits.open(os.path.join(path,f))[0]
            data.append(hdu.data)
            hdrs.append(hdu.header)
            fs.append(hdu.header['CRPIX3'])
            dfs.append(hdu.header['CDELT3'])

        # create cube
        cube = np.concatenate(data)
        cube = np.swapaxes(cube,0,1)

        # create header (take first)
        hdr = hdrs[0]

        # check frequency info and add if evenly spaced
        if len(set(dfs)) <=1 and len(set(np.array(fs)[1:]-np.array(fs)[:-1])) <=1:
            hdr['CRPIX3'] = 1
        elif check_uniform_freqs == False:
            hdr['CRPIX3'] = 1
        else: 
            print("Frequency channels not evenly spaced!!!")
            raise

        # add rest frequency if specififed
        if reffreq:
            hdr['RESTFRQ'] = reffreq

        fout = f'{file_base}-CUBE-{imtype}.fits'
        fits.writeto(os.path.join(path,fout), data=cube, header=hdr, overwrite=True)


tb = table()

def transfer_script(incoming_files, incoming_cal_file, output_file,
                    bad_ants='', uvrange='<150m'):

    if not os.path.exists(output_file):
        os.makedirs(output_file)

    apply_cal(incoming_files, [os.path.join(incoming_cal_file,'DELAY'),os.path.join(incoming_cal_file,'BPASS')], 
              output_file+'source.ms', output_file_overwrite=True)
    flag(incoming_file=output_file+'source.ms', reset_flags=False,
        flag_bad_ants=bad_ants,
        flag_uvrange=uvrange)

def tclean_selfcal(incoming_file, output_file, fields='', spw='', phase_center='', imsize=[5000,5000],
                   selfcal_thresholds=['100mJy', '10mJy'], selfcal_refant='pad8',
                   final_thresholds=['10mJy', '3mJy', '1mJy'],
                   psfcut=0.5, chanbin=0, pbcut=0.25):
    # Phase center should have the form 'J2000 14h59m07.5839s +71d40m19.868s'

    if not os.path.exists(output_file):
        os.makedirs(output_file)

    if os.path.exists(os.path.join(output_file,'tmp_selfcal.ms')):
        rmtables(os.path.join(output_file,'tmp_selfcal.ms'))
    if os.path.exists(os.path.join(output_file,'tmp_selfcal.ms.flagversions')):
        shutil.rmtree(os.path.join(output_file,'tmp_selfcal.ms.flagversions'))

    # # Doing this with mstransform instead to allow channel averaging
    # split(incoming_file, os.path.join(output_file,'tmp_selfcal.ms'), datacolumn='corrected', field=fields)

    if chanbin > 0:
        chanaverage=True
    else:
        chanaverage=False
    mstransform(vis=incoming_file, outputvis=os.path.join(output_file,'tmp_selfcal.ms'), 
                field=fields, spw=spw, chanaverage=chanaverage, chanbin=chanbin,
                datacolumn='corrected')

    selfcal_file = os.path.join(output_file,'selfcal_solutions')
    if not os.path.exists(selfcal_file):
        os.mkdir(selfcal_file)
    image_file = os.path.join(output_file,'imaging')
    if not os.path.exists(image_file):
        os.mkdir(image_file)

    niter = 1000000
    image_pars = {'vis':os.path.join(output_file,'tmp_selfcal.ms'),
                'psfcutoff':psfcut,
                'pblimit':pbcut, 
                'gridder':'mosaic',
                'weighting':'briggs',
                'robust':0.5,
                'specmode':'mfs',
                'deconvolver':'hogbom',
                'imsize':imsize, 
                'cell':['3arcsec'], 
                'interactive':False,
                'phasecenter':phase_center,
                'mosweight':False,
                }

    caltables = []
    for i in range(len(selfcal_thresholds)):
        thresh = selfcal_thresholds[i]

        image_name = os.path.join(image_file,'selfcal{}_{}'.format(i,thresh))
        selfcal_name = os.path.join(selfcal_file,'selfcal{}_{}'.format(i,thresh))
        os.system('rm -r '+image_name+'*')

        image_pars['threshold'] = thresh
        tclean(imagename=image_name, niter=0, **image_pars)

        exportfits(image_name+'.pb', image_name+'.pb.fits', dropstokes=True,dropdeg=True)
        exportfits(image_name+'.psf', image_name+'.psf.fits', dropstokes=True,dropdeg=True)
        exportfits(image_name+'.image', image_name+'.dirty_image.fits', dropstokes=True,dropdeg=True)

        tclean(imagename=image_name, niter=niter, calcres=False, calcpsf=False, savemodel='modelcolumn', **image_pars)
        exportfits(image_name+'.image', image_name+'.{}_clean_image.fits'.format(thresh), dropstokes=True,dropdeg=True)

        rmtables(selfcal_name)
        gaincal(vis=image_pars['vis'],caltable=selfcal_name,
                combine='scan,field', 
                solint='int',refant=selfcal_refant,gaintype='G',calmode='p',
                gaintable=caltables,
                interp=['','nearest'])

        caltables.append(selfcal_name)
        applycal(vis=image_pars['vis'], gaintable=caltables, calwt=False)


    if os.path.exists(os.path.join(output_file,'source_selfcal.ms')):
        rmtables(os.path.join(output_file,'source_selfcal.ms'))
    if os.path.exists(os.path.join(output_file,'source_selfcal.ms.flagversions')):
        shutil.rmtree(os.path.join(output_file,'source_selfcal.ms.flagversions'))
    split(os.path.join(output_file,'tmp_selfcal.ms'), os.path.join(output_file,'source_selfcal.ms'), datacolumn='corrected')

    rmtables(os.path.join(output_file,'tmp_selfcal.ms'))
    if os.path.exists(os.path.join(output_file,'tmp_selfcal.ms.flagversions')):
        shutil.rmtree(os.path.join(output_file,'tmp_selfcal.ms.flagversions'))

    # Final image
    image_pars['vis'] = os.path.join(output_file,'source_selfcal.ms')
    image_name = os.path.join(image_file,'final')
    os.system('rm -r '+image_name+'*')
    tclean(imagename=image_name, niter=0, **image_pars)

    exportfits(image_name+'.pb', image_name+'.pb.fits', dropstokes=True,dropdeg=True)
    exportfits(image_name+'.psf', image_name+'.psf.fits', dropstokes=True,dropdeg=True)
    exportfits(image_name+'.image', image_name+'.dirty_image.fits', dropstokes=True,dropdeg=True)

    for thresh in final_thresholds:
        image_pars['threshold'] = thresh
        tclean(imagename=image_name, niter=niter, calcres=False, calcpsf=False, **image_pars)
        exportfits(image_name+'.image', image_name+'.{}_clean_image.fits'.format(thresh), dropstokes=True,dropdeg=True)


def snapshot_image(incoming_file, output_file, field,
                   size=[4000,4000], scale=3, weight='briggs 0.5',
                   niter=0, mgain=0.8, autothresh=3,
                   chgcenter=None):
    """for chgcenter: the format can be either '00h00m00.0s +00d00m00.0s'
    or '00:00:00.0 +00.00.00.0'.
    """

    if not os.path.exists(output_file):
        os.makedirs(output_file)

    if os.path.exists(os.path.join(output_file,'tmp_vis.ms')):
        rmtables(os.path.join(output_file,'tmp_vis.ms'))
    split(incoming_file, os.path.join(output_file,'tmp_vis.ms'), datacolumn='corrected', field=f'{field}')
    
    if chgcenter is not None:
        print(f"Calling chgcenter to {chgcenter}")
        call = f'chgcentre {output_file}/tmp_vis.ms {chgcenter}'
        os.system(call)

    call = f'wsclean -name {output_file}/snapshot_{field} -size {size[0]} {size[1]} -scale {scale}asec -niter {niter} -mgain {mgain} -auto-threshold {autothresh} -weight {weight} -channels-out 1 {output_file}/tmp_vis.ms'

    os.system(call)

    rmtables(os.path.join(output_file,'tmp_vis.ms'))

def all_snapshot_image(incoming_file, output_file,
                       size=[4000,4000], scale=3, weight='briggs 0.5',
                       niter=0, mgain=0.8, autothresh=3,
                       do_image=True, # Set to false to just make video...
                       do_animate=True, vmax=.1, vmin=0, pb=1.2*.21/4.6*180/np.pi*3600/2, videoname='video',
                       field_min=None, field_max=None,
                       chgcenter=None):

    tb.open(incoming_file)
    field_ids = np.unique(tb.getcol('FIELD_ID'))
    tb.close()

    if field_min is not None:
        field_ids = field_ids[field_ids>=field_min]
    if field_max is not None:
        field_ids = field_ids[field_ids<=field_max]

    files = []
    for i in field_ids:
        if do_image:
            print(f'\nField {i}')
            snapshot_image(incoming_file=incoming_file, output_file=output_file, field=i, size=size, scale=scale, weight=weight, niter=niter, mgain=mgain, autothresh=autothresh, chgcenter=chgcenter)
        files.append(os.path.join(output_file,f'snapshot_{i}-image.fits'))

    if do_animate:
        animate(files, save=os.path.join(output_file,videoname), pixscale=scale, pb=pb, vmax=vmax, vmin=vmin, figsize=(size[0]/500,size[1]/500))

def animate_selected(incoming_file, inds=[],
                     scale=3, vmax=.1, vmin=0,
                     pb=1.2*.21/4.6*180/np.pi*3600/2):

    files = [os.path.join(incoming_file,f'snapshot_{i}-image.fits') for i in inds]
    animate(files, save=os.path.join(incoming_file,f'video_snapshots{np.min(inds)}to{np.max(inds)}'), pixscale=scale, pb=pb, vmax=vmax, vmin=vmin, figsize=(16,8))

def snapshot_cube(incoming_file, output_file, field,
                   size=[4000,4000], scale=3, weight='briggs 0.5'):

    if not os.path.exists(output_file):
        os.makedirs(output_file)

    if os.path.exists(os.path.join(output_file,'tmp_vis.ms')):
        rmtables(os.path.join(output_file,'tmp_vis.ms'))
    split(incoming_file, os.path.join(output_file,'tmp_vis.ms'), datacolumn='corrected', field=f'{field}')
    
    call = f'wsclean -name {output_file}/snapshot_{field}_cube -size {size[0]} {size[1]} -scale {scale}asec -niter 0 -weight {weight} -channels-out 768 {output_file}/tmp_vis.ms'
    os.system(call)

    stitch_images_simple(os.path.join(output_file,f'snapshot_{field}_cube'),check_uniform_freqs=True, restfreq=1.42040575e9)

    rmtables(os.path.join(output_file,'tmp_vis.ms'))

    
