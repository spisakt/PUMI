def transformlist(linear, nonlinear):
    return [nonlinear, linear]


def func2mni(stdreg, carpet_plot="", wf_name='func2mni', SinkTag="func_preproc"):

    """
    stdreg: either globals._RegType_.ANTS or globals._RegType_.FSL (do default value to make sure the user has to decide explicitly)

    Transaform 4D functional image to MNI space.

    carpet_plot: string specifying the tag parameter for carpet plot of the standardized MRI measurement
            (default is "": no carpet plot)
            if not "", inputs atlaslabels and confounds should be defined (it might work with defaults, though)

    Workflow inputs:
    :param func
    :param linear_reg_mtrx
    :param nonlinear_reg_mtrx
    :param reference_brain
    :param atlas (optional)
    :param confounds (optional)
    :param confound_names (optional)


    Workflow outputs:




        :return: anat2mni_workflow - workflow


        anat="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres.nii.gz",
                      brain="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres_brain.nii.gz",


    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """
    import os
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.ants as ants
    from nipype.interfaces.c3 import C3dAffineTool
    import PUMI.utils.globals as globals
    import PUMI.func_preproc.Onevol as onevol
    import PUMI.utils.QC as qc
    import nipype.interfaces.io as io
    from nipype.interfaces.utility import Function

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputspec=pe.Node(utility.IdentityInterface(fields=['func',
                                                        'anat', # only obligatory if stdreg==globals._RegType_.ANTS
                                                        'linear_reg_mtrx',
                                                        'nonlinear_reg_mtrx',
                                                        'reference_brain',
                                                        'atlas',
                                                        'confounds',
                                                        'confound_names']),
                                                name='inputspec')

    inputspec.inputs.atlas = globals._FSLDIR_ + '/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz'

    inputspec.inputs.reference_brain = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_brain.nii.gz"
    # TODO: does not work with the iterfiled definition for ref_file below:
    # TODO: it should be sepcified in a function argument, whether it shopuld be iterated
    #TODO_ready: ANTS
    #TODO: make resampling voxel size for func parametrizable

    # apply transformation martices
    if stdreg == globals._RegType_.FSL:
        applywarp = pe.MapNode(interface=fsl.ApplyWarp(interp="spline"),
                         iterfield=['in_file','field_file','premat'],
                         name='applywarp')
        myqc = qc.vol2png("func2mni", wf_name + "_FSL", overlayiterated=False)
    else: #ANTs
        # source file for C3dAffineToolmust not be 4D, so we extract the one example vol
        myonevol = onevol.onevol_workflow()
        # concat premat and ants transform
        bbr2ants = pe.MapNode(interface=C3dAffineTool(fsl2ras=True, itk_transform=True),
                              iterfield=['source_file', 'transform_file', 'reference_file'],  # output: 'itk_transform'
                              name="bbr2ants")
        #concat trfs into a list
        trflist = pe.MapNode(interface=Function(input_names=['linear', 'nonlinear'],
                                                output_names=['trflist'],
                                                function=transformlist),
                             iterfield=['linear', 'nonlinear'],
                             name="collect_trf")

        applywarp = pe.MapNode(interface=ants.ApplyTransforms(interpolation="BSpline", input_image_type=3),
                               iterfield=['input_image', 'transforms'],
                               name='applywarp')
        myqc = qc.vol2png("func2mni", wf_name + "_ANTS", overlayiterated=False)



    if carpet_plot:
        fmri_qc = qc.fMRI2QC("carpet_plots", tag=carpet_plot)

    outputspec = pe.Node(utility.IdentityInterface(fields=['func_std']),
                         name='outputspec')

    # Save outputs which are important
    ds_nii = pe.Node(interface=io.DataSink(),
                     name='ds_nii')
    ds_nii.inputs.base_directory = SinkDir
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$",  wf_name + ".nii.gz")]

    analysisflow = pe.Workflow(wf_name)
    analysisflow.base_dir = '.'
    if stdreg == globals._RegType_.FSL:
        analysisflow.connect(inputspec, 'func', applywarp, 'in_file')
        analysisflow.connect(inputspec, 'linear_reg_mtrx', applywarp, 'premat')
        analysisflow.connect(inputspec, 'nonlinear_reg_mtrx', applywarp, 'field_file')
        analysisflow.connect(inputspec, 'reference_brain', applywarp, 'ref_file')
        analysisflow.connect(applywarp, 'out_file', outputspec, 'func_std')
        analysisflow.connect(applywarp, 'out_file', myqc, 'inputspec.bg_image')
        analysisflow.connect(inputspec, 'reference_brain', myqc, 'inputspec.overlay_image')
        analysisflow.connect(applywarp, 'out_file', ds_nii, 'func2mni')
    else:  # ANTs
        analysisflow.connect(inputspec, 'func', myonevol, 'inputspec.func')
        analysisflow.connect(myonevol, 'outputspec.func1vol', bbr2ants, 'source_file')
        analysisflow.connect(inputspec, 'linear_reg_mtrx', bbr2ants, 'transform_file')
        analysisflow.connect(inputspec, 'anat', bbr2ants, 'reference_file')
        analysisflow.connect(bbr2ants, 'itk_transform', trflist, 'linear')
        analysisflow.connect(inputspec, 'nonlinear_reg_mtrx', trflist,'nonlinear')
        analysisflow.connect(trflist, 'trflist', applywarp, 'transforms')
        analysisflow.connect(inputspec, 'func', applywarp, 'input_image')
        analysisflow.connect(inputspec, 'reference_brain', applywarp, 'reference_image')

        analysisflow.connect(applywarp, 'output_image', outputspec, 'func_std')
        analysisflow.connect(applywarp, 'output_image', myqc, 'inputspec.bg_image')
        analysisflow.connect(inputspec, 'reference_brain', myqc, 'inputspec.overlay_image')
        analysisflow.connect(applywarp, 'output_image', ds_nii, 'func2mni')


    if carpet_plot:
        if stdreg == globals._RegType_.FSL:
            analysisflow.connect(applywarp, 'out_file', fmri_qc, 'inputspec.func')
        else:  # ANTs
            analysisflow.connect(applywarp, 'output_image', fmri_qc, 'inputspec.func')

        analysisflow.connect(inputspec, 'atlas', fmri_qc, 'inputspec.atlas')
        analysisflow.connect(inputspec, 'confounds', fmri_qc, 'inputspec.confounds')

    return analysisflow