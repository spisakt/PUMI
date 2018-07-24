import nipype
import nipype.pipeline as pe
import PUMI.anat_preproc.Better as bet
import PUMI.anat_preproc.Faster as fast
import PUMI.anat_preproc.Anat2MNI as anat2mni
import nipype.interfaces.utility as utility

class RegType:
    FSL = 1
    ANTS = 2

def AnatProc(stdreg=RegType.FSL, SinkTag="anat_preproc", wf_name="anatproc"):
    """
        Performs processing of anatomical images:
        - brain extraction
        - tissue type segmentation
        - spatial standardization (with either FSL or ANTS)

        Images should be already reoriented, e.g. with fsl fslreorient2std (see scripts/ex_pipeline.py)

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
    inputspec = pe.Node(utility.IdentityInterface(fields=['anat']),
                        name='inputspec')

    # build the actual pipeline
    mybet = bet.bet_workflow()
    myfast = fast.fast_workflow()

    if (stdreg==RegType.FSL):
        myanat2mni = anat2mni.anat2mni_fsl_workflow()
    else:  # ANTS
        myanat2mni = anat2mni.anat2mni_ants_workflow()

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['brain',
                                                           'brain_mask',
                                                           'skull',
                                                           'probmap_gm',
                                                           'probmap_wm',
                                                           'probmap_csf',
                                                           'parvol_gm',
                                                           'parvol_wm',
                                                           'parvol_csf',
                                                           'partvol_map',
                                                           'anat2mni_warpfield',
                                                           'std_brain',
                                                           'stdregtype']),
                         name='outputspec')

    outputspec.inputs.stdregtype = stdreg;  # return regtype as well
    # pickindex = lambda x, i: x[i]
    def pickindex(vec, i):
        return [x[i] for x in vec]

    totalWorkflow = nipype.Workflow(wf_name)
    totalWorkflow.connect([
        (inputspec, mybet,
         [('anat', 'inputspec.anat')]),
        (mybet, myfast,
         [('outputspec.brain', 'inputspec.brain')]),
        (mybet, myanat2mni,
         [('outputspec.brain', 'inputspec.brain')]),
        (inputspec, myanat2mni,
         [('anat', 'inputspec.skull')]),
        (mybet, outputspec,
         [('outputspec.skull', 'skull'),
          ('outputspec.brain', 'brain'),
          ('outputspec.brain_mask', 'brain_mask')]),

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
          ('outputspec.output_brain', 'std_brain')]),

    ])

    return totalWorkflow

