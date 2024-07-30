#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import glob
import random
from datetime import datetime
import bids
import datalad.api as dl
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.freesurfer import Binarize, MRIConvert
from nipype.interfaces.ants import ApplyTransforms
from nipype.pipeline.engine import Workflow, Node, MapNode
from niflow.nipype1.workflows.fmri.fsl import create_susan_smooth


def find_root(project_name):
    path_root = None
    roots = [os.getenv('PWD'), os.getcwd()]
    roots_project = [x for x in roots if project_name in x]
    roots_home = [x for x in roots_project if os.getenv('HOME') in x]
    path_root = random.choice(roots_home).split(project_name)[0] + project_name
    return path_root


now = datetime.now().strftime("%Y%m%d_%H%M%S")
os.environ['FSLOUTPUTTYPE'] = 'NIFTI_GZ'
os.environ['SUBJECTS_DIR'] = '/opt/software/freesurfer/6.0.0/subjects'

project_name = 'highspeed-fast-preproc'
path_root = find_root(project_name=project_name)
path_input = os.path.join(path_root, 'inputs')
path_bids = os.path.join(path_input, 'bids')
path_work = os.path.join(path_root, 'work')
path_logs = os.path.join(path_root, 'logs', now)
path_fmriprep = os.path.join(path_input, 'fmriprep')
path_freesurfer = os.path.join(path_input, 'fmriprep', 'sourcedata', 'freesurfer')
path_func = os.path.join(path_fmriprep, '*', '*', 'func')
path_parc = os.path.join(path_freesurfer, '*', 'mri')
path_anat = os.path.join(path_fmriprep, '*', 'anat')
path_temp_func = os.path.join(path_fmriprep, '{subject_id}', '*', 'func')
path_temp_freesurfer = os.path.join(path_freesurfer, '{subject_id}', 'mri')
path_temp_anat = os.path.join(path_fmriprep, '{subject_id}', 'anat')
path_output = os.path.join(path_root, 'preproc')
path_graphs = os.path.join(path_output, 'graphs')

for path in [path_work, path_logs, path_output, path_graphs]:
    if not os.path.exists(path):
        os.makedirs(path)

input_func = '*space-T1w*preproc_bold.nii.gz'
input_parc = 'aparc.a2009s+aseg.mgz'
input_mask = '*space-T1w*brain_mask.nii.gz'
input_trans = 'sub-*_rec-prenorm_from-fsnative_to-T1w_mode-image_xfm.txt'

if 'linux' in sys.platform:

    dl.get(glob.glob(os.path.join(path_bids, '*.json')), jobs=48)
    dl.get(glob.glob(os.path.join(path_bids, '*', '*', '*.json')), jobs=48)
    dl.get(glob.glob(os.path.join(path_bids, '*', '*', '*', '*.json')), jobs=48)

    dl.get(glob.glob(os.path.join(path_func, input_func)), jobs=48)
    dl.get(glob.glob(os.path.join(path_parc, input_parc)), jobs=48)
    dl.get(glob.glob(os.path.join(path_func, input_mask)), jobs=48)
    dl.get(glob.glob(os.path.join(path_anat, input_trans)), jobs=48)

templates = dict(
        input_func=os.path.join(path_temp_func, input_func),
        input_parc=os.path.join(path_temp_freesurfer, input_parc),
        input_mask=os.path.join(path_temp_func, input_mask),
        input_trans=os.path.join(path_temp_anat, input_trans)
)

job_template = """#!/bin/bash
#SBATCH --time 5:00:00
#SBATCH --mail-type NONE
#SBATCH --workdir {}
#SBATCH --output {}
source venv/bin/activate
module load fsl/5.0
module load freesurfer/6.0.0
module load ants/2.3.5-mpib0
""".format(path_work, path_logs)

bids_layout = bids.BIDSLayout(root=path_bids)
sub_list = ['sub-' + x for x in sorted(bids_layout.get_subjects())]
infosource = Node(IdentityInterface(fields=['subject_id']), name='infosource')
infosource.iterables = [('subject_id', sub_list)]

selectfiles = Node(SelectFiles(templates, sort_filelist=True), name='selectfiles')
selectfiles.interface.num_threads = 1
selectfiles.interface.mem_gb = 0.1
selectfiles.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
selectfiles.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

