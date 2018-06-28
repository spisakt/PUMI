def slt_workflow(func="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz",
               slicetiming_txt="alt+z",
               SinkDir=".",
               SinkTag="func_preproc",
               WorkingDirectory="."):

    """
    Modified version of porcupine generated slicetiming code:

    `source: -`


    Creates a slice time corrected functional image.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

    Workflow outputs:




        :return: slt_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """



    # This is a Nipype generator. Warning, here be dragons.
    # !/usr/bin/env python

    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.func_preproc.info.info_get as info_get
    import PUMI.utils.utils_convert as utils_convert
    import nipype.interfaces.afni as afni
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'slicetiming_txt']),
                                    name='inputspec')
    inputspec.inputs.func = func
    inputspec.inputs.slicetiming_txt = slicetiming_txt

    # Custom interface wrapping function TR
    #NodeHash_6000004b9860 = pe.MapNode(interface=info_get.TR, name='NodeName_6000004b9860', iterfield=['in_file'])
    TRvalue = pe.Node(interface=info_get.TR,
                      name='TRvalue')

    # Custom interface wrapping function Str2Float
    func_str2float = pe.Node(interface=utils_convert.Str2Float,
                                name='func_str2float')

    # Custom interface wrapping function Float2Str
    func_str2float_2 = pe.Node(interface=utils_convert.Float2Str,
                               name='func_str2float_2')

    # Wraps command **3dTshift**
    sltcor = pe.Node(interface=afni.TShift(),
                     name='sltcor')
    sltcor.inputs.rltplus = True
    sltcor.inputs.outputtype = "NIFTI_GZ"
    #sltcor.inputs.terminal_output = 'allatonce'

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['slicetimed', 'TR']),
                                    name='outputspec')

    # Custom interface wrapping function JoinVal2Dict
    #func_joinval2dict = pe.Node(interface=utils_convert.JoinVal2Dict,
    #                            name='func_joinval2dict')

    # Generic datasink module to store structured outputs
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir
    #ds.inputs.regexp_substitutions = [("func_slicetimed/_NodeName_.{13}", "")]





    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('slctWorkflow')
    analysisflow.base_dir =WorkingDirectory
    analysisflow.connect(inputspec, 'slicetiming_txt', sltcor, 'tpattern')
    analysisflow.connect(func_str2float, 'float', outputspec, 'TR')
    analysisflow.connect(inputspec, 'func', sltcor, 'in_file')
    analysisflow.connect(inputspec, 'func', TRvalue, 'in_file')
    analysisflow.connect(func_str2float_2, 'str', sltcor, 'tr')
    analysisflow.connect(TRvalue, 'TR', func_str2float_2, 'float')
    #analysisflow.connect(ds, 'out_file', func_joinval2dict, 'keys')
    #analysisflow.connect(func_str2float, 'float', func_joinval2dict, 'vals')
    analysisflow.connect(TRvalue, 'TR', func_str2float, 'str')
    analysisflow.connect(sltcor, 'out_file', ds, 'slicetimed')
    analysisflow.connect(sltcor, 'out_file', outputspec, 'slicetimed')



    return analysisflow




