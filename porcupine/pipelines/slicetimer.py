#This is a Nipype generator. Warning, here be dragons.
#!/usr/bin/env python
import sys
import nipype
import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import PUMI.func_preproc.info.info_get as info_get
import PUMI.utils.utils_convert as utils_convert
import nipype.interfaces.afni as afni
import nipype.interfaces.io as io

OutJSON = SinkDir + "/outputs.JSON"
WorkingDirectory = "."

#Basic interface class generates identity mappings
NodeHash_6040006ae640 = pe.Node(utility.IdentityInterface(fields=['func','slicetiming_txt']), name = 'NodeName_6040006ae640')
NodeHash_6040006ae640.inputs.func = func
NodeHash_6040006ae640.inputs.slicetiming_txt = slicetiming_txt

#Custom interface wrapping function TR
NodeHash_6000004b9860 = pe.MapNode(interface = info_get.TR, name = 'NodeName_6000004b9860', iterfield = ['in_file'])

#Custom interface wrapping function Str2Float
NodeHash_6040006ae9a0 = pe.MapNode(interface = utils_convert.Str2Float, name = 'NodeName_6040006ae9a0', iterfield = ['str'])

#Custom interface wrapping function Float2Str
NodeHash_6040004aee80 = pe.MapNode(interface = utils_convert.Float2Str, name = 'NodeName_6040004aee80', iterfield = ['float'])

#Wraps command **3dTshift**
NodeHash_6040004ad140 = pe.MapNode(interface = afni.TShift(), name = 'NodeName_6040004ad140', iterfield = ['in_file', 'tr'])
NodeHash_6040004ad140.inputs.rltplus = True
NodeHash_6040004ad140.inputs.outputtype = "NIFTI_GZ"
NodeHash_6040004ad140.inputs.terminal_output = 'allatonce'

#Generic datasink module to store structured outputs
NodeHash_6080008b3d40 = pe.Node(interface = io.DataSink(), name = 'NodeName_6080008b3d40')
NodeHash_6080008b3d40.inputs.base_directory = SinkDir
NodeHash_6080008b3d40.inputs.regexp_substitutions = [("func_slicetimed/_NodeName_.{13}", "")]

#Basic interface class generates identity mappings
NodeHash_6080008b5660 = pe.Node(utility.IdentityInterface(fields=['func_slicetimed','TR']), name = 'NodeName_6080008b5660')

#Custom interface wrapping function JoinVal2Dict
NodeHash_6040004afde0 = pe.Node(interface = utils_convert.JoinVal2Dict, name = 'NodeName_6040004afde0')

#Very simple frontend for storing values into a JSON file.
NodeHash_6080008b5240 = pe.Node(interface = io.JSONFileSink(), name = 'NodeName_6080008b5240')
NodeHash_6080008b5240.inputs.out_file = OutJSON

#Very simple frontend for storing values into a JSON file.
NodeHash_6080008b7400 = pe.Node(interface = io.JSONFileSink(), name = 'NodeName_6080008b7400')
NodeHash_6080008b7400.inputs.out_file = SinkDir + "/TR.json"

#Create a workflow to connect all those nodes
analysisflow = nipype.Workflow('MyWorkflow')
analysisflow.connect(NodeHash_6040006ae640, 'slicetiming_txt', NodeHash_6040004ad140, 'tpattern')
analysisflow.connect(NodeHash_6040006ae9a0, 'float', NodeHash_6080008b5660, 'TR')
analysisflow.connect(NodeHash_6040006ae640, 'func', NodeHash_6040004ad140, 'in_file')
analysisflow.connect(NodeHash_6040006ae640, 'func', NodeHash_6000004b9860, 'in_file')
analysisflow.connect(NodeHash_6040004aee80, 'str', NodeHash_6040004ad140, 'tr')
analysisflow.connect(NodeHash_6000004b9860, 'TR', NodeHash_6040004aee80, 'float')
analysisflow.connect(NodeHash_6080008b3d40, 'out_file', NodeHash_6040004afde0, 'keys')
analysisflow.connect(NodeHash_6040004afde0, 'dict', NodeHash_6080008b7400, 'in_dict')
analysisflow.connect(NodeHash_6040006ae9a0, 'float', NodeHash_6040004afde0, 'vals')
analysisflow.connect(NodeHash_6000004b9860, 'TR', NodeHash_6040006ae9a0, 'str')
analysisflow.connect(NodeHash_6040004ad140, 'out_file', NodeHash_6080008b3d40, 'func_slicetimed')
analysisflow.connect(NodeHash_6040004ad140, 'out_file', NodeHash_6080008b5660, 'func_slicetimed')
analysisflow.connect(NodeHash_6080008b5660, 'TR', NodeHash_6080008b5240, 'TR')
analysisflow.connect(NodeHash_6080008b3d40, 'out_file', NodeHash_6080008b5240, 'func_slicetimed')

#Run the workflow
plugin = 'MultiProc' #adjust your desired plugin here
plugin_args = {'n_procs': 1} #adjust to your number of cores
analysisflow.write_graph(graph2use='flat', format='png', simple_form=False)
analysisflow.run(plugin=plugin, plugin_args=plugin_args)
