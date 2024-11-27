#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def write_graph(wf, wf_name, cfg):
    import os
    graph_types = ['orig', 'colored', 'exec']
    for graph in graph_types:
        filename = 'graph_{}_{}.dot'.format(wf_name, graph)
        filepath = os.path.join(cfg['paths']['output']['graphs'], filename)
        wf.write_graph(graph2use=graph, dotfilename=filepath)


def workflow_main(cfg):
    from preproc import nodes
    from preproc.workflows import workflow_masks, workflow_l1analysis
    from preproc.workflows import write_graph
    from nipype.pipeline.engine import Workflow
    # create workflows:
    wf_main = Workflow(name='main')
    wf_main.base_dir = cfg['paths']['output']['work']
    wf_main.config = {
        'execution': {'stop_on_first_crash': True, 'hash_method': 'timestamp'},
        'logging': {'interface_level': 'INFO', 'workflow_level': 'INFO'}
    }
    regressor_of_interest = ['correct_rejection']
    strategy = ['all', 'crossvalidate']
    wf_subs = []
    for x in regressor_of_interest:
        for y in strategy:
            wf_subs.append(workflow_l1analysis(cfg, events_id=x, leave_out=y))
    infosource = nodes.node_infosource(cfg)
    selectfiles = nodes.node_selectfiles(cfg)
    susan = nodes.node_susan(cfg)
    trim = nodes.node_trim(cfg)
    mask_vis = nodes.node_binarize(cfg['mask_vis'])
    mask_hpc = nodes.node_binarize(cfg['mask_hpc'])
    mask_mtl = nodes.node_binarize(cfg['mask_mtl'])
    mask_mot = nodes.node_binarize(cfg['mask_mot'])
    datasink = nodes.node_datasink(cfg)
    wf_main.connect(infosource, 'subject_id', selectfiles, 'subject_id')
    wf_main.connect(selectfiles, 'func', susan, 'inputnode.in_files')
    wf_main.connect(selectfiles, 'mask', susan, 'inputnode.mask_file')
    wf_main.connect(susan, 'outputnode.smoothed_files', trim, 'in_file')
    wf_main.connect(susan, 'outputnode.smoothed_files', datasink, 'smooth')
    # add masksing workflow
    wf_main.connect(selectfiles, 'parc', mask_vis, 'in_file')
    wf_main.connect(selectfiles, 'parc', mask_hpc, 'in_file')
    wf_main.connect(selectfiles, 'parc', mask_mot, 'in_file')
    wf_main.connect(selectfiles, 'parc', mask_mtl, 'in_file')
    wf_main.connect(mask_vis, 'binary_file', datasink, 'mask_vis.@binary')
    wf_main.connect(mask_hpc, 'binary_file', datasink, 'mask_hpc.@binary')
    wf_main.connect(mask_mtl, 'binary_file', datasink, 'mask_mtl.@binary')
    wf_main.connect(mask_mot, 'binary_file', datasink, 'mask_mot.@binary')
    # add l1pipeline workflows
    for wf in wf_subs:
        #write_graph(wf=wf, wf_name=wf.name, cfg=cfg)
        wf_main.connect(selectfiles, 'events', wf, 'subjectinfo.events')
        wf_main.connect(selectfiles, 'confounds', wf, 'subjectinfo.confounds')
        wf_main.connect(trim, 'roi_file', wf, 'leaveoneout.data_func')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_contrasts.anat')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_tmap_raw.bg_img')
        wf_main.connect(mask_vis, 'binary', wf, 'tmap_mask.mask')
        wf_main.connect(selectfiles, 'anat', wf, 'plot_tmap_mask.bg_img')
    #    #maskaverage = nodes.node_mask_average(cfg)
        #l1pipeline.connect(selectfiles, 'mask_hpc', maskaverage, 'input_list')
        #l1pipeline.connect(maskaverage, 'out_path', l1analysis, 'l1design.mask_image')
    # execute / test nodes when running in interactive mode:
    #if cfg['code_execution'] == 'interactive':
    #    selectfiles.inputs.subject_id = 'sub-01'
    #    selectfiles_results = selectfiles.run()
    #    check_inputs(input_dict=selectfiles_results.outputs.get())
    #    subjectinfo_visual.inputs.events = selectfiles_results.outputs.events
    #    subjectinfo_visual.inputs.confounds = selectfiles_results.outputs.confounds
    #    subjectinfo_visual_results = subjectinfo_visual.run()
    #    subjectinfo_visual_results.outputs
    return wf_main


def workflow_l1analysis(cfg, events_id, leave_out):
    from preproc import nodes
    from nipype.pipeline.engine import Workflow
    # define nodes:
    subjectinfo = nodes.node_subjectinfo(cfg)
    leaveoneout = nodes.node_leaveoneout(cfg, leave_out, interest=events_id)
    l1model = nodes.node_l1model(cfg)
    l1design = nodes.node_l1design(cfg)
    l1estimate = nodes.node_l1estimate(cfg)
    l1contrasts = nodes.node_l1contrasts(cfg)
    thresh = nodes.node_thresh(cfg)
    plot_contrasts = nodes.node_plotcontrasts(cfg)
    plot_tmap_raw = nodes.node_plot_tmap_raw(cfg)
    tmap_mask = nodes.node_tmap_mask(cfg)
    plot_tmap_mask = nodes.node_plot_tmap_mask(cfg)
    datasink = nodes.node_datasink(cfg)
    # define workflow:
    wf = Workflow(name='l1analysis_{}_{}'.format(events_id, leave_out))
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
    wf.connect(tmap_mask, 'out_path', plot_tmap_mask, 'roi_file')
    # connect to datasink:
    wf.connect(l1estimate, 'beta_images', datasink, '{}.estimates.@beta_images'.format(wf.name))
    wf.connect(l1estimate, 'residual_image', datasink, '{}.estimates.@residual_image'.format(wf.name))
    wf.connect(l1contrasts, 'spm_mat_file', datasink, '{}.contrasts.@spm_mat'.format(wf.name))
    wf.connect(l1contrasts, 'spmT_images', datasink, '{}.contrasts.@spmT'.format(wf.name))
    wf.connect(l1contrasts, 'con_images', datasink, '{}.contrasts.@con'.format(wf.name))
    wf.connect(plot_contrasts, 'out_path', datasink, '{}.contrasts.@out_path'.format(wf.name))
    wf.connect(plot_tmap_raw, 'out_path', datasink, '{}.tmap_raw.@out_path'.format(wf.name))
    wf.connect(tmap_mask, 'out_path', datasink, '{}.tmap_mask.@out_path'.format(wf.name))
    wf.connect(thresh, 'thresholded_map', datasink, '{}.thresh.@threshhold_map'.format(wf.name))
    wf.connect(thresh, 'pre_topo_fdr_map', datasink, '{}.thresh.@pre_topo_fdr_map'.format(wf.name))
    return wf
