import sys
import nipype
import nipype.pipeline as pe
# import the defined workflow from the func_preproc folder
import PUMI.utils.Concat as conc
import PUMI.anat_preproc.Better as bet
import PUMI.func_preproc.MotionCorrecter as mc
import PUMI.func_preproc.Compcor as cmpcor
import PUMI.func_preproc.NuissanceCorr as nuisscorr
import PUMI.func_preproc.TemporalFiltering as tmpfilt
import PUMI.func_preproc.DataCensorer as cens
import PUMI.func_preproc.MedianAngleCorr as medangcor
import PUMI.func_preproc.DataCensorer as scrub
import nipype.interfaces.utility as utility
import nipype.interfaces.afni as afni
import PUMI.utils.globals as globals

import os

def FuncProc(stdrefvol="mid",SinkTag="func_preproc", wf_name="funcproc"):
    """
        Performs processing of functional (resting-state) images:

        Images should be already reoriented, e.g. with fsl fslreorient2std (see scripts/ex_pipeline.py)

        Workflow inputs:
            :param func: The functional image file.
            :param SinkDir: where to write important ouputs
            :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

        Workflow outputs:
            :param



            :return: anatproc_workflow


        Tamas Spisak
        tamas.spisak@uk-essen.de
        2018

        """

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func', 'cc_noise_roi']),
                        name='inputspec')

    # build the actual pipeline
    #myonevol = onevol.onevol_workflow(SinkDir=SinkDir)
    mybet = bet.bet_workflow(SinkTag="func_preproc", fmri=True, wf_name="brain_extraction_func")
    mymc = mc.mc_workflow_fsl(reference_vol=stdrefvol)
    mycmpcor = cmpcor.compcor_workflow()
    myconc = conc.concat_workflow(numconcat=2)
    mynuisscor = nuisscorr.nuissremov_workflow()
    mytmpfilt = tmpfilt.tmpfilt_workflow(highpass_Hz=0.008, lowpass_Hz=0.08)
    mycens = cens.datacens_workflow_percent()
    mymedangcor = medangcor.mac_workflow()

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_mc',
                                                           'func_mc_nuis',
                                                           'func_mc_nuis_bpf',
                                                           'func_mc_nuis_bpf_cens',
                                                           'func_mc_nuis_bpf_cens_medang',
                                                            # non-image data
                                                           'FD'
                                                           ]),
                         name='outputspec')
    wf_mc = nipype.Workflow(wf_name)

    wf_mc.connect([
        (inputspec, mybet,
         [('func', 'inputspec.in_file')]),
        (mybet, mymc,
         [('outputspec.brain', 'inputspec.func')]),
        (mymc, mycmpcor, [('outputspec.func_out_file', 'inputspec.func_aligned')]),
        (inputspec, mycmpcor, [('cc_noise_roi', 'inputspec.mask_file')]),
        (mycmpcor,myconc, [('outputspec.components_file','inputspec.par1')]),
        (mymc, myconc, [('outputspec.first24_file', 'inputspec.par2')]),
        (myconc,mynuisscor, [('outputspec.concat_file', 'inputspec.design_file')]),
        (mymc, mynuisscor, [('outputspec.func_out_file', 'inputspec.in_file')]),
        (mynuisscor,mytmpfilt,[('outputspec.out_file','inputspec.func')]),
        (mytmpfilt,mycens,[('outputspec.func_tmplfilt','inputspec.func')]),
        (mymc,mycens,[('outputspec.FD_file','inputspec.FD')]),
        (mybet,mymedangcor, [('outputspec.brain_mask','inputspec.mask')]),
        (mycens, mymedangcor, [('outputspec.scrubbed_image', 'inputspec.realigned_file')]),
        # outputspec
        (mymc, outputspec, [('outputspec.func_out_file', 'func_mc')]),
        (mynuisscor, outputspec, [('outputspec.out_file', 'func_mc_nuis')]),
        (mytmpfilt, outputspec, [('outputspec.func_tmplfilt', 'func_mc_nuis_bpf')]),
        (mycens, outputspec, [('outputspec.scrubbed_image', 'func_mc_nuis_bpf_cens')]),
        (mymedangcor, outputspec, [('outputspec.final_func', 'func_mc_nuis_bpf_cens_medang')]),
        # non-image data:
        (mycens, outputspec, [('outputspec.FD', 'FD')])
                   ])

    return wf_mc

