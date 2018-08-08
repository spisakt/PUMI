import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as io
from nipype.interfaces.utility import Function
import os
import PUMI.utils.globals as globals

# TODO_ready: its not really .png, its .ppm
# HINT: you can try to put various qc images in the same folder by using the tag parameter, like e.g. in IcaAroma.py
def vol2png(qcname, tag="", overlay=True, overlayiterated=True):

    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    inputspec = pe.Node(utility.IdentityInterface(fields=['bg_image', 'overlay_image']),
                        name='inputspec')

    # Create png images for quality check
    if overlay & overlayiterated:
        slicer = pe.MapNode(interface=fsl.Slicer(),
                        iterfield=['in_file', 'image_edges'],
                        name='slicer')
    else:
        slicer = pe.MapNode(interface=fsl.Slicer(),
                            iterfield=['in_file'],
                            name='slicer')

    slicer.inputs.image_width = 2000
    slicer.inputs.out_file = qcname
    # set output all axial slices into one picture
    slicer.inputs.sample_axial = 5
    #slicer.inputs.middle_slices = True

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                 name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".ppm")]

    analysisflow = pe.Workflow(name=qcname + tag + '_qc')

    analysisflow.connect(inputspec, 'bg_image', slicer, 'in_file')
    if overlay:
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

    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
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
        # TODO test
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


def fMRI2QC(qcname, tag="", SinkDir=".", QCDIR="QC"):
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.plot.image as plot

    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func', 'atlas', 'confounds']),
                        name='inputspec')
    inputspec.inputs.atlas = globals._FSLDIR_ + '/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-3mm.nii.gz'


    plotfmri = pe.MapNode(interface=Function(input_names=['func', 'atlaslabels', 'confounds', 'output_file'],
                                                  output_names=['plotfile'],
                                                  function=plot.plot_fmri_qc),
                               iterfield=['func', 'confounds'],
                               name="qc_fmri")
    plotfmri.inputs.output_file = "qc_fmri.png"
    # default atlas works only for standardized, 3mm-resoultion data

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                    name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Create a workflow
    analysisflow = nipype.Workflow(name=qcname + tag + '_qc')

    analysisflow.connect(inputspec, 'func', plotfmri, 'func')
    analysisflow.connect(inputspec, 'atlas', plotfmri, 'atlaslabels')
    analysisflow.connect(inputspec, 'confounds', plotfmri, 'confounds')

    analysisflow.connect(plotfmri, 'plotfile', ds_qc, qcname)

    return analysisflow

def regTimeseriesQC(qcname, tag="", SinkDir=".", QCDIR="QC"):
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.plot.timeseries as plot

    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['timeseries', 'modules', 'atlas']),
                        name='inputspec')
    inputspec.inputs.atlas = None

    plotregts = pe.MapNode(interface=Function(input_names=['timeseries', 'modules', 'output_file', 'atlas'],
                                                  output_names=['plotfile'],
                                                  function=plot.plot_carpet_ts),
                               iterfield=['timeseries'],
                               name="qc_timeseries")
    plotregts.inputs.output_file = "qc_timeseries.png"

    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                    name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Create a workflow
    analysisflow = nipype.Workflow(name=qcname + tag + '_qc')

    analysisflow.connect(inputspec, 'timeseries', plotregts, 'timeseries')
    analysisflow.connect(inputspec, 'atlas', plotregts, 'atlas')
    analysisflow.connect(inputspec, 'modules', plotregts, 'modules')
    analysisflow.connect(plotregts, 'plotfile', ds_qc, qcname)

    return analysisflow


def matrixQC(qcname, tag="", SinkDir=".", QCDIR="QC"):
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.plot.connectivity as plot

    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    if tag:
        tag = "_" + tag

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['matrix_file', 'modules', 'atlas', 'output_file']),
                        name='inputspec')
    inputspec.inputs.modules = None
    #inputspec.inputs.atlas = False
    inputspec.inputs.output_file = "qc_matrix.png"

    plt = pe.MapNode(interface=Function(input_names=['matrix_file', 'modules', 'atlas', 'output_file'],
                                                  output_names=['plotfile'],
                                                  function=plot.plot_matrix),
                               iterfield=['matrix_file'],
                               name="qc_conn_matrix")

    plt_hist = pe.MapNode(interface=Function(input_names=['matrix_file', 'modules', 'atlas', 'output_file'],
                                        output_names=['plotfile'],
                                        function=plot.plot_conn_hist),
                     iterfield=['matrix_file'],
                     name="qc_conn_hist")

    plt_polar = pe.MapNode(interface=Function(input_names=['matrix_file', 'modules', 'atlas', 'output_file'],
                                             output_names=['plotfile'],
                                             function=plot.plot_conn_polar),
                          iterfield=['matrix_file'],
                          name="qc_conn_polar")


    # Save outputs which are important
    ds_qc = pe.Node(interface=io.DataSink(),
                    name='ds_qc')
    ds_qc.inputs.base_directory = QCDir
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Save outputs which are important
    ds_qc_hist = pe.Node(interface=io.DataSink(),
                    name='ds_qc_hist')
    ds_qc_hist.inputs.base_directory = QCDir
    ds_qc_hist.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Save outputs which are important
    ds_qc_polar = pe.Node(interface=io.DataSink(),
                         name='ds_qc_polar')
    ds_qc_polar.inputs.base_directory = QCDir
    ds_qc_polar.inputs.regexp_substitutions = [("(\/)[^\/]*$", tag + ".png")]

    # Create a workflow
    analysisflow = nipype.Workflow(name=qcname + tag + '_qc')

    analysisflow.connect(inputspec, 'matrix_file', plt, 'matrix_file')
    analysisflow.connect(inputspec, 'output_file', plt, 'output_file')
    analysisflow.connect(inputspec, 'modules', plt, 'modules')
    analysisflow.connect(inputspec, 'atlas', plt, 'atlas')
    analysisflow.connect(plt, 'plotfile', ds_qc, qcname)

    analysisflow.connect(inputspec, 'matrix_file', plt_hist, 'matrix_file')
    analysisflow.connect(inputspec, 'output_file', plt_hist, 'output_file')
    analysisflow.connect(inputspec, 'modules', plt_hist, 'modules')
    analysisflow.connect(inputspec, 'atlas', plt_hist, 'atlas')
    analysisflow.connect(plt_hist, 'plotfile', ds_qc_hist, qcname + "_hist")

    analysisflow.connect(inputspec, 'matrix_file', plt_polar, 'matrix_file')
    analysisflow.connect(inputspec, 'output_file', plt_polar, 'output_file')
    analysisflow.connect(inputspec, 'modules', plt_polar, 'modules')
    analysisflow.connect(inputspec, 'atlas', plt_polar, 'atlas')
    analysisflow.connect(plt_polar, 'plotfile', ds_qc_polar, qcname + "_polar")

    return analysisflow