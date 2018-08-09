def onevol_workflow(SinkTag="anat_preproc", wf_name="get_example_vol"):


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

    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces. fsl as fsl
    import PUMI.func_preproc.info.info_get as info_get
    import nipype.interfaces.io as io
    import PUMI.utils.globals as globals

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func']),
                        name='inputspec')
    #inputspec.inputs.func = "/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz"

    # Get dimension infos
    idx = pe.MapNode(interface=info_get.tMinMax,
                     iterfield=['in_files'],
                     name='idx')

    # Get the last volume of the func image
    fslroi = pe.MapNode(fsl.ExtractROI(),
                      iterfield=['in_file', 't_min'],
                      name='fslroi')
    fslroi.inputs.t_size = 1

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func1vol']),
                         name='outputspec')

    # Generic datasink module to store structured outputs
    ds = pe.Node(interface=io.DataSink(),
                 name='ds')
    ds.inputs.base_directory = SinkDir
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    analysisflow = nipype.Workflow(wf_name)
    analysisflow.connect(inputspec, 'func', idx, 'in_files')
    analysisflow.connect(inputspec, 'func', fslroi, 'in_file')
    analysisflow.connect(idx, 'refvolidx', fslroi, 't_min')
    analysisflow.connect(fslroi, 'roi_file', ds, 'funclastvol')
    analysisflow.connect(fslroi, 'roi_file', outputspec, 'func1vol')


    return  analysisflow