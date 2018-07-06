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

    QCDir = os.path.abspath(SinkDir + "/QC")
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)
    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    fsldir = os.environ['FSLDIR']

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain']),
                        name='inputspec')


    # TODO: use prior probabilioty maps
    # Wraps command **fast**
    fast = pe.MapNode(interface=fsl.FAST(),
                      iterfield=['in_files'],
                      name='fast')
    fast.inputs.img_type = 1
    fast.inputs.segments = True
    fast.inputs.probability_maps = True
    fast.inputs.out_basename = 'fast_'

    # Create png images for quality check
    slicer = pe.MapNode(interface=fsl.Slicer(all_axial=True),
                        iterfield=['in_file'],
                        name='slicer')
    slicer.inputs.image_width = 5000
    slicer.inputs.out_file = "func2anat_subj"
    # set output all axial slices into one picture
    slicer.inputs.colour_map = fsldir + '/etc/luts/renderjet.lut'
    slicer.inputs.all_axial = True

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['probmap_csf',
                                                           'probmap_gm',
                                                           'probmap_wm',
                                                           'mixeltype',
                                                           'parvol_csf',
                                                           'parvol_gm',
                                                           'parvol_wm',
                                                           'partial_volume_map']),
                         name='outputspec')

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                 name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".png")]

    def pickindex(vec, i):
        #print "************************************************************************************************************************************************"
        #print vec
        #print i
        return [x[i] for x in vec]

    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('fastWorkflow')
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'brain', fast, 'in_files')
    #nalysisflow.connect(fast, 'probability_maps', outputspec, 'probability_maps')
    analysisflow.connect(fast, ('probability_maps', pickindex, 0), outputspec, 'probmap_csf')
    analysisflow.connect(fast, ('probability_maps', pickindex, 1), outputspec, 'probmap_gm')
    analysisflow.connect(fast, ('probability_maps', pickindex, 2), outputspec, 'probmap_wm')
    analysisflow.connect(fast, 'mixeltype', outputspec, 'mixeltype')
    #analysisflow.connect(fast, 'partial_volume_files', outputspec, 'partial_volume_files')
    analysisflow.connect(fast, ('partial_volume_files', pickindex, 0), outputspec, 'parvol_csf')
    analysisflow.connect(fast, ('partial_volume_files', pickindex, 0), outputspec, 'parvol_gm')
    analysisflow.connect(fast, ('partial_volume_files', pickindex, 0), outputspec, 'parvol_wm')
    analysisflow.connect(fast, 'partial_volume_map', outputspec, 'partial_volume_map')
    analysisflow.connect(fast, ('probability_maps', pickindex, 0), ds, 'fast_csf')
    analysisflow.connect(fast, ('probability_maps', pickindex, 1), ds, 'fast_gm')
    analysisflow.connect(fast, ('probability_maps', pickindex, 2), ds, 'fast_wm')

    analysisflow.connect(fast, 'partial_volume_map', slicer, 'in_file')
    analysisflow.connect(slicer, 'out_file', ds_qc, 'segmentation')

    return analysisflow
