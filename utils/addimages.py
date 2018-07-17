def addimgs_workflow(numimgs=2,
                    SinkDir=".",
                    SinkTag="func_preproc",
                    WorkingDirectory="."):
    """


               `source: -`


               Add any number of images whic are in the same space. The input files must be NIFTI files.

               Workflow inputs:
                   :param any number of .nii(.gz) files.
                   :param SinkDir:
                   :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

               Workflow outputs:


                   :return: addimgs_workflow - workflow




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
    import nipype.interfaces.fsl as fsl


    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputs=[]
    for i in range(1, numimgs + 1):
        inputs.append("par" + str(i))


    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=inputs),
                        name='inputspec')
    # Add masks with FSL
    add_masks = pe.MapNode(fsl.ImageMaths(op_string=' -add'),
                         iterfield=inputs,
                         name="addimgs")

    outputspec = pe.Node(utility.IdentityInterface(fields=['added_imgs']),
                                    name='outputspec')
    # Create workflow
    analysisflow = nipype.Workflow('addimgsWorkflow')
    analysisflow.base_dir = '.'
    #connect
    analysisflow.connect(inputspec, inputs, add_masks, inputs)
    analysisflow.connect(add_masks, 'out_file', outputspec, 'added_imgs')


    return analysisflow
