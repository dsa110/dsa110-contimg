import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from matplotlib import animation

def animate(files, save=None, vmax=.1, vmin=0, pixscale=1, pb=None, figsize=(6,6)):
    """Animated video of image series on a uniform grid
    
    Pix scale should be in arcseconds
    pb should be None or a number of arcseconds
    """

    # Set up plots
    figure = plt.figure(figsize=figsize)
    title = plt.suptitle('')

    ax = plt.subplot(111)
    ax.set(xlabel='x-offset [arcmin]', ylabel='y-offset [arcmin]')
    ax.set(aspect='equal')

    image0 = fits.getdata(files[0])[0,0]
    ax0 = np.arange(image0.shape[0]+1)*pixscale/60
    ax0 -= np.ptp(ax0)/2
    ax1 = np.arange(image0.shape[1]+1)*pixscale/60
    ax1 -= np.ptp(ax1)/2

    grid = ax.pcolormesh(ax1,ax0,image0,cmap='inferno',vmin=vmin,vmax=vmax)
    if pb is not None:
        t = np.linspace(0,2.1*np.pi,10000)
        ax.plot(pb/60*np.sin(t),pb/60*np.cos(t),color='white',lw='2.5')

    nsteps = len(files)
    def animate(i):
        image = fits.getdata(files[i])[0,0]
        grid.set_array(image.ravel())

    anim = animation.FuncAnimation(figure,animate,frames=nsteps,interval=100,blit=False)
    if save != None:
        anim.save(save+'.mp4')

    plt.show()
    return anim
