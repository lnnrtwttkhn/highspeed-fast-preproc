#!/usr/bin/env python3
# # -*- coding: utf-8 -*-


def plot_roi(roi_img, bg_img, name, path_figures):
    import os
    from preproc.functions import create_filename
    filename = create_filename(roi_img, name, '.png')
    out_path = os.path.join(path_figures, filename)
    from nilearn import plotting
    plotting.plot_roi(
        roi_img=roi_img,
        bg_img=bg_img,
        output_file=out_path,
        title=filename,
        draw_cross=False,
        colorbar=True,
    )
    return out_path