susan = create_susan_smooth()
susan.inputs.inputnode.fwhm = 4
susan.get_node('inputnode').interface.num_threads = 1
susan.get_node('inputnode').interface.mem_gb = 0.1
susan.get_node('inputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('inputnode').plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}
susan.get_node('median').interface.num_threads = 1
susan.get_node('median').interface.mem_gb = 2.5
susan.get_node('median').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('median').plugin_args = {'sbatch_args': '--mem 2500MB', 'overwrite': True}
susan.get_node('mask').interface.num_threads = 1
susan.get_node('mask').interface.mem_gb = 1
susan.get_node('mask').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('mask').plugin_args = {'sbatch_args': '--mem 1000MB', 'overwrite': True}
susan.get_node('meanfunc2').interface.num_threads = 1
susan.get_node('meanfunc2').interface.mem_gb = 2
susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('meanfunc2').plugin_args = {'sbatch_args': '--mem 2000MB', 'overwrite': True}
susan.get_node('merge').interface.num_threads = 1
susan.get_node('merge').interface.mem_gb = 3
susan.get_node('merge').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('merge').plugin_args = {'sbatch_args': '--mem 3000MB', 'overwrite': True}
susan.get_node('multi_inputs').interface.num_threads = 1
susan.get_node('multi_inputs').interface.mem_gb = 3
susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('multi_inputs').plugin_args = {'sbatch_args': '--mem 3000MB', 'overwrite': True}
susan.get_node('smooth').interface.num_threads = 1
susan.get_node('smooth').interface.mem_gb = 3
susan.get_node('smooth').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('smooth').plugin_args = {'sbatch_args': '--mem 3000MB', 'overwrite': True}
susan.get_node('outputnode').interface.num_threads = 1
susan.get_node('outputnode').interface.mem_gb = 0.1
susan.get_node('outputnode').plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
susan.get_node('outputnode').plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

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
mask_labels_hpc = [
    17, 53,  # left and right hippocampus
    ]
mask_labels_mot = [
    1024, 2024,  # left and right gyrus precentralis
    ]
mask_labels_mtl = [
    17, 53,  # left and right hippocampus
    1016, 2016,  # parahippocampal
    1006, 2006,  # ctx-entorhinal
]

mriconvert = Node(MRIConvert(), name='mriconvert')
mriconvert.inputs.out_type = 'niigz'
mriconvert.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mriconvert.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

mask_parc = MapNode(interface=ApplyTransforms(), name='mask_parc', iterfield=['reference_image'])
mask_parc.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_parc.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

mask_vis = MapNode(interface=Binarize(), name='mask_vis', iterfield=['in_file'])
mask_vis.inputs.match = mask_labels_vis
mask_vis.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_vis.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

mask_hpc = MapNode(interface=Binarize(), name='mask_hpc', iterfield=['in_file'])
mask_hpc.inputs.match = mask_labels_hpc
mask_hpc.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_hpc.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

mask_mot = MapNode(interface=Binarize(), name='mask_mot', iterfield=['in_file'])
mask_mot.inputs.match = mask_labels_mot
mask_mot.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_mot.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

mask_mtl = MapNode(interface=Binarize(), name='mask_mtl', iterfield=['in_file'])
mask_mtl.inputs.match = mask_labels_mtl
mask_mtl.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
mask_mtl.plugin_args = {'sbatch_args': '--mem 100MB', 'overwrite': True}

datasink = Node(DataSink(), name='datasink')
datasink.inputs.base_directory = path_output
substitutions = [('_subject_id_', '')]
datasink.inputs.substitutions = substitutions
datasink.inputs.parameterization = True
datasink.interface.num_threads = 1
datasink.interface.mem_gb = 0.05
datasink.plugin_args = {'sbatch_args': '--cpus-per-task 1', 'overwrite': True}
datasink.plugin_args = {'sbatch_args': '--mem 40MB', 'overwrite': True}

wf = Workflow(name='preproc')
wf.config = {'execution': {'stop_on_first_crash': True}}
wf.base_dir = os.path.join(path_root, 'work')
wf.connect(infosource, 'subject_id', selectfiles, 'subject_id')
wf.connect(selectfiles, 'input_func', susan, 'inputnode.in_files')
wf.connect(selectfiles, 'input_mask', susan, 'inputnode.mask_file')
wf.connect(susan, 'outputnode.smoothed_files', datasink, 'smooth')
wf.connect(selectfiles, 'input_parc', mriconvert, 'in_file')
wf.connect(mriconvert, 'out_file', mask_parc, 'input_image')
wf.connect(selectfiles, 'input_func', mask_parc, 'reference_image')
wf.connect(selectfiles, 'input_trans', mask_parc, 'transforms')
wf.connect(mask_parc, 'output_image', mask_vis, 'in_file')
wf.connect(mask_parc, 'output_image', mask_hpc, 'in_file')
wf.connect(mask_parc, 'output_image', mask_mot, 'in_file')
wf.connect(mask_parc, 'output_image', mask_mtl, 'in_file')
wf.connect(mriconvert, 'out_file', datasink, 'mriconvert')
wf.connect(mask_parc, 'output_image', datasink, 'mask_parc.@output_image')
wf.connect(mask_vis, 'binary_file', datasink, 'mask_vis.@binary')
wf.connect(mask_hpc, 'binary_file', datasink, 'mask_hpc.@binary')
wf.connect(mask_mot, 'binary_file', datasink, 'mask_mot.@binary')
wf.connect(mask_mtl, 'binary_file', datasink, 'mask_mtl.@binary')

wf.write_graph(graph2use='orig', dotfilename=os.path.join(path_graphs, 'graph_orig.dot'))
wf.write_graph(graph2use='colored', dotfilename=os.path.join(path_graphs, 'graph_colored.dot'))
wf.write_graph(graph2use='exec', dotfilename=os.path.join(path_graphs, 'graph_exec.dot'))

if 'darwin' in sys.platform:
    wf.run(plugin='MultiProc', plugin_args={'n_procs': 1})
elif 'linux' in sys.platform:
    wf.run(plugin='SLURM', plugin_args=dict(template=job_template))
