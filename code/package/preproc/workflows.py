#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from preproc import nodes
from nipype.pipeline.engine import Workflow


def write_graph(wf, wf_name, cfg):
    import os
    graph_types = ['orig', 'colored', 'exec']
    for graph in graph_types:
        filename = 'graph_{}_{}.dot'.format(wf_name, graph)
        filepath = os.path.join(cfg['paths']['output']['graphs'], filename)
        wf.write_graph(graph2use=graph, dotfilename=filepath)


def workflow_main(cfg):
    from preproc.workflows import workflow_l1analysis
    # create workflows:
    wf_main = Workflow(name='main')
    wf_main.base_dir = cfg['paths']['output']['work']
    wf_main.config = {
        'execution': {'stop_on_first_crash': True, 'hash_method': 'timestamp'},
        'logging': {'interface_level': 'INFO', 'workflow_level': 'INFO'}
    }
    regressors = ['correct_rejection']
    strategies = ['all', 'crossvalidate']
    masks = ['vis', 'hpc', 'mtl', 'mot']
    wf_subs = [
        workflow_l1analysis(cfg, mask=mask, regressor=regressor, strategy=strategy)
        for mask in masks
        for regressor in regressors
        for strategy in strategies
    ]
    infosource = nodes.node_infosource(cfg)
    selectfiles = nodes.node_selectfiles(cfg)
    susan = nodes.node_susan(cfg)
    trim = nodes.node_trim(cfg)
    datasink = nodes.node_datasink(cfg)
    wf_main.connect(infosource, 'subject_id', selectfiles, 'subject_id')
    wf_main.connect(selectfiles, 'func', susan, 'inputnode.in_files')
    wf_main.connect(selectfiles, 'mask', susan, 'inputnode.mask_file')
    wf_main.connect(susan, 'outputnode.smoothed_files', trim, 'in_file')
    wf_main.connect(susan, 'outputnode.smoothed_files', datasink, 'smooth')
    for wf in wf_subs:
        wf_main.connect(selectfiles, 'events', wf, 'subjectinfo.events')
        wf_main.connect(selectfiles, 'confounds', wf, 'subjectinfo.confounds')
        wf_main.connect(selectfiles, 'parc', wf, 'mask_binarize.in_file')
        wf_main.connect(trim, 'roi_file', wf, 'leaveoneout.data_func')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_contrasts.anat')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_roi_tmap_raw.bg_img')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_roi_tmap_mask.bg_img')
    # execute / test nodes when running in interactive mode:
    # if cfg['code_execution'] == 'interactive':
    #     selectfiles.inputs.subject_id = 'sub-01'
    #     selectfiles_results = selectfiles.run()
    #     selectfiles_results.outputs.get()
    return wf_main


