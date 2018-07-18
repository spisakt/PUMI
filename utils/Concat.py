def concat_workflow(numconcat=2,
                    SinkDir=".",
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
    from nipype.interfaces.utility import Function


    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputs=[]
    for i in range(1, numconcat + 1):
        inputs.append("par" + str(i))

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=inputs),
                        name='inputspec')
    # Custom interface to concatenate separate noise design files
    concatenate = pe.MapNode(interface=Function(input_names=inputs,
                                             output_names='concat_file',
                                             function=utils_convert.concatenate),
                             iterfield=inputs,
                                name='concatenate')


    outputspec = pe.Node(utility.IdentityInterface(fields=['concat_file']),
                                    name='outputspec')
    # Create workflow
    analysisflow = nipype.Workflow('concatWorkflow')
    analysisflow.base_dir = '.'
    #connect
    for i in range(1, numconcat + 1):
        actparam = "par" + str(i)
        analysisflow.connect(inputspec, actparam, concatenate, actparam)

    #analysisflow.connect(inputspec, 'par1', concatenate, 'par1')
    #analysisflow.connect(inputspec, 'par2', concatenate, 'par2')
    analysisflow.connect(concatenate, 'concat_file', outputspec, 'concat_file')


    return analysisflow


