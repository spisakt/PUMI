def onevol_workflow(func="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz",
           SinkDir=".",
           SinkTag="anat_preproc"):


    '''
    This function receive the raw functional image and return its last volume for registration purposes.
    MORE: It also returns information from the header file.
        Workflow inputs:
            :param func: Functional image.
            :param SinkDir:
            :param SinkTag: The output directiry in which the returned images (see workflow outputs) could be found.

        Workflow outputs:


            :return: onevol_workflow - workflow

        Balint Kincses
        kincses.balint@med.u-szeged.hu
        2018

    '''

    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces. fsl as fsl
    import PUMI.func_preproc.info.info_get as info_get
    import PUMI.utils.utils_convert as utils_convert
    import nipype.interfaces.afni as afni
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func']),
                        name='inputspec')
    inputspec.inputs.func=func
    #inputspec.inputs.func = "/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz"

    # Get dimension infos
    idx = pe.Node(interface=info_get.tMinMax,
                      name='idx')

    # Get the last volume of the func image
    fslroi=pe.Node(fsl.ExtractROI(),
                        name='fslroi')
    fslroi.inputs.t_size=1

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func1vol']),
                         name='outputspec')

    # Generic datasink module to store structured outputs
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir

    analysisflow = nipype.Workflow('onevolWorkflow')
    analysisflow.base_dir = '.'
    analysisflow.connect(inputspec, 'func', idx, 'in_files')
    analysisflow.connect(inputspec, 'func', fslroi, 'in_file')
    analysisflow.connect(idx, 'lastvolidx', fslroi, 't_min')
    analysisflow.connect(fslroi, 'roi_file', ds, 'funclastvol')
    analysisflow.connect(fslroi, 'roi_file', outputspec, 'func1vol')


    return  analysisflow