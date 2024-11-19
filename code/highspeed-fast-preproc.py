#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ======================================================================
# IMPORT RELEVANT PACKAGES
# ======================================================================
import os
import sys
import glob
import random
import warnings
from datetime import datetime
import bids
import datalad.api as dl
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline.engine import Workflow, Node, MapNode
from niflow.nipype1.workflows.fmri.fsl import create_susan_smooth
from nipype.interfaces.freesurfer import Binarize
from nipype.interfaces.fsl.utils import ExtractROI
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.interfaces.spm.model import \
    Level1Design, EstimateModel, EstimateContrast
from nipype.interfaces.matlab import MatlabCommand
from nipype.interfaces import spm
# ======================================================================
# ENVIRONMENT SETTINGS (DEALING WITH ERRORS AND WARNINGS):
# ======================================================================
# set the fsl output type environment variable:
os.environ['FSLOUTPUTTYPE'] = 'NIFTI_GZ'
# set the fsl subjects dir:
os.environ['SUBJECTS_DIR'] = '/opt/software/freesurfer/7.4.1/subjects'
# deal with nipype-related warnings:
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# inhibit CTF lock
os.environ['MCR_INHIBIT_CTF_LOCK'] = '1'
# filter out warnings related to the numpy package:
warnings.filterwarnings("ignore", message="numpy.dtype size changed*")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed*")
# ======================================================================
# CREATE FUNCTION TO FIND PROJECT ROOT:
# ======================================================================


def find_root(project_name):
    path_root = None
    roots = [os.getenv('PWD'), os.getcwd()]
    roots_project = [x for x in roots if project_name in x]
    roots_home = [x for x in roots_project if os.getenv('USER') in x]
    path_root = random.choice(roots_home).split(project_name)[0] + project_name
    return path_root


# ======================================================================
# SET PATHS AND SUBJECTS
# ======================================================================
now = datetime.now().strftime("%Y%m%d_%H%M%S")
project_name = 'highspeed-fast-preproc'
path_root = find_root(project_name=project_name)
path_input = os.path.join(path_root, 'inputs')
path_bids = os.path.join(path_input, 'bids')
path_work = os.path.join(path_root, 'work')
path_logs = os.path.join(path_root, 'logs', now)
path_fmriprep = os.path.join(path_input, 'fmriprep', 'bold2t1w-init')
path_func = os.path.join(path_fmriprep, '*', '*', 'func')
path_anat = os.path.join(path_fmriprep, '*', 'anat')
path_events = os.path.join(path_bids, '*', '*', 'func')
path_temp_func = os.path.join(path_fmriprep, '{subject_id}', '*', 'func')
path_temp_anat = os.path.join(path_fmriprep, '{subject_id}', 'anat')
path_temp_events = os.path.join(path_bids, '{subject_id}', '*', 'func')
path_output = os.path.join(path_root, 'outputs', 'bold2t1w-init')
path_graphs = os.path.join(path_output, 'graphs')
# ======================================================================
# SET PATH RELATED TO MATLAB AND SPM
# ======================================================================
if 'darwin' in sys.platform:
    path_spm = '/Users/Shared/spm12'
    path_matlab = '/Applications/MATLAB_R2021a.app/bin/matlab -nodesktop -nosplash'
    # set paths for spm:
    spm.SPMCommand.set_mlab_paths(paths=path_spm, matlab_cmd=path_matlab)
    MatlabCommand.set_default_paths(path_spm)
    MatlabCommand.set_default_matlab_cmd(path_matlab)
elif 'linux' in sys.platform:
    singularity_cmd = 'singularity run -B /home/mpib/wittkuhn -B /mnt/beegfs/home/wittkuhn /home/mpib/wittkuhn/highspeed/highspeed-glm/tools/spm/spm12.simg'
    singularity_spm = 'eval \$SPMMCRCMD'
    path_matlab = ' '.join([singularity_cmd, singularity_spm])
    spm.SPMCommand.set_mlab_paths(matlab_cmd=path_matlab, use_mcr=True)
