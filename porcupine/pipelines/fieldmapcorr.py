#This is a Nipype generator. Warning, here be dragons.
#!/usr/bin/env python
import sys
import nipype
import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import PUMI.utils.utils_math as utils_math
import nipype.interfaces.io as io

OutJSON = SinkDir + "/outputs.JSON"

#Basic interface class generates identity mappings
NodeHash_604000eb5d20 = pe.Node(utility.IdentityInterface(fields=['func','magnitude','phase','TE1','TE2','dwell_time','unwarp_direction']), name = 'NodeName_604000eb5d20')
NodeHash_604000eb5d20.inputs.func = func
NodeHash_604000eb5d20.inputs.magnitude = magnitude
NodeHash_604000eb5d20.inputs.phase = phase
NodeHash_604000eb5d20.inputs.TE1 = TE1
NodeHash_604000eb5d20.inputs.TE2 = TE2
NodeHash_604000eb5d20.inputs.dwell_time = dwell_time
NodeHash_604000eb5d20.inputs.unwarp_direction = unwarp_direction

#Wraps command **bet**
NodeHash_604000cba700 = pe.MapNode(interface = fsl.BET(), name = 'NodeName_604000cba700', iterfield = ['in_file'])
NodeHash_604000cba700.inputs.mask = True

#Wraps command **fslmaths**
NodeHash_600001ab26c0 = pe.MapNode(interface = fsl.ErodeImage(), name = 'NodeName_600001ab26c0', iterfield = ['in_file'])

#Wraps command **fslmaths**
NodeHash_60c0018a6e40 = pe.MapNode(interface = fsl.ErodeImage(), name = 'NodeName_60c0018a6e40', iterfield = ['in_file'])

#Custom interface wrapping function SubTwo
NodeHash_60c0018a4860 = pe.Node(interface = utils_math.SubTwo, name = 'NodeName_60c0018a4860')

#Custom interface wrapping function Abs
NodeHash_600001eab220 = pe.Node(interface = utils_math.Abs, name = 'NodeName_600001eab220')

#Wraps command **fsl_prepare_fieldmap**
NodeHash_6000018b2600 = pe.MapNode(interface = fsl.PrepareFieldmap(), name = 'NodeName_6000018b2600', iterfield = ['in_phase', 'in_magnitude'])

#Wraps command **fugue**
NodeHash_60c0018a5a60 = pe.MapNode(interface = fsl.FUGUE(), name = 'NodeName_60c0018a5a60', iterfield = ['in_file', 'fmap_in_file', 'mask_file'])

#Generic datasink module to store structured outputs
NodeHash_6000010a5b80 = pe.Node(interface = io.DataSink(), name = 'NodeName_6000010a5b80')
NodeHash_6000010a5b80.inputs.base_directory = SinkDir
NodeHash_6000010a5b80.inputs.regexp_substitutions = [("func_fieldmapcorr/_NodeName_.{13}", "")]

#Generic datasink module to store structured outputs
NodeHash_608001eb9bc0 = pe.Node(interface = io.DataSink(), name = 'NodeName_608001eb9bc0')
NodeHash_608001eb9bc0.inputs.base_directory = SinkDir
NodeHash_608001eb9bc0.inputs.regexp_substitutions = [("fieldmap/_NodeName_.{13}", "")]

#Very simple frontend for storing values into a JSON file.
NodeHash_6000024a5820 = pe.Node(interface = io.JSONFileSink(), name = 'NodeName_6000024a5820')
NodeHash_6000024a5820.inputs.out_file = OutJSON

#Create a workflow to connect all those nodes
analysisflow = nipype.Workflow('MyWorkflow')
analysisflow.connect(NodeHash_608001eb9bc0, 'out_file', NodeHash_6000024a5820, 'fieldmap')
analysisflow.connect(NodeHash_6000018b2600, 'out_fieldmap', NodeHash_608001eb9bc0, 'fieldmap')
analysisflow.connect(NodeHash_6000010a5b80, 'out_file', NodeHash_6000024a5820, 'func_fieldmapcorr')
analysisflow.connect(NodeHash_600001eab220, 'abs', NodeHash_6000018b2600, 'delta_TE')
analysisflow.connect(NodeHash_60c0018a4860, 'dif', NodeHash_600001eab220, 'x')
analysisflow.connect(NodeHash_604000eb5d20, 'unwarp_direction', NodeHash_60c0018a5a60, 'unwarp_direction')
analysisflow.connect(NodeHash_60c0018a5a60, 'unwarped_file', NodeHash_6000010a5b80, 'func_fieldmapcorr')
analysisflow.connect(NodeHash_6000018b2600, 'out_fieldmap', NodeHash_60c0018a5a60, 'fmap_in_file')
analysisflow.connect(NodeHash_60c0018a6e40, 'out_file', NodeHash_60c0018a5a60, 'mask_file')
analysisflow.connect(NodeHash_604000cba700, 'mask_file', NodeHash_60c0018a6e40, 'in_file')
analysisflow.connect(NodeHash_604000eb5d20, 'dwell_time', NodeHash_60c0018a5a60, 'dwell_time')
analysisflow.connect(NodeHash_604000eb5d20, 'func', NodeHash_60c0018a5a60, 'in_file')
analysisflow.connect(NodeHash_604000cba700, 'out_file', NodeHash_600001ab26c0, 'in_file')
analysisflow.connect(NodeHash_604000eb5d20, 'TE2', NodeHash_60c0018a4860, 'b')
analysisflow.connect(NodeHash_604000eb5d20, 'TE1', NodeHash_60c0018a4860, 'a')
analysisflow.connect(NodeHash_604000eb5d20, 'phase', NodeHash_6000018b2600, 'in_phase')
analysisflow.connect(NodeHash_600001ab26c0, 'out_file', NodeHash_6000018b2600, 'in_magnitude')
analysisflow.connect(NodeHash_604000eb5d20, 'magnitude', NodeHash_604000cba700, 'in_file')

#Run the workflow
plugin = 'MultiProc' #adjust your desired plugin here
plugin_args = {'n_procs': 1} #adjust to your number of cores
analysisflow.write_graph(graph2use='flat', format='png', simple_form=False)
analysisflow.run(plugin=plugin, plugin_args=plugin_args)
