import nipype
import nipype.pipeline as pe
import PUMI.anat_preproc.Better as bet
import PUMI.anat_preproc.Faster as fast
import PUMI.anat_preproc.Anat2MNI as anat2mni
import nipype.interfaces.utility as utility

def AnatProc(stdreg=anat2mni.RegType.FSL, SinkDir=".", SinkTag="anat_preproc"):
    """
        Performs processing of anatomical images:
        - reorient
        - brain extraction
        - tissue type segmentation
        - spatial standardization (with either FSL or ANTS)

        Workflow inputs:
            :param anat: The anatomical image file.
            :param SinkDir:
            :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

        Workflow outputs:
            :param



            :return: anatproc_workflow


        Tamas Spisak
        tamas.spisak@uk-essen.de
        2018

        """

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['anat']),
                        name='inputspec')

    # build the actual pipeline
    mybet = bet.bet_workflow(SinkDir=SinkDir)
    myfast = fast.fast_workflow(SinkDir=SinkDir)
    myanat2mni = anat2mni.anat2mni_workflow(SinkDir=SinkDir)

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
                                                           'std_brain']),
                         name='outputspec')


    # pickindex = lambda x, i: x[i]
    def pickindex(vec, i):
        return [x[i] for x in vec]

    totalWorkflow = nipype.Workflow('AnatProc')
    totalWorkflow.base_dir = '.'
    totalWorkflow.connect([
        (inputspec, mybet,
         [('anat', 'inputspec.anat')]),
        (mybet, myfast,
         [('outputspec.brain', 'inputspec.brain')]),
        (mybet, myanat2mni,
         [('outputspec.brain', 'inputspec.brain'),
          ('outputspec.skull', 'inputspec.skull')]),

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