# print the SPM version:
print('using SPM version %s' % spm.SPMCommand().version)
# ======================================================================
# CREATE RELEVANT OUTPUT DIRECTORIES
# ======================================================================
for path in [path_work, path_logs, path_output, path_graphs]:
    if not os.path.exists(path):
        os.makedirs(path)
# ======================================================================
# SPECIFY RELEVANT INPUT FILES:
# ======================================================================
input_func = '*space-T1w*preproc_bold.nii.gz'
input_parc = '*space-T1w*aparcaseg_dseg.nii.gz'
input_mask = '*space-T1w*brain_mask.nii.gz'
input_confounds = '*task-highspeed*confounds_timeseries.tsv'
input_events = '*task-highspeed*_events.tsv'
# ======================================================================
# GET DATA OF RELEVANT BIDS JSON FILES FOR BIDS LAYOUT:
# ======================================================================
dl.get(glob.glob(os.path.join(path_bids, '*.json')), jobs=48)
dl.get(glob.glob(os.path.join(path_bids, '*', '*', '*.json')), jobs=48)
dl.get(glob.glob(os.path.join(path_bids, '*', '*', '*', '*.json')), jobs=48)
# ======================================================================
# GET DATA (ON LINUX / HPC ENVIRONMENTS ONLY):
# ======================================================================
if 'linux' in sys.platform:
    dl.get(glob.glob(os.path.join(path_func, input_func)), jobs=48)
    dl.get(glob.glob(os.path.join(path_func, input_parc)), jobs=48)
    dl.get(glob.glob(os.path.join(path_func, input_mask)), jobs=48)
    dl.get(glob.glob(os.path.join(path_func, input_confounds)), jobs=48)
    dl.get(glob.glob(os.path.join(path_events, input_events)), jobs=48)
