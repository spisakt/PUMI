"""
    Build  on the NetworkBuilder.py function:



    Workflow inputs:
        :param timeseries_list: the list of the subjects timeserie. the columns are the certain ROIs and the rows represents the certain timepoints.
        :param SinkDir: where to write important ouputs
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found.

    Workflow outputs:
        :param

        :return:


    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018

    """

def netmat(timeseries_list, measure="correlation",timewindow=38,winstepsize=2):
    # measure van be: "correlation", "partial correlation", "tangent"
    # This takes the timeseries of all subjects, needed for the "tangent" measure

    import pandas as pd
    import numpy as np
    import os
    from nilearn.connectome import ConnectivityMeasure
    from nilearn.connectome import vec_to_sym_matrix


    pooled_subjects = []
    for subj in timeseries_list:
        ts = pd.read_csv(subj, sep="\t")
        pooled_subjects.append(ts.values)

    conn_measure = ConnectivityMeasure(kind=measure, discard_diagonal=True)
    correlation_matrix = conn_measure.fit_transform(pooled_subjects)

    strtidx = np.arange(((pooled_subjects[0].shape[0] - timewindow) / winstepsize) + 1) * winstepsize
    conn_measure = ConnectivityMeasure(kind=measure)
    funccorstd=[]
    for i in range(len(pooled_subjects)):
        slidingwincormatrix=[]
        for j in strtidx:
            tmpsubj=pooled_subjects[i]
            tmp = conn_measure.fit_transform([tmpsubj[j:(j + timewindow), :]])[0]
            slidingwincormatrix.append(tmp)
        tempstdmatricis=np.std(np.array(slidingwincormatrix),axis=0)
        funccorstd.append(tempstdmatricis)
    mean_stdcormatrixoffuncconn=plotting.plot_matrix(np.mean(funccorstd, axis=0))
    #TODO save the correlation plot in the directory

    # regnum = ts.shape[1]
    #
    # subject_matrix_list = []
    # for i in range(correlation_matrix.shape[0]):
    #     mat = pd.DataFrame(vec_to_sym_matrix(correlation_matrix[i,:], diagonal=np.repeat(0, regnum)))
    #     mat.columns = ts.columns
    #     mat.index = mat.columns
    #     # mimic mapnode behavior!!
    #     directory = "mapflow/_" + measure.replace(' ', '_') + "_matrix" + str(i)
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)
    #     mat.to_csv(directory + "/" + "mtx.tsv", sep="\t")
    #     #print os.path.join(os.getcwd(), str(i) + "_mtx.tsv")
    #     subject_matrix_list.append( str(os.path.join(os.getcwd(), directory, "mtx.tsv")) )

    # mean = pd.DataFrame(conn_measure.mean_)
    # mean.values[range(regnum), range(regnum)] = 0  # zero-out digonal
    # mean.columns = ts.columns
    # mean.index = mean.columns
    # outfile = measure.replace(' ', '_') + "_mean_mtx.tsv"
    # mean.to_csv(outfile, sep="\t")
    #
    # return os.path.join(os.getcwd(), outfile), subject_matrix_list
    return funccorstd


# the workflow
def build_netmat(SinkTag="connectivity", wf_name="build_network"):
    ########################################################################
    # Extract timeseries
    ########################################################################

    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    from nipype.interfaces.utility import Function
    import nipype.interfaces.io as io
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    import os

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Identitiy mapping for input variables
    inputspec = pe.Node(utility.IdentityInterface(fields=['timeseries', #contains labels
                                                          'modules',  # optional
                                                          'measure',
                                                          'atlas' # optional, only for plotting purposes
                                                          ]),
                        name='inputspec')
    inputspec.inputs.atlas = False  # default value
    inputspec.inputs.measure = "partial correlation"

    # This is not a map node, since it takes all the subject-level regional timseries in a list and does population-level modelling
    # if measure == "tangent"
    estimate_network_mtx = pe.Node(interface=Function(input_names=['timeseries_list', 'modules', 'measure'],
                                              output_names=['mean_mtx', 'subject_matrix_list'],
                                              function=netmat),
                           name='estimate_network_mtx')

    matrix_qc_mean = qc.matrixQC("group_mean_matrix", tag=wf_name + "_")
    matrix_qc = qc.matrixQC("matrices", tag=wf_name)

    # Save outputs which are important
    ds_meanmat = pe.Node(interface=io.DataSink(),
                           name='ds_meanmat')
    ds_meanmat.inputs.base_directory = SinkDir
    ds_meanmat.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".tsv")]

    # Save outputs which are important
    ds_mat = pe.Node(interface=io.DataSink(),
                         name='ds_mats')
    ds_mat.inputs.base_directory = SinkDir
    ds_mat.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".tsv")]

    analysisflow = pe.Workflow(wf_name)
    analysisflow.connect(inputspec, 'timeseries', estimate_network_mtx, 'timeseries_list')
    analysisflow.connect(inputspec, 'measure', estimate_network_mtx, 'measure')

    analysisflow.connect(estimate_network_mtx, 'mean_mtx', ds_meanmat, 'mean_connectivity_mat')
    analysisflow.connect(estimate_network_mtx, 'subject_matrix_list', ds_mat, 'connectivity_matrices')

    analysisflow.connect(estimate_network_mtx, 'mean_mtx', matrix_qc_mean, 'inputspec.matrix_file')
    analysisflow.connect(inputspec, 'modules', matrix_qc_mean, 'inputspec.modules')
    analysisflow.connect(inputspec, 'atlas', matrix_qc_mean, 'inputspec.atlas')

    analysisflow.connect(estimate_network_mtx, 'subject_matrix_list', matrix_qc, 'inputspec.matrix_file')
    analysisflow.connect(inputspec, 'modules', matrix_qc, 'inputspec.modules')
    analysisflow.connect(inputspec, 'atlas', matrix_qc, 'inputspec.atlas')

    return analysisflow