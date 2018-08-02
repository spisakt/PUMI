from sklearn.externals import joblib
import numpy as np
import pandas as pd
from nilearn.connectome import vec_to_sym_matrix
from nilearn import plotting

def mist_modules(mist_directory, resolution="122"):
    # possible values for resolution: s7,s12,s20,s36,s64,s122,sROI,sATOM
    import pandas as pd

    resolution='s'+resolution
    mist_hierarchy_filename = mist_directory + '/' + 'Hierarchy/MIST_PARCEL_ORDER_ROI.csv'
    mist_hierarchy = pd.read_csv(mist_hierarchy_filename, sep=",")
    mist_hierarchy_res = mist_hierarchy[(resolution)]
    mist_hierarchy_res = mist_hierarchy_res.drop_duplicates()

    modul_indices = mist_hierarchy.loc[mist_hierarchy_res.index.values, ['s7', resolution]].sort_values(by=resolution)['s7']
    mist_s7_filename = mist_directory + '/' + 'Parcel_Information/MIST_7.csv'
    mist_s7 = pd.read_csv(mist_s7_filename, sep=";")

    labels =  mist_s7.loc[modul_indices-1, ['roi', 'label']].reset_index()

    return labels['label'].values.tolist()


def mist_labels(mist_directory, resolution="122"):
    # possible values for resolution: s7,s12,s20,s36,s64,s122,sROI,sATOM
    import pandas as pd

    mist_filename = mist_directory + '/' + 'Parcel_Information/MIST_' + resolution + '.csv'

    mist = pd.read_csv(mist_filename, sep=";")

    return mist['label'].values.tolist()


def relabel_atlas(atlas_file, modules, labels):
    # currently works only with labelmap!!
    # TODO: make it work with 4D probmaps or list or probmaps, as well

    import os
    import numpy as np
    import pandas as pd
    import nibabel as nib

    df = pd.DataFrame({'modules': modules,
                       'labels': labels})
    df.index += 1  # indexing from 1

    reordered = df.sort_values(by='modules')

    # relabel labelmap
    img = nib.load(atlas_file)
    if len(img.shape) != 3:
        raise Exception("relabeling does not work for probability maps!")

    lut = np.array([0] + reordered.index.values.tolist())

    data = img.get_data()
    newdata=lut[np.array(data, dtype=int)] # apply lookup table to swap labels
    #newdata=np.all(lut[data.astype(int)] == np.take(lut, data.astype(int)))

    img = nib.Nifti1Image(newdata, img.get_affine())
    nib.save(img, 'relabeled_atlas.nii.gz')

    return os.path.join(os.getcwd(), 'relabeled_atlas.nii.gz'), reordered['modules'].values.tolist(), reordered['labels'].values.tolist()
    #return relabeled atlas labelmap file, reordered module names, reordered labels (region names)

def extract_timeseries(SinkTag="connectivity", wf_name="extract_timeseries", modularise=True):
    ########################################################################
    # Extract timeseries
    ########################################################################

    import nipype.interfaces.nilearn as learn
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.io as io
    from nipype.interfaces.utility import Function
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc
    import os

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Identitiy mapping for input variables
    inputspec = pe.Node(utility.IdentityInterface(fields=['std_func',
                                                          'atlas_file',  # nii labelmap (or 4D probmaps)
                                                          'labels',  # list of short names to regions
                                                          'modules'  # list of modules of regions
                                                          ]),
                        name='inputspec')
    # re-label atlas, so that regions corresponding to the same modules follow each other
    if modularise:
        relabel_atls = pe.Node(interface=Function(input_names=['atlas_file', 'modules', 'labels'],
                       output_names=['relabelled_atlas_file', 'reordered_modules', 'reordered_labels'],
                       function=relabel_atlas),
                                name='relabel_atlas')


    extract_timesereies = pe.MapNode(interface=learn.SignalExtraction(detrend=False),
                                     iterfield=['in_file'],
                                     name='extract_timeseries')

    # Save outputs which are important
    ds_txt = pe.Node(interface=io.DataSink(),
                     name='ds_txt')
    ds_txt.inputs.base_directory = SinkDir
    ds_txt.inputs.regexp_substitutions = [("(\/)[^\/]*$", wf_name + ".tsv")]

    #QC
    timeseries_qc = qc.regTimeseriesQC("regional_timeseries", tag=wf_name)

    outputspec = pe.Node(utility.IdentityInterface(fields=['timeseries_file']),
                         name='outputspec')

    # Create workflow
    analysisflow = pe.Workflow(wf_name)
    analysisflow.connect(inputspec, 'std_func', extract_timesereies, 'in_file')
    if modularise:
        analysisflow.connect(inputspec, 'atlas_file', relabel_atls, 'atlas_file')
        analysisflow.connect(inputspec, 'modules', relabel_atls, 'modules')
        analysisflow.connect(inputspec, 'labels', relabel_atls, 'labels')

        analysisflow.connect(relabel_atls, 'relabelled_atlas_file', extract_timesereies, 'label_files')
        analysisflow.connect(relabel_atls, 'reordered_labels', extract_timesereies, 'class_labels')
        analysisflow.connect(relabel_atls, 'reordered_modules', timeseries_qc, 'inputspec.modules')
    else:
        analysisflow.connect(inputspec, 'atlas_file', extract_timesereies, 'label_files')
        analysisflow.connect(inputspec, 'labels', extract_timesereies, 'class_labels')
        analysisflow.connect(inputspec, 'modules', timeseries_qc, 'inputspec.modules')

    analysisflow.connect(extract_timesereies, 'out_file', ds_txt, 'regional_timeseries')
    analysisflow.connect(extract_timesereies, 'out_file', timeseries_qc, 'inputspec.timeseries')

    analysisflow.connect(extract_timesereies, 'out_file', outputspec, 'timeseries_file')

    return analysisflow