# ======================================================================
# CREATE FILE TEMPLATES FOR INFOSOURCE NODE:
# ======================================================================
templates = dict(
        input_func=os.path.join(path_temp_func, input_func),
        input_parc=os.path.join(path_temp_func, input_parc),
        input_mask=os.path.join(path_temp_func, input_mask),
        input_confounds=os.path.join(path_temp_func, input_confounds),
        input_events=os.path.join(path_temp_events, input_events)
)
# ======================================================================
# DEFINE SLURM CLUSTER JOB TEMPLATE (NEEDED WHEN RUNNING ON THE CLUSTER):
# ======================================================================
job_template = """#!/bin/bash -l
#SBATCH --time 10:00:00
#SBATCH --mail-type NONE
#SBATCH --chdir {}
#SBATCH --output {}
source {}/venv/bin/activate
module load fsl/6.0.5.1
module load freesurfer/7.4.1
module load ants/2.3.5-mpib0
module load matlab/R2017b
""".format(path_work, path_logs, path_root)
# ======================================================================
# MEMORY SETTINGS FOR EACH NODE
# ======================================================================
mem_mb = {
    'selectfiles': 100,
    'susan.inputnode': 100,
    'susan.median': 10000,
    'susan.mask': 10000,
    'susan.meanfunc2': 10000,
    'susan.merge': 10000,
    'susan.multi_inputs': 10000,
    'susan.smooth': 10000,
    'susan.outputnode': 100,
    'subject_info': 100,
    'trim': 10000,
    'l1design': 10000,
    'l1estimate': 10000,
    'l1contrasts': 10500,
    'mask_vis': 1000,
    'mask_hpc': 1000,
    'mask_mot': 1000,
    'mask_mtl': 1000,
    'datasink': 50
}
# ======================================================================
# GET SUBJECTS INPUTS:
# ======================================================================
# grab the list of subjects from the bids data set:
bids_layout = bids.BIDSLayout(root=path_bids)
# get all subject ids:
sub_list = ['sub-' + x for x in sorted(bids_layout.get_subjects())]
# remove sub-06 (incomplete data):
sub_list.remove('sub-06')
# ======================================================================
# DEFINE WORKFLOW PARAMETERS
# ======================================================================
# time of repetition, in seconds:
time_repetition = bids_layout.get_tr()
# total number of runs:
num_runs = 8
# smoothing kernel, in mm:
fwhm = 4
# number of dummy variables to remove from each run:
num_dummy = 0
# ======================================================================
# DEFINE NODE: INFOSOURCE
# ======================================================================
# define the infosource node that collects the data:
infosource = Node(IdentityInterface(fields=['subject_id']), name='infosource')
# let the node iterate (parallelize) over all subjects:
infosource.iterables = [('subject_id', sub_list)]
# ======================================================================
# DEFINE SELECTFILES NODE
# ======================================================================
selectfiles = Node(SelectFiles(templates, sort_filelist=True), name='selectfiles')
selectfiles.interface.num_threads = 1
selectfiles.interface.mem_gb = mem_mb['selectfiles'] / 1000
selectfiles.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
selectfiles.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['selectfiles']), 'overwrite': True}
# ======================================================================
# DEFINE CREATE_SUSAN_SMOOTH WORKFLOW NODE
# ======================================================================
susan = create_susan_smooth()
susan.inputs.inputnode.fwhm = fwhm
susan.get_node('inputnode').interface.num_threads = 1
susan.get_node('inputnode').interface.mem_gb = mem_mb['susan.inputnode'] / 1000
susan.get_node('inputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('inputnode').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.inputnode']), 'overwrite': True}
susan.get_node('median').interface.num_threads = 1
susan.get_node('median').interface.mem_gb = mem_mb['susan.inputnode'] / 1000
susan.get_node('median').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('median').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.median']), 'overwrite': True}
susan.get_node('mask').interface.num_threads = 1
susan.get_node('mask').interface.mem_gb = mem_mb['susan.mask'] / 1000
susan.get_node('mask').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('mask').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.mask']), 'overwrite': True}
susan.get_node('meanfunc2').interface.num_threads = 1
susan.get_node('meanfunc2').interface.mem_gb = mem_mb['susan.meanfunc2'] / 1000
susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.meanfunc2']), 'overwrite': True}
susan.get_node('merge').interface.num_threads = 1
susan.get_node('merge').interface.mem_gb = mem_mb['susan.merge'] / 1000
susan.get_node('merge').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('merge').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.merge']), 'overwrite': True}
susan.get_node('multi_inputs').interface.num_threads = 1
susan.get_node('multi_inputs').interface.mem_gb = mem_mb['susan.multi_inputs']
susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.multi_inputs']), 'overwrite': True}
susan.get_node('smooth').interface.num_threads = 1
susan.get_node('smooth').interface.mem_gb = mem_mb['susan.smooth'] / 1000
susan.get_node('smooth').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('smooth').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.smooth']), 'overwrite': True}
susan.get_node('outputnode').interface.num_threads = 1
susan.get_node('outputnode').interface.mem_gb = mem_mb['susan.outputnode'] / 1000
susan.get_node('outputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('outputnode').plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['susan.outputnode']), 'overwrite': True}
# ======================================================================
# DEFINE FUNCTION TO GET THE SUBJECT-SPECIFIC INFORMATION
# ======================================================================


def get_subject_info(events, confounds):
    """
    FUNCTION TO GET THE SUBJECT-SPECIFIC INFORMATION
    :param events: list with paths to events files
    :param confounds: list with paths to confounds files
    :return: Bunch object with event onsets, durations and regressors
    """

    # import libraries (needs to be done in the function):
    import pandas as pd
    from nipype.interfaces.base import Bunch

    # event types we consider:
    event_spec = {
        'correct_rejection': {'target': 0, 'key_down': 0},
        'hit': {'target': 1, 'key_down': 1},
        'false_alarm': {'target': 0, 'key_down': 1},
        'miss': {'target': 1, 'key_down': 0},
    }

    #event_names = ['correct_rejection']

    # read the events and confounds files of the current run:
    #events = selectfiles_results.outputs.events[0]
    #confounds = selectfiles_results.outputs.confounds[0]
    run_events = pd.read_csv(events, sep="\t")
    run_confounds = pd.read_csv(confounds, sep="\t")

    # define confounds to include as regressors:
    confounds = ['trans', 'rot', 'a_comp_cor', 'framewise_displacement']

    # search for confounds of interest in the confounds data frame:
    regressor_names = [col for col in run_confounds.columns if
                       any([conf in col for conf in confounds])]

    def replace_nan(regressor_values):
        # calculate the mean value of the regressor:
        mean_value = regressor_values.mean(skipna=True)
        # replace all values containing nan with the mean value:
        regressor_values[regressor_values.isnull()] = mean_value
        # return list of the regressor values:
        return list(regressor_values)

    # create a nested list with regressor values
    regressors = [replace_nan(run_confounds[conf]) for conf in regressor_names]

    onsets = []
    durations = []
    event_names = []

    for event in event_spec:

        onset_list = list(
            run_events['onset']
            [(run_events['condition'] == 'oddball') &
             (run_events['target'] == event_spec[event]['target']) &
             (run_events['key_down'] == event_spec[event]['key_down'])])

        duration_list = list(
            run_events['duration']
            [(run_events['condition'] == 'oddball') &
             (run_events['target'] == event_spec[event]['target']) &
             (run_events['key_down'] == event_spec[event]['key_down'])])

        if (onset_list != []) & (duration_list != []):
            event_names.append(event)
            onsets.append(onset_list)
            durations.append(duration_list)

    # create a bunch for each run:
    subject_info = Bunch(
        conditions=event_names, onsets=onsets, durations=durations,
        regressor_names=regressor_names, regressors=regressors)

    return subject_info, sorted(event_names)


# ======================================================================
# DEFINE NODE: FUNCTION TO GET THE SUBJECT-SPECIFIC INFORMATION
# ======================================================================
subject_info = MapNode(Function(
    input_names=['events', 'confounds'],
    output_names=['subject_info', 'event_names'],
    function=get_subject_info),
    name='subject_info', iterfield=['events', 'confounds'])
# set expected thread and memory usage for the node:
subject_info.interface.num_threads = 1
subject_info.interface.mem_gb = mem_mb['subject_info'] / 1000
subject_info.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
subject_info.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['subject_info']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: REMOVE DUMMY VARIABLES (USING FSL ROI)
# ======================================================================
# function: extract region of interest (ROI) from an image
trim = MapNode(ExtractROI(), name='trim', iterfield=['in_file'])
# define index of the first selected volume (i.e., minimum index):
trim.inputs.t_min = num_dummy
# define the number of volumes selected starting at the minimum index:
trim.inputs.t_size = -1
# define the fsl output type:
trim.inputs.output_type = 'NIFTI'
# set expected thread and memory usage for the node:
trim.interface.num_threads = 1
trim.interface.mem_gb = mem_mb['trim'] / 1000
trim.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
trim.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['trim']), 'overwrite': True}
# ======================================================================
# DEFINE FUNCTION TO PROCESS DATA LEAVE-ONE-RUN-OUT:
# ======================================================================


