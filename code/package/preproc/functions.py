#!/usr/bin/env python3
# # -*- coding: utf-8 -*-

import os
import warnings
import bids
import datalad.api as dl


def setup():
    cfg = config()
    cfg = set_environment(cfg)
    cfg = get_host(cfg)
    cfg = get_execution(cfg)
    cfg = get_subs(cfg)
    cfg = get_paths(cfg)
    cfg['time_repetition'] = get_time_repetition(cfg['paths']['bids'])
    cfg = setup_logger(cfg)
    cfg = get_job_template(cfg)
    cfg = write_cfg(cfg)
    return cfg


def get_time_repetition(path_bids):
    # time of repetition, in seconds:
    bids_layout = bids.BIDSLayout(root=path_bids)
    time_repetition = bids_layout.get_tr()
    return time_repetition


def config():
    cfg = {
        'project_name': 'highspeed-fast-preproc',
        'environment': {
            'FSLOUTPUTTYPE': 'NIFTI_GZ',
            'TF_CPP_MIN_LOG_LEVEL': '3',
            'MCR_INHIBIT_CTF_LOCK': '1',
        },
        'time_repetition': 1.25,
        'num_runs': 8,
        'selectfiles': {
            # when matching mutliple files, return them in sorted order.
            # (Nipype default value: True)
            'sort_filelist': True,
            'mem_mb': 100,
        },
        'mask_vis': {
            'name': 'mask_vis',
            'labels': [
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
            ],
            'mem_mb': 1000,
        },
        'mask_hpc': {
            'name': 'mask_hpc',
            'labels': [
                17, 53,  # left and right hippocampus
            ],
            'mem_mb': 1000,
        },
        'mask_mtl': {
            'name': 'mask_mtl',
            'labels': [
                17, 53,  # left and right hippocampus
                1016, 2016,  # parahippocampal
                1006, 2006,  # ctx-entorhinal
            ],
            'mem_mb': 1000,
        },
        'mask_mot': {
            'name': 'mask_mot',
            'labels': [
                1024, 2024,  # left and right gyrus precentralis
            ],
            'mem_mb': 1000,
        },
        'subjectinfo': {
            'events_spec': {
                'correct_rejection': {
                    'condition': 'oddball',
                    'target': 0,
                    'key_down': 0,
                },
                'hit': {
                    'condition': 'oddball',
                    'target': 1,
                    'key_down': 1,
                },
                'false_alarm': {
                    'condition': 'oddball',
                    'target': 0,
                    'key_down': 1,
                },
                'miss': {
                    'condition': 'oddball',
                    'target': 1,
                    'key_down': 0,
                },
            },
            # define confounds to include as regressors:
            'confounds_spec': [
                'trans',
                'rot',
                'a_comp_cor',
                'framewise_displacement',
            ],
            'mem_mb': 150,
        },
        'susan': {
            # name of workflow (default: susan_smooth)
            'name': 'susan',
            # inputnode.fwhm : fwhm for smoothing with SUSAN:
            'fwhm': 4,
            # set memory demand:
            'inputnode.mem_mb': 100,
            'median.mem_mb': 10000,
            'mask.mem_mb': 10000,
            'meanfunc2.mem_mb': 10000,
            'merge.mem_mb': 10000,
            'multi_inputs.mem_mb': 10000,
            'smooth.mem_mb': 12000,
            'outputnode.mem_mb': 100,
        },
        'l1model': {
            # mandatory input: high_pass_filter_cutoff (a float)
            # high-pass filter cutoff in secs.
            # common default: 128 secs
            'high_pass_filter_cutoff': 128,
            # mandatory input: input_units ('secs' or 'scans')
            # units of event onsets and durations (secs or scans).
            # output units are always in secs.
            'input_units': 'secs',
            # optional input: concatenate_runs (a boolean)
            # concatenate all runs to look like a single session.
            # (Nipype default value: False)
            'concatenate_runs': False,
            # optional input: output_units ('secs' or 'scans')
            # units of design event onsets and durations (secs or scans).
            # (Nipype default value: secs)
            'output_units': 'secs',
            # optional input: parameter_source ('SPM' or 'FSL' or 'AFNI' or 'FSFAST' or 'NIPY')
            # source of motion parameters
            # (Nipype default value: SPM)
            'parameter_source': 'SPM'
        },
        'l1design': {
            # mandatory input: bases (a dictionary with keys which are
            # 'hrf' or 'fourier' or 'fourier_han' or 'gamma' or 'fir'
            # and with values which are any value)
            # input: 'derivs': model HRF derivatives (2-element list)
            # No derivatives: [0,0], Time derivatives : [1,0], Time and Dispersion derivatives: [1,1]
            'bases': {'hrf': {'derivs': [0, 0]}},
            # mandatory input: timing_units ('secs' or 'scans')
            # units for specification of onsets.
            'timing_units': 'secs',
            # optional input: microtime_onset (a float)
            # the onset/time-bin in seconds for alignment (opt).
            # depends on slice-timing correction: if slice-timing correction was
            # performed in reference to middle slice (default in fMRIPrep),
            # it should be half of the microtime_resolution
            'microtime_onset': 8,
            # optional input: microtime_resolution (an integer)
            # number of time-bins per scan in secs (opt).
            # traditionally it's number of slices
            # with multi-band it's number of slices divided by multiband factor
            # e.g., with 64 slices and MB4, it's 16
            'microtime_resolution': 16,
            # optional input: model_serial_correlations ('AR(1)' or 'FAST' or 'none')
            # model serial correlations AR(1), FAST or none. FAST is available in SPM12.
            'model_serial_correlations': 'AR(1)',
            # memory demand:
            'mem_mb': 10000,
        },
        'l1estimate': {
            # mandatory input: estimation_method (a dictionary with keys which are 'Classical' or 'Bayesian2' or 'Bayesian'
            # and with values which are any value)
            # dictionary of either Classical: 1, Bayesian: 1, or Bayesian2: 1 (dict).
            'estimation_method': {'Classical': 1},
            # optional input: write_residuals (a boolean)
            # write individual residual images.
            'write_residuals': False,
            # memory demand:
            'mem_mb': 10000,
        },
        'l1contrasts': {
            # optional node input: overwrite previous results
            # the overwrite keyword arg forces a node to be rerun.
            'overwrite': True,
            # memory demand:
            'mem_mb': 10500,
        },
        'plot_contrasts': {
            # set expected thread and memory usage for the node:
            'mem_mb': 200,
        },
        'trim': {
            # note that the arguments are minimum index and size (not maximum index).
            # input: t_min (an integer (int or long)) flag: %d, position: 8
            't_min': 0,
            # input: t_size: (an integer (int or long)) flag: %d, position: 9
            't_size': -1,
            # input: output_type: ('NIFTI_PAIR' or 'NIFTI_PAIR_GZ' or 'NIFTI_GZ' or 'NIFTI')
            'output_type': 'NIFTI',
            # set memory demand:
            'mem_mb': 10000,
        },
        'thresh': {
            # mandatory input: contrast_index (an integer)
            # Which contrast in the SPM.mat to use.
            'contrast_index': 1,
            # optional input: height_threshold (a float)
            # value for initial thresholding (defining clusters).
            # (Nipype default value: 0.05)
            'height_threshold': 0.05,
            # optional input: height_threshold_type ('p-value' or 'stat')
            # Is the cluster forming threshold a stat value or p-value?.
            # (Nipype default value: p-value)
            'height_threshold_type': 'p-value',
            # optional input: extent_fdr_p_threshold (a float)
            # p threshold on FDR corrected cluster size probabilities.
            # (Nipype default value: 0.05)
            'extent_fdr_p_threshold': 0.05,
            # optional input: extent_threshold (an integer)
            # minimum cluster size in voxels.
            # (Nipype default value: 0)
            'extent_threshold': 0,
            # optional input: use_fwe_correction (a boolean)
            # whether to use FWE (Bonferroni) correction for initial threshold
            # (height_threshold_type has to be set to p-value).
            # (Nipype default value: True)
            'use_fwe_correction': True,
            # optional input: use_topo_fdr (a boolean)
            # whether to use FDR over cluster extent probabilities
            # (Nipype default value: True)
            'use_topo_fdr': True,
            # set expected memory usage for the node:
            'mem_mb': 10000,
        },
        'datasink': {
            # memory demand:
            'mem_mb': 50
        }
    }
    return cfg


