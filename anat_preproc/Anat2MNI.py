import os
import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as io
import copy, pprint
from nipype.interfaces.ants import Registration
import PUMI.utils.QC as qc
import PUMI.utils.globals as globals

def anat2mni_fsl_workflow(SinkTag="anat_preproc", wf_name="anat2mni_fsl"):

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

    SinkDir = os.path.abspath( globals._SinkDir_+ "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                          'skull',
                                                          'reference_brain',
                                                          'reference_skull',
                                                          'ref_mask',
                                                          'fnirt_config'
                                                          ]),
                        name='inputspec')

    inputspec.inputs.reference_brain = globals._FSLDIR_ + globals._brainref
    inputspec.inputs.reference_skull = globals._FSLDIR_ + globals._headref
    inputspec.inputs.ref_mask = globals._FSLDIR_ + globals._brainref_mask
    # inputspec.inputs.fnirt_config = "T1_2_MNI152_2mm"


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

    # Calculate inverse of the nonlinear warping field
    inv_fnirt_xfm = pe.MapNode(interface=fsl.utils.InvWarp(),
                               iterfield=['warp', 'reference'],
                               name="inv_nonlinear_xfm")

    # Create png images for quality check
    myqc = qc.vol2png("anat2mni", "FSL2", overlayiterated=False)
    myqc.inputs.inputspec.overlay_image = globals._FSLDIR_ + globals._brainref
    myqc.inputs.slicer.image_width = 500
    myqc.inputs.slicer.threshold_edges = 0.1

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'invnonlinear_xfm',
                                                           'std_template']),
                         name='outputspec')

    # Create workflow nad connect nodes
    analysisflow = pe.Workflow(name=wf_name)
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

    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file', inv_fnirt_xfm, 'warp')
    analysisflow.connect(inputspec, 'brain', inv_fnirt_xfm, 'reference')
    analysisflow.connect(inv_fnirt_xfm, 'inverse_warp', outputspec, 'invnonlinear_xfm')

    analysisflow.connect(linear_reg, 'out_matrix_file',outputspec, 'linear_xfm')
    analysisflow.connect(inputspec, 'reference_brain', outputspec, 'std_template')
    analysisflow.connect(brain_warp, 'out_file', ds, 'anat2mni_std')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file', ds, 'anat2mni_warpfield')
    analysisflow.connect(brain_warp, 'out_file', myqc, 'inputspec.bg_image')


    return analysisflow


