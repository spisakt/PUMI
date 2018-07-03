#!/usr/bin/env python
import sys
# sys.path.append("/Users/tspisak/src/") #PUMI should be added to the path by install or by the developer

# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
# TODO set a datagrabber
# import the defined workflow from the func_preproc folder
import PUMI.func_preproc.Onevol as onevol
import PUMI.func_preproc.MotionCorrecter as mc
import PUMI.func_preproc.Compcor as cmpcor
import PUMI.func_preproc.NuissanceCorr as nuisscorr
import PUMI.func_preproc.TemporalFiltering as tmpfilt
import PUMI.func_preproc.DataCensorer as cens
import PUMI.func_preproc.MedianAngleCorr as medangcor

# TODO set an auxiliary workflow/node to concatenate regressor (txt) files-its name should be concat.py
# TODO set an auxiliary workflow/node to convert anatomical mask files to functional space(or put these nodes in the bbr workflow...?)-its name should be anat2funcmask.py
# TODO set the last workflow: the func2standard.py which use the final preprocessed functional data nad the wrapped field from the anatprocessing subpipeline.
# a workflown belul az altalunk az elsosorban definialt fgv nevet kell a . utan irni.

# parse command line arguments
if (len(sys.argv) <= 1):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <functional_data_template>")
    print("Example:")
    print(sys.argv[0] + " <func_data/subject_*.nii.gz>")
    quit()

# create data grabber

# build the actual pipeline
myonevol = onevol.onevol_workflow()
mymc = mc.mc_workflow()
mycmpcor = cmpcor.compcor_workflow()
mynuisscor = nuisscorr.nuissremov_workflow()
mytmpfilt = tmpfilt.tmpfilt_workflow()
mycens = cens.datacens_workflow()
mymedangcor = medangcor.mac_workflow()

total = nipype.Workflow('totalWorkflow')
total.base_dir = '.'
total.connect([(mymc, mycmpcor, [('outputspec.func_out_file', 'inputspec.func_aligned')]),
               (myanat2funcmask, mycmpcor, [('outputspec.mask', 'inputspec.mask')]),
               (mycompcor, myconcat, [('outputspec.components_file', 'inputspec.arg1')]),
               (mymc, myconcat, [('outputspec.mvpar_file', 'inputspec.arg2')]),
               (myconcat, mycmpcor, [('outputspec.out_file', 'inputspec.design_file')]),
               (mymc, mycmpcor, [('outputspec.func_out_file', 'inputspec.in_file')]),
               (mycmpcor, mytmpfilt, [('outputspec.out_file', 'inputspec.func')]),
               (mytmpfilt, mycens, [('outputspec.func_tmplfilt', 'inputspec.func')]),
               (mymc, mycens, [('outputspec.mat_file', 'inputspec.movement_parameters')]),
               (mycens, mymedangcor, [('outputspec.scrubbed_image', 'inputspec.realigned_file')]),
               (mymedangcor, myfunc2struc, [('outputspec.final_func', 'inputspec.in_file')])
               ])
total.run()
