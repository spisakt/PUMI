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

    labels = mist_s7.loc[modul_indices-1, ['roi', 'label']].reset_index()

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

    lut = reordered.reset_index().sort_values(by="index").index.values + 1
    lut = np.array([0] + lut.tolist())
    # maybe this is a bit complicated, but believe me it does what it should

    data = img.get_data()
    newdata = lut[np.array(data, dtype=np.int32)]  # apply lookup table to swap labels
    #newdata=np.all(lut[data.astype(int)] == np.take(lut, data.astype(int)))

    img = nib.Nifti1Image(newdata.astype(np.float64), img.get_affine())
    nib.save(img, 'relabeled_atlas.nii.gz')

    out = reordered.reset_index()
    out.index = out.index + 1
    out.to_csv(r'newlabels.tsv', sep='\t')

    return os.path.join(os.getcwd(), 'relabeled_atlas.nii.gz'), reordered['modules'].values.tolist(), reordered['labels'].values.tolist(), os.path.join(os.getcwd(), 'newlabels.tsv')
    #return relabeled atlas labelmap file, reordered module names, reordered labels (region names), newlabels_file


def TsExtractor(labels, labelmap, func, mask, global_signal=True, pca=False, outfile="reg_timeseries.tsv", outlabelmap="individual_gm_labelmap.nii.gz"):

    import nibabel as nib
    import pandas as pd
    import numpy as np

    func_data = nib.load(func).get_data()
    labelmap_data = nib.load(labelmap).get_data()
    mask_data = nib.load(mask).get_data()

    labelmap_data[mask_data==0] = 0 # background

    outlab=nib.Nifti1Image(labelmap_data, nib.load(labelmap).affine)
    nib.save(outlab, outlabelmap)

    ret=[]

    if global_signal:
        indices = np.argwhere(mask_data > 0)
        X = []
        for i in indices:
            x = func_data[i[0], i[1], i[2], :]
            if np.std(x) > 0.000001:
                X.append(x.tolist())
        if pca:
            import sklearn.decomposition as decomp
            from sklearn.preprocessing import StandardScaler
            X = StandardScaler().fit_transform(np.transpose(X))
            PCA = decomp.PCA(n_components=1, svd_solver="arpack")
            x = PCA.fit_transform(X).flatten()
        else:
            #from sklearn.preprocessing import StandardScaler
            #X = StandardScaler().fit_transform(np.transpose(X))
            x = np.mean(X, axis=0)
        ret.append(x)

    for l in range(1,len(labels)+1):
        indices=np.argwhere(labelmap_data == l)
        X=[]
        for i in indices:
            x=func_data[i[0], i[1], i[2], :]
            if np.std(x) > 0.000001:
                X.append(x.tolist())
        X=np.array(X)
        if X.shape[0]==0:
            x=np.repeat(0,func_data.shape[3])
        elif X.shape[0]==1:
            x=X.flatten()
        elif pca:
            import sklearn.decomposition as decomp
            from sklearn.preprocessing import StandardScaler
            X = StandardScaler().fit_transform(np.transpose(X))
            PCA=decomp.PCA(n_components=1, svd_solver="arpack")
            x=PCA.fit_transform(X).flatten()
        else:
            #from sklearn.preprocessing import StandardScaler
            #X = StandardScaler().fit_transform(np.transpose(X))
            x=np.mean(X, axis=0)
        ret.append(x)

    ret = np.transpose(np.array(ret))

    if global_signal:
        labels = ["GlobSig"] + labels

    import pandas as pd
    ret=pd.DataFrame(data=ret,
                     columns=labels)

    ret.to_csv(outfile, sep="\t", index=False)

    import os
    return os.path.join(os.getcwd(), outfile), labels, os.path.join(os.getcwd(), outlabelmap)


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
                       output_names=['relabelled_atlas_file', 'reordered_modules', 'reordered_labels', 'newlabels_file'],
                       function=relabel_atlas),
                                name='relabel_atlas')
        # Save outputs which are important
        ds_nii = pe.Node(interface=io.DataSink(),
                         name='ds_relabeled_atlas')
        ds_nii.inputs.base_directory = SinkDir
        ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

        # Save outputs which are important
        ds_newlabels = pe.Node(interface=io.DataSink(),
                         name='ds_newlabels')
        ds_newlabels.inputs.base_directory = SinkDir
        ds_newlabels.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".tsv")]


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

    outputspec = pe.Node(utility.IdentityInterface(fields=['timeseries_file', 'relabelled_atlas_file', 'reordered_modules', 'reordered_labels']),
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
        analysisflow.connect(relabel_atls, 'relabelled_atlas_file', timeseries_qc, 'inputspec.atlas')
        analysisflow.connect(relabel_atls, 'relabelled_atlas_file', ds_nii, 'atlas_relabeled')
        analysisflow.connect(relabel_atls, 'newlabels_file', ds_newlabels, 'atlas_relabeled')
        analysisflow.connect(relabel_atls, 'relabelled_atlas_file', outputspec, 'relabelled_atlas_file')
        analysisflow.connect(relabel_atls, 'reordered_labels', outputspec, 'reordered_labels')
        analysisflow.connect(relabel_atls, 'reordered_modules', outputspec, 'reordered_modules')
    else:
        analysisflow.connect(inputspec, 'atlas_file', extract_timesereies, 'label_files')
        analysisflow.connect(inputspec, 'labels', extract_timesereies, 'class_labels')
        analysisflow.connect(inputspec, 'modules', timeseries_qc, 'inputspec.modules')
        analysisflow.connect(inputspec, 'atlas_file', timeseries_qc, 'inputspec.atlas')
        analysisflow.connect(inputspec, 'atlas_file', outputspec, 'relabelled_atlas_file')
        analysisflow.connect(inputspec, 'labels', outputspec, 'reordered_labels')
        analysisflow.connect(inputspec, 'modules', outputspec, 'reordered_modules')

    analysisflow.connect(extract_timesereies, 'out_file', ds_txt, 'regional_timeseries')
    analysisflow.connect(extract_timesereies, 'out_file', timeseries_qc, 'inputspec.timeseries')

    analysisflow.connect(extract_timesereies, 'out_file', outputspec, 'timeseries_file')


    return analysisflow

def PickAtlas(SinkTag="connectivity", wf_name="pick_atlas", reorder=True):
    # reorder if modules is given (like for MIST atlases)
    # if no module information available, pass a text file with a constant value x number of regions
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.afni as afni
    import PUMI.utils.globals as globals
    import nipype.interfaces.io as io

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    wf = nipype.Workflow(wf_name)

    inputspec = pe.Node(utility.IdentityInterface(fields=['labelmap', 'modules', 'labels']), name="inputspec")

    # create atlas matching the stabndard space used
    resample_atlas = pe.Node(interface=afni.Resample(outputtype='NIFTI_GZ',
                                                     master=globals._FSLDIR_ + globals._brainref),
                             name='resample_atlas')  # default interpolation is nearest neighbour

    # Save outputs which are important
    ds_newlabels = pe.Node(interface=io.DataSink(),
                           name='ds_newlabels')
    ds_newlabels.inputs.base_directory = globals._SinkDir_
    ds_newlabels.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".tsv")]

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['relabeled_atlas', 'reordered_labels', 'reordered_modules']),
                         name='outputspec')

    if reorder:
        relabel_atls = pe.Node(interface=utility.Function(input_names=['atlas_file', 'modules', 'labels'],
                                                          output_names=['relabelled_atlas_file', 'reordered_modules',
                                                                        'reordered_labels', 'newlabels_file'],
                                                          function=relabel_atlas),
                               name='relabel_atlas')
        wf.connect(inputspec, 'labelmap', relabel_atls, 'atlas_file')
        wf.connect(inputspec, 'modules', relabel_atls, 'modules')
        wf.connect(inputspec, 'labels', relabel_atls, 'labels')

        wf.connect(relabel_atls, 'relabelled_atlas_file', resample_atlas, 'in_file')

        wf.connect(relabel_atls, 'reordered_labels', ds_newlabels, 'reordered_labels')
        #wf.connect(relabel_atls, 'reordered_modules', ds_newlabels, 'reordered_modules')

        wf.connect(relabel_atls, 'reordered_labels', outputspec, 'reordered_labels')
        wf.connect(relabel_atls, 'reordered_modules', outputspec, 'reordered_modules')

    else:
        wf.connect(inputspec, 'labelmap', resample_atlas, 'in_file')
        wf.connect(inputspec, 'labels', ds_newlabels, 'atlas_labels')
        # wf.connect(relabel_atls, 'reordered_modules', ds_newlabels, 'reordered_modules')
        wf.connect(inputspec, 'labels', outputspec, 'reordered_labels')
        wf.connect(inputspec, 'modules', outputspec, 'reordered_modules')

    # Save outputs which are important
    ds_nii = pe.Node(interface=io.DataSink(),
                     name='ds_relabeled_atlas')
    ds_nii.inputs.base_directory = globals._SinkDir_
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]
    wf.connect(resample_atlas, 'out_file', ds_nii, 'atlas')

    wf.connect(resample_atlas, 'out_file', outputspec, 'relabeled_atlas')

    return wf



