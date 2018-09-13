def mc_workflow_fsl(reference_vol="mid",
                FD_mode="Power",
                SinkTag = "func_preproc",
                wf_name="motion_correction_fsl"):

    """
    Modified version of CPAC.func_preproc.func_preproc and CPAC.generate_motion_statistics.generate_motion_statistics:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/func_preproc/func_preproc.html`
    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/generate_motion_statistics/generate_motion_statistics.html`

    Use FSL MCFLIRT to do the motion correction of the 4D functional data and use the 6df rigid body motion parameters to calculate friston24 parameters
    for later nuissance regression step.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param reference_vol: Either "first", "mid", "last", "mean", or the index of the volume which the rigid body registration (motion correction) will use as reference.
        default: "mid"
        :param FD_mode Eiher "Power" or "Jenkinson"
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow..

    Workflow outputs:




        :return: mc_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """
    # TODO_ready nipype has the ability to calculate FD: the function from CPAC calculates it correctly
    # import relevant packages
    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import PUMI.func_preproc.info.info_get as info_get
    import nipype.interfaces.io as io
    import PUMI.utils.utils_math as utils_math
    import PUMI.utils.utils_convert as utils_convert
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)


    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'ref_vol',
                                                          'save_plots',
                                                          'stats_imgs']),
                        name='inputspec')
    inputspec.inputs.save_plots = True
    inputspec.inputs.stats_imgs = True
    inputspec.inputs.ref_vol = reference_vol

    # todo_ready: make parametrizable: the reference_vol variable is an argumentum of the mc_workflow


    # extract reference volume
    refvol = pe.MapNode(utility.Function(input_names=['refvol', 'func'],
                                               output_names=['refvol'],
                                               function=getRefVol),
                              iterfield=['func'],
                              name='getRefVol')

    # Wraps command **mcflirt**
    mcflirt = pe.MapNode(interface=fsl.MCFLIRT(interpolation="spline"), # stages=4), #stages 4: more accurate but slow
                         iterfield=['in_file','ref_file'], # , 'ref_vol'], # make parametrizable
                         name='mcflirt')

    if (reference_vol == "mean"):
        mcflirt = pe.MapNode(interface=fsl.MCFLIRT(interpolation="spline"),
                             # stages=4), #stages 4: more accurate but slow
                             iterfield=['in_file'],  # , 'ref_vol'], # make parametrizable
                             name='mcflirt')
        mcflirt.inputs.mean_vol = True
    else:
        mcflirt = pe.MapNode(interface=fsl.MCFLIRT(interpolation="spline"),
                             # stages=4), #stages 4: more accurate but slow
                             iterfield=['in_file', 'ref_file'],  # , 'ref_vol'], # make parametrizable
                             name='mcflirt')


    mcflirt.inputs.dof = 6
    mcflirt.inputs.save_mats = True
    mcflirt.inputs.save_plots = True
    mcflirt.inputs.save_rms = True
    mcflirt.inputs.stats_imgs = True

    myqc = qc.timecourse2png("timeseries", tag="010_motioncorr")

    # Calculate Friston24 parameters
    calc_friston = pe.MapNode(utility.Function(input_names=['in_file'],
                                            output_names=['out_file'],
                                            function=calc_friston_twenty_four),
                              iterfield=['in_file'],
                              name='calc_friston')

    # Calculate FD based on Power's method
    if FD_mode == "Power":
        calculate_FD = pe.MapNode(utility.Function(input_names=['in_file'],
                                               output_names=['out_file'],
                                               function=calculate_FD_P),
                              iterfield=['in_file'],
                              name='calculate_FD_Power')
    elif FD_mode == "Jenkinson":
        calculate_FD = pe.MapNode(utility.Function(input_names=['in_file'],
                                                   output_names=['out_file'],
                                                   function=calculate_FD_J),
                                  iterfield=['in_file'],
                                  name='calculate_FD_Jenkinson')

    # compute mean FD
    meanFD = pe.MapNode(interface=utils_math.Txt2meanTxt,
                        iterfield=['in_file'],
                        name='meanFD')
    meanFD.inputs.axis = 0  # global mean

    pop_FD = pe.Node(interface=utils_convert.List2TxtFileOpen,
                     name='pop_FD')

    # save data out with Datasink
    ds_fd = pe.Node(interface=io.DataSink(), name='ds_pop_fd')
    ds_fd.inputs.regexp_substitutions = [("(\/)[^\/]*$", "FD.txt")]
    ds_fd.inputs.base_directory = SinkDir

    plot_motion_rot = pe.MapNode(
        interface=fsl.PlotMotionParams(in_source='fsl'),
        name='plot_motion_rot',
        iterfield=['in_file'])
    plot_motion_rot.inputs.plot_type = 'rotations'

    plot_motion_tra = pe.MapNode(
        interface=fsl.PlotMotionParams(in_source='fsl'),
        name='plot_motion_trans',
        iterfield=['in_file'])
    plot_motion_tra.inputs.plot_type = 'translations'


    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_out_file',
                                                           'first24_file',
                                                           'mat_file',
                                                           'mc_par_file',
                                                           'FD_file']),
                         name='outputspec')

    # save data out with Datasink
    ds_nii = pe.Node(interface=io.DataSink(),name='ds_nii')
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]
    ds_nii.inputs.base_directory = SinkDir

    # save data out with Datasink
    ds_text = pe.Node(interface=io.DataSink(), name='ds_txt')
    ds_text.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".txt")]
    ds_text.inputs.base_directory = SinkDir

    # Save outputs which are important
    ds_qc_rot = pe.Node(interface=io.DataSink(),
                  name='ds_qc_rot')
    ds_qc_rot.inputs.base_directory = QCDir
    ds_qc_rot.inputs.regexp_substitutions = [("(\/)[^\/]*$", "_rot.png")]

    # Save outputs which are important
    ds_qc_tra = pe.Node(interface=io.DataSink(),
                    name='ds_qc_tra')
    ds_qc_tra.inputs.base_directory = QCDir
    ds_qc_tra.inputs.regexp_substitutions = [("(\/)[^\/]*$", "_trans.png")]


    #TODO_ready set the proper images which has to be saved in a the datasink specified directory
    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)
    analysisflow.connect(inputspec, 'func', mcflirt, 'in_file')
    analysisflow.connect(inputspec, 'func', refvol, 'func')
    analysisflow.connect(inputspec, 'ref_vol', refvol, 'refvol')
    if (reference_vol != "mean"):
        analysisflow.connect(refvol, 'refvol', mcflirt, 'ref_file')
    analysisflow.connect(mcflirt, 'par_file', calc_friston, 'in_file')
    analysisflow.connect(mcflirt, 'par_file', calculate_FD, 'in_file')

    analysisflow.connect(mcflirt, 'out_file', outputspec, 'func_out_file')
    analysisflow.connect(mcflirt, 'mat_file', outputspec, 'mat_file')
    analysisflow.connect(mcflirt, 'par_file', outputspec, 'mc_par_file')
    analysisflow.connect(mcflirt, 'out_file', ds_nii, 'mc_func')
    analysisflow.connect(mcflirt, 'par_file', ds_text, 'mc_par')
    #analysisflow.connect(mcflirt, 'std_img', ds, 'mc.@std_img')
    analysisflow.connect(mcflirt, 'rms_files', ds_text, 'mc_rms')
    #analysisflow.connect(mcflirt, 'variance_img', ds, 'mc.@variance_img')
    analysisflow.connect(calc_friston, 'out_file', outputspec, 'first24_file')
    analysisflow.connect(calc_friston, 'out_file', ds_text, 'mc_first24')
    analysisflow.connect(calculate_FD, 'out_file', outputspec, 'FD_file')
    analysisflow.connect(mcflirt, 'par_file', plot_motion_rot, 'in_file')
    analysisflow.connect(mcflirt, 'par_file', plot_motion_tra, 'in_file')
    analysisflow.connect(plot_motion_rot, 'out_file', ds_qc_rot, 'motion_correction')
    analysisflow.connect(plot_motion_tra, 'out_file', ds_qc_tra, 'motion_correction')
    analysisflow.connect(mcflirt, 'out_file', myqc, 'inputspec.func')
    # pop-level mean FD
    analysisflow.connect(calculate_FD, 'out_file', meanFD, 'in_file')
    analysisflow.connect(calculate_FD, 'out_file', ds_text, 'mc_fd')
    analysisflow.connect(meanFD, 'mean_file', pop_FD, 'in_list')
    analysisflow.connect(pop_FD, 'txt_file', ds_fd, 'pop')

    return analysisflow


