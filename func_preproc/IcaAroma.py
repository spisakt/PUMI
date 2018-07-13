def aroma_workflow(SinkDir = ".",
                SinkTag = "func_preproc",
                WorkingDirectory="."):

    """
   ICA AROMA method embedded into PUMI
   https://github.com/rhr-pruim/ICA-AROMA

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
    import os

    QCDir = os.path.abspath(SinkDir + "/QC")
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)
    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of the workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['mc_func',
                                                          'mc_par',
                                                          'fnirt_warp_file',
                                                          'mat_file',
                                                          'mask'
                                                          ]),
                            name='inputspec')

    # build the actual pipeline
    aroma = pe.MapNode(interface=ICA_AROMA(denoise_type='both'),
                       iterfield=['in_file',
                                  'motion_parameters',
                                  'mat_file',
                                  'fnirt_warp_file',
                                  'mask',
                                  'out_dir'],
                       name="ICA_AROMA")
    aroma.inputs.denoise_type = 'both'
    aroma.inputs.out_dir = 'AROMA_out'

    # Save outputs which are important
    ds_nii = pe.Node(interface=io.DataSink(),
                 name='ds_nii')
    ds_nii.inputs.base_directory = SinkDir
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                  name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".png")]

    # Define outputs of the workflow
    # TODO inverted transformation matrix node is necessery
    outputspec = pe.Node(utility.IdentityInterface(fields=['aggr_denoised_file',
                                                           'nonaggr_denoised_file'
                                                           'out_dir']),
                         name='outputspec')

    analysisflow = pe.Workflow(name='AROMA')
    analysisflow.connect(inputspec, 'mc_func', aroma, 'in_file')
    analysisflow.connect(inputspec, 'mc_par', aroma, 'motion_parameters')
    analysisflow.connect(inputspec, 'mat_file', aroma, 'mat_file')
    analysisflow.connect(inputspec, 'fnirt_warp_file', aroma, 'fnirt_warp_file')
    analysisflow.connect(inputspec, 'mask', aroma, 'mask')
    analysisflow.connect(aroma, 'aggr_denoised_file', ds_nii, 'AROMA_aggr_denoised')
    analysisflow.connect(aroma, 'nonaggr_denoised_file', ds_nii, 'AROMA_nonaggr_denoised')

    return analysisflow