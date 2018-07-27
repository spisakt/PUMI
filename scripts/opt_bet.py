#!/usr/bin/env python
import sys
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
import PUMI.anat_preproc.Better as bet
import PUMI.func_preproc.func2standard as transform
import PUMI.utils.utils_convert as utils_convert
import os
import PUMI.utils.globals as globals
#import PUMI.utils.addimages as adding

# parse command line arguments
if (len(sys.argv) <= 1):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <\"highres_data_template\">  [results_sink_directory]")
    print("Example:")
    print(sys.argv[0] + " \"highres_data/subject_*.nii.gz\" ")
    print "HINT: Make sure to always optimise on an unbiased sample! (considering your outcopme variable.)"
    quit()

if (len(sys.argv) > 2):
    globals._SinkDir_ = sys.argv[2]

###################################################################################################
# NODES

# create data grabber
datagrab = pe.Node(nio.DataGrabber(outfields=['func', 'struct']), name='data_grabber')

datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(struct=sys.argv[1])  # specified by command line arguments
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

mybet = bet.bet_workflow()
mybet.get_node( "inputspec").iterables = [("fract_int_thr", [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]),
                                          ("vertical_gradient", [-0.3, 0, 0.3])]  # set if needed

###################################################################################################
# PIPELINE

totalWorkflow = nipype.Workflow('BET_optimiser')
totalWorkflow.base_dir = '.'

# anatomical part and func2anat
totalWorkflow.connect([
    (datagrab, pop_id,
     [('func', 'in_list')]),
    (pop_id, ds_id,
     [('txt_file', 'subjects')]),
    (datagrab, reorient_struct,
     [('struct', 'in_file')]),
    (reorient_struct, mybet,
     ([('out_file', 'inputspec.in_file')]))
    ])

#from nipype.utils.profiler import log_nodes_cb
# Set path to log file
#import logging
#callback_log_path = 'run_stats.log'
#logger = logging.getLogger('callback')
#logger.setLevel(logging.DEBUG)
#handler = logging.FileHandler(callback_log_path)
#logger.addHandler(handler)
#args_dict = {'n_procs' : 8, 'memory_gb' : 16, 'status_callback' : log_nodes_cb}
totalWorkflow.run(plugin='MultiProc')  #, plugin_args=args_dict)

#from nipype.utils.draw_gantt_chart import generate_gantt_chart
#generate_gantt_chart('run_stats.log', cores=8)