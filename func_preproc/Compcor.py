def compcor_workflow(SinkDir=".",
                     SinkTag="func_preproc",
                     WorkingDirectory="."):
    """


               `source: -`


               Component based noise reduction method (Behzadi et al.,2007): Regressing out principal components from noise ROIs.
               Here the aCompCor is used.

               Workflow inputs:
                   :param func_aligned: The reoriented and realigned functional image.
                   :param mask_files: Mask files which determine ROI(s).
                   :param components_file
                   :param num_componenets:
                   :param pre_filter: Detrend time series prior to component extraction.
                   :param TR
                   :param SinkDir:
                   :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

               Workflow outputs:




                   :return: slt_workflow - workflow




               Balint Kincses
               kincses.balint@med.u-szeged.hu
               2018


     """





    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.algorithms.confounds as cnf
    import PUMI.func_preproc.info.info_get as info_get
    import PUMI.utils.utils_convert as utils_convert
    import nipype.interfaces.io as io
    import nipype.interfaces.utility as utility


    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func_aligned',
                                                          'mask_file']),
                        name='inputspec')

    # Calculate compcor files
    compcor=pe.Node(cnf.ACompCor(pre_filter=False),
                    name='compcor')

    # Custom interface wrapping function Float2Str
    func_str2float = pe.Node(interface=utils_convert.Float2Str,
                               name='func_str2float')

    # Custom interface wrapping function TR
    TRvalue = pe.Node(interface=info_get.TR,
                      name='TRvalue')

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['components_file']),
                         name='outputspec')


    # Generic datasink module to store structured outputs
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir

    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('compcorWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'func_aligned', compcor, 'realigned_file')
    analysisflow.connect(inputspec, 'func_aligned', TRvalue, 'in_file')
    analysisflow.connect(TRvalue, 'TR', func_str2float, 'float')
    analysisflow.connect(func_str2float, 'float', compcor, 'repetition_time')
    analysisflow.connect(inputspec, 'mask_file', compcor, 'mask_files')
    analysisflow.connect(compcor, 'components_file', outputspec, 'components_file')


    return analysisflow