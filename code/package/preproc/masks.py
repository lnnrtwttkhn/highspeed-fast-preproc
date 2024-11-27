#!/usr/bin/env python3
# # -*- coding: utf-8 -*-


def get_tmap_mask(tmap, mask, path_output):
    import os
    from nilearn import image
    import numpy as np
    from preproc.functions import create_filename
    tmap_img = image.load_img(tmap)
    mask_img = image.load_img(mask)
    tmap_data = tmap_img.get_fdata().astype(float)
    mask_data = mask_img.get_fdata().astype(bool).astype(int)
    # save output:
    filename = create_filename(mask, 'tmaps_masked', 'nii.gz')
    out_path = os.path.join(path_output, filename)
    # multiply anatomical masks (ones and zeros) with tmap data (floats):
    tmap_data_masked = np.multiply(mask_data, tmap_data)
    tmap_data_masked_img = image.new_img_like(ref_niimg=tmap, data=tmap_data_masked)
    tmap_data_masked_img.to_filename(out_path)
    return out_path


def get_tmap_mask_thresh(img, threshold, path_output):
    import os
    from nilearn import image
    from preproc.functions import create_filename
    # save output:
    filename = create_filename(img, 'thresh', 'nii.gz')
    out_path = os.path.join(path_output, filename)
    # threshold the masked tmap image:
    tmap_img = image.load_img(img)
    tmaps_masked_thresh_img = image.threshold_img(img=tmap_img, threshold=threshold)
    tmaps_masked_thresh_img.to_filename(out_path)
    return out_path


def get_tmap_mask_thresh_bin(img, path_output):
    import os
    import numpy as np
    from nilearn import image
    from preproc.functions import create_filename
    # save output:
    filename = create_filename(img, 'binarized', 'nii.gz')
    out_path = os.path.join(path_output, filename)
    # extract data from the thresholded images
    tmaps_masked_thresh = image.load_img(img).get_fdata().astype(float)
    # replace all NaNs with 0:
    tmaps_masked_thresh_bin = np.where(np.isnan(tmaps_masked_thresh), 0, tmaps_masked_thresh)
    # replace all other values with 1:
    tmaps_masked_thresh_bin = np.where(tmaps_masked_thresh_bin > 0, 1, tmaps_masked_thresh_bin)
    # turn the 3D-array into booleans:
    tmaps_masked_thresh_bin = tmaps_masked_thresh_bin.astype(bool)
    # create image like object:
    tmaps_masked_thresh_bin_img = image.new_img_like(ref_niimg=img, data=tmaps_masked_thresh_bin)
    tmaps_masked_thresh_bin_img.to_filename(out_path)
    return out_path
