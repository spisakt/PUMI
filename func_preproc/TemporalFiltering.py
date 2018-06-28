def tmpfilt_workflow(highpass_insec=100,
                     lowpass_insec=10,
                     SinkDir=".",
                     SinkTag="func_preproc",
                     WorkingDirectory="."):
    """
    Modified version of porcupine generated temporal filtering code:

    `source: -`


    Creates a slice time corrected functional image.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

    Workflow outputs:




        :return: tmpfilt_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """

    # Todo
    #This is a Nipype generator. Warning, here be dragons.
    #!/usr/bin/env python
    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.utils.utils_math as utils_math
    import PUMI.func_preproc.info.info_get as info_get
    import PUMI.utils.utils_convert as utils_convert
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'highpass_insec',
                                                          'lowpass_insec',
                                                          'TR']),
                               name = 'inputspec')
    inputspec.inputs.highpass_insec = highpass_insec
    inputspec.inputs.lowpass_insec = lowpass_insec

    #Custom interface wrapping function Sec2sigmaV
    func_sec2sigmaV = pe.Node(interface = utils_math.Sec2sigmaV,
                               name = 'func_sec2sigmaV')
    #Custom interface wrapping function Sec2sigmaV_2
    func_sec2sigmaV_2 = pe.Node(interface = utils_math.Sec2sigmaV,
                               name = 'func_sec2sigmaV_2')

    # Custom interface wrapping function Float2Str
    func_str2float_2 = pe.Node(interface=utils_convert.Float2Str,
                               name='func_str2float_2')

    #Wraps command **fslmaths**
    tmpfilt = pe.Node(interface = fsl.TemporalFilter(),
                               name = 'tmpfilt')

    # Get TR value from header
    TRvalue = pe.Node(interface=info_get.TR,
                      name='TRvalue')
    #Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_tmplfilt']),
                               name = 'outputspec')

    #Generic datasink module to store structured outputs
    ds = pe.Node(interface = io.DataSink(),
                 name = 'ds')
    ds.inputs.base_directory = SinkDir
    #ds.inputs.regexp_substitutions = [("tmpfilt/_NodeName_.{13}", "")]



    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('tmpfiltWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'func', tmpfilt, 'in_file')
    analysisflow.connect(inputspec, 'func', TRvalue, 'in_file')
    analysisflow.connect(TRvalue, 'TR', func_str2float_2, 'float')
    analysisflow.connect(func_str2float_2, 'float', func_sec2sigmaV, 'TR')
    analysisflow.connect(inputspec, 'highpass_insec', func_sec2sigmaV, 'highpasssec')
    analysisflow.connect(func_str2float_2, 'float', func_sec2sigmaV_2, 'TR')
    analysisflow.connect(inputspec, 'lowpass_insec', func_sec2sigmaV_2, 'lowpasssec')
    analysisflow.connect(func_sec2sigmaV, 'sigmaV', tmpfilt, 'highpass_sigma')
    analysisflow.connect(func_sec2sigmaV_2, 'sigmaV', tmpfilt, 'lowpass_sigma')
    analysisflow.connect(tmpfilt, 'out_file', ds, 'tmpfilt')
    analysisflow.connect(tmpfilt, 'out_file', outputspec, 'tmpfilt')



    return analysisflow