def mc_workflow_afni(reference_vol="mid",
                     FD_mode="Power",
                     SinkTag="func_preproc",
                     wf_name="motion_correction_afni"
                     ):
    from nipype.interfaces.afni import preprocess
    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import PUMI.func_preproc.info.info_get as info_get
    import nipype.interfaces.io as io
    import PUMI.utils.utils_math as utils_math
    import PUMI.utils.utils_convert as utils_convert
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)
    QCDir = os.path.abspath(globals._SinkDir_ + "/" + globals._QCDir_)
    if not os.path.exists(QCDir):
        os.makedirs(QCDir)

    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'ref_vol',
                                                          'save_plots',
                                                          'stats_imgs']),
                        name='inputspec')
    inputspec.inputs.save_plots = True
    inputspec.inputs.stats_imgs = True
    inputspec.inputs.ref_vol = reference_vol

    # extract reference volume
    refvol = pe.MapNode(utility.Function(input_names=['refvol', 'func'],
                                         output_names=['refvol'],
                                         function=getRefVol),
                        iterfield=['func'],
                        name='getRefVol')


    if (reference_vol == "mean"):
        func_motion_correct1 = pe.MapNode(interface=preprocess.Volreg(),
                                          iterfield=["in_file", "basefile"],
                                          name='mc_afni_init')
        func_motion_correct1.inputs.args = '-Fourier -twopass'
        func_motion_correct1.inputs.zpad = 4
        func_motion_correct1.inputs.outputtype = 'NIFTI_GZ'

        # extract reference volume
        refvol2 = pe.MapNode(utility.Function(input_names=['refvol', 'func'],
                                             output_names=['refvol'],
                                             function=getRefVol),
                            iterfield=['func'],
                            name='getRefVol2')


    func_motion_correct = pe.MapNode(interface=preprocess.Volreg(),
                                     iterfield=["in_file", "basefile"],
                                   name='mc_afni')
    func_motion_correct.inputs.args = '-Fourier -twopass'
    func_motion_correct.inputs.zpad = 4
    func_motion_correct.inputs.outputtype = 'NIFTI_GZ'

    myqc = qc.timecourse2png("timeseries", tag="010_motioncorr")

    # Calculate Friston24 parameters
    calc_friston = pe.MapNode(utility.Function(input_names=['in_file'],
                                               output_names=['out_file'],
                                               function=calc_friston_twenty_four),
                              iterfield=['in_file'],
                              name='calc_friston')

    # Calculate FD based on Power's method
    if FD_mode == "Power":
        calculate_FD = pe.MapNode(utility.Function(input_names=['in_file'],
                                                   output_names=['out_file'],
                                                   function=calculate_FD_P),
                                  iterfield=['in_file'],
                                  name='calculate_FD_Power')
    elif FD_mode == "Jenkinson":
        calculate_FD = pe.MapNode(utility.Function(input_names=['in_file'],
                                                   output_names=['out_file'],
                                                   function=calculate_FD_J),
                                  iterfield=['in_file'],
                                  name='calculate_FD_Jenkinson')

    # compute mean FD
    meanFD = pe.MapNode(interface=utils_math.Txt2meanTxt,
                        iterfield=['in_file'],
                        name='meanFD')
    meanFD.inputs.axis = 0  # global mean

    pop_FD = pe.Node(interface=utils_convert.List2TxtFileOpen,
                     name='pop_FD')

    # save data out with Datasink
    ds_fd = pe.Node(interface=io.DataSink(), name='ds_pop_fd')
    ds_fd.inputs.regexp_substitutions = [("(\/)[^\/]*$", "FD.txt")]
    ds_fd.inputs.base_directory = SinkDir

    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_out_file',
                                                           'first24_file',
                                                           'mat_file',
                                                           'mc_par_file',
                                                           'FD_file']),
                         name='outputspec')

    # save data out with Datasink
    ds_nii = pe.Node(interface=io.DataSink(), name='ds_nii')
    ds_nii.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".nii.gz")]
    ds_nii.inputs.base_directory = SinkDir

    # save data out with Datasink
    ds_text = pe.Node(interface=io.DataSink(), name='ds_txt')
    ds_text.inputs.regexp_substitutions = [("(\/)[^\/]*$", ".txt")]
    ds_text.inputs.base_directory = SinkDir

    # TODO_ready set the proper images which has to be saved in a the datasink specified directory
    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow(wf_name)

    analysisflow.connect(inputspec, 'func', refvol, 'func')
    analysisflow.connect(inputspec, 'ref_vol', refvol, 'refvol')
    if (reference_vol == "mean"):
        analysisflow.connect(inputspec, 'func', func_motion_correct1, 'in_file')
        analysisflow.connect(refvol, 'refvol', func_motion_correct1, 'basefile')
        analysisflow.connect(func_motion_correct1, 'out_file', refvol2, 'func')
        analysisflow.connect(inputspec, 'ref_vol', refvol2, 'refvol')
        analysisflow.connect(inputspec, 'func', func_motion_correct, 'in_file')
        analysisflow.connect(refvol2, 'refvol', func_motion_correct, 'basefile')
    else:
        analysisflow.connect(inputspec, 'func', func_motion_correct, 'in_file')
        analysisflow.connect(refvol, 'refvol', func_motion_correct, 'basefile')

    analysisflow.connect(func_motion_correct, 'oned_file', calc_friston, 'in_file')
    analysisflow.connect(func_motion_correct, 'oned_file', calculate_FD, 'in_file')

    analysisflow.connect(func_motion_correct, 'out_file', outputspec, 'func_out_file')
    analysisflow.connect(func_motion_correct, 'oned_matrix_save', outputspec, 'mat_file')
    analysisflow.connect(func_motion_correct, 'oned_file', outputspec, 'mc_par_file')
    analysisflow.connect(func_motion_correct, 'out_file', ds_nii, 'mc_func')
    analysisflow.connect(func_motion_correct, 'oned_file', ds_text, 'mc_par')
    # analysisflow.connect(func_motion_correct, 'variance_img', ds, 'mc.@variance_img')
    analysisflow.connect(calc_friston, 'out_file', outputspec, 'first24_file')
    analysisflow.connect(calc_friston, 'out_file', ds_text, 'mc_first24')
    analysisflow.connect(calculate_FD, 'out_file', outputspec, 'FD_file')
    analysisflow.connect(func_motion_correct, 'out_file', myqc, 'inputspec.func')
    # pop-level mean FD
    analysisflow.connect(calculate_FD, 'out_file', meanFD, 'in_file')
    analysisflow.connect(calculate_FD, 'out_file', ds_text, 'mc_fd')
    analysisflow.connect(meanFD, 'mean_file', pop_FD, 'in_list')
    analysisflow.connect(pop_FD, 'txt_file', ds_fd, 'pop')

    return analysisflow