def anat2mni_ants_workflow_nipype(SinkTag="anat_preproc", wf_name="anat2mni_ants"):

    """
    Register skull and brain extracted image to MNI space and return the transformation martices.
    Using ANTS, doing it in the nipype way.

    Workflow inputs:
        :param skull: The reoriented anatomical file.
        :param brain: The brain extracted anat.
        :param ref_skull: MNI152 skull file.
        :param ref_brain: MNI152 brain file.
        :param SinkDir:
        :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

    Workflow outputs:




        :return: anat2mni_workflow - workflow


        anat="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres.nii.gz",
                      brain="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres_brain.nii.gz",


    Tamas Spisak
    tamas.spisak@uk-essen.de
    2018


    """
    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                          'skull',
                                                          'reference_brain',
                                                          'reference_skull']),
                        name='inputspec')

    inputspec.inputs.reference_brain = globals._FSLDIR_ + globals._brainref #TODO_ready: 1 or 2mm???
    inputspec.inputs.reference_skull = globals._FSLDIR_ + globals._headref

    # Multi-stage registration node with ANTS
    reg = pe.MapNode(interface=Registration(),
                     iterfield=['moving_image'], # 'moving_image_mask'],
                     name="ANTS")
    """
    reg.inputs.transforms = ['Affine', 'SyN']
    reg.inputs.transform_parameters = [(2.0,), (0.1, 3.0, 0.0)]
    reg.inputs.number_of_iterations = [[1500, 200], [100, 50, 30]]
    reg.inputs.dimension = 3
    reg.inputs.write_composite_transform = True
    reg.inputs.collapse_output_transforms = False
    reg.inputs.initialize_transforms_per_stage = False
    reg.inputs.metric = ['Mattes', 'Mattes']
    reg.inputs.metric_weight = [1] * 2  # Default (value ignored currently by ANTs)
    reg.inputs.radius_or_number_of_bins = [32] * 2
    reg.inputs.sampling_strategy = ['Random', None]
    reg.inputs.sampling_percentage = [0.05, None]
    reg.inputs.convergence_threshold = [1.e-8, 1.e-9]
    reg.inputs.convergence_window_size = [20] * 2
    reg.inputs.smoothing_sigmas = [[1, 0], [2, 1, 0]]
    reg.inputs.sigma_units = ['vox'] * 2
    reg.inputs.shrink_factors = [[2, 1], [4, 2, 1]]
    reg.inputs.use_estimate_learning_rate_once = [True, True]
    reg.inputs.use_histogram_matching = [True, True]  # This is the default
    reg.inputs.output_warped_image = 'output_warped_image.nii.gz'
    reg.inputs.winsorize_lower_quantile = 0.01
    reg.inputs.winsorize_upper_quantile = 0.99
    """

    #satra says:
    reg.inputs.transforms = ['Rigid', 'Affine', 'SyN']
    reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
    reg.inputs.number_of_iterations = ([[10000, 111110, 11110]] * 2 + [[100, 50, 30]])
    reg.inputs.dimension = 3
    reg.inputs.write_composite_transform = True
    reg.inputs.collapse_output_transforms = True
    reg.inputs.initial_moving_transform_com = True
    reg.inputs.metric = ['Mattes'] * 2 + [['Mattes', 'CC']]
    reg.inputs.metric_weight = [1] * 2 + [[0.5, 0.5]]
    reg.inputs.radius_or_number_of_bins = [32] * 2 + [[32, 4]]
    reg.inputs.sampling_strategy = ['Regular'] * 2 + [[None, None]]
    reg.inputs.sampling_percentage = [0.3] * 2 + [[None, None]]
    reg.inputs.convergence_threshold = [1.e-8] * 2 + [-0.01]
    reg.inputs.convergence_window_size = [20] * 2 + [5]
    reg.inputs.smoothing_sigmas = [[4, 2, 1]] * 2 + [[1, 0.5, 0]]
    reg.inputs.sigma_units = ['vox'] * 3
    reg.inputs.shrink_factors = [[3, 2, 1]] * 2 + [[4, 2, 1]]
    reg.inputs.use_estimate_learning_rate_once = [True] * 3
    reg.inputs.use_histogram_matching = [False] * 2 + [True]
    reg.inputs.winsorize_lower_quantile = 0.005
    reg.inputs.winsorize_upper_quantile = 0.995
    reg.inputs.args = '--float'


    # Create png images for quality check
    myqc = qc.vol2png("anat2mni", "ANTS3", overlayiterated=False)
    myqc.inputs.inputspec.overlay_image = globals._FSLDIR_ + globals._brainref #TODO_ready: 1 or 2mm???
    myqc.inputs.slicer.image_width = 500 # 5000 # for the 1mm template
    myqc.inputs.slicer.threshold_edges = 0.1 # 0.1  # for the 1mm template


    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds_nii')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'invnonlinear_xfm',
                                                           'std_template']),
                         name='outputspec')

    outputspec.inputs.std_template=inputspec.inputs.reference_brain

    # Create workflow nad connect nodes
    analysisflow = pe.Workflow(name=wf_name)

    analysisflow.connect(inputspec, 'reference_skull', reg, 'fixed_image')
    #analysisflow.connect(inputspec, 'reference_brain', reg, 'fixed_image_mask')
    analysisflow.connect(inputspec, 'skull', reg, 'moving_image')
    #analysisflow.connect(inputspec, 'brain', reg, 'moving_image_mask')

    analysisflow.connect(reg, 'composite_transform', outputspec, 'nonlinear_xfm')
    analysisflow.connect(reg, 'inverse_composite_transform', outputspec, 'invnonlinear_xfm')
    analysisflow.connect(reg, 'warped_image',outputspec, 'output_brain')
    analysisflow.connect(reg, 'warped_image', ds, 'anat2mni_std')
    analysisflow.connect(reg, 'composite_transform', ds, 'anat2mni_warpfield')
    analysisflow.connect(reg, 'warped_image', myqc, 'inputspec.bg_image')

    return analysisflow

