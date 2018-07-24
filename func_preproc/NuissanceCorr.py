def nuissremov_workflow(SinkTag="func_preproc", wf_name="nuisance_correction"):
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
    import PUMI.utils.QC as qc
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
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

    myqc = qc.timecourse2png("timeseries", tag="020_nuiscorr")

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['out_file']),
                         name='outputspec')

    # save data out with Datasink
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir

    #TODO: qc timeseries before and after

    # Generate workflow
    analysisflow = nipype.Workflow(wf_name)
    analysisflow.connect(inputspec, 'in_file', nuisregression, 'in_file')
    analysisflow.connect(inputspec, 'design_file', nuisregression, 'design_file')
    analysisflow.connect(nuisregression, 'out_file', outputspec, 'out_file')
    analysisflow.connect(nuisregression, 'out_file', ds, 'func_nuiss_corrected')
    analysisflow.connect(nuisregression, 'out_file', myqc, 'inputspec.func')

    return analysisflow