def getRefVol(refvol, func):
    # refvol is Either "first", "mid", "last", "mean", the index of the volume or an existing filename of a volume which the rigid body registration (motion correction) will use as reference
    # default: "mid"
    import nibabel as nb
    import numpy as np
    import os

    img4D=nb.load(func)
    if refvol=="first":
        idx=0
    elif refvol=="mid":
        idx=img4D.shape[3]/2 # warning: this does not round, but uses integer arithmetics
    elif refvol=="last":
        idx=img4D.shape[3]-1
    else:
        idx=refvol #  this does include the "mean" case, as well


    if idx=="mean":
        refdata = np.mean(img4D.dataobj, axis=3) # calculate mean image
    elif isinstance(idx, basestring): # its a string but not "mean" so it must be an existing filename
        return idx
    else:
        refdata = img4D.dataobj[..., idx] # loads only what is needed

    refimg = nb.Nifti1Image(refdata, img4D.affine, img4D.header)
    nb.save(refimg, 'mc_reference.nii.gz')

    return os.path.join(os.getcwd(), 'mc_reference.nii.gz')


def calc_friston_twenty_four(in_file):
        """
         Method to calculate friston twenty four parameters

                     Parameters
                     ----------
                     in_file: string
                         input movement parameters file from motion correction

                     Returns
                     -------
                     new_file: string
                         output 1D file containing 24 parameter values

        """

        import numpy as np
        import os

        new_data = None
        data = np.genfromtxt(in_file)
        data_squared = data ** 2
        new_data = np.concatenate((data, data_squared), axis=1)
        data_roll = np.roll(data, 1, axis=0)
        data_roll[0] = 0
        new_data = np.concatenate((new_data, data_roll), axis=1)
        data_roll_squared = data_roll ** 2
        new_data = np.concatenate((new_data, data_roll_squared), axis=1)
        new_file = os.path.join(os.getcwd(), 'fristons_twenty_four.1D')
        #np.savetxt(new_file, new_data, fmt='%0.8f', delimiter=' ')
        np.savetxt(new_file, new_data, delimiter=' ')

        return new_file


