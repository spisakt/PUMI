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
                                                          'fnirt_config']),
                        name='inputspec')

    inputspec.inputs.reference_brain = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_brain.nii.gz"
    inputspec.inputs.reference_skull = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm.nii.gz"
    inputspec.inputs.ref_mask = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_brain_mask_dil.nii.gz"
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
    myqc = qc.vol2png("anat2mni", "FSL", overlayiterated=False)
    myqc.inputs.inputspec.overlay_image = globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_brain.nii.gz"
    myqc.inputs.slicer.image_width = 5000
    myqc.inputs.slicer.threshold_edges = 0.12

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm']),
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
    analysisflow.connect(linear_reg, 'out_matrix_file',outputspec, 'linear_xfm')
    analysisflow.connect(brain_warp, 'out_file', ds, 'anat2mni_std')
    analysisflow.connect(nonlinear_reg, 'fieldcoeff_file', ds, 'anat2mni_warpfield')
    analysisflow.connect(brain_warp, 'out_file', myqc, 'inputspec.bg_image')


    return analysisflow


def anat2mni_ants_workflow(SinkTag="anat_preproc", wf_name="anat2mni_ants"):

    """
    Register skull and brain extracted image to MNI space and return the transformation martices.

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


    Balint Kincses
    kincses.balint@med.u-szeged.hu
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

    inputspec.inputs.reference_brain = globals._FSLDIR_ + "/data/standard/MNI152_T1_1mm_brain.nii.gz"
    inputspec.inputs.reference_skull = globals._FSLDIR_ + "/data/standard/MNI152_T1_1mm.nii.gz"

    # Multi-stage registration node with ANTS
    reg = pe.MapNode(interface=Registration(),
                     iterfield=['moving_image'],
                     name="ANTS")

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


    # Applying warp field

    # Calculate the invers of the linear transformation

    # Create png images for quality check
    # Create png images for quality check
    myqc = qc.vol2png("anat2mni", "ANTS", overlayiterated=False)
    myqc.inputs.inputspec.overlay_image = globals._FSLDIR_ + "/data/standard/MNI152_T1_1mm_brain.nii.gz"
    myqc.inputs.slicer.image_width = 5000
    myqc.inputs.slicer.threshold_edges = 0.1  # for the 1mm template


    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(), name='ds_nii')
    ds.inputs.base_directory = SinkDir
    #ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=['output_brain',
                                                           'linear_xfm',
                                                           'invlinear_xfm',
                                                           'nonlinear_xfm',
                                                           'composite_transform']),
                         name='outputspec')

    # Create workflow nad connect nodes
    analysisflow = pe.Workflow(name=wf_name)

    analysisflow.connect(inputspec, 'reference_brain', reg, 'fixed_image')
    analysisflow.connect(inputspec, 'brain', reg, 'moving_image')

    analysisflow.connect(reg, 'composite_transform', outputspec, 'nonlinear_xfm')
    analysisflow.connect(reg, 'warped_image',outputspec, 'output_brain')
    analysisflow.connect(reg, 'warped_image', ds, 'anat2mni_std')
    analysisflow.connect(reg, 'composite_transform', ds, 'anat2mni_warpfield')
    analysisflow.connect(brain_warp, 'out_file', myqc, 'inputspec.bg_image')

    return analysisflow