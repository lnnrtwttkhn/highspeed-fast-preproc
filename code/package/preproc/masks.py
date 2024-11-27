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
