#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from nipype.pipeline.engine import Node, MapNode
from nipype.interfaces.utility import Function


def node_settings(node, node_cfg):
    threads = 1
    mem_mb = node_cfg.get('mem_mb', 0)
    node.interface.num_threads = threads
    node.interface.mem_gb = mem_mb / 1000.0
    node.plugin_args = {'sbatch_args': f"--cpus-per-task={threads} --mem={mem_mb}MB", 'overwrite': True}
    return node


def node_infosource(cfg):
    from nipype.interfaces.utility import IdentityInterface
    # define the infosource node that collects the data:
    infosource = Node(IdentityInterface(fields=['subject_id']), name='infosource')
    # let the node iterate (parallelize) over all subjects:
    infosource.iterables = [('subject_id', cfg['sub_list'])]
    return infosource


def node_selectfiles(cfg):
    from preproc.nodes import node_settings
    from nipype.interfaces.io import SelectFiles
    selectfiles = Node(SelectFiles(cfg['paths']['templates']), name='selectfiles')
    # optional input: sort_filelist (a boolean)
    # when matching mutliple files, return them in sorted order.
    # (Nipype default value: True)
    selectfiles.inputs.sort_filelist = cfg['selectfiles']['sort_filelist']
    # configure general node settings:
    selectfiles = node_settings(node=selectfiles, node_cfg=cfg['selectfiles'])
    return selectfiles


def node_binarize(node_cfg):
    from nipype.interfaces.freesurfer import Binarize
    binarize = MapNode(interface=Binarize(), name='mask_binarize', iterfield=['in_file'])
    binarize.inputs.match = node_cfg['labels']
    binarize = node_settings(node=binarize, node_cfg=node_cfg)
    return binarize


def node_plot_roi(cfg, name):
    from preproc.plotting import get_plot_roi
    mem_mb = 1000
    plot_roi = MapNode(Function(
        input_names=['roi_img', 'bg_img', 'name', 'path_figures'],
        output_names=['out_path'],
        function=get_plot_roi,
    ),
        name='plot_roi_' + name,
        iterfield=['roi_img']
    )
    plot_roi.inputs.name = name
    plot_roi.inputs.path_figures = cfg['paths']['output']['figures']
    # set expected thread and memory usage for the node:
    plot_roi.interface.num_threads = 1
    plot_roi.interface.mem_gb = mem_mb / 1000
    plot_roi.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    plot_roi.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb), 'overwrite': True}
    return plot_roi


def node_tmap_mask(cfg):
    from preproc.masks import get_tmap_mask
    name = 'tmap_mask'
    mem_mb = 0.2
    tmap_mask = MapNode(Function(
        input_names=['tmap', 'mask', 'path_output'],
        output_names=['out_path'],
        function=get_tmap_mask,
    ),
        name=name,
        iterfield=['tmap', 'mask']
    )
    tmap_mask.path_output = cfg['paths']['output']['masks']
    # set expected thread and memory usage for the node:
    tmap_mask.interface.num_threads = 1
    tmap_mask.interface.mem_gb = mem_mb / 1000
    tmap_mask.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    tmap_mask.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb), 'overwrite': True}
    return tmap_mask


def node_tmap_mask_thresh(cfg):
    from preproc.masks import get_tmap_mask_thresh
    name = 'tmap_mask_thresh'
    mem_mb = 2000
    tmap_mask_tresh = MapNode(Function(
        input_names=['img', 'threshold', 'path_output'],
        output_names=['out_path'],
        function=get_tmap_mask_thresh,
    ),
        name=name,
        iterfield=['img']
    )
    tmap_mask_tresh.inputs.path_output = cfg['paths']['output']['masks']
    # define the threshold as an iterable:
    tmap_mask_tresh.iterables = ('threshold', [1, 2, 3, 4])
    # set expected thread and memory usage for the node:
    tmap_mask_tresh.interface.num_threads = 1
    tmap_mask_tresh.interface.mem_gb = mem_mb / 1000
    tmap_mask_tresh.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    tmap_mask_tresh.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb), 'overwrite': True}
    return tmap_mask_tresh


