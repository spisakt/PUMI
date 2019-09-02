import nipype
import nipype.pipeline as pe
import PUMI.anat_preproc.Better as bet
import PUMI.anat_preproc.Faster as fast
import PUMI.anat_preproc.Anat2MNI as anat2mni
import nipype.interfaces.utility as utility
import nipype.interfaces.afni as afni
import nipype.interfaces.fsl as fsl
import nipype.interfaces.ants as ants
import PUMI.utils.globals as globals

def AnatProc(stdreg, SinkTag="anat_preproc", wf_name="anatproc"):
    """
    stdreg: either globals._RegType_.ANTS or globals._RegType_.FSL (do default value to make sure the user has to decide explicitly)


        Performs processing of anatomical images:
        - brain extraction
        - tissue type segmentation
        - spatial standardization (with either FSL or ANTS)

        Images should be already "reoriented", e.g. with fsl fslreorient2std (see scripts/ex_pipeline.py)

        Workflow inputs:
            :param func: The functional image file.
            :param SinkDir: where to write important ouputs
            :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

        Workflow outputs:
            :param brain: brain extracted image in subject space
            :param brain_mask: brain mask in subject space
            :param skull: full head image in subjacet space
            :param probmap_gm: gray matter probability map
            :param probmap_wm: white matter probability map
            :param probmap_csf: CSF probability map
            :param parvol_gm: gray matter partial volume map
            :param parvol_wm: white matter partial volume map
            :param parvol_csf: CSF partial volume map
            :param partvol_map: hard segmented tissue map
            :param anat2mni_warpfield: spatial standardization warping field
            :param std_brain: spatially standardised brain extracted image
            :param stdregtype: type of stabndard registration: FSL=1, ANTS=2



            :return: anatproc_workflow


        Tamas Spisak
        tamas.spisak@uk-essen.de
        2018

        """
    import PUMI.utils.globals as globals
    import os

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['anat',
                                                          'bet_vertical_gradient',
                                                          'bet_fract_int_thr']),
                        name='inputspec')

    inputspec.inputs.bet_fract_int_thr = globals._fsl_bet_fract_int_thr_anat_
    inputspec.inputs.bet_vertical_gradient = globals._fsl_bet_vertical_gradient_

    # build the actual pipeline
    mybet = bet.bet_workflow()
    myfast = fast.fast_workflow()
    myfast.get_node("inputspec").inputs.priorprob=[] # switch off prior probmaps
    # ToDo make settable

    if stdreg==globals._RegType_.FSL:
        myanat2mni = anat2mni.anat2mni_fsl_workflow()
    else:  # ANTS
        myanat2mni = anat2mni.anat2mni_ants_workflow_harcoded()  # currently hardcoded
        #TODO_read set fsl linear reg matrix here: the anat2mni_ants_workflow_harcoded contains has the output

    #resample 2mm-std ventricle to the actual standard space
    resample_std_ventricle = pe.Node(interface=afni.Resample(outputtype='NIFTI_GZ',
                                          in_file=globals._FSLDIR_ + "/data/standard/MNI152_T1_2mm_VentricleMask.nii.gz"),
                         name='resample_std_ventricle') #default interpolation is nearest neighbour

    #transform std ventricle mask to anat space, applying the invers warping filed
    if (stdreg ==globals._RegType_.FSL):
        unwarp_ventricle = pe.MapNode(interface=fsl.ApplyWarp(),
                           iterfield=['ref_file', 'field_file'],
                           name='unwarp_ventricle')
    else:  # ANTS
        unwarp_ventricle = pe.MapNode(interface=ants.ApplyTransforms(),
                                      iterfield=['reference_image', 'transforms'],
                                      name='unwarp_ventricle')

    # mask csf segmentation with anat-space ventricle mask
    ventricle_mask = pe.MapNode(fsl.ImageMaths(op_string=' -mas'),
                                iterfield=['in_file', 'in_file2'],
                                name="ventricle_mask")

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                           'brain_mask',
                                                           'skull',
                                                           'probmap_gm',
                                                           'probmap_wm',
                                                           'probmap_csf',
                                                           'probmap_ventricle',
                                                           'parvol_gm',
                                                           'parvol_wm',
                                                           'parvol_csf',
                                                           'partvol_map',
                                                           'anat2mni_warpfield',
                                                           'mni2anat_warpfield',
                                                           'std_brain',
                                                           'stdregtype',
                                                           'std_template']),
                         name='outputspec')

    outputspec.inputs.stdregtype = stdreg;  # return regtype as well
    # pickindex = lambda x, i: x[i]
    def pickindex(vec, i):
        return [x[i] for x in vec]

    totalWorkflow = nipype.Workflow(wf_name)
    totalWorkflow.connect([
        (inputspec, mybet,
         [('anat', 'inputspec.in_file'),
          ('bet_fract_int_thr', 'inputspec.fract_int_thr'),
          ('bet_vertical_gradient', 'inputspec.vertical_gradient')]),
        (mybet, myfast,
         [('outputspec.brain', 'inputspec.brain')]),
        #(myanat2mni, myfast,
        # [('outputspec.invlinear_xfm','inputspec.stand2anat_xfm')]), # this uses no propr right now ToDo: make settable
        (mybet, myanat2mni,
         [('outputspec.brain', 'inputspec.brain')]),
        (inputspec, myanat2mni,
         [('anat', 'inputspec.skull')]),
        (mybet, outputspec,
         [('outputspec.brain', 'brain'),
          ('outputspec.brain_mask', 'brain_mask')]),
        (inputspec, outputspec,
         [('anat', 'skull')]),
        (myanat2mni, resample_std_ventricle,
         [('outputspec.std_template', 'master')]),
        (myfast, ventricle_mask,
         [('outputspec.probmap_csf', 'in_file')]),

        (ventricle_mask, outputspec,
         [('out_file', 'probmap_ventricle')]),

        (myfast, outputspec,
         [('outputspec.partial_volume_map', 'parvol_map'),
          ('outputspec.probmap_csf', 'probmap_csf'),
          ('outputspec.probmap_gm', 'probmap_gm'),
          ('outputspec.probmap_wm', 'probmap_wm'),
          ('outputspec.parvol_csf', 'parvol_csf'),
          ('outputspec.parvol_gm', 'parvol_gm'),
          ('outputspec.parvol_wm', 'parvol_wm')]),

        (myanat2mni, outputspec,
         [('outputspec.nonlinear_xfm', 'anat2mni_warpfield'),
          ('outputspec.output_brain', 'std_brain'),
          ('outputspec.std_template', 'std_template')]),

    ])

    if stdreg == globals._RegType_.FSL:
        totalWorkflow.connect(resample_std_ventricle, 'out_file', unwarp_ventricle, 'in_file')
        totalWorkflow.connect(inputspec, 'anat', unwarp_ventricle, 'ref_file')
        totalWorkflow.connect(myanat2mni, 'outputspec.invnonlinear_xfm', unwarp_ventricle, 'field_file')
        totalWorkflow.connect(myanat2mni, 'outputspec.invnonlinear_xfm', outputspec, 'mni2anat_warpfield')
        totalWorkflow.connect(unwarp_ventricle, 'out_file', ventricle_mask, 'in_file2')
    else: #ANTs
        totalWorkflow.connect(resample_std_ventricle, 'out_file', unwarp_ventricle, 'input_image')
        totalWorkflow.connect(inputspec, 'anat', unwarp_ventricle, 'reference_image')
        totalWorkflow.connect(myanat2mni, 'outputspec.invnonlinear_xfm', unwarp_ventricle, 'transforms')
        totalWorkflow.connect(myanat2mni, 'outputspec.invnonlinear_xfm', outputspec, 'mni2anat_warpfield')
        totalWorkflow.connect(unwarp_ventricle, 'output_image', ventricle_mask, 'in_file2')

    return totalWorkflow

