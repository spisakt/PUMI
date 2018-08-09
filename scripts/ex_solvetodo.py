#!/usr/bin/env python
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
import PUMI.anat_preproc.Better as bet
import PUMI.anat_preproc.Faster as fast
import PUMI.anat_preproc.Anat2MNI as anat2mni
import nipype.interfaces.utility as utility
import nipype.interfaces.io as io

import PUMI.FuncProc as funcproc
# import the necessary workflows from the func_preproc folder
import PUMI.anat_preproc.Func2Anat as bbr
import PUMI.func_preproc.func2standard as transform
import PUMI.utils.utils_convert as utils_convert
import os
import PUMI.utils.globals as globals
#import PUMI.utils.addimages as adding


if (len(sys.argv) > 3):
    globals._SinkDir_ = sys.argv[3]

##############################
_regtype_ = globals._RegType_.FSL
#_regtype_ = globals._RegType_.ANTS
##############################

# create data grabber
datagrab = pe.Node(nio.DataGrabber(outfields=['struct']), name='data_grabber')

datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(struct=sys.argv[1])  # specified by command line arguments
datagrab.inputs.sort_filelist = True

SinkDir = os.path.abspath(globals._SinkDir_ + "/" + "anat_preproc")
    # if not os.path.exists(SinkDir):
    #     os.makedirs(SinkDir)
# Basic interface class generates identity mappings


 # build the actual pipeline
myanatproc = anatproc.AnatProc(stdreg=_regtype_)
myanatproc.inputs.inputspec.bet_fract_int_thr = 0.3  # feel free to adjust, a nice bet is important!
myanatproc.inputs.inputspec.bet_vertical_gradient = -0.3 # feel free to adjust, a nice bet is important!
# try scripts/opt_bet.py to optimise these parameters

ds = pe.Node(interface=io.DataSink(), name='ds')
ds.inputs.base_directory = SinkDir
ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]



totalWorkflow = nipype.Workflow('preprocess_solvetodos')
totalWorkflow.base_dir = '.'

# anatomical part and func2anat
totalWorkflow.connect([
    (datagrab, myanatproc,
        [('struct', 'inputspec.anat')])
    # (mybet, myfast,
    #      [('outputspec.brain', 'inputspec.brain')]),
    # (mybet, myanat2mni,
    #      [('outputspec.brain', 'inputspec.brain')]),
    # (datagrab, myanat2mni,
    #      [('struct', 'inputspec.skull')]),
    # (myanat2mni, myfast,
    #      [('outputspec.invlinear_xfm', 'inputspec.stand2anat_xfm')])
    # (myfast, ds,
    #      [('outputspec.partial_volume_map', 'parvol_map'),
    #       ('outputspec.probmap_csf', 'probmap_csf'),
    #       ('outputspec.probmap_gm', 'probmap_gm'),
    #       ('outputspec.probmap_wm', 'probmap_wm'),
    #       ('outputspec.parvol_csf', 'parvol_csf'),
    #       ('outputspec.parvol_gm', 'parvol_gm'),
    #       ('outputspec.parvol_wm', 'parvol_wm')])
    ])


# RUN #
#from nipype.utils.profiler import log_nodes_cb
#import logging
#callback_log_path = 'run_stats.log'
#logger = logging.getLogger('callback')
#logger.setLevel(logging.DEBUG)
#handler = logging.FileHandler(callback_log_path)
#logger.addHandler(handler)
totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True)
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False)
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run(plugin='MultiProc')

#from nipype.utils.draw_gantt_chart import generate_gantt_chart
#generate_gantt_chart('run_stats.log', cores=8)