def extract_timeseries_nativespace(SinkTag="connectivity", wf_name="extract_timeseries_nativespace", global_signal=True):
    # this workflow transforms atlas back to native space and uses TsExtractor

    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.io as io
    import nipype.interfaces.utility as utility
    import PUMI.func_preproc.func2standard as transform
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    wf = nipype.Workflow(wf_name)

    inputspec = pe.Node(utility.IdentityInterface(fields=['atlas',
                                                          'labels',
                                                          'modules',
                                                          'anat', # only obligatory if stdreg==globals._RegType_.ANTS
                                                          'inv_linear_reg_mtrx',
                                                          'inv_nonlinear_reg_mtrx',
                                                          'func',
                                                          'gm_mask',
                                                          'confounds',
                                                          'confound_names']), name="inputspec")


    # transform atlas back to native EPI spaces!
    atlas2native = transform.atlas2func(stdreg=globals._regType_)
    wf.connect(inputspec, 'atlas', atlas2native, 'inputspec.atlas')
    wf.connect(inputspec, 'anat', atlas2native, 'inputspec.anat')
    wf.connect(inputspec, 'inv_linear_reg_mtrx', atlas2native, 'inputspec.inv_linear_reg_mtrx')
    wf.connect(inputspec, 'inv_nonlinear_reg_mtrx', atlas2native, 'inputspec.inv_nonlinear_reg_mtrx')
    wf.connect(inputspec, 'func', atlas2native, 'inputspec.func')
    wf.connect(inputspec, 'gm_mask', atlas2native, 'inputspec.example_func')
    wf.connect(inputspec, 'confounds', atlas2native, 'inputspec.confounds')
    wf.connect(inputspec, 'confound_names', atlas2native, 'inputspec.confound_names')

    # extract timeseries
    extract_timeseries = pe.MapNode(interface=utility.Function(input_names=['labels', 'labelmap',
                                                                            'func', 'mask', 'global_signal'],
                                                                output_names=['out_file', 'labels', 'out_gm_label'],
                                                                function=TsExtractor),
                                     iterfield=['labelmap', 'func', 'mask'],
                                     name='extract_timeseries')
    extract_timeseries.inputs.global_signal = global_signal
    wf.connect(atlas2native, 'outputspec.atlas2func', extract_timeseries, 'labelmap')
    wf.connect(inputspec, 'labels', extract_timeseries, 'labels')
    wf.connect(inputspec, 'gm_mask', extract_timeseries, 'mask')
    wf.connect(inputspec, 'func', extract_timeseries, 'func')

    # Save outputs which are important
    ds_regts = pe.Node(interface=io.DataSink(),
                           name='ds_regts')
    ds_regts.inputs.base_directory = globals._SinkDir_
    ds_regts.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".tsv")]
    wf.connect(extract_timeseries, 'out_file', ds_regts, 'regional_timeseries')

    # QC
    timeseries_qc = qc.regTimeseriesQC("regional_timeseries", tag=wf_name)
    wf.connect(inputspec, 'modules', timeseries_qc, 'inputspec.modules')
    wf.connect(inputspec, 'atlas', timeseries_qc, 'inputspec.atlas')
    wf.connect(extract_timeseries, 'out_file', timeseries_qc, 'inputspec.timeseries')

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['timeseries', 'out_gm_label']),
                         name='outputspec')
    wf.connect(extract_timeseries, 'out_file', outputspec, 'timeseries')
    wf.connect(extract_timeseries, 'out_gm_label', outputspec, 'out_gm_label')

    return wf






