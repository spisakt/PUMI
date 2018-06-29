def bet_workflow(
        Robust=True,
        SinkDir=".",
        SinkTag="anat_preproc"):

    """
    Modified version of CPAC.anat_preproc.anat_preproc:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/anat_preproc/anat_preproc.html`


    Creates a brain extracted image and its mask from a T1w anatomical image.

    Workflow inputs:
        :param anat: The reoriented anatomical file.
        :param SinkDir:
        :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

    Workflow outputs:




        :return: bet_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """


    #This is a Nipype generator. Warning, here be dragons.
    #!/usr/bin/env python
    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['anat',
                                                          'opt_R']),
                        name='inputspec')
    inputspec.inputs.opt_R = Robust

    #Wraps command **bet**
    bet = pe.MapNode(interface=fsl.BET(),
                     iterfield=['in_file'],
                  name='bet')
    bet.inputs.mask=True
    #bet.inputs.robust=Robust

    #Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                           'brain_mask',
                                                           'skull']),
                         name = 'outputspec')

    #Save outputs which are important
    ds=pe.Node(interface=io.DataSink(),
               name='ds')
    ds.inputs.base_directory=SinkDir
    #ds.inputs.container=SinkDir+"anat"
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('betWorkflow') # The name here determine the folder of the workspace
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'anat', bet, 'in_file')
    analysisflow.connect(inputspec, 'opt_R', bet, 'robust')
    analysisflow.connect(bet, 'mask_file', outputspec, 'brain_mask')
    analysisflow.connect(bet, 'out_file', outputspec, 'brain')
    analysisflow.connect(bet, 'out_file', ds, 'bet_brain')
    analysisflow.connect(bet, 'mask_file', ds, 'bet_mask')
    analysisflow.connect(inputspec, 'anat', outputspec, 'skull')

    return analysisflow

