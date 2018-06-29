#!/usr/bin/env python
import sys
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
# import the defined workflows from the anat_preproc folder
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import PUMI.anat_preproc.better as bet
import PUMI.anat_preproc.faster as fast
import PUMI.anat_preproc.anat2mni as anat2mni
import PUMI.anat_preproc.bbr as bbr
# import the necessary workflows from the func_preproc folder
import PUMI.func_preproc.onevol as onevol

# a workflown belul az altalunk az elso sorban definialt fgv nevet kell a . utan irni.

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
import os
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

mybet = bet.bet_workflow()
myfast = fast.fast_workflow()
myanat2mni = anat2mni.anat2mni_workflow()
mybbr = bbr.bbr_workflow()
myonevol = onevol.onevol_workflow()
#pickindex = lambda x, i: x[i]
def pickindex(vec, i):
    return [x[i] for x in vec]

totalWorkflow = nipype.Workflow('totalWorkflow')
totalWorkflow.base_dir = '.'
totalWorkflow.connect([
    (datagrab, reorient_struct,
     [('struct', 'in_file')]),
    (reorient_struct, mybet,
     [('out_file', 'inputspec.anat')]),
    (datagrab, reorient_func,
     [('func', 'in_file')]),
    (reorient_func, myonevol,
     [('out_file', 'inputspec.func')]),
    (mybet, myfast,
      [('outputspec.brain', 'inputspec.brain')]),
    (mybet, myanat2mni,
      [('outputspec.brain', 'inputspec.brain'),
       ('outputspec.skull', 'inputspec.skull')]),
    (mybet, mybbr,
      [('outputspec.skull', 'inputspec.skull')]),
    (myfast, mybbr,
      [(('outputspec.probability_maps', pickindex, 2), 'inputspec.anat_wm_segmentation')]),
    (myonevol, mybbr,
     [('outputspec.func1vol', 'inputspec.func')])
    ])


totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
totalWorkflow.write_graph('graph.dot', graph2use='colored');
totalWorkflow.run(plugin='MultiProc')
