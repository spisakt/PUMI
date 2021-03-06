def median_angle_correct(target_angle_deg, realigned_file, mask):
    """
    Performs median angle correction on fMRI data.  Median angle correction algorithm
    based on [1]_.

    Parameters
    ----------
    target_angle_deg : float
        Target median angle to adjust the time-series data.
    realigned_file : string
        Path of a realigned nifti file.

    Returns
    -------
    corrected_file : string
        Path of corrected file (nifti file).
    angles_file : string
        Path of numpy file (.npy file) containing the angles (in radians) of all voxels with
        the 5 largest principal components.

    References
    ----------
    .. [1] H. He and T. T. Liu, "A geometric view of global signal confounds in resting-state functional MRI," NeuroImage, Sep. 2011.

    """
    import numpy as np
    import nibabel as nb
    import os
    from scipy.stats.stats import pearsonr

    def shiftCols(pc, A, dtheta):
        pcxA = np.dot(pc, A)
        x = A - np.dot(pc[:, np.newaxis], pcxA[np.newaxis, :])

        theta = np.arccos(np.dot(pc.T, A))
        theta_new = theta + dtheta

        x /= np.tile(np.sqrt((x * x).sum(0)), (x.shape[0], 1))
        v_new = np.dot(pc[:, np.newaxis], \
                       np.cos(theta_new)[np.newaxis, :]) + (np.sin(theta_new) * x)

        return v_new

    def writeToFile(data, nii, fname):
        img_whole_y = nb.Nifti1Image(data, \
                                     header=nii.get_header(), affine=nii.get_affine())
        img_whole_y.to_filename(fname)

    nii = nb.load(realigned_file)
    data = nii.get_data().astype(np.float64)
    #print "realigned file: " + realigned_file + ", subject data dimensions: " + data.shape

    # mask = (data != 0).sum(-1) != 0
    masknii = nb.load(mask)
    maskdata = masknii.get_data().astype(np.bool)

    # additionally mask out all-zero voxels, as well
    STD=np.std(data, axis=3)
    maskdata[STD==0] = False

    #maskdata_bool = (maskdata!= 0).sum(-1) != 0
    Y = data[maskdata].T



    Yc = Y - np.tile(Y.mean(0), (Y.shape[0], 1))
    Yn = Yc / np.tile(np.sqrt((Yc * Yc).sum(0)), (Yc.shape[0], 1))
    U, S, Vh = np.linalg.svd(Yn, full_matrices=False)

    G = Yc.mean(1)
    corr_gu = pearsonr(G, U[:, 0])
    PC1 = U[:, 0] if corr_gu[0] >= 0 else -U[:, 0]
    #print 'Correlation of Global and U: ' + corr_gu

    median_angle = np.median(np.arccos(np.dot(PC1.T, Yn)))
    print '*** Median Angle: ' + str((180.0 / np.pi) * median_angle) + ', Target Angle: ' + str(target_angle_deg)
    angle_shift = (np.pi / 180) * target_angle_deg - median_angle
    if (angle_shift > 0):
        print '*** Shifting all vectors by ' + str((180.0 / np.pi) * angle_shift) + ' degrees.'
        Ynf = shiftCols(PC1, Yn, angle_shift)
    else:
        print '*** Warning: Median Angle >= Target Angle, skipping correction'
        Ynf = Yn

    corrected_file = os.path.join(os.getcwd(), 'median_angle_corrected.nii.gz')
    angles_file = os.path.join(os.getcwd(), 'angles_U5_Yn.npy')

    #print 'Writing U[:,0:5] angles to file...' + angles_file
    angles_U5_Yn = np.arccos(np.dot(U[:, 0:5].T, Yn))
    np.save(angles_file, angles_U5_Yn)

    #print 'Writing correction to file...' + corrected_file
    data = np.zeros_like(data)
    data[maskdata] = Ynf.T
    writeToFile(data, nii, corrected_file)

    return corrected_file, angles_file

