def bbr_workflow(SinkDir=".",
                 SinkTag="anat_preproc"):


    """
        Modified version of CPAC.registration.registration:

        `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/registration/registration.html`


        BBR registration of functional image to standard.

        Workflow inputs:
            :param func: One volume of the 4D fMRI (The one which os the closest to the fieldmap recording in time should be chosen).
            :param skull: The oriented high res T1w image.
            :param anat_wm_segmentation: WM probability mask in .
            :param bbr_schedule: Parameters which specifies BBR options.
            :param SinkDir:
            :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

        Workflow outputs:




            :return: bbreg_workflow - workflow
                func="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz",
                 skull="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/MS001/highres.nii.gz",
                 anat_wm_segmentation="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/anat_preproc/fast/fast__prob_2.nii.gz",



        Balint Kincses
        kincses.balint@med.u-szeged.hu
        2018


        """
    import os
    import nipype.pipeline as pe
    from nipype.interfaces.utility import Function
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io
    import PUMI.func_preproc.Onevol as onevol
    import PUMI.utils.QC as qc

    QCDir = os.path.abspath(SinkDir + "/QC")
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)
    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    fsldir = os.environ['FSLDIR']

    # Define inputs of the workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                       'skull',
                                                       'anat_wm_segmentation',
                                                       'bbr_schedule']),
                        name='inputspec')

    inputspec.inputs.bbr_schedule = fsldir + "/etc/flirtsch/bbr.sch"
    #inputspec.inputs.func=func
    #inputspec.inputs.skull=skull
    #inputspec.inputs.anat_wm_segmentation=anat_wm_segmentation

    myonevol = onevol.onevol_workflow()

    # trilinear interpolation is used by default
    linear_reg = pe.MapNode(interface=fsl.FLIRT(),
                            iterfield=['in_file', 'reference'],
                            name='linear_func_to_anat')
    linear_reg.inputs.cost = 'corratio'
    linear_reg.inputs.dof = 6
    linear_reg.inputs.out_matrix_file = "lin_mat"

    # WM probability map is thresholded and masked
    wm_bb_mask = pe.MapNode(interface=fsl.ImageMaths(),
                            iterfield=['in_file'],
                            name='wm_bb_mask')
    wm_bb_mask.inputs.op_string = '-thr 0.5 -bin'
    # A function is defined for define bbr argumentum which says flirt to perform bbr registration
    # for each element of the list, due to MapNode
    def bbreg_args(bbreg_target):
        return '-cost bbr -wmseg ' + bbreg_target

    bbreg_arg_convert = pe.MapNode(interface=Function(input_names=["bbreg_target"],
                                                    output_names=["arg"],
                                                    function=bbreg_args),
                                   iterfield=['bbreg_target'],
                                   name="bbr_arg_converter"
                                 )

    # BBR regostration within the FLIRT node
    bbreg_func_to_anat = pe.MapNode(interface=fsl.FLIRT(),
                                    iterfield=['in_file', 'reference', 'in_matrix_file', 'args'],
                                    name='bbreg_func_to_anat')
    bbreg_func_to_anat.inputs.dof = 6

    # Create png images for quality check

    myqc = qc.vol2png("func2anat")

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(),
                 name='ds_nii')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    #TODO inverted transformation matrix node is necessery
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_to_anat_linear_xfm',
                                                           'func_to_anat_linear_xfm_nobbreg'
                                                        # 'func_to_mni_linear_xfm',
                                                        # 'mni_to_func_linear_xfm',
                                                        # 'anat_wm_edge',
                                                        'func_sample2anat']),
                         name='outputspec')

    analysisflow = pe.Workflow(name='Func2Anat')

    analysisflow.connect(inputspec, 'bbr_schedule', bbreg_func_to_anat, 'schedule')
    analysisflow.connect(wm_bb_mask, 'out_file', bbreg_arg_convert, 'bbreg_target')
    analysisflow.connect(bbreg_arg_convert, 'arg', bbreg_func_to_anat, 'args')
    analysisflow.connect(inputspec, 'anat_wm_segmentation', wm_bb_mask, 'in_file')
    analysisflow.connect(inputspec, 'func', myonevol, 'inputspec.func')
    analysisflow.connect(myonevol, 'outputspec.func1vol', bbreg_func_to_anat, 'in_file')
    analysisflow.connect(inputspec, 'skull', bbreg_func_to_anat, 'reference')
    analysisflow.connect(linear_reg, 'out_matrix_file', bbreg_func_to_anat, 'in_matrix_file')
    analysisflow.connect(bbreg_func_to_anat, 'out_matrix_file', outputspec, 'func_to_anat_linear_xfm')
    analysisflow.connect(bbreg_func_to_anat, 'out_file', outputspec, 'func_sample2anat')
    analysisflow.connect(inputspec, 'func', linear_reg, 'in_file')
    analysisflow.connect(inputspec, 'skull',linear_reg, 'reference')
    analysisflow.connect(linear_reg, 'out_matrix_file', outputspec, 'func_to_anat_linear_xfm_nobbreg')
    analysisflow.connect(bbreg_func_to_anat, 'out_file', ds, 'bbr')
    analysisflow.connect(bbreg_func_to_anat, 'out_file', myqc, 'inputspec.bg_image')
    analysisflow.connect(wm_bb_mask, 'out_file', myqc, 'inputspec.overlay_image')


    return analysisflow