def leave_one_out(subject_info, event_names, data_func, run):
    """
    Select subsets of lists in leave-one-out fashion:
    :param subject_info: list of subject info bunch objects
    :param data_func: list of functional runs
    :param run: current run
    :return: return list of subject info and data excluding the current run
    """

    # create new list with event_names of all runs except current run:
    event_names = [info for i, info in enumerate(event_names) if i != run]
    num_events = [len(i) for i in event_names]
    max_events = event_names[num_events.index(max(num_events))]

    # create list of contrasts:
    stim = 'correct_rejection'
    contrast1 = (stim, 'T', max_events, [1 if stim in s else 0 for s in max_events])
    contrasts = [contrast1]

    # create new list with subject info of all runs except current run:
    subject_info = [info for i, info in enumerate(subject_info) if i != run]
    # select all data func files that are task data:
    data_func = [file for file in data_func if 'task-highspeed' in file]
    # create new list with functional data of all runs except current run:
    data_func = [info for i, info in enumerate(data_func) if i != run]

    # return the new lists
    return subject_info, data_func, contrasts


# ======================================================================
# DEFINE NODE: LEAVE-ONE-RUN-OUT SELECTION OF DATA
# ======================================================================
leave_one_run_out = Node(Function(
    input_names=['subject_info', 'event_names', 'data_func', 'run'],
    output_names=['subject_info', 'data_func', 'contrasts'],
    function=leave_one_out),
    name='leave_one_run_out')
