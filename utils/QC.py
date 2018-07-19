import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as io
from nipype.interfaces.utility import Function
import os

# TODO: its not really .png, its .ppm
def vol2png(qcname, tag="", SinkDir=".", QCDIR="QC"):

    QCDir = os.path.abspath(SinkDir + "/" + QCDIR)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    inputspec = pe.Node(utility.IdentityInterface(fields=['bg_image', 'overlay_image']),
                        name='inputspec')

    # Create png images for quality check
    slicer = pe.MapNode(interface=fsl.Slicer(all_axial=True),
                        iterfield=['in_file', 'image_edges'],
                        name='slicer')
    slicer.inputs.image_width = 5000
    slicer.inputs.out_file = qcname
    # set output all axial slices into one picture
    slicer.inputs.all_axial = True

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                 name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".ppm")]

    analysisflow = pe.Workflow(name=qcname + tag + '_qc')
    analysisflow.connect(inputspec, 'bg_image', slicer, 'in_file')
    analysisflow.connect(inputspec, 'overlay_image', slicer, 'image_edges')
    analysisflow.connect(slicer, 'out_file', ds_qc, qcname)

    return analysisflow


# you must decide whether you want to output timeseries of a voxel or a roi

class TsPlotType:
    ALL = 0  # nothing to specify, will input everything greater than zero
    VOX = 1  # use 'x', 'y', 'z' fields for voxel then
    ROI = 2  # use 'mask' for roi

# HINT: yopu can trey to put various qc images in the same folder by using the tag parameter, like in IcaAroma.py
def timecourse2png(qcname, tag="", type=TsPlotType.ALL, SinkDir=".", QCDIR="QC"):
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import nipype.interfaces.io as io

    QCDir = os.path.abspath(SinkDir + "/" + QCDIR)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func', 'mask', 'x', 'y', 'z']),
                        name='inputspec')

    if type == TsPlotType.VOX:
        voxroi=pe.MapNode(fsl.ImageMaths(),
                          iterfield=['in_file'],
                          name='voxroi')
        #TODO add voxel coordinates
        def setInputs(x,y,z):
            return '-roi '\
                           + str(x) + ' 1 '\
                           + str(y) + ' 1 '\
                           + str(z) + ' 1 0 -1 -bin'

        voxroi_args = pe.Node(Function(input_names=['x', 'y', 'z'],
                                       output_names=['args'],
                                       function=setInputs),
                              name="voxroi_args")
    elif type == TsPlotType.ALL:
        voxroi = pe.MapNode(fsl.ImageMaths(op_string= '-bin'),
                            iterfield=['in_file'],
                            name='voxroi')
    # elif type == TsPloType.ROI: nothing to do here in this case, just connect it


    meants=pe.MapNode(fsl.ImageMeants(),
                      iterfield=['in_file', 'mask'],
                      name='meants')

    plottimeser=pe.MapNode(fsl.PlotTimeSeries(),
                           iterfield=['in_file'],
                           name='plottimeser')

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                    name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Create a workflow
    analysisflow = nipype.Workflow(name=qcname + tag + '_qc')

    if type == TsPlotType.VOX:
        analysisflow.connect(inputspec, 'func', voxroi, 'in_file')
        analysisflow.connect(inputspec, 'x', voxroi_args, 'x')
        analysisflow.connect(inputspec, 'y', voxroi_args, 'y')
        analysisflow.connect(inputspec, 'z', voxroi_args, 'z')
        analysisflow.connect(voxroi_args, 'args', voxroi, 'args')
        analysisflow.connect(voxroi, 'out_file', meants, 'mask')
    elif type == TsPlotType.ALL:
        analysisflow.connect(inputspec, 'func', voxroi, 'in_file')
        analysisflow.connect(voxroi, 'out_file', meants, 'mask')
    elif type == TsPlotType.ROI:
        analysisflow.connect(inputspec, 'mask', meants, 'mask')

    analysisflow.connect(inputspec, 'func',  meants, 'in_file')
    analysisflow.connect(meants, 'out_file', plottimeser, 'in_file')
    analysisflow.connect(plottimeser, 'out_file', ds_qc, qcname)

    return analysisflow

