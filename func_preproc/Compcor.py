def compcor_workflow(SinkDir=".",
                     SinkTag="func_preproc",
                     WorkingDirectory="."):
    """


               `source: -`


               Component based noise reduction method (Behzadi et al.,2007): Regressing out principal components from noise ROIs.
               Here the aCompCor is used.

               Workflow inputs:
                   :param func_aligned: The reoriented and realigned functional image.
                   :param mask_files: Mask files which determine ROI(s). The default mask is the
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

    QCDir = os.path.abspath(SinkDir + "/QC")
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)
    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func_aligned',
                                                          'mask_file']),
                        name='inputspec')

    # Calculate compcor files
    compcor=pe.MapNode(interface=cnf.ACompCor(pre_filter=False,header_prefix=""),
                       iterfield=['realigned_file','repetition_time','mask_files'],
                    name='compcor')

    # Custom interface wrapping function Float2Str
    func_str2float = pe.MapNode(interface=utils_convert.Str2Float,
                                iterfield=['str'],
                               name='func_str2float')
    # Drop first line of the Acompcor function output
    drop_firstline=pe.MapNode(interface=utils_convert.DropFirstLine,
               iterfield=['txt'],
               name='drop_firstline'
                )
    # Custom interface wrapping function TR
    TRvalue = pe.MapNode(interface=info_get.TR,
                         iterfield=['in_file'],
                      name='TRvalue')

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['components_file']),
                         name='outputspec')

    # save data out with Datasink
    ds_text = pe.Node(interface=io.DataSink(), name='ds_txt')
    ds_text.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".txt")]
    ds_text.inputs.base_directory = SinkDir

    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('compcorWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'func_aligned', compcor, 'realigned_file')
    analysisflow.connect(inputspec, 'func_aligned', TRvalue, 'in_file')
    analysisflow.connect(TRvalue, 'TR', func_str2float, 'str')
    analysisflow.connect(func_str2float, 'float', compcor, 'repetition_time')
    #analysisflow.connect(TRvalue, 'TR', compcor, 'repetition_time')
    analysisflow.connect(inputspec, 'mask_file', compcor, 'mask_files')
    analysisflow.connect(compcor, 'components_file',drop_firstline,'txt')
    analysisflow.connect(drop_firstline, 'droppedtxtfloat', outputspec, 'components_file')
    analysisflow.connect(compcor, 'components_file', ds_text, 'compcor_noise')

    return analysisflow