def node_tmap_mask_thresh_bin(cfg):
    from preproc.masks import get_tmap_mask_thresh_bin
    name = 'tmap_mask_thresh_bin'
    mem_mb = 2000
    tmap_mask_tresh_bin = MapNode(Function(
        input_names=['img', 'path_output'],
        output_names=['out_path'],
        function=get_tmap_mask_thresh_bin,
    ),
        name=name,
        iterfield=['img']
    )
    tmap_mask_tresh_bin.inputs.path_output = cfg['paths']['output']['masks']
    # set expected thread and memory usage for the node:
    tmap_mask_tresh_bin.interface.num_threads = 1
    tmap_mask_tresh_bin.interface.mem_gb = mem_mb / 1000
    tmap_mask_tresh_bin.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    tmap_mask_tresh_bin.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb), 'overwrite': True}
    return tmap_mask_tresh_bin


def node_num_voxels(cfg, name):
    from preproc.masks import get_num_voxels
    mem_mb = 2000
    num_voxels = MapNode(Function(
        input_names=['img', 'path_output'],
        output_names=['out_path'],
        function=get_num_voxels,
    ),
        name='num_voxels_' + name,
        iterfield=['img']
    )
    num_voxels.inputs.path_output = cfg['paths']['output']['masks']
    # set expected thread and memory usage for the node:
    num_voxels.interface.num_threads = 1
    num_voxels.interface.mem_gb = mem_mb / 1000
    num_voxels.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    num_voxels.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb), 'overwrite': True}
    return num_voxels


def node_subjectinfo(cfg):
    from preproc.functions import get_subjectinfo
    from nipype.interfaces.utility import Function
    from nipype.pipeline.engine import MapNode
    # define note with function to get participant-specific information:
    subjectinfo = MapNode(Function(
        input_names=['events', 'confounds', 'cfg'],
        output_names=['subject_info', 'event_names'],
        function=get_subjectinfo,
    ),
        name='subjectinfo',
        iterfield=['events', 'confounds']
    )
    # provide inputs for events specification:
    subjectinfo.inputs.cfg = cfg
    # set expected thread and memory usage for the node:
    subjectinfo.interface.num_threads = 1
    subjectinfo.interface.mem_gb = cfg['subjectinfo']['mem_mb'] / 1000
    subjectinfo.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    subjectinfo.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['subjectinfo']['mem_mb']), 'overwrite': True}
    return subjectinfo


