def fieldmapper(TE1=4.9,
                TE2=7.3,
                dwell_time=0.00035,
                unwarp_direction="y-",
                SinkTag="func_fieldmapcorr",
                wf_name="fieldmap_correction"):
    import os
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    ###########################################
    # HERE INSERT PORCUPINE GENERATED CODE
    # MUST DEFINE
    # OutJSON: file path to JSON file contaioning the output strings to be returned
    # variables can (should) use variable SinkDir (defined here as function argument)
    ###########################################
    # To do
    ###########################################
    # adjust number of cores with psutil.cpu_count()
    ###########################################
    # also subtract:
    # analysisflow = nipype.Workflow('FieldMapper')
    # analysisflow.base_dir = '.'
    ###########################################
    # Here comes the generated code
    ###########################################

    # This is a Nipype generator. Warning, here be dragons.
    # !/usr/bin/env python
    import sys
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import PUMI.utils.utils_math as utils_math
    import nipype.interfaces.io as io
    import PUMI.utils.QC as qc
    import PUMI.utils.utils_convert as utils_convert

    OutJSON = SinkDir + "/outputs.JSON"

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(
                                    fields=['in_file',
                                            'magnitude',
                                            'phase',
                                            'TE1',
                                            'TE2',
                                            'dwell_time',
                                            'unwarp_direction']),
                                    name='inputspec')
    #defaults:
    #inputspec.inputs.func = func
    #inputspec.inputs.magnitude = magnitude
    #inputspec.inputs.phase = phase
    inputspec.inputs.TE1 = TE1
    inputspec.inputs.TE2 = TE2
    inputspec.inputs.dwell_time = dwell_time
    inputspec.inputs.unwarp_direction = unwarp_direction

    # Wraps command **bet**
    bet = pe.MapNode(interface=fsl.BET(),
                     name='bet',
                     iterfield=['in_file'])
    bet.inputs.mask = True

    # Wraps command **fslmaths**
    erode = pe.MapNode(interface=fsl.ErodeImage(),
                       name='erode',
                       iterfield=['in_file'])

    # Wraps command **fslmaths**
    erode2 = pe.MapNode(interface=fsl.ErodeImage(),
                        name='erode2',
                        iterfield=['in_file'])

    # Custom interface wrapping function SubTwo
    subtract = pe.Node(interface=utils_math.SubTwo,
                       name='subtract')

    # Custom interface wrapping function Abs
    abs = pe.Node(interface=utils_math.Abs,
                  name='abs')

    # Wraps command **fsl_prepare_fieldmap**
    preparefm = pe.MapNode(interface=fsl.PrepareFieldmap(),
                           name='preparefm',
                           iterfield=['in_phase', 'in_magnitude'])

    # Wraps command **fugue**
    fugue = pe.MapNode(interface=fsl.FUGUE(),
                       name='fugue',
                       iterfield=['in_file', 'fmap_in_file', 'mask_file'])

    # Generic datasink module to store structured outputs
    outputspec = pe.Node(interface=io.DataSink(),
                         name='outputspec')
    outputspec.inputs.base_directory = SinkDir
    outputspec.inputs.regexp_substitutions = [("func_fieldmapcorr/_NodeName_.{13}", "")]

    # Generic datasink module to store structured outputs
    outputspec2 = pe.Node(interface=io.DataSink(), name='outputspec2')
    outputspec2.inputs.base_directory = SinkDir
    outputspec2.inputs.regexp_substitutions = [("_NodeName_.{13}", "")]

    myqc_orig = qc.vol2png("fielmap_correction", tag="original")
    myqc_unwarp = qc.vol2png("fielmap_correction", tag="unwarped")

    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)
    analysisflow.base_dir = '.'
    analysisflow.connect(preparefm, 'out_fieldmap', outputspec2, 'fieldmap')
    analysisflow.connect(abs, 'abs', preparefm, 'delta_TE')
    analysisflow.connect(subtract, 'dif', abs, 'x')
    analysisflow.connect(inputspec, 'unwarp_direction', fugue, 'unwarp_direction')
    analysisflow.connect(fugue, 'unwarped_file', outputspec, 'func_fieldmapcorr')
    analysisflow.connect(preparefm, 'out_fieldmap', fugue, 'fmap_in_file')
    analysisflow.connect(erode2, 'out_file', fugue, 'mask_file')
    analysisflow.connect(bet, 'mask_file', erode2, 'in_file')
    analysisflow.connect(inputspec, 'dwell_time', fugue, 'dwell_time')
    analysisflow.connect(inputspec, 'in_file', fugue, 'in_file')
    analysisflow.connect(bet, 'out_file', erode, 'in_file')
    analysisflow.connect(inputspec, 'TE2', subtract, 'b')
    analysisflow.connect(inputspec, 'TE1', subtract, 'a')
    analysisflow.connect(inputspec, 'phase', preparefm, 'in_phase')
    analysisflow.connect(erode, 'out_file', preparefm, 'in_magnitude')
    analysisflow.connect(inputspec, 'magnitude', bet, 'in_file')

    analysisflow.connect(inputspec, 'magnitude', myqc_orig, 'inputspec.bg_image')
    analysisflow.connect(inputspec, 'in_file', myqc_orig, 'inputspec.overlay_image')
    analysisflow.connect( inputspec, 'magnitude', myqc_unwarp, 'inputspec.bg_image')
    analysisflow.connect(fugue, 'unwarped_file',myqc_unwarp, 'inputspec.overlay_image')


    # Run the workflow
    #plugin = 'MultiProc'  # adjust your desired plugin here
    #plugin_args = {'n_procs': psutil.cpu_count()}  # adjust to your number of cores
    #analysisflow.write_graph(graph2use='flat', format='png', simple_form=False)
    #analysisflow.run(plugin=plugin, plugin_args=plugin_args)

    ####################################################################################################
    # Porcupine generated code ends here
    ####################################################################################################

    #load and return json
    # you have to be aware the keys of the json map here

    #ret = json.load(open(OutJSON))
    #return ret['func_fieldmapcorr'], ret['fieldmap']
    return analysisflow


#WorkFlow = Function(input_names=['func', 'magnitude', 'phase', 'TE1', 'TE2', 'dwell_time', 'unwarp_direction', 'SinkDir', 'SinkTag'],
#                    output_names=['func_fieldmapcorr', 'fieldmap'],
#                    function=fieldmapper)

