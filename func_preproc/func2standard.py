def func2mni(wf_name='func2mni', SinkTag="func_preproc"):

    """
    Modified version of CPAC.registration.registration:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/registration/registration.html`


    Register skull and brain extracted image to MNI space and return the transformation martices.

    Workflow inputs:
        :param skull: The reoriented anatomical file.
        :param brain: The brain extracted anat.
        :param ref_skull: MNI152 skull file.
        :param ref_brain: MNI152 brain file.
        :param ref_mask: CSF mask of the MNI152 file.
        :param fnirt config: Parameters which specifies FNIRT options.
        :param SinkDir:
        :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

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
                                                        'reference_brain']),
                                                name='inputspec')
    inputspec.inputs.reference_brain = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_brain.nii.gz"

    # apply transformation marticis
    applywarp = pe.MapNode(interface=fsl.ApplyWarp(),
                         iterfield=['in_file', 'ref_file','field_file','premat'],
                         name='applywarp')

    myqc = qc.vol2png("func2mni", "FSL")

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

    return analysisflow