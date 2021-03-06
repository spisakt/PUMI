def tmpfilt_workflow(highpass_Hz,
                     lowpass_Hz,
                     SinkTag="func_preproc",
                     wf_name="temporal_filtering"):
    #TODO kivezetni a higpass_inseces lowpass_insec valtozokat egy(esetleg kettto)-vel feljebbi szintekre.
    """
    Modified version of porcupine generated temporal filtering code:

    `source: -`


    Creates a slice time corrected functional image.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param highpass: The highpass filter, which is 100s by default.
        :param lowpass: The lowpass filter, which is 1s by default.
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow.

    Workflow outputs:




        :return: tmpfilt_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """

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
    from nipype.interfaces import afni
    import nipype.interfaces.io as io
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    #Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func'
                                                          #'highpass_Hz', # TODO: make these available as input
                                                          #'lowpass_Hz'
                                                           ]),
                               name = 'inputspec')
    #nputspec.inputs.highpass_HZ = highpass_Hz
    #inputspec.inputs.lowpass_Hz = lowpass_Hz

    #Custom interface wrapping function Sec2sigmaV
    #func_sec2sigmaV = pe.MapNode(interface = utils_math.Sec2sigmaV,
    #                            iterfield=['TR'],
    #                          name = 'func_sec2sigmaV')
    #Custom interface wrapping function Sec2sigmaV_2
    #func_sec2sigmaV_2 = pe.MapNode(interface = utils_math.Sec2sigmaV,
    #                               iterfield=['TR'],
    #                           name = 'func_sec2sigmaV_2')

    # Custom interface wrapping function Str2Func
    func_str2float = pe.MapNode(interface=utils_convert.Str2Float,
                                iterfield=['str'],
                               name='func_str2float')

    #Wraps command **fslmaths**
    # TODO_done: change highpass filter to AFNI implewmentation:
    # https://neurostars.org/t/bandpass-filtering-different-outputs-from-fsl-and-nipype-custom-function/824
    #tmpfilt = pe.MapNode(interface=fsl.TemporalFilter(),
    #                     iterfield=['in_file','highpass','lowpass'],
    #                           name = 'tmpfilt')

    tmpfilt = pe.MapNode(interface=afni.Bandpass(highpass=highpass_Hz, lowpass=lowpass_Hz),
                         iterfield=['in_file', 'tr'],
                         name='tmpfilt')
    tmpfilt.inputs.despike = False
    tmpfilt.inputs.no_detrend = False #True
    tmpfilt.inputs.notrans = True  # hopefully there are no initial transients in our data
    tmpfilt.inputs.outputtype = 'NIFTI_GZ'
    # Get TR value from header
    TRvalue = pe.MapNode(interface=info_get.TR,
                         iterfield=['in_file'],
                      name='TRvalue')

    myqc = qc.timecourse2png("timeseries", tag="030_filtered_" + str(highpass_Hz).replace('0.','') + "_" + str(lowpass_Hz).replace('0.','') + "_Hz")

    #Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_tmplfilt']),
                               name='outputspec')

    #Generic datasink module to store structured outputs
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir
    #ds.inputs.regexp_substitutions = [("tmpfilt/_NodeName_.{13}", "")]



    #Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)
    analysisflow.connect(inputspec, 'func', tmpfilt, 'in_file')
    analysisflow.connect(inputspec, 'func', TRvalue, 'in_file')
    analysisflow.connect(TRvalue, 'TR', func_str2float, 'str')
    analysisflow.connect(func_str2float, 'float', tmpfilt, 'tr')
    #analysisflow.connect(inputspec, 'highpass_Hz', tmpfilt, 'highpass')
    #analysisflow.connect(inputspec, 'lowpass_Hz', tmpfilt, 'lowpass')
    analysisflow.connect(tmpfilt, 'out_file', ds, 'tmpfilt')
    analysisflow.connect(tmpfilt, 'out_file', outputspec, 'func_tmplfilt')
    analysisflow.connect(tmpfilt, 'out_file', myqc, 'inputspec.func')



    return analysisflow