def mac_workflow(target_angle=90,
        SinkTag="func_preproc",
        wf_name="median_angle_correction"):
    """

     Modified version of CPAC.median_angle.median_angle:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/median_angle/median_angle.html`


    Do the data censoring on the 4D functional data.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param target angle: the default is 90.
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow..

    Workflow outputs:




        :return: datacens_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018
    Median Angle Correction

    Parameters
    ----------
    name : string, optional
        Name of the workflow.

    Returns
    -------
    median_angle_correction : nipype.pipeline.engine.Workflow
        Median Angle Correction workflow.

    Notes
    -----

    Workflow Inputs::

        inputspec.subject : string (nifti file)
            Realigned nifti file of a subject
        inputspec.target_angle : integer
            Target angle in degrees to correct the median angle to

    Workflow Outputs::

        outputspec.subject : string (nifti file)
            Median angle corrected nifti file of the given subject
        outputspec.pc_angles : string (.npy file)
            Numpy file (.npy file) containing the angles (in radians) of all voxels with
            the 5 largest principal components.

    Median Angle Correction Procedure:

    1. Compute the median angle with respect to the first principal component of the subject
    2. Shift the angle of every voxel so that the new median angle equals the target angle

    Workflow Graph:

    .. image:: ../images/median_angle_correction.dot.png
        :width: 500

    Detailed Workflow Graph:

    .. image:: ../images/median_angle_correction_detailed.dot.png
        :width: 500

    """
    import os
    import nipype.pipeline.engine as pe
    import nipype.interfaces.utility as utility
    import PUMI.utils.utils_convert as utils_convert
    import nipype.interfaces.io as io
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    #TODO set target angle...
    inputspec = pe.Node(utility.IdentityInterface(fields=['realigned_file',
                                                       'target_angle',
                                                          'mask']),
                        name='inputspec')
    inputspec.inputs.target_angle=target_angle
    outputspec = pe.Node(utility.IdentityInterface(fields=['final_func',
                                                        'pc_angles']),
                         name='outputspec')


    # Caution: inpout fmri must be masked (background=0)
    mac = pe.MapNode(utility.Function(input_names=['target_angle_deg',
                                             'realigned_file',
                                                   'mask'],
                                output_names=['corrected_file',
                                              'angles_file'],
                                function=median_angle_correct),
                     iterfield=['realigned_file',
                                'mask'],
                  name='median_angle_correct')

    myqc = qc.timecourse2png("timeseries", tag="050_medang")

    # collect and save median angle values
    pop_medang = pe.Node(interface=utils_convert.List2TxtFile, #TODO: save subject level median angle
                     name='pop_medang')

    # save mac file
    ds = pe.Node(interface=io.DataSink(), name='ds')
    ds.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]

    # save data out with Datasink
    ds_medang = pe.Node(interface=io.DataSink(), name='ds_pop_medang')
    ds_medang.inputs.regexp_substitutions = [("(\/)[^\/]*$", "medang.txt")]
    ds_medang.inputs.base_directory = SinkDir

    #TODO set which files should be put into the datasink node...
    # Create workflow
    analysisflow= pe.Workflow(wf_name)
    analysisflow.connect(inputspec, 'realigned_file', mac, 'realigned_file')
    analysisflow.connect(inputspec, 'target_angle', mac, 'target_angle_deg')
    analysisflow.connect(inputspec, 'mask', mac, 'mask')
    analysisflow.connect(mac, 'corrected_file', outputspec, 'final_func')
    analysisflow.connect(mac, 'angles_file', outputspec, 'pc_angles')
    analysisflow.connect(mac, 'corrected_file', myqc, 'inputspec.func')
    # pop-level medang values
    analysisflow.connect(mac, 'angles_file', pop_medang, 'in_list')
    analysisflow.connect(pop_medang, 'txt_file', ds_medang, 'pop')
    analysisflow.connect(mac, 'corrected_file',ds, 'med_ang')


    return analysisflow
