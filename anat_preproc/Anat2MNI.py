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

    fsldir=os.environ['FSLDIR']


    # Define inputs of workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                          'skull',
                                                          'reference_brain',
                                                          'reference_skull',
                                                          'ref_mask',
                                                          'fnirt_config']),
                        name='inputspec')

    inputspec.inputs.reference_brain = fsldir + "/data/standard/MNI152_T1_2mm_brain.nii.gz"
    inputspec.inputs.reference_skull = fsldir + "/data/standard/MNI152_T1_2mm.nii.gz"
    inputspec.inputs.ref_mask = fsldir + "/data/standard/MNI152_T1_2mm_brain_mask_dil.nii.gz"
    inputspec.inputs.fnirt_config = "T1_2_MNI152_2mm"


    # Linear registration node
    linear_reg = pe.MapNode(interface=fsl.FLIRT(),
                         iterfield=['in_file'],
                         name='linear_reg_0')
    linear_reg.inputs.cost = 'corratio'

    # Non-linear registration node
    nonlinear_reg = pe.MapNode(interface=fsl.FNIRT(),
                               iterfield=['in_file', 'affine_file'],
                               name='nonlinear_reg_1')
    nonlinear_reg.inputs.fieldcoeff_file = True
    nonlinear_reg.inputs.jacobian_file = True

    # Applying warp field
    brain_warp = pe.MapNode(interface=fsl.ApplyWarp(),
                            iterfield=['in_file', 'field_file'],
                            name='brain_warp')

    # Calculate the invers of the linear transformation
    inv_flirt_xfm = pe.MapNode(interface=fsl.utils.ConvertXFM(),
                               iterfield=['in_file'],
                               name='inv_linear_reg0_xfm')
    inv_flirt_xfm.inputs.invert_xfm = True

    # Create png images for quality check
    slicer = pe.MapNode(interface=fsl.Slicer(all_axial=True),
                        iterfield=['in_file'],
                        name='slicer')
    slicer.inputs.image_width = 1400
    # set output all axial slices into one picture
    slicer.inputs.all_axial = True
    slicer.inputs.threshold_edges = 0.12
    slicer.inputs.image_edges = fsldir + "/data/standard/MNI152_T1_2mm_brain.nii.gz"

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Save outputs which are important
    ds2 = pe.Node(interface=io.DataSink(), name='ds_slicer')
    ds2.inputs.base_directory = SinkDir
    ds2.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".png")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'field_file']),
                         name='outputspec')

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
    analysisflow.connect(brain_warp, 'out_file', ds, 'anat2mni_std')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file', ds, 'anat2mni_warpfield')
    analysisflow.connect(brain_warp, 'out_file', slicer, 'in_file')
    analysisflow.connect(slicer, 'out_file', ds2, 'anat2mni_regcheck')

    return analysisflow