def set_environment(cfg):
    # set the fsl output type environment variable:
    os.environ['FSLOUTPUTTYPE'] = cfg['environment']['FSLOUTPUTTYPE']
    # set the fsl subjects dir:
    os.environ['SUBJECTS_DIR'] = '/opt/software/freesurfer/7.4.1/subjects'
    # deal with nipype-related warnings:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = cfg['environment']['TF_CPP_MIN_LOG_LEVEL']
    # inhibit CTF lock:
    os.environ['MCR_INHIBIT_CTF_LOCK'] = cfg['environment']['MCR_INHIBIT_CTF_LOCK']
    # filter out warnings related to the numpy package:
    warnings.filterwarnings("ignore", message="numpy.dtype size changed*")
    warnings.filterwarnings("ignore", message="numpy.ufunc size changed*")
    return cfg


def get_host(cfg=None):
    from preproc.functions import log_event
    import sys
    import platform
    cfg['host_os'] = sys.platform
    cfg['host_name'] = platform.node()
    if cfg['host_os'] == 'darwin':
        if cfg['host_name'] == 'nrcd-osx-003854' or cfg['host_name'] == 'lip-osx-005509':
            cfg['host_id'] = 'lennart'
    elif cfg['host_os'] == 'linux' and cfg['host_name'] == 'master':
        cfg['host_id'] = 'tardis'
    else:
        cfg['host_id'] = 'unknown'
    log_event('host operating system: {}'.format(cfg['host_os']))
    log_event('host name: {}'.format(cfg['host_name']))
    log_event('host id: {}'.format(cfg['host_id']))
    return cfg


