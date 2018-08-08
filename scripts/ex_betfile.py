#!/usr/bin/env python


import os
import sys
import nipype
import nipype.pipeline as pe
import nipype.interfaces.io as nio
import PUMI.anat_preproc.Better as bet

import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as io
import PUMI.utils.QC as qc
import PUMI.utils.globals as globals


datagrab = pe.Node(nio.DataGrabber(outfields=['struct']),
                   name='data_grabber')
datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(struct=sys.argv[1])  # specified by command line arguments
datagrab.inputs.sort_filelist = True


reorient_struct = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_struct")

bet = pe.MapNode(interface=fsl.BET(),
                     iterfield=['in_file'],
                 #iterables=[('frac',[0.3,0.8])],
                  name='bet')

myqc = qc.vol2png("brain_extraction", overlay=True)

totalWorkflow = nipype.Workflow('bet_probe')
totalWorkflow.base_dir = '.'

totalWorkflow.connect([
    (datagrab,reorient_struct,
     [('struct','in_file')]),
    (reorient_struct, bet,
     [('out_file', 'in_file')]),
    (bet,myqc,
     [('out_file', 'inputspec.overlay_image')]),
    (reorient_struct, myqc,
     [('out_file','inputspec.bg_image')])
    ])

totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True)
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False)
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run()



