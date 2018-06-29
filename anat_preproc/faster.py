def fast_workflow(
            SinkDir=".",
            SinkTag="anat_preproc"
           ):
    """

     Modified version of CPAC.seg_preproc.seg_preproc

     `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/seg_preproc/seg_preproc.html`


        Do the segmentation of a brain extracted T1w image.


        Workflow inputs:
            :param anat: The brain extracted image, the output of the better_workflow.
            :param SinkDir:
            :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

        Workflow outputs:




            :return: fast_workflow - workflow




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
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain']),
                        name='inputspec')


    # Wraps command **fast**
    fast = pe.MapNode(interface=fsl.FAST(),
                      iterfield=['in_files'],
                      name='fast')
    fast.inputs.img_type = 1
    fast.inputs.segments = True
    fast.inputs.probability_maps = True
    fast.inputs.out_basename = 'fast_'


    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['probability_maps',
                                                           'mixeltype',
                                                           'partial_volume_files',
                                                           'partial_volume_map']),
                         name='outputspec')

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir

    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('fastWorkflow')
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'brain', fast, 'in_files')
    analysisflow.connect(fast, 'probability_maps', outputspec, 'probability_maps')
    analysisflow.connect(fast, 'mixeltype', outputspec, 'mixeltype')
    analysisflow.connect(fast, 'partial_volume_files', outputspec, 'partial_volume_files')
    analysisflow.connect(fast, 'partial_volume_map', outputspec, 'partial_volume_map')
    analysisflow.connect(fast, 'probability_maps', ds, 'fast.@probability_maps')

    return analysisflow