def get_execution(cfg):
    try:
        __file__
        cfg['code_execution'] = 'terminal'
    except NameError:
        cfg['code_execution'] = 'interactive'
    log_event('code execution: {}'.format(cfg['code_execution']))
    return cfg


def find_root(project_name):
    import os
    import random
    path_root = None
    roots = [os.getenv('PWD'), os.getcwd()]
    roots_project = [x for x in roots if project_name in x]
    roots_home = [x for x in roots_project if os.getenv('HOME') in x]
    path_root = random.choice(roots_home).split(project_name)[0] + project_name
    return path_root


def create_dir(directory):
    # create relevant output directories:
    import os
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_paths(cfg):
    import os
    import glob
    from itertools import chain
    from datetime import datetime
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_root = find_root(project_name=cfg['project_name'])
    fmriprep_subfolder = 'bold2t1w-init'
    paths = {
        'home': os.getenv('HOME'),
        'root': path_root,
        'bids': os.path.join('inputs', 'bids'),
        'fmriprep': os.path.join('inputs', 'fmriprep', fmriprep_subfolder),
        'outputs': os.path.join(path_root, 'outputs', fmriprep_subfolder)
    }
    # define output directories:
    paths_output = dict()
    paths_output['logs'] = os.path.join(paths['outputs'], 'logs', now)
    paths_output['work'] = os.path.join(paths['outputs'], 'work')
    paths_output['datasink'] = os.path.join(paths['outputs'], 'l1pipeline')
    paths_output['figures'] = os.path.join(paths['outputs'], 'figures')
    paths_output['masks'] = os.path.join(paths['outputs'], 'masks')
    paths_output['maskaverage'] = os.path.join(paths_output['work'], 'maskaverage')
    paths_output['graphs'] = os.path.join(paths['outputs'], 'graphs')
    paths_output['config'] = os.path.join(paths['outputs'], 'config')
    # define input files:
    file_anat = os.path.join('anat', '*preproc_T1w.nii.gz')
    file_func = os.path.join('ses-*', 'func', '*task-highspeed*space-T1w*preproc_bold.nii.gz')
    file_parc = os.path.join('ses-*', 'func', '*space-T1w*aparcaseg_dseg.nii.gz')
    file_mask = os.path.join('ses-*', 'func', '*task-highspeed*space-T1w*brain_mask.nii.gz')
    file_events = os.path.join('ses-*', 'func', '*task-highspeed*events.tsv')
    file_confounds = os.path.join('ses-*', 'func', '*task-highspeed*confounds_timeseries.tsv')
    # define templates paths:
    templates = dict()
    templates['anat'] = os.path.join(path_root, paths['fmriprep'], '{subject_id}', file_anat)
    templates['func'] = os.path.join(path_root, paths['fmriprep'], '{subject_id}', file_func)
    templates['parc'] = os.path.join(path_root, paths['fmriprep'], '{subject_id}', file_parc)
    templates['mask'] = os.path.join(path_root, paths['fmriprep'], '{subject_id}', file_mask)
    templates['events'] = os.path.join(path_root, paths['bids'], '{subject_id}', file_events)
    templates['confounds'] = os.path.join(path_root, paths['fmriprep'], '{subject_id}', file_confounds)
    # define data paths
    paths_input = dict()
    paths_input['anat'] = sorted(list(chain(*[glob.glob(os.path.join(paths['fmriprep'], x, file_anat)) for x in cfg['sub_list']])))
    paths_input['func'] = sorted(list(chain(*[glob.glob(os.path.join(paths['fmriprep'], x, file_func)) for x in cfg['sub_list']])))
    paths_input['parc'] = sorted(list(chain(*[glob.glob(os.path.join(paths['fmriprep'], x, file_parc)) for x in cfg['sub_list']])))
    paths_input['mask'] = sorted(list(chain(*[glob.glob(os.path.join(paths['fmriprep'], x, file_mask)) for x in cfg['sub_list']])))
    paths_input['events'] = sorted(list(chain(*[glob.glob(os.path.join(paths['bids'], x, file_events)) for x in cfg['sub_list']])))
    paths_input['confounds'] = sorted(list(chain(*[glob.glob(os.path.join(paths['fmriprep'], x, file_confounds)) for x in cfg['sub_list']])))
    paths_input['bids_json'] = sorted(
        glob.glob(os.path.join(paths['bids'], '*.json')) +
        list(chain(*[glob.glob(os.path.join(paths['bids'], x, 'ses-*', '*.json')) for x in cfg['sub_list']])) +
        list(chain(*[glob.glob(os.path.join(paths['bids'], x, 'ses-*', '*', '*.json')) for x in cfg['sub_list']]))
    )
    paths['output'] = paths_output
    paths['templates'] = templates
    paths['input'] = paths_input
    # define spm path:
    paths = get_spm(paths)
    # create output directories:
    for path in paths['output'].values():
        create_dir(path)
    cfg['paths'] = paths
    return cfg