def node_susan(cfg):
    # import the nipype susan workflow:
    from niflow.nipype1.workflows.fmri.fsl import create_susan_smooth
    # define the susan smoothing node:
    susan = create_susan_smooth()
    # set the name of the workflow:
    susan.name = cfg['susan']['name']
    # set the smoothing kernel:
    susan.inputs.inputnode.fwhm = cfg['susan']['fwhm']
    # set expected thread and memory usage for the nodes: 
    susan.get_node('inputnode').interface.num_threads = 1
    susan.get_node('inputnode').interface.mem_gb = cfg['susan']['inputnode.mem_mb'] / 1000
    susan.get_node('inputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('inputnode').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['inputnode.mem_mb']), 'overwrite': True}
    susan.get_node('median').interface.num_threads = 1
    susan.get_node('median').interface.mem_gb = cfg['susan']['median.mem_mb'] / 1000
    susan.get_node('median').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('median').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['median.mem_mb']), 'overwrite': True}
    susan.get_node('mask').interface.num_threads = 1
    susan.get_node('mask').interface.mem_gb = cfg['susan']['mask.mem_mb'] / 1000
    susan.get_node('mask').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('mask').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['mask.mem_mb']), 'overwrite': True}
    susan.get_node('meanfunc2').interface.num_threads = 1
    susan.get_node('meanfunc2').interface.mem_gb = cfg['susan']['meanfunc2.mem_mb'] / 1000
    susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['meanfunc2.mem_mb']), 'overwrite': True}
    susan.get_node('merge').interface.num_threads = 1
    susan.get_node('merge').interface.mem_gb = cfg['susan']['merge.mem_mb'] / 1000
    susan.get_node('merge').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('merge').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['merge.mem_mb']), 'overwrite': True}
    susan.get_node('multi_inputs').interface.num_threads = 1
    susan.get_node('multi_inputs').interface.mem_gb = cfg['susan']['multi_inputs.mem_mb']
    susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['multi_inputs.mem_mb']), 'overwrite': True}
    susan.get_node('smooth').interface.num_threads = 1
    susan.get_node('smooth').interface.mem_gb = cfg['susan']['smooth.mem_mb'] / 1000
    susan.get_node('smooth').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('smooth').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['smooth.mem_mb']), 'overwrite': True}
    susan.get_node('outputnode').interface.num_threads = 1
    susan.get_node('outputnode').interface.mem_gb = cfg['susan']['outputnode.mem_mb'] / 1000
    susan.get_node('outputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    susan.get_node('outputnode').plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['susan']['outputnode.mem_mb']), 'overwrite': True}
    return susan


def node_leaveoneout(cfg, strategy, regressor):
    from preproc.functions import leave_one_out
    from nipype.pipeline.engine import Node
    from nipype.interfaces.utility import Function
    # function: leave-one-out selection of data:
    leaveoneout = Node(Function(
        input_names=['subject_info', 'event_names', 'data_func', 'regressor', 'run'],
        output_names=['subject_info', 'data_func', 'contrasts'],
        function=leave_one_out),
        name='leaveoneout')
    # define the number of runs as an iterable:
    if strategy == 'crossvalidate':
        leaveoneout.iterables = ('run', range(cfg['num_runs']))
    # provide inputs for contrast specification:
    leaveoneout.inputs.regressor = regressor
    return leaveoneout


def node_mask_average(cfg):
    from zoo_glm.functions import mask_average
    from nipype.interfaces.utility import Function
    from nipype.pipeline.engine import Node
    # define note with function to get participant-specific information:
    maskaverage = Node(Function(
        input_names=['input_list', 'path_output'],
        output_names=['out_path'],
        function=mask_average,
    ),
        name='maskaverage'
    )
    maskaverage.inputs.path_output = cfg['paths']['output']['maskaverage']
    # set expected thread and memory usage for the node:
    maskaverage.interface.num_threads = 1
    maskaverage.interface.mem_gb = 1.0
    return maskaverage


def node_plotcontrasts(cfg):
    from preproc.functions import plot_stat_maps
    from nipype.pipeline.engine import MapNode
    from nipype.interfaces.utility import Function
    plot_contrasts = MapNode(Function(
        input_names=['anat', 'stat_map', 'thresh'],
        output_names=['out_path'],
        function=plot_stat_maps),
        name='plot_contrasts', iterfield=['thresh'])
    # input: plot data with set of different thresholds:
    plot_contrasts.inputs.thresh = [None, 1, 2, 3]
    # set expected thread and memory usage for the node:
    plot_contrasts.interface.num_threads = 1
    plot_contrasts.interface.mem_gb = cfg['plot_contrasts']['mem_mb'] / 1000
    plot_contrasts.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    plot_contrasts.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['plot_contrasts']['mem_mb']), 'overwrite': True}
    return plot_contrasts


