import os
from casatools import linearmosaic

lm = linearmosaic()

# Define output image parameters.
# You can let linearmosaic infer output image parameters from one of the input images,
# or use defineoutputimage()/setoutputimage(). For simplicity, let's base it on field0:
#lm.setoutputimage("/data/jfaber/msdir/field_calib_split/mosaic_test/my_final_mosaic.image")  # Set the name of the output mosaic image
#lm.defineoutputimage(nx=3000, cellx='3arcsec', imagecenter='19h13m13.469 4d50m09.649', outputimage='test.linmos', outputweight='test.weightlinmos')
lm.setlinmostype('optimal')
#lm.defineoutputimage(nx=3000, ny=3000, cellx='1arcsec', celly='1arcsec', imagecenter='J2000 16h38m28.2058s +62d34m44.318s', \
#        outputimage='/data/jfaber/msdir/field_calib_split/stacked_24fields/test_opt.linmos', \
#        outputweight = '/data/jfaber/msdir/field_calib_split/stacked_24fields/test_opt.weightlinmos')
lm.defineoutputimage(nx=4800, ny=4800, cellx='3arcsec', celly='3arcsec', \
        imagecenter = 'J2000 01h34m00s 33d00m00s', #01h37m41.299431s 33d09m35.132990s', #set to calibrator coordinates
        outputimage='3C48_diry_nomodel_33_43.linmos', \
        outputweight = '3C48_dirty_nomodel_33_43.weightlinmos')

# Now combine the images. Provide the list of image and corresponding pb images:
#input_images = ["field0.image", "field1.image", "field2.image", "field3.image"]
#pb_images    = ["field0.pb",    "field1.pb",    "field2.pb",    "field3.pb"]

input_images = ['2024-11-02T06:33:15_ra022.328_dec+33.023_calib.mssource.image', '2024-11-02T06:38:24_ra023.618_dec+33.024_calib.mssource.image', '2024-11-02T06:43:34_ra024.908_dec+33.025_calib.mssource.image']
pb_images = ['2024-11-02T06:33:15_ra022.328_dec+33.023_calib.mssource.pb', '2024-11-02T06:38:24_ra023.618_dec+33.024_calib.mssource.pb', '2024-11-02T06:43:34_ra024.908_dec+33.025_calib.mssource.pb']

#path = "/data/jfaber/msdir/field/indiv_ms/mosaiced_images/"
#fields = os.listdir(path)
#files = os.listdir(path)

##for field in fields:
##    files = os.listdir(path + field + "/")
#for file in files:
#    if file.endswith('.image'):
#        #input_images.append(path + field + "/" + file)
#        input_images.append(path + file)
#    elif file.endswith('.pb'):
#        #pb_images.append(path + field + "/" + file)
#        pb_images.append(path + file)
#    else:
#        pass
#
print(input_images)
print(pb_images)

#input_image = '/data/jfaber/msdir/field/2024-11-02T06:33:15-06:48:43_ra022.328-026.198_dec+33.023-33.026_calib.source.image'
#pb_image = '/data/jfaber/msdir/field/2024-11-02T06:33:15-06:48:43_ra022.328-026.198_dec+33.023-33.026_calib.source.pb'

# Make the mosaic:
lm.makemosaic(images=input_images, weightimages=pb_images)
