def func2mni(wf_name='applywarpWorkflow', #TODO parametrize workflow name for all workflows
            SinkDir=".",
             SinkTag="func_preproc"
           ):

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
    import nipype.interfaces.io as io
    import copy, pprint
    from nipype.interfaces.ants import Registration

    fsldir = os.environ['FSLDIR']

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputspec=pe.Node(utility.IdentityInterface(fields=['func',
                                                        'linear_reg_mtrx',
                                                        'nonlinear_reg_mtrx',
                                                        'reference_brain']),
                                                name='inputspec')
    inputspec.inputs.reference_brain = fsldir + "/data/standard/MNI152_T1_2mm_brain.nii.gz"

    # apply transformation marticis
    applywarp = pe.MapNode(interface=fsl.ApplyWarp(),
                         iterfield=['in_file', 'ref_file','field_file','premat'],
                         name='applywarp')
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_std']),
                         name='outputspec')

    analysisflow = pe.Workflow(wf_name)
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'func', applywarp, 'in_file')
    analysisflow.connect(inputspec, 'linear_reg_mtrx', applywarp, 'premat')
    analysisflow.connect(inputspec, 'nonlinear_reg_mtrx', applywarp, 'field_file')
    analysisflow.connect(inputspec, 'reference_brain', applywarp, 'ref_file')
    analysisflow.connect(applywarp, 'out_file', outputspec, 'func_std')

    return analysisflow