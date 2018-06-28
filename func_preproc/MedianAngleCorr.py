def median_angle_correct(target_angle_deg, realigned_file):
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
    print "realigned file: " + realigned_file + ", subject data dimensions: " + data.shape

    mask = (data != 0).sum(-1) != 0

    Y = data[mask].T

    Yc = Y - np.tile(Y.mean(0), (Y.shape[0], 1))
    Yn = Yc / np.tile(np.sqrt((Yc * Yc).sum(0)), (Yc.shape[0], 1))
    U, S, Vh = np.linalg.svd(Yn, full_matrices=False)

    G = Yc.mean(1)
    corr_gu = pearsonr(G, U[:, 0])
    PC1 = U[:, 0] if corr_gu[0] >= 0 else -U[:, 0]
    print 'Correlation of Global and U: ' + corr_gu

    median_angle = np.median(np.arccos(np.dot(PC1.T, Yn)))
    print 'Median Angle: ' + (180.0 / np.pi) * median_angle, \
        ', Target Angle: ' + target_angle_deg
    angle_shift = (np.pi / 180) * target_angle_deg - median_angle
    if (angle_shift > 0):
        print 'Shifting all vectors by ', \
            (180.0 / np.pi) * angle_shift + ' degrees.'
        Ynf = shiftCols(PC1, Yn, angle_shift)
    else:
        print 'Median Angle >= Target Angle, skipping correction'
        Ynf = Yn

    corrected_file = os.path.join(os.getcwd(), 'median_angle_corrected.nii.gz')
    angles_file = os.path.join(os.getcwd(), 'angles_U5_Yn.npy')

    print 'Writing U[:,0:5] angles to file...' + angles_file
    angles_U5_Yn = np.arccos(np.dot(U[:, 0:5].T, Yn))
    np.save(angles_file, angles_U5_Yn)

    print 'Writing correction to file...' + corrected_file
    data = np.zeros_like(data)
    data[mask] = Ynf.T
    writeToFile(data, nii, corrected_file)

    return corrected_file, angles_file

def mac_workflow(SinkDir=".",
        SinkTag="func_preproc",
        WorkingDirectory="."):
    """

     Modified version of CPAC.median_angle.median_angle:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/median_angle/median_angle.html`


    Do the data censoring on the 4D functional data.

    Workflow inputs:
        :param func: The reoriented functional file.
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

    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    inputspec = pe.Node(utility.IdentityInterface(fields=['realigned_file',
                                                       'target_angle']),
                        name='inputspec')
    outputspec = pe.Node(utility.IdentityInterface(fields=['final_func',
                                                        'pc_angles']),
                         name='outputspec')

    mac = pe.Node(utility.Function(input_names=['target_angle_deg',
                                             'realigned_file'],
                                output_names=['corrected_file',
                                              'angles_file'],
                                function=median_angle_correct),
                  name='median_angle_correct')
    #TODO set which files should be put into the datasink node...
    # Create workflow
    analysisflow= pe.Workflow('macWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'realigned_file', mac, 'realigned_file')
    analysisflow.connect(inputspec, 'target_angle', mac, 'target_angle_deg')
    analysisflow.connect(mac, 'corrected_file', outputspec, 'final_func')
    analysisflow.connect(mac, 'angles_file', outputspec, 'pc_angles')

    return analysisflow
# After here, functions are manipulating in a group level.
#TODO ezt nekünk is használni kell??
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
    print 'Loaded ' + subject
    print 'Volume size ' + data.shape

    Y = data[mask].T
    print 'Data shape ' + Y.shape

    Yc = Y - np.tile(Y.mean(0), (Y.shape[0], 1))
    Yn = Yc / np.tile(np.sqrt((Yc * Yc).sum(0)), (Yc.shape[0], 1))
    U, S, Vh = np.linalg.svd(Yn, full_matrices=False)

    glb = (Yn / np.tile(Yn.std(0), (Y.shape[0], 1))).mean(1)

    from scipy.stats.stats import pearsonr
    corr = pearsonr(U[:, 0], glb)
    print "PC1_glb r: " + corr

    PC1 = U[:, 0] if corr[0] >= 0 else -U[:, 0]
    median_angle = np.median(np.arccos(np.dot(PC1.T, Yn)))
    median_angle *= 180.0 / np.pi
    Yp = Yc
    # /np.tile(Y.mean(0), (Y.shape[0], 1))
    mean_bold = Yp.std(0).mean()

    print 'Median Angle ' + median_angle
    print 'Mean Bold ' + mean_bold

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

    print 'target angle ' + target_angle

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


