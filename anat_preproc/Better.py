def bet_workflow(Robust=True, fmri=False, SinkTag="anat_preproc", wf_name="brain_extraction"):

    """
    Modified version of CPAC.anat_preproc.anat_preproc:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/anat_preproc/anat_preproc.html`


    Creates a brain extracted image and its mask from a T1w anatomical image.

    Workflow inputs:
        :param anat: The reoriented anatomical file.
        :param SinkDir:
        :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

    Workflow outputs:




        :return: bet_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """

    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io
    import PUMI.utils.QC as qc
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['in_file',
                                                          'opt_R',
                                                          'fract_int_thr',  # optional
                                                          'vertical_gradient']),   # optional
                        name='inputspec')
    inputspec.inputs.opt_R = Robust
    if fmri:
        inputspec.inputs.fract_int_thr = 0.3
    else:
        inputspec.inputs.fract_int_thr = 0.5

    inputspec.inputs.vertical_gradient = 0

    #Wraps command **bet**
    bet = pe.MapNode(interface=fsl.BET(),
                     iterfield=['in_file'],
                  name='bet')
    bet.inputs.mask=True
    # bet.inputs.robust=Robust
    if fmri:
        bet.inputs.functional = True
        applymask = pe.MapNode(fsl.ApplyMask(),
                               iterfield=['in_file', 'mask_file'],
                               name="apply_mask")


    myqc = qc.vol2png(wf_name, overlay=True)

    #Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                           'brain_mask'
                                                           #'skull'  #TODO: is it supposed to be really the skull or the full head image?
                                                           ]),
                         name = 'outputspec')

    # Save outputs which are important
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)  # The name here determine the folder of the workspace
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'in_file', bet, 'in_file')
    analysisflow.connect(inputspec, 'opt_R', bet, 'robust')
    analysisflow.connect(inputspec, 'fract_int_thr', bet, 'frac')
    analysisflow.connect(inputspec, 'vertical_gradient', bet, 'vertical_gradient')
    analysisflow.connect(bet, 'mask_file', outputspec, 'brain_mask')
    if fmri:
        analysisflow.connect(bet, 'mask_file', applymask, 'mask_file')
        analysisflow.connect(inputspec, 'in_file', applymask, 'in_file')
        analysisflow.connect(applymask, 'out_file', outputspec, 'brain')
    else:
        analysisflow.connect(bet, 'out_file', outputspec, 'brain')
    analysisflow.connect(bet, 'out_file', ds, 'bet_brain')
    analysisflow.connect(bet, 'mask_file', ds, 'bet_mask')

    analysisflow.connect(inputspec, 'in_file', myqc, 'inputspec.bg_image')
    analysisflow.connect(bet, 'out_file', myqc, 'inputspec.overlay_image')

    return analysisflow

