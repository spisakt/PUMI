#!/usr/bin/env python
import sys
import os
# walkaround for a bug, ehrn matplotlib is used in threads on MacOS!
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
import nipype.interfaces.io as nio
import PUMI.connectivity.TimeseriesExtractor as tsext
import PUMI.utils.globals as globals

# parse command line arguments
if (len(sys.argv) <= 1):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <\"preprocessed_func_in_std_template\"> [results_sink_directory]")
    print("Example:")
    print(sys.argv[0] + " \"func_preproc/subject_*.nii.gz\"")
    quit()

if (len(sys.argv) > 2):
    globals._SinkDir_ = sys.argv[2]

# create data grabber
datagrab = pe.Node(nio.DataGrabber(outfields=['std_func']), name='data_grabber')

datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(std_func=sys.argv[1])  # specified by command line arguments
datagrab.inputs.sort_filelist = True


# specify atlas:
# name of labelmap nii (or list of probmaps)
_ATLAS_FILE = '/Users/tspisak/data/atlases/MIST/Parcellations/MIST_122.nii.gz'
# a list of labels, where index+1 corresponds to the label in the labelmap
_ATLAS_LABELS = tsext.mist_labels(mist_directory='/Users/tspisak/data/atlases/MIST/', resolution="122")
# a list of labels, where index i corresponds to the module of the i+1th region, this is optional
_ATLAS_MODULES = tsext.mist_modules(mist_directory='/Users/tspisak/data/atlases/MIST/', resolution="122")


myextract = tsext.extract_timeseries()
myextract.inputs.inputspec.atlas_file = _ATLAS_FILE
myextract.inputs.inputspec.labels = _ATLAS_LABELS
myextract.inputs.inputspec.modules = _ATLAS_MODULES

totalWorkflow = pe.Workflow('ex_graph')
totalWorkflow.base_dir="."
totalWorkflow.connect(datagrab, 'std_func', myextract, 'inputspec.std_func')

totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True)
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False)
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run(plugin='MultiProc')
