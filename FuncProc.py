import sys
import nipype
import nipype.pipeline as pe
# import the defined workflow from the func_preproc folder
import PUMI.utils.Concat as conc
import PUMI.func_preproc.Onevol as onevol
import PUMI.func_preproc.MotionCorrecter as mc
import PUMI.func_preproc.Compcor as cmpcor
import PUMI.func_preproc.NuissanceCorr as nuisscorr
import PUMI.func_preproc.TemporalFiltering as tmpfilt
import PUMI.func_preproc.DataCensorer as cens
import PUMI.func_preproc.MedianAngleCorr as medangcor
import nipype.interfaces.utility as utility
import PUMI.utils.globals as globals
import os

def FuncProc(SinkTag="func_preproc", wf_name="funcproc"):
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
    mymc = mc.mc_workflow()
    mycmpcor = cmpcor.compcor_workflow()
    myconc = conc.concat_workflow(numconcat=2)
    mynuisscor = nuisscorr.nuissremov_workflow()
    mytmpfilt = tmpfilt.tmpfilt_workflow()
    mycens = cens.datacens_workflow()
    mymedangcor = medangcor.mac_workflow()

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['mc_func']),
                         name='outputspec')


    wf_mc = nipype.Workflow(wf_name)

    wf_mc.connect([
        (inputspec, mymc,
         [('func', 'inputspec.func')]),
        (mymc, mycmpcor, [('outputspec.func_out_file', 'inputspec.func_aligned')]),
        (inputspec, mycmpcor, [('cc_noise_roi', 'inputspec.mask_file')]),
        (mycmpcor,myconc, [('outputspec.components_file','inputspec.par1')]),
        (mymc, myconc, [('outputspec.first24_file', 'inputspec.par2')]),
        (myconc,mynuisscor, [('outputspec.concat_file', 'inputspec.design_file')]),
        (mymc, mynuisscor, [('outputspec.func_out_file', 'inputspec.in_file')]),
        (mynuisscor,mytmpfilt,[('outputspec.out_file','inputspec.func')]),
        (mytmpfilt,mycens,[('outputspec.func_tmplfilt','inputspec.func')]),
        (mymc,mycens,[('outputspec.mc_par_file','inputspec.movement_parameters')]),
        (mycens, mymedangcor, [('outputspec.scrubbed_image', 'inputspec.realigned_file')]),
                   #(mymedangcor, myfunc2struc, [('outputspec.final_func', 'inputspec.in_file')])
                   ])

    return wf_mc