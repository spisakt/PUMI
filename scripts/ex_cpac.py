#!/usr/bin/env python
# This is a PUMI pipeline closely replicating the results of C-PAC, with the configuration file

import sys
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
# import the defined workflows from the anat_preproc folder
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni as afni
import PUMI.AnatProc as anatproc
import PUMI.FuncProc as funcproc
# import the necessary workflows from the func_preproc folder
import PUMI.anat_preproc.Func2Anat as bbr
import PUMI.func_preproc.func2standard as transform
import PUMI.utils.utils_convert as utils_convert
import os
import PUMI.utils.globals as globals
#import PUMI.utils.addimages as adding

# parse command line arguments
if (len(sys.argv) <= 2):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <\"highres_data_template\"> <\"func_data_template\"> [results_sink_directory]")
    print("Example:")
    print(sys.argv[0] + " \"highres_data/subject_*.nii.gz\" \"func_data/subject_*.nii.gz\"")
    quit()

if (len(sys.argv) > 3):
    globals._SinkDir_ = sys.argv[3]

##############################
_regtype_ = globals._RegType_.FSL
#_regtype_ = globals._RegType_.ANTS
##############################

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

myanatproc = anatproc.AnatProc(stdreg=_regtype_)
myanatproc.inputs.inputspec.bet_fract_int_thr = 0.3  # feel free to adjust, a nice bet is important!
myanatproc.inputs.inputspec.bet_vertical_gradient = -0.3 # feel free to adjust, a nice bet is important!
# try scripts/opt_bet.py to optimise these parameters

mybbr = bbr.bbr_workflow()
# Add arbitrary number of nii images wthin the same space. The default is to add csf and wm masks for anatcompcor calculation.
#myadding=adding.addimgs_workflow(numimgs=2)
add_masks = pe.MapNode(fsl.ImageMaths(op_string=' -add'),
                       iterfield=['in_file', 'in_file2'],
                       name="addimgs")

# TODO_ready: erode compcor noise mask!!!!
erode_mask = pe.MapNode(fsl.ErodeImage(),
                        iterfield=['in_file'],
                        name="erode_compcor_mask")

def pickindex(vec, i):
    return [x[i] for x in vec]

myfuncproc = funcproc.FuncProc_cpac()

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
    (reorient_struct, mybbr,
     [('out_file', 'inputspec.skull')]),
    (datagrab, reorient_func,
     [('func', 'in_file')]),
    (reorient_func, mybbr,
     [('out_file', 'inputspec.func')]),
    (myanatproc, mybbr,
      [('outputspec.probmap_wm', 'inputspec.anat_wm_segmentation'),
       ('outputspec.probmap_csf', 'inputspec.anat_csf_segmentation'),
       ('outputspec.probmap_gm', 'inputspec.anat_gm_segmentation'),
       ('outputspec.probmap_ventricle', 'inputspec.anat_ventricle_segmentation')])

    ])

# functional part
totalWorkflow.connect([
    (reorient_func, myfuncproc,
     [('out_file', 'inputspec.func')]),
    (mybbr, add_masks,
     [('outputspec.ventricle_mask_in_funcspace','in_file'),
      ('outputspec.wm_mask_in_funcspace','in_file2')]),
    (add_masks, erode_mask,
     [('out_file','in_file')]),
    (erode_mask, myfuncproc,
     [('out_file','inputspec.cc_noise_roi')])
    ])