def anat2mni_ants_workflow_harcoded(SinkTag="anat_preproc", wf_name="anat2mni_ants"):

    """
    Register skull and brain extracted image to MNI space and return the transformation martices.
    Using ANTS, doing it with a hardcoded function, a'la C-PAC.
    This uses brain masks and full head images, as well.

    Workflow inputs:
        :param skull: The reoriented anatomical file.
        :param brain: The brain extracted anat.
        :param ref_skull: MNI152 skull file.
        :param ref_brain: MNI152 brain file.
        :param SinkDir:
        :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

    Workflow outputs:




        :return: anat2mni_workflow - workflow


        anat="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres.nii.gz",
                      brain="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres_brain.nii.gz",


    Tamas Spisak
    tamas.spisak@uk-essen.de
    2018


    """
    from nipype.interfaces.utility import Function

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                          'skull',
                                                          'reference_brain',
                                                          'reference_skull']),
                        name='inputspec')

    inputspec.inputs.reference_brain = globals._FSLDIR_ + globals._brainref #TODO_ready: 1 or 2mm???
    inputspec.inputs.reference_skull = globals._FSLDIR_ + globals._headref

    # Multi-stage registration node with ANTS
    reg = pe.MapNode(interface=Function(input_names=['anatomical_brain',
                                                     'reference_brain',
                                                     'anatomical_skull',
                                                     'reference_skull'],
                                        output_names=['transform_composite',
                                                      'transform_inverse_composite',
                                                      'warped_image'],
                                        function=hardcoded_reg_fast),
                     iterfield=['anatomical_brain', 'anatomical_skull'],
                     name="ANTS_hardcoded",
                     mem_gb=4.1)

    # Calculate linear transformation with FSL. This matrix has to be used in segmentation with fast if priors are set. (the default).
    # Linear registration node
    linear_reg = pe.MapNode(interface=fsl.FLIRT(),
                         iterfield=['in_file'],
                         name='linear_reg_0')
    linear_reg.inputs.cost = 'corratio'

    # Calculate the invers of the linear transformation
    inv_flirt_xfm = pe.MapNode(interface=fsl.utils.ConvertXFM(),
                               iterfield=['in_file'],
                               name='inv_linear_reg0_xfm')
    inv_flirt_xfm.inputs.invert_xfm = True

    #  # or hardcoded_reg_cpac

    # Create png images for quality check
    myqc = qc.vol2png("anat2mni", "ANTS", overlayiterated=False)
    myqc.inputs.inputspec.overlay_image = globals._FSLDIR_ + globals._brainref #TODO_ready: 1 or 2mm???
    myqc.inputs.slicer.image_width = 500  # 5000 # for the 1mm template
    myqc.inputs.slicer.threshold_edges = 0.1  # 0.1  # for the 1mm template


    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds_nii')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'invnonlinear_xfm',
                                                           'std_template']),
                         name='outputspec')

    outputspec.inputs.std_template = inputspec.inputs.reference_brain

    # Create workflow nad connect nodes
    analysisflow = pe.Workflow(name=wf_name)
    # FSL part for the transformation matrix
    analysisflow.connect(inputspec, 'brain',linear_reg, 'in_file')
    analysisflow.connect(inputspec, 'reference_brain',linear_reg, 'reference')
    analysisflow.connect(linear_reg, 'out_matrix_file',inv_flirt_xfm, 'in_file')
    analysisflow.connect(inv_flirt_xfm, 'out_file',outputspec, 'invlinear_xfm')

    analysisflow.connect(inputspec, 'reference_skull', reg, 'reference_skull')
    analysisflow.connect(inputspec, 'reference_brain', reg, 'reference_brain')
    analysisflow.connect(inputspec, 'skull', reg, 'anatomical_skull')
    analysisflow.connect(inputspec, 'brain', reg, 'anatomical_brain')

    analysisflow.connect(reg, 'transform_composite', outputspec, 'nonlinear_xfm')
    analysisflow.connect(reg, 'transform_inverse_composite', outputspec, 'invnonlinear_xfm')
    analysisflow.connect(reg, 'warped_image',outputspec, 'output_brain')
    analysisflow.connect(reg, 'warped_image', ds, 'anat2mni_std')
    analysisflow.connect(reg, 'transform_composite', ds, 'anat2mni_warpfield')
    analysisflow.connect(reg, 'warped_image', myqc, 'inputspec.bg_image')

    return analysisflow

