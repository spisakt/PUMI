#!/usr/bin/env python
import sys
# sys.path.append("/home/balint/Dokumentumok/phd/github/") #PUMI should be added to the path by install or by the developer
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
# import the defined workflows from the anat_preproc folder
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni as afni
import PUMI.AnatProc as anatproc
import PUMI.FuncProc as funcproc
# import the necessary workflows from the func_preproc folder
import PUMI.anat_preproc.Func2Anat as bbr
import PUMI.func_preproc.func2standard as transform
import os
import PUMI.utils.globals as globals
#import PUMI.utils.addimages as adding

# parse command line arguments
if (len(sys.argv) <= 2):
    print("Please specify command line arguments!")
    print("Usage:")
    print(sys.argv[0] + " <\"highres_data_template\"> <\"func_data_template\"> [results_sink_directory]")
    print("Example:")
    print(sys.argv[0] + " \"highres_data/subject_*.nii.gz\" \"func_data/subject_*.nii.gz\"")
    quit()

if (len(sys.argv) > 3):
    globals._SinkDir_ = sys.argv[3]

# create data grabber
datagrab = pe.Node(nio.DataGrabber(outfields=['func', 'struct']), name='data_grabber')

datagrab.inputs.base_directory = os.getcwd()  # do we need this?
datagrab.inputs.template = "*"  # do we need this?
datagrab.inputs.field_template = dict(func=sys.argv[2],
                                      struct=sys.argv[1])  # specified by command line arguments
datagrab.inputs.sort_filelist = True
# build the actual pipeline
reorient_struct = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_struct")
reorient_func = pe.MapNode(fsl.utils.Reorient2Std(),
                      iterfield=['in_file'],
                      name="reorient_func")

myanatproc = anatproc.AnatProc(stdreg=anatproc.RegType.FSL)

mybbr = bbr.bbr_workflow()
# Add arbitrary number of nii images wthin the same space. The default is to add csf and wm masks for anatcompcor calculation.
#myadding=adding.addimgs_workflow(numimgs=2)
add_masks = pe.MapNode(fsl.ImageMaths(op_string=' -add'),
                       iterfield=['in_file', 'in_file2'],
                       name="addimgs")

def pickindex(vec, i):
    return [x[i] for x in vec]

myfuncproc = funcproc.FuncProc()

#create atlas matching this space
resample_atlas = pe.Node(interface=afni.Resample(outputtype = 'NIFTI_GZ',
                                          in_file="/Users/tspisak/data/atlases/MIST/Parcellations/MIST_7.nii.gz",
                                          master=globals._FSLDIR_ + '/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz'),
                         name='resample_atlas') #default interpolation is nearest neighbour

# standardize what you need
myfunc2mni = transform.func2mni(carpet_plot="1_original", wf_name="func2mni")
myfunc2mni_cc = transform.func2mni(carpet_plot="2_cc", wf_name="func2mni_cc")
myfunc2mni_cc_bpf = transform.func2mni(carpet_plot="3_cc_bpf", wf_name="func2mni_cc_bpf")
myfunc2mni_cc_bpf_cens = transform.func2mni(carpet_plot="4_cc_bpf_cens", wf_name="func2mni_cc_bpf_cens")
myfunc2mni_cc_bpf_cens_mac = transform.func2mni(carpet_plot="5_cc_bpf_cens_mac", wf_name="func2mni_cc_bpf_cens_mac")


totalWorkflow = nipype.Workflow('totalWorkflow')
totalWorkflow.base_dir = '.'

# anatomical part and func2anat
totalWorkflow.connect([
    (datagrab, reorient_struct,
     [('struct', 'in_file')]),
    (reorient_struct, myanatproc,
     [('out_file', 'inputspec.anat')]),
    (reorient_struct, mybbr,
     [('out_file', 'inputspec.skull')]),
    (datagrab, reorient_func,
     [('func', 'in_file')]),
    (reorient_func, mybbr,
     [('out_file', 'inputspec.func')]),
    (myanatproc, mybbr,
      [('outputspec.probmap_wm', 'inputspec.anat_wm_segmentation'),
       ('outputspec.probmap_csf', 'inputspec.anat_csf_segmentation'),
       ('outputspec.probmap_gm', 'inputspec.anat_gm_segmentation')])

    ])

# functional part
totalWorkflow.connect([
    (reorient_func, myfuncproc,
     [('out_file', 'inputspec.func')]),
    (mybbr, add_masks,
     [('outputspec.csf_mask_in_funcspace','in_file'),
      ('outputspec.wm_mask_in_funcspace','in_file2')]),
    (add_masks, myfuncproc,
     [('out_file','inputspec.cc_noise_roi')]),


    # push func to standard space
    (myfuncproc, myfunc2mni,
     [('outputspec.func_mc', 'inputspec.func'),
      ('outputspec.FD', 'inputspec.confounds')]),
    (mybbr, myfunc2mni,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, myfunc2mni,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx'),
      ('outputspec.std_brain', 'inputspec.reference_brain')]),
    (resample_atlas, myfunc2mni,
     [('out_file', 'inputspec.atlas')]),

    (myfuncproc, myfunc2mni_cc,
     [('outputspec.func_mc_nuis', 'inputspec.func'),
      ('outputspec.FD', 'inputspec.confounds')]),
    (mybbr, myfunc2mni_cc,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, myfunc2mni_cc,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx'),
      ('outputspec.std_brain', 'inputspec.reference_brain')]),
    (resample_atlas, myfunc2mni_cc,
     [('out_file', 'inputspec.atlas')]),

    (myfuncproc, myfunc2mni_cc_bpf,
     [('outputspec.func_mc_nuis_bpf', 'inputspec.func'),
      ('outputspec.FD', 'inputspec.confounds')]),
    (mybbr, myfunc2mni_cc_bpf,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, myfunc2mni_cc_bpf,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx'),
      ('outputspec.std_brain', 'inputspec.reference_brain')]),
    (resample_atlas, myfunc2mni_cc_bpf,
     [('out_file', 'inputspec.atlas')]),

    (myfuncproc, myfunc2mni_cc_bpf_cens,
     [('outputspec.func_mc_nuis_bpf_cens', 'inputspec.func'),
      ('outputspec.FD', 'inputspec.confounds')]),
    (mybbr, myfunc2mni_cc_bpf_cens,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, myfunc2mni_cc_bpf_cens,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx'),
      ('outputspec.std_brain', 'inputspec.reference_brain')]),
    (resample_atlas, myfunc2mni_cc_bpf_cens,
     [('out_file', 'inputspec.atlas')]),

(myfuncproc, myfunc2mni_cc_bpf_cens_mac,
     [('outputspec.func_mc_nuis_bpf_cens_medang', 'inputspec.func'),
      ('outputspec.FD', 'inputspec.confounds')]),
    (mybbr, myfunc2mni_cc_bpf_cens_mac,
     [('outputspec.func_to_anat_linear_xfm', 'inputspec.linear_reg_mtrx')]),
    (myanatproc, myfunc2mni_cc_bpf_cens_mac,
     [('outputspec.anat2mni_warpfield', 'inputspec.nonlinear_reg_mtrx'),
      ('outputspec.std_brain', 'inputspec.reference_brain')]),
    (resample_atlas, myfunc2mni_cc_bpf_cens_mac,
     [('out_file', 'inputspec.atlas')]),


    ])



totalWorkflow.write_graph('graph-orig.dot', graph2use='orig', simple_form=True)
totalWorkflow.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False)
totalWorkflow.write_graph('graph.dot', graph2use='colored')
totalWorkflow.run(plugin='MultiProc')
