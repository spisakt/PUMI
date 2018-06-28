from nipype.interfaces.utility import Function
def get_timecourse(func="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz",
                SinkDir = ".",
                SinkTag = "func_preproc",
                WorkingDirectory="."):
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func']),
                        name='inputspec')
    inputspec.inputs.func = func

    voxroi=pe.Node(fsl.ImageMaths(),
                    name='voxroi')
    #TODO add voxel coordinates
    voxroi.inputs.args='-roi 48 1 48 1 18 1 0 -1 -bin'

    meants=pe.Node(fsl.ImageMeants(),
                       name='meants')

    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.base_directory = SinkDir


    plottimeser=pe.Node(fsl.PlotTimeSeries(),
                        name='plottimeser')

    # Create a workflow
    analysisflow = nipype.Workflow('get_tcWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'func', voxroi, 'in_file')
    analysisflow.connect(voxroi, 'out_file', meants, 'mask')
    analysisflow.connect(inputspec, 'func',  meants, 'in_file')
    analysisflow.connect(meants, 'out_file', plottimeser, 'in_file')
    analysisflow.connect(plottimeser, 'out_file', ds, 'timeseriesimgs')
    analysisflow.connect(meants, 'out_file', ds, 'timeseriesimgs.@parfile')

    return analysisflow


