def func2mni(carpet_plot=None, wf_name='func2mni', SinkTag="func_preproc"):

    """
    Transaform 4D functional image to MNI space.

    carpet_plot: string specifying the tag parameter for carpet plot of the standardized MRI measurement
            (default is None: no carpet plot)
            if not None, inputs atlaslabels and confounds should be defined (it might work with defaults, though)

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
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputspec=pe.Node(utility.IdentityInterface(fields=['func',
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

    # apply transformation marticis
    applywarp = pe.MapNode(interface=fsl.ApplyWarp(),
                         iterfield=['in_file', 'ref_file','field_file','premat'],
                         name='applywarp')

    myqc = qc.vol2png("func2mni", "FSL")

    if carpet_plot:
        fmri_qc = qc.fMRI2QC("carpet_plots", tag=carpet_plot)

    outputspec = pe.Node(utility.IdentityInterface(fields=['func_std']),
                         name='outputspec')

    analysisflow = pe.Workflow(wf_name)
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'func', applywarp, 'in_file')
    analysisflow.connect(inputspec, 'linear_reg_mtrx', applywarp, 'premat')
    analysisflow.connect(inputspec, 'nonlinear_reg_mtrx', applywarp, 'field_file')
    analysisflow.connect(inputspec, 'reference_brain', applywarp, 'ref_file')
    analysisflow.connect(applywarp, 'out_file', outputspec, 'func_std')

    analysisflow.connect(applywarp, 'out_file', myqc, 'inputspec.bg_image')
    analysisflow.connect(inputspec, 'reference_brain', myqc, 'inputspec.overlay_image')

    if carpet_plot:
        analysisflow.connect(applywarp, 'out_file', fmri_qc, 'inputspec.func')
        analysisflow.connect(inputspec, 'atlas', fmri_qc, 'inputspec.atlas')
        analysisflow.connect(inputspec, 'confounds', fmri_qc, 'inputspec.confounds')

    return analysisflow