def hardcoded_reg_cpac(anatomical_brain, reference_brain, anatomical_skull, reference_skull):

    # very much like in C-PAC, but collapses output transforms
    import subprocess
    import os

    regcmd = ["antsRegistration",
              "--collapse-output-transforms", "1",
              "--write-composite-transform", "1",
              "--dimensionality", "3",
              "--initial-moving-transform",
              "[{0},{1},0]".format(reference_brain, anatomical_brain),
              "--interpolation", "Linear",
              "--output", "[transform,transform_Warped.nii.gz]",
              "--transform", "Rigid[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.25]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250x100,1e-08,10]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "8x4x2x1",
              "--use-histogram-matching", "1",
              "--transform", "Affine[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.25]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250x100,1e-08,10]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "8x4x2x1",
              "--use-histogram-matching", "1",
              "--transform", "SyN[0.1,3.0,0.0]",
              "--metric", "CC[{0},{1},1,4]".format(reference_skull,
                                                   anatomical_skull),
              "--convergence", "[100x100x70x20,1e-09,15]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "6x4x2x1",
              "--use-histogram-matching", "1",
              "--winsorize-image-intensities", "[0.01,0.99]"]

    try:
        retcode = subprocess.check_output(regcmd)
    except Exception as e:
        raise Exception('[!] ANTS registration did not complete successfully.'
                        '\n\nError details:\n{0}\n'.format(e))

    transform_composite = None
    transform_inverse_composite = None
    warped_image = None

    files = [f for f in os.listdir('.') if os.path.isfile(f)]

    for f in files:
        if ("transformComposite" in f) and ("Warped" not in f):
            transform_composite = os.getcwd() + "/" + f
        if ("transformInverseComposite" in f) and ("Warped" not in f):
            transform_inverse_composite = os.getcwd() + "/" + f
        if "Warped" in f:
            warped_image = os.getcwd() + "/" + f

    if not warped_image:
        raise Exception("\n\n[!] No registration output file found. ANTS "
                        "registration may not have completed "
                        "successfully.\n\n")

    return transform_composite, transform_inverse_composite, warped_image

def hardcoded_reg_fast(anatomical_brain, reference_brain, anatomical_skull, reference_skull):
    # faster than the C-PAC solution??
    # parameters based on Satra's post:
    #https: // gist.github.com / satra / 8439778
    import subprocess
    import os

    regcmd = ["antsRegistration",
              "--collapse-output-transforms", "1",
              "--dimensionality", "3",

              "--initial-moving-transform",
              "[{0},{1},1]".format(reference_brain, anatomical_brain),
              "--interpolation", "Linear",
              "--output", "[transform,transform_Warped.nii.gz]",

              "--transform", "Rigid[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.3]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250,1e-08,20]",
              "--smoothing-sigmas", "4.0x2.0x1.0",
              "--shrink-factors", "3x2x1",
              "--use-estimate-learning-rate-once", "1",
              "--use-histogram-matching", "0",

              "--transform", "Affine[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.3]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250,1e-08,20]",
              "--smoothing-sigmas", "4.0x2.0x1.0",
              "--shrink-factors", "3x2x1",
              "--use-estimate-learning-rate-once", "1",
              "--use-histogram-matching", "0",

              "--transform", "SyN[0.2,3.0,0.0]",
              "--metric", "Mattes[{0},{1},0.5,32]".format(reference_skull,
                                                   anatomical_skull),
              "--metric", "CC[{0},{1},0.5,4]".format(reference_skull,
                                                   anatomical_skull),
              "--convergence", "[100x50x30,-0.01,5]",
              "--smoothing-sigmas", "1.0x0.5x0.0",
              "--shrink-factors", "4x2x1",
              "--use-histogram-matching", "1",
              "--winsorize-image-intensities", "[0.005,0.995]",
              "--use-estimate-learning-rate-once", "1",
              "--write-composite-transform", "1"]

    try:
        retcode = subprocess.check_output(regcmd)
    except Exception as e:
        raise Exception('[!] ANTS registration did not complete successfully.'
                        '\n\nError details:\n{0}\n'.format(e))

    transform_composite = None
    transform_inverse_composite = None
    warped_image = None

    files = [f for f in os.listdir('.') if os.path.isfile(f)]

    for f in files:
        if ("transformComposite" in f) and ("Warped" not in f):
            transform_composite = os.getcwd() + "/" + f
        if ("transformInverseComposite" in f) and ("Warped" not in f):
            transform_inverse_composite = os.getcwd() + "/" + f
        if "Warped" in f:
            warped_image = os.getcwd() + "/" + f

    if not warped_image:
        raise Exception("\n\n[!] No registration output file found. ANTS "
                        "registration may not have completed "
                        "successfully.\n\n")

    return transform_composite, transform_inverse_composite, warped_image