def calculate_FD_P(in_file):
    """

    Method to calculate Framewise Displacement (FD) calculations
    (Power et al., 2012)

    Parameters
    ----------
    in_file : string
        movement parameters vector file path

    Returns
    -------
    out_file : string
        Frame-wise displacement mat
        file path

    Comment by BK:
    Framewise displacement shows relative head motion as a scalar. The absolute values of relative translational (in mm) and rotational ( in mm, derived from a sphere of radius 50mm) parameters are added.
    The higher the value the larger the displacement.
    """

    import os
    import numpy as np

    out_file = os.path.join(os.getcwd(), 'FD.1D')

    lines = open(in_file, 'r').readlines()
    rows = [[float(x) for x in line.split()] for line in lines]
    cols = np.array([list(col) for col in zip(*rows)])

    translations = np.transpose(np.abs(np.diff(cols[3:6, :])))
    rotations = np.transpose(np.abs(np.diff(cols[0:3, :])))

    FD_power = np.sum(translations, axis=1) + (50 * 3.141 / 180) * np.sum(rotations, axis=1)

    # FD is zero for the first time point
    FD_power = np.insert(FD_power, 0, 0)

    np.savetxt(out_file, FD_power)

    return out_file


def calculate_FD_J(in_file):

    import numpy as np
    import os
    import sys
    import math

    """
    Method to calculate Framewise Displacement (FD) calculations
    (Jenkinson et al., 2002)
    
    Adapted from C-PAC

    Parameters; in_file : string
    Returns; out_file : string
    NOTE: infile should be the motion parameters

    """

    out_file = os.path.join(os.getcwd(), 'FD_J.1D')

    lines = open(in_file, 'r').readlines()
    rows = [[float(x) for x in line.split()] for line in lines]
    cols = np.array([list(col) for col in zip(*rows)])

    translations = np.transpose(np.diff(cols[3:6, :]))
    rotations = np.transpose(np.diff(cols[0:3, :]))

    # TODO: validate to CPACs 3D volreg-based implementation
    flag = 0

    # The default radius (as in FSL) of a sphere represents the brain
    rmax = 80.0

    out_lines = []

    for i in range(0, translations.shape[0]+1):

        if flag == 0:
            flag = 1
            # first timepoint
            out_lines.append('0')
        else:
            r = rotations[i-1,]
            t = translations[i-1,]
            FD_J = math.sqrt((rmax * rmax / 5) * np.dot(r,r) + np.dot(t,t))
            out_lines.append('\n{0:.8f}'.format(FD_J))


    with open(out_file, "w") as f:
        for line in out_lines:
            f.write(line)

    return out_file