def get_spm(paths):
    import os
    import sys
    import platform
    from nipype.interfaces import spm
    from nipype.interfaces.matlab import MatlabCommand
    if ('darwin' in sys.platform and platform.node() == 'lip-osx-005509'):
        paths['spm'] = os.path.join(paths['home'], 'tools', 'spm12')
        paths['matlab'] = '/Applications/MATLAB_R2021a.app/bin/matlab -nodesktop -nosplash'
        spm.SPMCommand.set_mlab_paths(paths=paths['spm'], matlab_cmd=paths['matlab'])
        MatlabCommand.set_default_paths(paths['spm'])
        MatlabCommand.set_default_matlab_cmd(paths['matlab'])
    elif 'linux' in sys.platform:
        paths['spm'] = '/home/mpib/wittkuhn/highspeed/highspeed-glm/tools/spm/spm12.simg'
        # dl.get(paths['spm'])
        singularity_cmd = 'singularity run -B /home/mpib/wittkuhn -B /mnt/beegfs/home/wittkuhn {}'.format(paths['spm'])
        singularity_spm = 'eval \$SPMMCRCMD'
        paths['matlab'] = ' '.join([singularity_cmd, singularity_spm])
        spm.SPMCommand.set_mlab_paths(matlab_cmd=paths['matlab'], use_mcr=True)
    else:
        sys.exit('Could not determine host!')
    log_event('using SPM version %s' % spm.SPMCommand().version)
    return paths