# define the number of rows as an iterable:
leave_one_run_out.iterables = ('run', range(num_runs))
# ======================================================================
# DEFINE NODE: SPECIFY SPM MODEL (GENERATE SPM-SPECIFIC MODEL)
# ======================================================================
# function: makes a model specification compatible with spm designers
# adds SPM specific options to SpecifyModel
l1model = Node(SpecifySPMModel(), name="l1model")
# input: concatenate runs to a single session (boolean, default: False):
l1model.inputs.concatenate_runs = False
# input: units of event onsets and durations (secs or scans):
l1model.inputs.input_units = 'secs'
# input: units of design event onsets and durations (secs or scans):
l1model.inputs.output_units = 'secs'
# input: time of repetition (a float):
l1model.inputs.time_repetition = time_repetition
# high-pass filter cutoff in secs (a float, default = 128 secs):
l1model.inputs.high_pass_filter_cutoff = 128
# ======================================================================
# DEFINE NODE: LEVEL 1 DESIGN (GENERATE AN SPM DESIGN MATRIX)
# ======================================================================
# function: generate an SPM design matrix
l1design = Node(Level1Design(), name="l1design")
# input: (a dictionary with keys which are 'hrf' or 'fourier' or
# 'fourier_han' or 'gamma' or 'fir' and with values which are any value)
l1design.inputs.bases = {'hrf': {'derivs': [0, 0]}}
# input: units for specification of onsets ('secs' or 'scans'):
l1design.inputs.timing_units = 'secs'
# input: interscan interval / repetition time in secs (a float):
l1design.inputs.interscan_interval = time_repetition
# input: Model serial correlations AR(1), FAST or none:
l1design.inputs.model_serial_correlations = 'AR(1)'
# input: number of time-bins per scan in secs (an integer):
l1design.inputs.microtime_resolution = 16
# input: the onset/time-bin in seconds for alignment (a float):
l1design.inputs.microtime_onset = 8
# set expected thread and memory usage for the node:
l1design.interface.num_threads = 1
l1design.interface.mem_gb = mem_mb['l1design'] / 1000
l1design.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
l1design.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['l1design']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: ESTIMATE MODEL (ESTIMATE THE PARAMETERS OF THE MODEL)
# ======================================================================
# function: use spm_spm to estimate the parameters of a model
l1estimate = Node(EstimateModel(), name="l1estimate")
# input: (a dictionary with keys which are 'Classical' or 'Bayesian2'
# or 'Bayesian' and with values which are any value)
l1estimate.inputs.estimation_method = {'Classical': 1}
# set expected thread and memory usage for the node:
l1estimate.interface.num_threads = 1
l1estimate.interface.mem_gb = mem_mb['l1estimate'] / 1000
l1estimate.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
l1estimate.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['l1estimate']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: ESTIMATE CONTRASTS (ESTIMATES THE CONTRASTS)
# ======================================================================
# function: use spm_contrasts to estimate contrasts of interest
l1contrasts = Node(EstimateContrast(), name="l1contrasts")
# input: list of contrasts with each contrast being a list of the form:
# [('name', 'stat', [condition list], [weight list], [session list])]:
# l1contrasts.inputs.contrasts = l1contrasts_list
# node input: overwrite previous results:
l1contrasts.overwrite = True
# set expected thread and memory usage for the node:
l1contrasts.interface.num_threads = 1
l1contrasts.interface.mem_gb = mem_mb['l1contrasts'] / 1000
l1contrasts.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
l1contrasts.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['l1contrasts']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: CREATE ANATOMICAL MASK FOR VISUAL CORTEX
# ======================================================================
mask_labels_vis = [
    1005, 2005,  # cuneus
    1011, 2011,  # lateral occipital
    1021, 2021,  # pericalcarine
    1029, 2029,  # superioparietal
    1013, 2013,  # lingual
    1008, 2008,  # inferioparietal
    1007, 2007,  # fusiform
    1009, 2009,  # inferiotemporal
    1016, 2016,  # parahippocampal
    1015, 2015,  # middle temporal
]
mask_vis = MapNode(interface=Binarize(), name='mask_vis', iterfield=['in_file'])
mask_vis.inputs.match = mask_labels_vis
mask_vis.interface.mem_gb = mem_mb['mask_vis'] / 1000
mask_vis.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_vis.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['mask_vis']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: CREATE ANATOMICAL MASK FOR HIPPOCAMPUS
# ======================================================================
mask_labels_hpc = [
    17, 53,  # left and right hippocampus
]
mask_hpc = MapNode(interface=Binarize(), name='mask_hpc', iterfield=['in_file'])
mask_hpc.inputs.match = mask_labels_hpc
mask_hpc.interface.mem_gb = mem_mb['mask_hpc'] / 1000
mask_hpc.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_hpc.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['mask_hpc']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: CREATE ANATOMICAL MASK FOR MOTOR CORTEX
# ======================================================================
mask_labels_mot = [
    1024, 2024,  # left and right gyrus precentralis
    ]
