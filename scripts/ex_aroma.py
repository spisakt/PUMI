#!/usr/bin/env python
import sys
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe

import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import PUMI.AnatProc as anatproc
import PUMI.func_preproc.IcaAroma as aroma
import PUMI.func_preproc.func2standard as func2standard
import PUMI.anat_preproc.Func2Anat as bbr
from nipype.interfaces import fsl
import PUMI.func_preproc.MotionCorrecter as mc
from nipype.interfaces.utility import Function
import PUMI.func_preproc.DataCensorer as dc

from nipype.interfaces import afni
import PUMI.func_preproc.info.info_get as info_get
import os
import PUMI.utils.utils_math as utils_math
import PUMI.utils.utils_convert as utils_convert
import PUMI.utils.globals as globals
import PUMI.utils.QC as qc
# parse command line arguments
if (len(sys.argv) <= 2):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <\"highres_data_template\"> <\"func_data_template\">")
    print("Example:")
    print(sys.argv[0] + " \"highres_data/subject_*.nii.gz\" \"func_data/subject_*.nii.gz\"")
    quit()

# create data grabber
datagrab = pe.Node(nio.DataGrabber(outfields=['func', 'struct']), name='data_grabber')
datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(func=sys.argv[2],
                                      struct=sys.argv[1])  # specified by command line arguments
datagrab.inputs.sort_filelist = True


# sink: file - idx relationship!!
pop_id = pe.Node(interface=utils_convert.List2TxtFile,
                     name='pop_id')
pop_id.inputs.rownum = 0
pop_id.inputs.out_file = "subject_IDs.txt"
pop_id.inputs.filelist = False
ds_id = pe.Node(interface=nio.DataSink(), name='ds_pop_id')
ds_id.inputs.regexp_substitutions = [("(\/)[^\/]*$", "IDs.txt")]
ds_id.inputs.base_directory = globals._SinkDir_


# build the actual pipeline
reorient_struct = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_struct")
reorient_func = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_func")

myanatproc = anatproc.AnatProc(stdreg=globals._RegType_.FSL)  # regtype MUST be FSL for ICA AROMA!!!

mymc = mc.mc_workflow()

mybbr = bbr.bbr_workflow()

mybet = pe.MapNode(interface=fsl.BET(frac=0.3, mask=True),
                   iterfield=['in_file'],
                   name="func_bet")

# Get TR value from header
#TRvalue = pe.MapNode(interface=info_get.TR,
#                     iterfield=['in_file'],
#                     name='TRvalue')

# highpass-filter - no, we dont need it
#tempfilt = pe.MapNode(interface=afni.Bandpass(highpass=0.008,  # TODO: parametrize hpf threshold
#                            outputtype='NIFTI_GZ', despike=False, no_detrend=True, notrans=True),
#                      iterfield=['in_file', 'tr'],
#                      name="highpass_filter")

scale_glob_4d = pe.MapNode(interface=fsl.ImageMaths(op_string="-ing 1000"),
                           iterfield=['in_file'],
                           name='scale')

#todo: parametrize fwhm
myaroma = aroma.aroma_workflow(fwhm=8)

func2std = func2standard.func2mni(stdreg=globals._RegType_.FSL, wf_name='func2std')
func2std_aroma_nonaggr = func2standard.func2mni(stdreg=globals._RegType_.FSL, wf_name='func2std_aroma_nonaggr')
func2std_aroma_aggr = func2standard.func2mni(stdreg=globals._RegType_.FSL, wf_name='func2std_aroma_aggr')

fmri_qc_original = qc.fMRI2QC("carpet_aroma", tag="1_orinal")
fmri_qc_nonaggr = qc.fMRI2QC("carpet_aroma", tag="2_nonaggressive")
fmri_qc_aggr = qc.fMRI2QC("carpet_aroma", tag="3_aggressive")


# compute mean FD
meanFD = pe.MapNode(interface=utils_math.Txt2meanTxt,
                  iterfield=['in_file'],
                  name='meanFD')
meanFD.inputs.axis = 0  # global mean