def get_data(cfg):
    dataset_root = dl.Dataset(cfg['paths']['root'])
    msg_success = ['notneeded', 'ok']
    for paths in cfg['paths']['input'].values():
        attempts = 0
        max_attempts = 10
        while attempts < max_attempts:
            try:
                msg = dataset_root.get(paths, jobs=48)
                assert all([y in msg_success for y in [x['status'] for x in msg]])
                break
            except AssertionError:
                attempts += 1


def check_datalad():
    import subprocess
    from preproc.functions import log_event
    process = subprocess.Popen(
        ['datalad', '--version'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    stdout, stderr = process.communicate()
    assert stderr == ''
    datalad_version = stdout.strip('\n')
    log_event('found installation of {}'.format(datalad_version))


def write_cfg(cfg):
    import os
    import json
    path_file = os.path.join(cfg['paths']['output']['config'], 'configuration.json')
    with open(path_file, 'w') as f:
        json.dump(cfg, f, sort_keys=True, indent=4, separators=(',', ': '))
    return cfg


def setup_logger(cfg):
    import os
    import time
    import logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    timestr = time.strftime("%Y-%m-%d-%H-%M-%S")
    path_log = os.path.join(cfg['paths']['output']['logs'], '%s.log' % timestr)
    logging.basicConfig(
        filename=path_log,
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S')
    log_event('setup logger at {}'.format(path_log))
    return cfg


def log_event(text):
    import logging
    print(text)
    logging.info(text)


def get_job_template(cfg):
    # define slurm cluster job template (needed when running on the cluster)
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
    """.format(cfg['paths']['output']['work'], cfg['paths']['output']['logs'], cfg['paths']['root'])
    cfg['job_template'] = job_template
    return cfg


def get_subs(cfg):
    # grab the list of subjects from the bids data set:
    # bids_layout = bids.BIDSLayout(root=cfg['paths']['bids'])
    # get all subject ids:
    num_subs = 13
    sub_list = ['sub-' + str(x).zfill(2) for x in range(1, num_subs + 1)]
    # remove sub-06 (incomplete data):
    sub_list.remove('sub-06')
    cfg['sub_list'] = sub_list
    return cfg


def replace_nan(regressor_values):
    # calculate the mean value of the regressor:
    mean_value = regressor_values.mean(skipna=True)
    # replace all values containing nan with the mean value:
    regressor_values[regressor_values.isnull()] = mean_value
    # return list of the regressor values:
    return list(regressor_values)


def get_confounds(confounds, confounds_spec):
    import pandas as pd
    # read the confounds file of the current run:
    run_confounds = pd.read_csv(confounds, sep="\t")
    # search for confounds of interest in the confounds data frame:
    regressor_names = [col for col in run_confounds.columns if any([conf in col for conf in confounds_spec])]
    # create a nested list with regressor values:
    regressors = [replace_nan(run_confounds[conf]) for conf in regressor_names]
    return regressors, regressor_names


def create_filename(file_path, text_to_append, new_extension=None):
    """
    Appends text before the first dot in the filename and optionally changes the extension.

    Parameters:
        file_path (str): The full path of the file.
        text_to_append (str): The text to append before the first dot.
        new_extension (str, optional): The new extension to use (e.g., ".jpg"). If None, retains the original extension.

    Returns:
        str: The new file path with the appended text and optionally a new extension.
    """
    # Extract directory and filename
    directory, filename = os.path.split(file_path)

    # Find the position of the first dot
    dot_index = filename.find(".")

    if dot_index != -1:
        # Insert text before the first dot
        name_part = filename[:dot_index]
        extension_part = filename[dot_index:] if not new_extension else new_extension
        new_filename = f"{name_part}_{text_to_append}{extension_part}"
    else:
        # No dot in filename, just append the text and handle the new extension
        name_part = filename
        extension_part = new_extension if new_extension else ''
        new_filename = f"{name_part}_{text_to_append}{extension_part}"

    # Return the new full path
    return new_filename


def get_events(events, events_spec):
    import pandas as pd
    import copy

    # read the events files of the current run:
    run_events = pd.read_csv(events, sep="\t")

    onsets = []
    durations = []
    event_names = []

    for event in events_spec:
        events_selected = copy.deepcopy(run_events)

        # select events based on critera specified in the events_spec:
        for key, value in events_spec[event].items():
            events_selected = events_selected.loc[events_selected[key] == value]

        # get onsets and durations of selected events as list:
        onset_list = events_selected['onset'].tolist()
        duration_list = events_selected['duration'].tolist()

        # only add to the onsets and durations list if event exists:
        if (onset_list != []) & (duration_list != []):
            event_names.append(event)
            onsets.append(onset_list)
            durations.append(duration_list)

    assert len(onsets) == len(durations) == len(event_names)

    return onsets, durations, event_names


def get_subjectinfo(events, confounds, cfg):

    # import libraries (needs to be done in the function):
    import copy
    from preproc.functions import get_events, get_confounds
    from nipype.interfaces.base import Bunch

    # check inputs:
    assert isinstance(cfg, dict), 'cfg is not a dict!'
    # get the specification of events and confounds:
    events_spec = copy.deepcopy(cfg['subjectinfo']['events_spec'])
    confounds_spec = copy.deepcopy(cfg['subjectinfo']['confounds_spec'])
    assert isinstance(events_spec, dict), 'events_spec is not a dict!'
    assert isinstance(confounds_spec, list), 'confounds_spec is not a list!'

    if cfg['code_execution'] == 'interactive':
        # load example data in interactive code execution mode:
        events = cfg['paths']['input']['events'][0]
        confounds = cfg['paths']['input']['confounds'][0]

    regressors, regressor_names = get_confounds(confounds, confounds_spec)
    onsets, durations, event_names = get_events(events, events_spec)

    # create a bunch for each run:
    subject_info = Bunch(
        conditions=event_names, onsets=onsets, durations=durations,
        regressor_names=regressor_names, regressors=regressors)

    return subject_info, event_names


def plot_stat_maps(anat, stat_map, thresh):
    """

    :param anat:
    :param stat_map:
    :param thresh:
    :return:
    """
    # import libraries (needed to be done in the function):
    from nilearn.plotting import plot_stat_map
    from os import path as op

    out_path = op.join(op.dirname(stat_map), 'contrast_thresh_%s.png' % thresh)
    plot_stat_map(
            stat_map, title=('Threshold: %s' % thresh),
            bg_img=anat, threshold=thresh, dim=-1, display_mode='ortho',
            output_file=out_path)

    return out_path


def leave_one_out(subject_info, event_names, data_func, interest, run=None):

    if run:
        # create new list with event_names of all runs except current run:
        event_names = [info for i, info in enumerate(event_names) if i != run]
        # create new list with subject info of all runs except current run:
        subject_info = [info for i, info in enumerate(subject_info) if i != run]
        # select all data func files that are task data:
        data_func = [file for file in data_func if 'task-highspeed' in file]
        # create new list with functional data of all runs except current run:
        data_func = [info for i, info in enumerate(data_func) if i != run]

    # get the number of event names for each run:
    num_events = [len(i) for i in event_names]
    # get all the event names with the maximum number of available events:
    max_events = event_names[num_events.index(max(num_events))]

    # create list of contrasts:
    contrast1 = (interest, 'T', max_events, [1 if interest in s else 0 for s in max_events])
    contrasts = [contrast1]

    # return the new lists
    return subject_info, data_func, contrasts