mask_mot = MapNode(interface=Binarize(), name='mask_mot', iterfield=['in_file'])
mask_mot.inputs.match = mask_labels_mot
mask_mot.interface.mem_gb = mem_mb['mask_mot'] / 1000
mask_mot.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_mot.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['mask_mot']), 'overwrite': True}
# ======================================================================
# DEFINE NODE: CREATE ANATOMICAL MASK FOR MEDIAL TEMPORAL LOBE
# ======================================================================
mask_labels_mtl = [
    17, 53,  # left and right hippocampus
    1016, 2016,  # parahippocampal
    1006, 2006,  # ctx-entorhinal
]
mask_mtl = MapNode(interface=Binarize(), name='mask_mtl', iterfield=['in_file'])
mask_mtl.inputs.match = mask_labels_mtl
mask_mtl.interface.mem_gb = mem_mb['mask_mtl'] / 1000
mask_mtl.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_mtl.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['mask_mtl']), 'overwrite': True}
# ======================================================================
# CREATE DATASINK NODE (OUTPUT STREAM):
# ======================================================================
# create a node of the function:
datasink = Node(DataSink(), name='datasink')
# assign the path to the base directory:
datasink.inputs.base_directory = path_output
# create a list of substitutions to adjust the file paths of datasink:
substitutions = [('_subject_id_', '')]
# assign the substitutions to the datasink command:
datasink.inputs.substitutions = substitutions
# determine whether to store output in parameterized form:
datasink.inputs.parameterization = True
# set expected thread and memory usage for the node:
datasink.interface.num_threads = 1
datasink.interface.mem_gb = mem_mb['datasink'] / 1000
datasink.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
datasink.plugin_args = {'sbatch_args': '--mem {}MB'.format(mem_mb['datasink']), 'overwrite': True}
# ======================================================================
# DEFINE THE LEVEL 1 ANALYSIS SUB-WORKFLOW AND CONNECT THE NODES:
# ======================================================================
# initiation of the 1st-level analysis workflow:
l1analysis = Workflow(name='l1analysis')
# connect the 1st-level analysis components
l1analysis.connect(l1model, 'session_info', l1design, 'session_info')
l1analysis.connect(l1design, 'spm_mat_file', l1estimate, 'spm_mat_file')
l1analysis.connect(l1estimate, 'spm_mat_file', l1contrasts, 'spm_mat_file')
l1analysis.connect(l1estimate, 'beta_images', l1contrasts, 'beta_images')
l1analysis.connect(l1estimate, 'residual_image', l1contrasts, 'residual_image')
# ======================================================================
# DEFINE META-WORKFLOW PIPELINE:
# ======================================================================
wf = Workflow(name='preproc')
# stop execution of the workflow if an error is encountered:
wf.config = {'execution': {'stop_on_first_crash': True}}
# define the base directory of the workflow:
wf.base_dir = os.path.join(path_root, 'work')
# ======================================================================
# CONNECT WORKFLOW NODES:
# ======================================================================
# connect infosource to selectfiles node:
wf.connect(infosource, 'subject_id', selectfiles, 'subject_id')
# generate subject specific events and regressors to subject_info:
wf.connect(selectfiles, 'input_events', subject_info, 'events')
wf.connect(selectfiles, 'input_confounds', subject_info, 'confounds')
# connect functional files to smoothing workflow:
wf.connect(selectfiles, 'input_func', susan, 'inputnode.in_files')
wf.connect(selectfiles, 'input_mask', susan, 'inputnode.mask_file')
wf.connect(susan, 'outputnode.smoothed_files', datasink, 'smooth')
# connect smoothed functional data to the trimming node:
wf.connect(susan, 'outputnode.smoothed_files', trim, 'in_file')
# connect parcellated functional files to masking nodes:
wf.connect(selectfiles, 'input_parc', mask_vis, 'in_file')
wf.connect(selectfiles, 'input_parc', mask_hpc, 'in_file')
wf.connect(selectfiles, 'input_parc', mask_mot, 'in_file')
wf.connect(selectfiles, 'input_parc', mask_mtl, 'in_file')
wf.connect(mask_vis, 'binary_file', datasink, 'mask_vis.@binary')
wf.connect(mask_hpc, 'binary_file', datasink, 'mask_hpc.@binary')
wf.connect(mask_mot, 'binary_file', datasink, 'mask_mot.@binary')
wf.connect(mask_mtl, 'binary_file', datasink, 'mask_mtl.@binary')
# ======================================================================
# INPUT AND OUTPUT STREAM FOR THE LEVEL 1 SPM ANALYSIS SUB-WORKFLOW:
# ======================================================================
# connect regressors to the subsetting node::
wf.connect(subject_info, 'subject_info', leave_one_run_out, 'subject_info')
# connect event_names to the subsetting node:
wf.connect(subject_info, 'event_names', leave_one_run_out, 'event_names')
# connect smoothed and trimmed data to subsetting node:
wf.connect(trim, 'roi_file', leave_one_run_out, 'data_func')
# connect regressors to the level 1 model specification node:
wf.connect(leave_one_run_out, 'subject_info', l1analysis, 'l1model.subject_info')
# connect smoothed and trimmed data to the level 1 model specification:
wf.connect(leave_one_run_out, 'data_func', l1analysis, 'l1model.functional_runs')
# connect l1 contrast specification to contrast estimation
wf.connect(leave_one_run_out, 'contrasts', l1analysis, 'l1contrasts.contrasts')
# connect all output results of the level 1 analysis to the datasink:
wf.connect(l1analysis, 'l1estimate.beta_images', datasink, 'estimates.@beta_images')
wf.connect(l1analysis, 'l1estimate.residual_image', datasink, 'estimates.@residual_image')
wf.connect(l1analysis, 'l1contrasts.spm_mat_file', datasink, 'contrasts.@spm_mat')
wf.connect(l1analysis, 'l1contrasts.spmT_images', datasink, 'contrasts.@spmT')
wf.connect(l1analysis, 'l1contrasts.con_images', datasink, 'contrasts.@con')
# ======================================================================
# WRITE GRAPH AND EXECUTE THE WORKFLOW
# ======================================================================
# write the graph:
wf.write_graph(graph2use='orig', dotfilename=os.path.join(path_graphs, 'graph_orig.dot'))
wf.write_graph(graph2use='colored', dotfilename=os.path.join(path_graphs, 'graph_colored.dot'))
wf.write_graph(graph2use='exec', dotfilename=os.path.join(path_graphs, 'graph_exec.dot'))
# execute the workflow depending on the operating system:
if 'darwin' in sys.platform:
    wf.run(plugin='MultiProc', plugin_args={'n_procs': 1})
elif 'linux' in sys.platform:
    wf.run(plugin='SLURM', plugin_args=dict(template=job_template))