def workflow_l1analysis(cfg, mask, regressor, strategy):
    mask_name = 'mask_' + mask
    mask_binarize = nodes.node_binarize(cfg[mask_name])
    subjectinfo = nodes.node_subjectinfo(cfg)
    leaveoneout = nodes.node_leaveoneout(cfg, strategy=strategy, regressor=regressor)
    l1model = nodes.node_l1model(cfg)
    l1design = nodes.node_l1design(cfg)
    l1estimate = nodes.node_l1estimate(cfg)
    l1contrasts = nodes.node_l1contrasts(cfg)
    thresh = nodes.node_thresh(cfg)
    plot_contrasts = nodes.node_plotcontrasts(cfg)
    plot_tmap_raw = nodes.node_plot_roi(cfg, name='tmap_raw')
    tmap_mask = nodes.node_tmap_mask(cfg)
    plot_tmap_mask = nodes.node_plot_roi(cfg, name='tmap_mask')
    num_voxels_tmap_mask = nodes.node_num_voxels(cfg, name='tmap_mask')
    tmap_mask_thresh = nodes.node_tmap_mask_thresh(cfg)
    plot_tmap_mask_thresh = nodes.node_plot_roi(cfg, name='tmap_mask_thresh')
    tmap_mask_thresh_bin = nodes.node_tmap_mask_thresh_bin(cfg)
    plot_tmap_mask_thresh_bin = nodes.node_plot_roi(cfg, name='tmap_mask_thresh_bin')
    num_voxels_tmap_mask_thresh_bin = nodes.node_num_voxels(cfg, name='tmap_mask_thresh_bin')
    datasink = nodes.node_datasink(cfg)
    # define workflow:
    wf_name = f"l1analysis_{mask}_{regressor}_{strategy}"
    wf = Workflow(name=wf_name)
    wf.connect(subjectinfo, 'subject_info', leaveoneout, 'subject_info')
    wf.connect(subjectinfo, 'event_names', leaveoneout, 'event_names')
    wf.connect(leaveoneout, 'subject_info', l1model, 'subject_info')
    wf.connect(leaveoneout, 'data_func', l1model, 'functional_runs')
    wf.connect(leaveoneout, 'contrasts', l1contrasts, 'contrasts')
    wf.connect(l1model, 'session_info', l1design, 'session_info')
    wf.connect(l1design, 'spm_mat_file', l1estimate, 'spm_mat_file')
    wf.connect(l1estimate, 'spm_mat_file', l1contrasts, 'spm_mat_file')
    wf.connect(l1estimate, 'beta_images', l1contrasts, 'beta_images')
    wf.connect(l1estimate, 'residual_image', l1contrasts, 'residual_image')
    wf.connect(l1contrasts, 'spmT_images', thresh, 'stat_image')
    wf.connect(l1contrasts, 'spm_mat_file', thresh, 'spm_mat_file')
    wf.connect(l1contrasts, 'spmT_images', plot_contrasts, 'stat_map')
    wf.connect(l1contrasts, 'spmT_images', plot_tmap_raw, 'roi_img')
    wf.connect(l1contrasts, 'spmT_images', tmap_mask, 'tmap')
    wf.connect(mask_binarize, 'binary_file', tmap_mask, 'mask')
    wf.connect(tmap_mask, 'out_path', plot_tmap_mask, 'roi_file')
    wf.connect(tmap_mask, 'out_path', tmap_mask_thresh, 'img')
    wf.connect(tmap_mask, 'out_path', num_voxels_tmap_mask, 'img')
    wf.connect(tmap_mask_thresh, 'out_path', plot_tmap_mask_thresh, 'roi_file')
    wf.connect(tmap_mask_thresh, 'out_path', tmap_mask_thresh_bin, 'img')
    wf.connect(tmap_mask_thresh_bin, 'out_path', plot_tmap_mask_thresh_bin, 'roi_file')
    wf.connect(tmap_mask_thresh_bin, 'out_path', num_voxels_tmap_mask_thresh_bin, 'img')
    # connect to datasink:
    wf.connect(mask_binarize, 'binary_file', datasink, f"{wf.name}.{mask_binarize.name}.@binary_file")
    wf.connect(l1estimate, 'beta_images', datasink, f"{wf.name}.estimates.@beta_images")
    wf.connect(l1estimate, 'residual_image', datasink, f"{wf.name}.estimates.@residual_image")
    wf.connect(l1contrasts, 'spm_mat_file', datasink, f"{wf.name}.contrasts.@spm_mat")
    wf.connect(l1contrasts, 'spmT_images', datasink, f"{wf.name}.contrasts.@spmT")
    wf.connect(l1contrasts, 'con_images', datasink, f"{wf.name}.contrasts.@con")
    wf.connect(plot_contrasts, 'out_path', datasink, f"{wf.name}.contrasts.@out_path")
    wf.connect(plot_tmap_raw, 'out_path', datasink, f"{wf.name}.tmap_raw.@out_path")
    wf.connect(tmap_mask, 'out_path', datasink, f"{wf.name}.tmap_mask.@out_path")
    wf.connect(num_voxels_tmap_mask, 'out_path', datasink, f"{wf.name}.num_voxels_tmap_mask.@out_path")
    wf.connect(tmap_mask_thresh, 'out_path', datasink, f"{wf.name}.tmap_mask_tresh.@out_path")
    wf.connect(tmap_mask_thresh_bin, 'out_path', datasink, f"{wf.name}.tmap_mask_thresh_bin.@out_path")
    wf.connect(num_voxels_tmap_mask_thresh_bin, 'out_path', datasink, f"{wf.name}.num_voxels_tmap_mask_thresh_bin.@out_path")
    wf.connect(thresh, 'thresholded_map', datasink, f"{wf.name}.thresh.@threshhold_map")
    wf.connect(thresh, 'pre_topo_fdr_map', datasink, f"{wf.name}.thresh.@pre_topo_fdr_map")
    return wf
