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
import PUMI.anat_preproc.Func2Anat as bbr
from nipype.interfaces import fsl
import PUMI.func_preproc.MotionCorrecter as mc
import os
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


# build the actual pipeline
reorient_struct = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_struct")
reorient_func = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_func")

myanatproc = anatproc.AnatProc(stdreg=anatproc.RegType.FSL)

mymc = mc.mc_workflow()

mybbr = bbr.bbr_workflow()

mybet = pe.MapNode(interface=fsl.BET(frac=0.3, mask=True),
                   iterfield=['in_file'],
                   name="func_bet")

myaroma = aroma.aroma_workflow()

totalWorkflow = nipype.Workflow('exAROMA')
totalWorkflow.base_dir = '.'

# anatomical part and func2anat
totalWorkflow.connect([
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
      [('outputspec.probmap_wm', 'inputspec.anat_wm_segmentation')]),
#    (reorient_func, mymc,
#     [('out_file', 'inputspec.func')]),
#    (reorient_func, mybet,
#     [('out_file', 'in_file')])
#    (mymc, myaroma,
#     [('outputspec.func_out_file', 'inputspec.mc_func'),
#      ('outputspec.mc_par_file', 'inputspec.mc_par')]),
#    (mybbr, myaroma,
#     [('outputspec.func_to_anat_linear_xfm', 'inputspec.mat_file')]),
#    (myanatproc, myaroma,
#     [('outputspec.anat2mni_warpfield', 'inputspec.fnirt_warp_file')]),
#    (mybet, myaroma,
#     [('mask_file', 'inputspec.mask')])
    ])

totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
totalWorkflow.write_graph('graph.dot', graph2use='colored');
totalWorkflow.run(plugin='MultiProc')