def FuncProc_cpac(stdrefvol="mid",SinkTag="func_preproc", wf_name="funcproc"):
    """
        Performs processing of functional (resting-state) images, closely replicating the results of C-PAC,
        with the conf file: etc/cpac_conf.yml

        Images should be already reoriented, e.g. with fsl fslreorient2std (see scripts/ex_pipeline.py)

        Workflow inputs:
            :param func: The functional image file.
            :param SinkDir: where to write important ouputs
            :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

        Workflow outputs:
            :param



            :return: anatproc_workflow


        Tamas Spisak
        tamas.spisak@uk-essen.de
        2018

        """

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func', 'cc_noise_roi']),
                        name='inputspec')

    # build the actual pipeline
    #myonevol = onevol.onevol_workflow(SinkDir=SinkDir)
    mymc = mc.mc_workflow_afni(reference_vol=stdrefvol, FD_mode = "Power")
    mybet = bet.bet_workflow(SinkTag="func_preproc", fmri=True,
                             wf_name="brain_extraction_func")  # do it with Automaks of AFNI?
    mycmpcor = cmpcor.compcor_workflow()
    mydespike = cens.despike_workflow()
    myconc = conc.concat_workflow(numconcat=3)
    mynuisscor = nuisscorr.nuissremov_workflow()
    mymedangcor = medangcor.mac_workflow()
    mytmpfilt = tmpfilt.tmpfilt_workflow(highpass_Hz=0.01, lowpass_Hz=0.08)


    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_mc',
                                                           'func_mc_nuis',
                                                           'func_mc_nuis_medang',
                                                           'func_mc_nuis_medang_bpf',
                                                            # non-image data
                                                           'FD'
                                                           ]),
                         name='outputspec')
    wf_mc = nipype.Workflow(wf_name)

    wf_mc.connect([
        (inputspec, mymc,
         [('func', 'inputspec.func')]),
        (mymc, mybet,
         [('outputspec.func_out_file', 'inputspec.in_file')]),
        (mybet, mycmpcor, [('outputspec.brain', 'inputspec.func_aligned')]),
        (inputspec, mycmpcor, [('cc_noise_roi', 'inputspec.mask_file')]),
        (mymc, mydespike, [("outputspec.FD_file", "inputspec.FD")]),
        (mycmpcor, myconc, [('outputspec.components_file', 'inputspec.par1')]),
        (mymc, myconc, [('outputspec.first24_file', 'inputspec.par2')]),
        (mydespike, myconc, [('outputspec.despike_mat', 'inputspec.par3')]),
        (myconc,mynuisscor, [('outputspec.concat_file', 'inputspec.design_file')]),
        (mybet, mynuisscor, [('outputspec.brain', 'inputspec.in_file')]),
        (mybet, mymedangcor, [('outputspec.brain_mask', 'inputspec.mask')]),
        (mynuisscor, mymedangcor, [('outputspec.out_file', 'inputspec.realigned_file')]),
        (mymedangcor, mytmpfilt, [('outputspec.final_func', 'inputspec.func')]),

        # outputspec
        (mymc, outputspec, [('outputspec.func_out_file', 'func_mc')]),
        (mynuisscor, outputspec, [('outputspec.out_file', 'func_mc_nuis')]),
        (mymedangcor, outputspec, [('outputspec.final_func', 'func_mc_nuis_medang')]),
        (mytmpfilt, outputspec, [('outputspec.func_tmplfilt', 'func_mc_nuis_medang_bpf')]),

        # non-image data:
        (mymc, outputspec, [('outputspec.FD_file', 'FD')]),
                   ])

    return wf_mc

def FuncProc_despike_afni(stdrefvol="mid",SinkTag="func_preproc", wf_name="func_preproc_dspk_afni"):
    """
        Performs processing of functional (resting-state) images:

        Images should be already reoriented, e.g. with fsl fslreorient2std (see scripts/ex_pipeline.py)

        Workflow inputs:
            :param func: The functional image file.
            :param SinkDir: where to write important ouputs
            :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

        Workflow outputs:
            :param



            :return: anatproc_workflow


        Tamas Spisak
        tamas.spisak@uk-essen.de
        2018

        """

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func', 'cc_noise_roi']),
                        name='inputspec')

    # build the actual pipeline
    #myonevol = onevol.onevol_workflow(SinkDir=SinkDir)
    mybet = bet.bet_workflow(SinkTag="func_preproc", fmri=True, wf_name="brain_extraction_func")
    mymc = mc.mc_workflow_fsl(reference_vol=stdrefvol)

    mydespike = pe.MapNode(afni.Despike(outputtype="NIFTI_GZ"),  # I do it after motion correction...
                           iterfield=['in_file'],
                           name="DeSpike")

    mycmpcor = cmpcor.compcor_workflow() # to  WM+CSF signal
    myconc = conc.concat_workflow(numconcat=2)
    mynuisscor = nuisscorr.nuissremov_workflow() # regress out 5 compcor variables and the Friston24
    #mymedangcor = medangcor.mac_workflow() #skip it this time
    mytmpfilt = tmpfilt.tmpfilt_workflow(highpass_Hz=0.008, lowpass_Hz=0.08) #will be done by the masker?

    myscrub = scrub.datacens_workflow_threshold(ex_before=0, ex_after=0)
    # "liberal scrubbing" since despiking was already performed

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=[
                                                           'func_preprocessed',
                                                           'func_preprocessed_scrubbed'
                                                            # non-image data
                                                           'FD'
                                                           ]),
                         name='outputspec')
    wf_mc = nipype.Workflow(wf_name)

    wf_mc.connect([
        (inputspec, mybet,
         [('func', 'inputspec.in_file')]),
        (mybet, mymc,
         [('outputspec.brain', 'inputspec.func')]),
        (mymc, mydespike, [('outputspec.func_out_file', 'in_file')]),
        (mydespike, mycmpcor, [('out_file', 'inputspec.func_aligned')]),
        (inputspec, mycmpcor, [('cc_noise_roi', 'inputspec.mask_file')]),
        (mycmpcor,myconc, [('outputspec.components_file','inputspec.par1')]),
        (mymc, myconc, [('outputspec.first24_file', 'inputspec.par2')]),
        (myconc,mynuisscor, [('outputspec.concat_file', 'inputspec.design_file')]),
        (mydespike, mynuisscor, [('out_file', 'inputspec.in_file')]),
        (mynuisscor,mytmpfilt,[('outputspec.out_file','inputspec.func')]),
        (mytmpfilt, myscrub, [('outputspec.func_tmplfilt', 'inputspec.func')]),
        (mymc, myscrub, [('outputspec.FD_file', 'inputspec.FD')]),

        (mytmpfilt,outputspec,[('outputspec.func_tmplfilt','func_preprocessed')]),
        # non-image data:
        (mymc, outputspec, [('outputspec.FD_file', 'FD')]),
        (myscrub, outputspec, [('outputspec.scrubbed_image', 'func_preprocessed_scrubbed')]),
                   ])

    return wf_mc
