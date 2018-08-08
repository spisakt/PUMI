def fast_workflow(SinkTag="anat_preproc", wf_name="tissue_segmentation"):
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
    import PUMI.utils.QC as qc
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                           'stand2anat_xfm',
                                                           'priorprob'
                                                          # 'stand_csf',
                                                          # 'stand_gm',
                                                          # 'stand_wm'
                                                          ]),
                        name='inputspec')
    #TODO set standard mask to 2mm
    inputspec.inputs.priorprob=[globals._FSLDIR_ + '/MNI152_T1_2mm_VentricleMask.nii.gz',
                                globals._FSLDIR_ + '/MNI152_T1_2mm_VentricleMask.nii.gz',
                                globals._FSLDIR_ + '/MNI152_T1_2mm_VentricleMask.nii.gz']
    inputspec.inputs.stand2anat_xfm='/home/analyser/Documents/PAINTER/probewith2subj/preprocess_solvetodos/anat2mni_fsl/inv_linear_reg0_xfm/mapflow/_inv_linear_reg0_xfm0/anat_brain_flirt_inv.mat'
                                # globals._FSLDIR_ + '/data/standard/tissuepriors/avg152T1_gray.img',
                                # globals._FSLDIR_ + '/data/standard/tissuepriors/avg152T1_white.img']
    # inputspec.inputs.stand_csf=globals._FSLDIR_ + "/data/standard/tissuepriors/avg152T1_csf.hdr"
    # inputspec.inputs.stand_gm=globals._FSLDIR_ + "/data/standard/tissuepriors/avg152T1_gm.hdr"
    # inputspec.inputs.stand_wm=globals._FSLDIR_ + "/data/standard/tissuepriors/avg152T1_wm.hdr"
    # TODO: use prior probabilioty maps
    # Wraps command **fast**
    fast = pe.MapNode(interface=fsl.FAST(),
                      iterfield=['in_files',
                                 'init_transform'
                          # ,'other_priors'
                                 ],
                      name='fast')
    fast.inputs.img_type = 1
    fast.inputs.segments = True
    fast.inputs.probability_maps = True
    fast.inputs.out_basename = 'fast_'


    myqc = qc.vol2png("tissue_segmentation", overlay=False)
    myqc.inputs.slicer.colour_map = globals._FSLDIR_ + '/etc/luts/renderjet.lut'

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

    def pickindex(vec, i):
        #print "************************************************************************************************************************************************"
        #print vec
        #print i
        return [x[i] for x in vec]

    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'brain', fast, 'in_files')
    analysisflow.connect(inputspec, 'stand2anat_xfm',fast, 'init_transform ')
    # analysisflow.connect(inputspec, 'priorprob', fast,'other_priors')
    # analysisflow.connect(inputspec, 'stand_csf' ,fast,('other_priors', pickindex, 0))
    # analysisflow.connect(inputspec, 'stand_gm' ,fast,('other_priors', pickindex, 1))
    # analysisflow.connect(inputspec, 'stand_wm' ,fast,('other_priors', pickindex, 2))

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
    analysisflow.connect(fast, 'partial_volume_map', myqc, 'inputspec.bg_image')

    return analysisflow
