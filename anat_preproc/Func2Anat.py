def bbr_workflow(SinkTag="func_preproc", wf_name="func2anat"):


    """
        Modified version of CPAC.registration.registration:

        `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/registration/registration.html`


        BBR registration of functional image to anat.

        Workflow inputs:
            :param func: One volume of the 4D fMRI (The one which is the closest to the fieldmap recording in time should be chosen- e.g: if fieldmap was recorded after the fMRI the last volume of it should be chosen).
            :param skull: The oriented high res T1w image.
            :param anat_wm_segmentation: WM probability mask in .
            :param anat_csf_segmentation: CSF probability mask in
            :param bbr_schedule: Parameters which specifies BBR options.
            :param SinkDir:
            :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

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
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Define inputs of the workflow
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                       'skull',
                                                       'anat_wm_segmentation',
                                                       'anat_gm_segmentation',
                                                       'anat_csf_segmentation',
                                                        'anat_ventricle_segmentation']),
                        name='inputspec')


    myonevol = onevol.onevol_workflow()

    # trilinear interpolation is used by default in linear registration for func to anat
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
    # CSf probability map is thresholded and masked
    csf_bb_mask = pe.MapNode(interface=fsl.ImageMaths(),
                            iterfield=['in_file'],
                            name='csf_bb_mask')
    csf_bb_mask.inputs.op_string = '-thr 0.5 -bin'

    # GM probability map is thresholded and masked
    gm_bb_mask = pe.MapNode(interface=fsl.ImageMaths(),
                             iterfield=['in_file'],
                             name='gm_bb_mask')
    gm_bb_mask.inputs.op_string = '-thr 0.1 -bin' # liberal mask to capture all gm signal

    # ventricle probability map is thresholded and masked
    vent_bb_mask = pe.MapNode(interface=fsl.ImageMaths(),
                            iterfield=['in_file'],
                            name='vent_bb_mask')
    vent_bb_mask.inputs.op_string = '-thr 0.8 -bin -ero -dilM'  # stricter threshold and some morphology for compcor

    # add the CSF and WM masks
    #add_masks=pe.MapNode(interface=fsl.ImageMaths(),
    #                     iterfield=['in_file','in_file2'],
    #                     name='add_masks')
    #add_masks.inputs.op_string = ' -add'

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

    # BBR registration within the FLIRT node
    bbreg_func_to_anat = pe.MapNode(interface=fsl.FLIRT(),
                                    iterfield=['in_file', 'reference', 'in_matrix_file', 'args'],
                                    name='bbreg_func_to_anat')
    bbreg_func_to_anat.inputs.dof = 6

    # calculate the inverse of the transformation matrix (of func to anat)
    convertmatrix = pe.MapNode(interface=fsl.ConvertXFM(),
                               iterfield=['in_file'],
                               name="convertmatrix")
    convertmatrix.inputs.invert_xfm = True

    # use the invers registration (anat to func) to transform anatomical csf mask
    reg_anatmask_to_func1 = pe.MapNode(interface=fsl.FLIRT(apply_xfm=True, interp='nearestneighbour'),
                                       iterfield=['in_file', 'reference', 'in_matrix_file'],
                                       name='anatmasks_to_func1')
    #reg_anatmask_to_func1.inputs.apply_xfm = True
    # use the invers registration (anat to func) to transform anatomical wm mask
    reg_anatmask_to_func2 = pe.MapNode(interface=fsl.FLIRT(apply_xfm=True, interp='nearestneighbour'),
                                       iterfield=['in_file', 'reference', 'in_matrix_file'],
                                       name='anatmasks_to_func2')
    #reg_anatmask_to_func2.inputs.apply_xfm = True

    # use the invers registration (anat to func) to transform anatomical gm mask
    reg_anatmask_to_func3 = pe.MapNode(interface=fsl.FLIRT(apply_xfm=True, interp='nearestneighbour'),
                                       iterfield=['in_file', 'reference', 'in_matrix_file'],
                                       name='anatmasks_to_func3')
    # reg_anatmask_to_func2.inputs.apply_xfm = True

    # use the invers registration (anat to func) to transform anatomical gm mask
    reg_anatmask_to_func4 = pe.MapNode(interface=fsl.FLIRT(apply_xfm=True, interp='nearestneighbour'),
                                       iterfield=['in_file', 'reference', 'in_matrix_file'],
                                       name='anatmasks_to_func4')
    # reg_anatmask_to_func2.inputs.apply_xfm = True

    # Create png images for quality check
    myqc = qc.vol2png("func2anat")

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(),
                 name='ds_nii')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # Define outputs of the workflow
    outputspec = pe.Node(utility.IdentityInterface(fields=[ 'func_sample2anat',
                                                            'example_func',
                                                            'func_to_anat_linear_xfm',
                                                            'anat_to_func_linear_xfm',
                                                            'csf_mask_in_funcspace',
                                                            'wm_mask_in_funcspace',
                                                            'gm_mask_in_funcspace',
                                                            'ventricle_mask_in_funcspace']),
                         name='outputspec')

    analysisflow = pe.Workflow(name=wf_name)
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'func', linear_reg, 'in_file')
    analysisflow.connect(inputspec, 'skull',linear_reg, 'reference')
    analysisflow.connect(linear_reg, 'out_matrix_file', bbreg_func_to_anat, 'in_matrix_file')
    analysisflow.connect(inputspec, 'func', myonevol, 'inputspec.func')
    analysisflow.connect(myonevol, 'outputspec.func1vol', bbreg_func_to_anat, 'in_file')
    analysisflow.connect(inputspec, 'anat_wm_segmentation', bbreg_arg_convert, 'bbreg_target')
    analysisflow.connect(bbreg_arg_convert, 'arg', bbreg_func_to_anat, 'args')
    analysisflow.connect(inputspec, 'skull', bbreg_func_to_anat, 'reference')
    analysisflow.connect(bbreg_func_to_anat, 'out_matrix_file', convertmatrix, 'in_file')
    analysisflow.connect(convertmatrix, 'out_file',reg_anatmask_to_func1,'in_matrix_file')
    analysisflow.connect(inputspec, 'func',reg_anatmask_to_func1,'reference')
    analysisflow.connect(csf_bb_mask,'out_file', reg_anatmask_to_func1, 'in_file')
    analysisflow.connect(convertmatrix, 'out_file',reg_anatmask_to_func2,'in_matrix_file')
    analysisflow.connect(inputspec, 'func',reg_anatmask_to_func2,'reference')
    analysisflow.connect(wm_bb_mask,'out_file', reg_anatmask_to_func2, 'in_file')
    analysisflow.connect(convertmatrix, 'out_file',reg_anatmask_to_func3,'in_matrix_file')
    analysisflow.connect(inputspec, 'func', reg_anatmask_to_func3, 'reference')
    analysisflow.connect(gm_bb_mask, 'out_file', reg_anatmask_to_func3, 'in_file')
    analysisflow.connect(convertmatrix, 'out_file', reg_anatmask_to_func4, 'in_matrix_file')
    analysisflow.connect(inputspec, 'func', reg_anatmask_to_func4, 'reference')
    analysisflow.connect(vent_bb_mask, 'out_file', reg_anatmask_to_func4, 'in_file')
    analysisflow.connect(inputspec, 'anat_wm_segmentation', wm_bb_mask, 'in_file')
    analysisflow.connect(inputspec, 'anat_csf_segmentation', csf_bb_mask, 'in_file')
    analysisflow.connect(inputspec, 'anat_gm_segmentation', gm_bb_mask, 'in_file')
    analysisflow.connect(inputspec, 'anat_ventricle_segmentation', vent_bb_mask, 'in_file')
    analysisflow.connect(bbreg_func_to_anat, 'out_file', outputspec, 'func_sample2anat')
    analysisflow.connect(bbreg_func_to_anat, 'out_matrix_file', outputspec, 'func_to_anat_linear_xfm')
    analysisflow.connect(reg_anatmask_to_func1,'out_file',outputspec, 'csf_mask_in_funcspace')
    analysisflow.connect(reg_anatmask_to_func2,'out_file',outputspec, 'wm_mask_in_funcspace')
    analysisflow.connect(reg_anatmask_to_func3, 'out_file', outputspec, 'gm_mask_in_funcspace')
    analysisflow.connect(reg_anatmask_to_func4, 'out_file', outputspec, 'ventricle_mask_in_funcspace')
    analysisflow.connect(myonevol, 'outputspec.func1vol', outputspec, 'example_func')
    analysisflow.connect(convertmatrix, 'out_file',outputspec,'anat_to_func_linear_xfm')
    analysisflow.connect(bbreg_func_to_anat, 'out_file', ds, "func2anat")
    analysisflow.connect(bbreg_func_to_anat, 'out_file', myqc, 'inputspec.bg_image')
    analysisflow.connect(wm_bb_mask, 'out_file', myqc, 'inputspec.overlay_image')


    return analysisflow