pop_FD = pe.Node(interface=utils_convert.List2TxtFile,
                     name='pop_FD')  # TODO  sink this

totalWorkflow = nipype.Workflow('exAROMA')
totalWorkflow.base_dir = '.'

# anatomical part and func2anat
totalWorkflow.connect([
    (datagrab, pop_id,
     [('func', 'in_list')]),
    (pop_id, ds_id,
     [('txt_file', 'subjects')]),
    (datagrab, reorient_struct,
     [('struct', 'in_file')]),
    (reorient_struct, myanatproc,
     [('out_file', 'inputspec.anat')]),
    (datagrab, reorient_func,
     [('func', 'in_file')]),
    (reorient_func, mybbr,
     [('out_file', 'inputspec.func')]),
    (myanatproc, mybbr,
      [('outputspec.skull', 'inputspec.skull')]),
    (myanatproc, mybbr,
      [('outputspec.probmap_wm', 'inputspec.anat_wm_segmentation'),
       ('outputspec.probmap_csf', 'inputspec.anat_csf_segmentation'),
       ('outputspec.probmap_gm', 'inputspec.anat_gm_segmentation'),
       ('outputspec.probmap_ventricle', 'inputspec.anat_ventricle_segmentation')]),
    (reorient_func, mymc,
     [('out_file', 'inputspec.func')]),
    (mymc, mybet,
     [('outputspec.func_out_file', 'in_file')]),
    #aroma
    (mymc, scale_glob_4d,
     [('outputspec.func_out_file', 'in_file')]),
    (scale_glob_4d, myaroma,
     [('out_file', 'inputspec.mc_func')]),
    (mymc, myaroma,
     [('outputspec.mc_par_file', 'inputspec.mc_par')]),
    (mybbr, myaroma,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.mat_file'),
      ('outputspec.gm_mask_in_funcspace', 'inputspec.qc_mask')]),
    (myanatproc, myaroma,
    [('outputspec.anat2mni_warpfield', 'inputspec.fnirt_warp_file')]),
    (mybet, myaroma,
     [('mask_file', 'inputspec.mask')]),
    #func2std
    (scale_glob_4d, func2std,
     [('out_file', 'inputspec.func')]),
    (mybbr, func2std,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, func2std,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx')]),
    (myanatproc, func2std,
     [('outputspec.std_brain', 'inputspec.reference_brain')]),

    (myaroma, func2std_aroma_nonaggr,
     [('outputspec.nonaggr_denoised_file', 'inputspec.func')]),
    (mybbr, func2std_aroma_nonaggr,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, func2std_aroma_nonaggr,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx')]),
    (myanatproc, func2std_aroma_nonaggr,
     [('outputspec.std_brain', 'inputspec.reference_brain')]),

    (myaroma, func2std_aroma_aggr,
     [('outputspec.aggr_denoised_file', 'inputspec.func')]),
    (mybbr, func2std_aroma_aggr,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, func2std_aroma_aggr,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx')]),
    (myanatproc, func2std_aroma_aggr,
     [('outputspec.std_brain', 'inputspec.reference_brain')]),
    # carpet plots!!!
    (func2std, fmri_qc_original,
     [('outputspec.func_std', 'inputspec.func')]),
    (mymc, fmri_qc_original,
     [('outputspec.FD_file', 'inputspec.confounds')]),
    (func2std_aroma_nonaggr, fmri_qc_nonaggr,
     [('outputspec.func_std', 'inputspec.func')]),
    (mymc, fmri_qc_nonaggr,
     [('outputspec.FD_file', 'inputspec.confounds')]),
    (func2std_aroma_aggr, fmri_qc_aggr,
     [('outputspec.func_std', 'inputspec.func')]),
    (mymc, fmri_qc_aggr,
     [('outputspec.FD_file', 'inputspec.confounds')]),
    # pop-level mean FD
    (mymc, meanFD,
     [('outputspec.FD_file', 'in_file')]),
    (meanFD, pop_FD,
     [('mean_file', 'in_list')])
    ])

totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run(plugin='MultiProc')