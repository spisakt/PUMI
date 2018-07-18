def nuissremov_workflow(SinkDir=".",
                        SinkTag="func_preproc",
                        WorkingDirectory="."):
    """
    The script uses the noise information to regress it out from the data.
   Workflow inputs:
        :param in_file: The reoriented an motion corrected functional data.
        :param desing_file: A matrix which contains all the nuissance regressor(motion+compcor noise+...).
        :param filter_all: To regress out all the columns of the desing matrix (default: True)
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

   Workflow outputs:


    :return: nuissremov_workflow


    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018

    """

    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io


    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['in_file',
                                                              'design_file']),
                        name='inputspec')

    # Perform the nuissance regression
    nuisregression=pe.MapNode(interface=fsl.FilterRegressor(filter_all=True),
                              iterfield=['design_file','in_file'],
                           name='nuisregression')

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['out_file']),
                         name='outputspec')

    # save data out with Datasink
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir

    # Generate workflow
    analysisflow = nipype.Workflow('nuissWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'in_file', nuisregression, 'in_file')
    analysisflow.connect(inputspec, 'design_file', nuisregression, 'design_file')
    analysisflow.connect(nuisregression, 'out_file', outputspec, 'func_out_file')
    analysisflow.connect(nuisregression, 'out_file', ds, 'func_nuiss_corrected')

    return analysisflow