def node_l1model(cfg):
    from nipype.pipeline.engine import Node
    from nipype.algorithms.modelgen import SpecifySPMModel
    # adds SPM specific options to SpecifyModel
    l1model = Node(SpecifySPMModel(), name='l1model')
    # input: concatenate runs to a single session (boolean, default: False):
    l1model.inputs.concatenate_runs = cfg['l1model']['concatenate_runs']
    # input: units of event onsets and durations (secs or scans):
    l1model.inputs.input_units = cfg['l1model']['input_units']
    # input: units of design event onsets and durations (secs or scans):
    l1model.inputs.output_units = cfg['l1model']['output_units']
    # input: time of repetition (a float):
    l1model.inputs.time_repetition = cfg['time_repetition']
    # high-pass filter cutoff in secs (a float, default = 128 secs):
    l1model.inputs.high_pass_filter_cutoff = cfg['l1model']['high_pass_filter_cutoff']
    l1model.inputs.parameter_source = cfg['l1model']['parameter_source']
    return l1model


def node_l1design(cfg):
    from nipype.pipeline.engine import Node
    from nipype.interfaces.spm.model import Level1Design
    # function: generate an SPM design matrix
    l1design = Node(Level1Design(), name="l1design")
    # input: (a dictionary with keys which are 'hrf' or 'fourier' or
    # 'fourier_han' or 'gamma' or 'fir' and with values which are any value)
    l1design.inputs.bases = cfg['l1design']['bases']
    # input: units for specification of onsets ('secs' or 'scans'):
    l1design.inputs.timing_units = cfg['l1design']['timing_units']
    # input: interscan interval / repetition time in secs (a float):
    l1design.inputs.interscan_interval = cfg['time_repetition']
    # optional input: microtime_resolution (an integer)
    # number of time-bins per scan in secs (opt).
    # traditionally it's number of slices
    # with multi-band it's number of slices divided by multiband factor
    # e.g., with 64 slices and MB4, it's 16
    l1design.inputs.microtime_resolution = int(cfg['num_slices'] / cfg['multiband_factor'])
    # optional input: microtime_onset (a float)
    # the onset/time-bin in seconds for alignment.
    # depends on slice-timing correction: if slice-timing correction was
    # performed in reference to middle slice (default in fMRIPrep),
    # it should be half of the microtime_resolution
    l1design.inputs.microtime_onset = float(cfg['num_slices'] / cfg['multiband_factor'] / 2)
    # input: Model serial correlations AR(1), FAST or none:
    l1design.inputs.model_serial_correlations = cfg['l1design']['model_serial_correlations']
    # set expected thread and memory usage for the node:
    l1design.interface.num_threads = 1
    l1design.interface.mem_gb = cfg['l1design']['mem_mb'] / 1000
    l1design.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    l1design.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['l1design']['mem_mb']), 'overwrite': True}
    return l1design


def node_l1estimate(cfg):
    from nipype.pipeline.engine import Node
    from nipype.interfaces.spm.model import EstimateModel
    # function: use spm_spm to estimate the parameters of a model
    l1estimate = Node(EstimateModel(), name="l1estimate")
    # input: (a dictionary with keys which are 'Classical' or 'Bayesian2'
    # or 'Bayesian' and with values which are any value)
    l1estimate.inputs.estimation_method = cfg['l1estimate']['estimation_method']
    l1estimate.inputs.write_residuals = cfg['l1estimate']['write_residuals']
    # set expected thread and memory usage for the node:
    l1estimate.interface.num_threads = 1
    l1estimate.interface.mem_gb = cfg['l1estimate']['mem_mb'] / 1000
    l1estimate.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    l1estimate.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['l1estimate']['mem_mb']), 'overwrite': True}
    return l1estimate


def node_l1contrasts(cfg):
    from nipype.pipeline.engine import Node
    from nipype.interfaces.spm.model import EstimateContrast
    # function: use spm_contrasts to estimate contrasts of interest:
    l1contrasts = Node(EstimateContrast(), name="l1contrasts")
    # input: list of contrasts with each contrast being a list of the form:
    # [('name', 'stat', [condition list], [weight list], [session list])]:
    # l1contrasts.inputs.contrasts = l1contrasts_list
    # node input: overwrite previous results:
    l1contrasts.overwrite = cfg['l1contrasts']['overwrite']
    # set expected thread and memory usage for the node:
    l1contrasts.interface.num_threads = 1
    l1contrasts.interface.mem_gb = cfg['l1contrasts']['mem_mb'] / 1000
    l1contrasts.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    l1contrasts.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['l1contrasts']['mem_mb']), 'overwrite': True}
    return l1contrasts


