import nipype.pipeline as pe
import nipype.interfaces.utility as utility
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as io
import os

def vol2png(qcname, SinkDir=".", QCDIR="QC"):

    QCDir = os.path.abspath(SinkDir + "/" + QCDIR)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

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
    ds_qc.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".png")]

    analysisflow = pe.Workflow(name=qcname + '_qc')
    analysisflow.connect(inputspec, 'bg_image', slicer, 'in_file')
    analysisflow.connect(inputspec, 'overlay_image', slicer, 'image_edges')
    analysisflow.connect(slicer, 'out_file', ds_qc, qcname)

    return analysisflow