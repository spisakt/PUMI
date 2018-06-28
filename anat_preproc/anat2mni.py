def anat2mni_workflow(
                      SinkDir=".",
                      SinkTag="anat_preproc"
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


    # Define inputs of workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                          'skull',
                                                          'reference_brain',
                                                          'reference_skull',
                                                          'ref_mask',
                                                          'fnirt_config']),
                        name='inputspec')
    #inputspec.inputs.brain=brain
    #inputspec.inputs.skull=anat
    #TODO ask for FSLDIR
    inputspec.inputs.reference_brain="/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm_brain.nii.gz"
    inputspec.inputs.reference_skull="/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm.nii.gz"
    inputspec.inputs.ref_mask="/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm_brain_mask_dil.nii.gz"
    inputspec.inputs.fnirt_config = "T1_2_MNI152_2mm"


    # Linear registration node
    linear_reg = pe.Node(interface=fsl.FLIRT(),
                         name='linear_reg_0')
    linear_reg.inputs.cost = 'corratio'

    # Non-linear registration node
    nonlinear_reg = pe.Node(interface=fsl.FNIRT(),
                            name='nonlinear_reg_1')
    nonlinear_reg.inputs.fieldcoeff_file = True
    nonlinear_reg.inputs.jacobian_file = True

    # Applying warp field
    brain_warp = pe.Node(interface=fsl.ApplyWarp(),
                         name='brain_warp')

    # Calculate the invers of the linear transformation
    inv_flirt_xfm = pe.Node(interface=fsl.utils.ConvertXFM(),
                            name='inv_linear_reg0_xfm')
    inv_flirt_xfm.inputs.invert_xfm = True

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'field_file']),
                         name='outputspec')

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir

    # Create workflow nad connect nodes
    analysisflow = pe.Workflow(name='anat2mniWorkflow')
    analysisflow.connect(inputspec, 'brain',linear_reg, 'in_file')
    analysisflow.connect(inputspec, 'reference_brain',linear_reg, 'reference')
    analysisflow.connect(inputspec, 'skull',nonlinear_reg, 'in_file')
    analysisflow.connect(inputspec, 'reference_skull',nonlinear_reg, 'ref_file')
    analysisflow.connect(inputspec, 'ref_mask',nonlinear_reg, 'refmask_file')
    # FNIRT parameters are specified by FSL config file
    # ${FSLDIR}/etc/flirtsch/TI_2_MNI152_2mm.cnf (or user-specified)
    analysisflow.connect(inputspec, 'fnirt_config',nonlinear_reg, 'config_file')
    analysisflow.connect(linear_reg, 'out_matrix_file',nonlinear_reg, 'affine_file')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file',outputspec, 'nonlinear_xfm')
    analysisflow.connect(nonlinear_reg, 'field_file', outputspec,'field_file')
    analysisflow.connect(inputspec, 'brain',brain_warp, 'in_file')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file',brain_warp, 'field_file')
    analysisflow.connect(inputspec, 'reference_brain',brain_warp, 'ref_file')
    analysisflow.connect(brain_warp, 'out_file',outputspec, 'output_brain')
    analysisflow.connect(linear_reg, 'out_matrix_file',inv_flirt_xfm, 'in_file')
    analysisflow.connect(inv_flirt_xfm, 'out_file',outputspec, 'invlinear_xfm')
    analysisflow.connect(linear_reg, 'out_matrix_file',outputspec, 'linear_xfm')
    analysisflow.connect(brain_warp, 'out_file', ds, 'anat2mni')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file', ds, 'anat2mni.@warpfield')

    return analysisflow