def node_trim(cfg):
    from nipype.interfaces.fsl.utils import ExtractROI
    # function: uses FSL Fslroi command to extract region of interest (ROI) from an image.
    # here we use it to remove dummy volumes (e.g., TRs at the beginning of a run)
    trim = MapNode(ExtractROI(), name='trim', iterfield=['in_file'])
    # define index of the first selected volume (i.e., minimum index):
    trim.inputs.t_min = cfg['trim']['t_min']
    # define the number of volumes selected starting at the minimum index:
    trim.inputs.t_size = cfg['trim']['t_size']
    # define the fsl output type:
    trim.inputs.output_type = cfg['trim']['output_type']
    # input: set the expected thread and memory usage for the node:
    trim.interface.num_threads = 1
    trim.interface.mem_gb = cfg['trim']['mem_mb'] / 1000
    trim.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    trim.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['trim']['mem_mb']), 'overwrite': True}
    return trim


def node_thresh(cfg):
    from nipype.pipeline.engine import Node
    from nipype.interfaces.spm.model import Threshold
    # function: topological FDR thresholding based on cluster extent/size.
    # smoothness is estimated from GLM residuals but is assumed to be the same for all of the voxels.
    thresh = Node(Threshold(), name="thresh")
    # input: whether to use FWE (Bonferroni) correction for initial threshold (a boolean, nipype default value: True):
    thresh.inputs.use_fwe_correction = cfg['thresh']['use_fwe_correction']
    # input: whether to use FDR over cluster extent probabilities (boolean)
    thresh.inputs.use_topo_fdr = cfg['thresh']['use_topo_fdr']
    # input: value for initial thresholding (defining clusters):
    thresh.inputs.height_threshold = cfg['thresh']['height_threshold']
    # input: is the cluster forming threshold a stat value or p-value?
    # ('p-value' or 'stat', nipype default value: p-value):
    thresh.inputs.height_threshold_type = cfg['thresh']['height_threshold_type']
    # input: which contrast in the SPM.mat to use (an integer):
    thresh.inputs.contrast_index = cfg['thresh']['contrast_index']
    # input: p threshold on FDR corrected cluster size probabilities (float):
    thresh.inputs.extent_fdr_p_threshold = cfg['thresh']['extent_fdr_p_threshold']
    # input: minimum cluster size in voxels (an integer, default = 0):
    thresh.inputs.extent_threshold = cfg['thresh']['extent_threshold']
    # input: set the expected thread and memory usage for the node:
    thresh.interface.num_threads = 1
    thresh.interface.mem_gb = cfg['thresh']['mem_mb'] / 1000
    thresh.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    thresh.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['thresh']['mem_mb']), 'overwrite': True}
    return thresh


def node_datasink(cfg):
    from nipype.interfaces.io import DataSink
    # function: create datasink node to handle the output stream:
    datasink = Node(DataSink(), name='datasink')
    # input: assign the path to the datasink directory:
    datasink.inputs.base_directory = cfg['paths']['output']['datasink']
    # create a list of substitutions to adjust the file paths of datasink:
    substitutions = [('_subject_id_', '')]
    # input: assign the substitutions to the datasink command:
    datasink.inputs.substitutions = substitutions
    # input: determine whether to store output in parameterized form:
    datasink.inputs.parameterization = True
    # input: set expected thread and memory usage for the node:
    datasink.interface.num_threads = 1
    datasink.interface.mem_gb = cfg['datasink']['mem_mb'] / 1000
    datasink.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
    datasink.plugin_args = {'sbatch_args': '--mem {}MB'.format(cfg['datasink']['mem_mb']), 'overwrite': True}
    return datasink