# After here, functions are manipulating in a group level.
#TODO do we need this?
def calc_median_angle_params(subject):
    """
    Calculates median angle parameters of a subject

    Parameters
    ----------
    subject : string
        Path of a subject's nifti file.

    Returns
    -------
    mean_bold : float
        Mean bold amplitude of a subject.
    median_angle : float
        Median angle of a subject.
    """
    import numpy as np
    import nibabel as nb

    data = nb.load(subject).get_data().astype('float64')
    mask = (data != 0).sum(-1) != 0
    #print 'Loaded ' + subject
    #print 'Volume size ' + data.shape

    Y = data[mask].T
    #print 'Data shape ' + Y.shape

    Yc = Y - np.tile(Y.mean(0), (Y.shape[0], 1))
    Yn = Yc / np.tile(np.sqrt((Yc * Yc).sum(0)), (Yc.shape[0], 1))
    U, S, Vh = np.linalg.svd(Yn, full_matrices=False)

    glb = (Yn / np.tile(Yn.std(0), (Y.shape[0], 1))).mean(1)

    from scipy.stats.stats import pearsonr
    corr = pearsonr(U[:, 0], glb)
    #print "PC1_glb r: " + corr

    PC1 = U[:, 0] if corr[0] >= 0 else -U[:, 0]
    median_angle = np.median(np.arccos(np.dot(PC1.T, Yn)))
    median_angle *= 180.0 / np.pi
    Yp = Yc
    # /np.tile(Y.mean(0), (Y.shape[0], 1))
    mean_bold = Yp.std(0).mean()

    #print 'Median Angle ' + median_angle
    #print 'Mean Bold ' + mean_bold

    return mean_bold, median_angle

def calc_target_angle(mean_bolds, median_angles):
    """
    Calculates a target angle based on median angle parameters of
    the group.

    Parameters
    ----------
    mean_bolds : list (floats)
        List of mean bold amplitudes of the group
    median_angles : list (floats)
        List of median angles of the group

    Returns
    -------
    target_angle : float
        Calculated target angle of the given group
    """
    import numpy as np

    if (len(mean_bolds) != len(median_angles)):
        raise ValueError('Length of parameters do not match')

    X = np.ones((len(mean_bolds), 2))
    X[:, 1] = np.array(mean_bolds)

    Y = np.array(median_angles)

    B = np.linalg.inv(X.T.dot(X)).dot(X.T).dot(Y)
    target_bold = X[:, 1].min()
    target_angle = target_bold * B[1] + B[0]

    #print 'target angle ' + target_angle

    return target_angle

def create_target_angle(name='target_angle'):
    """
    Target Angle Calculation

    Parameters
    ----------
    name : string, optional
        Name of the workflow.

    Returns
    -------
    target_angle : nipype.pipeline.engine.Workflow
        Target angle workflow.

    Notes
    -----

    Workflow Inputs::

        inputspec.subjects : list (nifti files)
            List of subject paths.

    Workflow Outputs::

        outputspec.target_angle : float
            Target angle over the provided group of subjects.

    Target Angle procedure:

    1. Compute the median angle and mean bold amplitude of each subject in the group.
    2. Fit a linear model with median angle as the dependent variable.
    3. Calculate the corresponding median_angle on the fitted model for the subject
       with the smallest mean bold amplitude of the group.

    Workflow Graph:

    .. image:: ../images/target_angle.dot.png
        :width: 500

    Detailed Workflow Graph:

    .. image:: ../images/target_angle_detailed.dot.png
        :width: 500

    """
    target_angle = pe.Workflow(name=name)

    inputspec = pe.Node(utility.IdentityInterface(fields=['subjects']),
                        name='inputspec')
    outputspec = pe.Node(utility.IdentityInterface(fields=['target_angle']),
                         name='outputspec')

    cmap = pe.MapNode(utility.Function(input_names=['subject'],
                                    output_names=['mean_bold',
                                                  'median_angle'],
                                    function=calc_median_angle_params),
                      name='median_angle_params',
                      iterfield=['subject'])

    cta = pe.Node(utility.Function(input_names=['mean_bolds',
                                             'median_angles'],
                                output_names=['target_angle'],
                                function=calc_target_angle),
                  name='target_angle')

    target_angle.connect(inputspec, 'subjects',
                         cmap, 'subject')
    target_angle.connect(cmap, 'mean_bold',
                         cta, 'mean_bolds')
    target_angle.connect(cmap, 'median_angle',
                         cta, 'median_angles')
    target_angle.connect(cta, 'target_angle',
                         outputspec, 'target_angle')

    return target_angle


