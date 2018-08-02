#!/usr/bin/env python
import sys
import os
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import PUMI.func_preproc.FieldMapper as fm


datagrab = pe.Node(nio.DataGrabber(outfields=['func',
                                              'phase',
                                              'magnitude',
                                              'TE1',
                                              'TE2',
                                              'dwelltime']), name='data_grabber')

datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.sort_filelist = True


reorient_func = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_func")

myfm=fm.fielmapper()

totalWorkflow = nipype.Workflow('fm_probe')
totalWorkflow.base_dir = '.'

totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True)
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False)
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run()
