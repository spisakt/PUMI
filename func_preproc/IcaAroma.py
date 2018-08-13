from nipype.interfaces.utility import Function

def extract_motionICs(aroma_dir):
    import numpy as np
    import os
    melmix = np.loadtxt(os.path.join(aroma_dir, 'melodic.ica', 'melodic_mix'))
    noiseidx = np.loadtxt(os.path.join(aroma_dir, 'classified_motion_ICs.txt'), delimiter=",")
    noiseidx = noiseidx - 1  # since python starts with zero
    noiseidx = [int(x) for x in noiseidx]
    motionICs = melmix[:, noiseidx]

    np.savetxt('motionICs.txt', motionICs)
    return os.path.join(os.getcwd(),'motionICs.txt')


def aroma_workflow(fwhm=0, # in mm
                SinkTag = "func_preproc", wf_name="ICA_AROMA"):

    """
   ICA AROMA method embedded into PUMI
   https://github.com/rhr-pruim/ICA-AROMA

    function input: fwhm: smoothing FWHM in mm. fwhm=0 means no smoothing

    Workflow inputs:
        :param mc_func: The reoriented and motion-corrected functional file.
        :param mc_params: motion parameters file from mcflirt
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow..

    Workflow outputs:




        :return: aroma_workflow - workflow

    Tamas Spisak
    tamas.spisak@uk-essen.de
    2018


    """
    from nipype.interfaces.fsl import ICA_AROMA
    import nipype.pipeline as pe
    from nipype.interfaces import utility
    import nipype.interfaces.io as io
    import PUMI.utils.QC as qc
    from nipype.interfaces.fsl import Smooth
    import os
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of the workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['mc_func',
                                                          'mc_par',
                                                          'fnirt_warp_file',
                                                          'mat_file',
                                                          'mask',
                                                          'qc_mask'
                                                          ]),
                            name='inputspec')

    # build the actual pipeline
    if fwhm != 0:
        smoother = pe.MapNode(interface=Smooth(fwhm=fwhm),
                              iterfield=['in_file'],
                              name="smoother")
    myqc_before = qc.timecourse2png("timeseries", tag="1_original")

    aroma = pe.MapNode(interface=ICA_AROMA(denoise_type='both'),
                       iterfield=['in_file',
                                  'motion_parameters',
                                  'mat_file',
                                  'fnirt_warp_file',
                                  'mask'],
                       name="ICA_AROMA")
    aroma.inputs.denoise_type = 'both'
    aroma.inputs.out_dir = 'AROMA_out'

    myqc_after_nonaggr = qc.timecourse2png("timeseries", tag="2_nonaggressive")
    myqc_after_aggr = qc.timecourse2png("timeseries", tag="3_aggressive")  # put these in the same QC dir

    getMotICs=pe.MapNode(interface=Function(input_names=['aroma_dir'],
                                            output_names=['motion_ICs'],
                                            function=extract_motionICs),
                         iterfield=['aroma_dir'],
                         name="get_motion_ICs")

    # Save outputs which are important
    ds_nii = pe.Node(interface=io.DataSink(),
                 name='ds_nii')
    ds_nii.inputs.base_directory = SinkDir
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    ds_txt = pe.Node(interface=io.DataSink(),
                     name='ds_txt')
    ds_txt.inputs.base_directory = SinkDir
    ds_txt.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".txt")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['aggr_denoised_file',
                                                           'nonaggr_denoised_file',
                                                           'motion_ICs',
                                                           'out_dir',
                                                           'fwhm']),
                         name='outputspec')
    outputspec.inputs.fwhm = fwhm

    analysisflow = pe.Workflow(name=wf_name)
    if fwhm != 0:
        analysisflow.connect(inputspec, 'mc_func', smoother, 'in_file')
        analysisflow.connect(smoother, 'smoothed_file', aroma, 'in_file')
        analysisflow.connect(smoother, 'smoothed_file', myqc_before, 'inputspec.func')
    else:
        analysisflow.connect(inputspec, 'mc_func', aroma, 'in_file')
        analysisflow.connect(inputspec, 'mc_func', myqc_before, 'inputspec.func')
    analysisflow.connect(inputspec, 'mc_par', aroma, 'motion_parameters')
    analysisflow.connect(inputspec, 'mat_file', aroma, 'mat_file')
    analysisflow.connect(inputspec, 'fnirt_warp_file', aroma, 'fnirt_warp_file')
    analysisflow.connect(inputspec, 'mask', aroma, 'mask')
    analysisflow.connect(aroma, 'out_dir', getMotICs, 'aroma_dir')
    analysisflow.connect(getMotICs, 'motion_ICs', ds_txt, 'motion_ICs')
    analysisflow.connect(aroma, 'aggr_denoised_file', ds_nii, 'AROMA_aggr_denoised')
    analysisflow.connect(aroma, 'nonaggr_denoised_file', ds_nii, 'AROMA_nonaggr_denoised')

    analysisflow.connect(inputspec, 'qc_mask', myqc_before, 'inputspec.mask')
    analysisflow.connect(aroma, 'aggr_denoised_file', myqc_after_aggr, 'inputspec.func')
    #analysisflow.connect(inputspec, 'qc_mask', myqc_after_aggr, 'inputspec.mask')
    analysisflow.connect(aroma, 'nonaggr_denoised_file', myqc_after_nonaggr, 'inputspec.func')
    #analysisflow.connect(inputspec, 'qc_mask', myqc_after_nonaggr, 'inputspec.mask')

    analysisflow.connect(aroma, 'aggr_denoised_file', outputspec, 'aggr_denoised_file')
    analysisflow.connect(aroma, 'nonaggr_denoised_file', outputspec, 'nonaggr_denoised_file')
    analysisflow.connect(aroma, 'out_dir', outputspec, 'out_dir')
    analysisflow.connect(getMotICs, 'motion_ICs', outputspec, 'motion_ICs')

    return analysisflow