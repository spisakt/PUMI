def concat_workflow(SinkDir=".",
                     SinkTag="func_preproc",
                     WorkingDirectory="."):
    """


               `source: -`


               Concatenate any number of nuissance regressors in one txt file. Inputs should be 'txt' files.

               Workflow inputs:
                   :param any number of txt files.
                   :param SinkDir:
                   :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

               Workflow outputs:


                   :return: compcor_workflow - workflow




               Balint Kincses
               kincses.balint@med.u-szeged.hu
               2018


     """

    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.utils.utils_convert as utils_convert


    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)


    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['compcor',
                                                          'motion']),
                        name='inputspec')

    # Custom interface to concatenate separate noise design files
    concatenate = pe.Node(interface=utils_convert.Concatenate,
                                name='concatenate')


    outputspec = pe.Node(utility.IdentityInterface(fields=['noisedesign']),
                                    name='outputspec')

    # Create workflow
    analysisflow = nipype.Workflow('concatWorkflow')
    analysisflow.base_dir = '.'


