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

def mc_workflow(reference_vol,
                SinkTag = "func_preproc",
                wf_name="motion_correction"):

    """
    Modified version of CPAC.func_preproc.func_preproc and CPAC.generate_motion_statistics.generate_motion_statistics:

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/func_preproc/func_preproc.html`
    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/generate_motion_statistics/generate_motion_statistics.html`

    Use FSL MCFLIRT to do the motion correction of the 4D functional data and use the 6df rigid body motion parameters to calculate friston24 parameters
    for later nuissance regression step.

    Workflow inputs:
        :param func: The reoriented functional file.
        :param ref_vol: The index of the volume which the rigid body registration (motion correction) will use as reference.
        The default is the last volume which is returned by the info_get.tMinMax function.
        The reason of this is because the last volume is closest to the fieldmapin the PAINTER study.
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

    # currently aligned to middle volume (default)
    # todo_ready: make parametrizable: the reference_vol variable is an argumentum of the mc_workflow


    # add the number of volumes in the functional data
    refvolnumber = pe.MapNode(utility.Function(input_names=['in_files','refvolnumb'],
                                               output_names=['startidx', 'stopidx','refvolidx'],
                                               function=info_get.get_idx),
                              iterfield=['in_files'],
                              name='refvolnumber')
    refvolnumber.inputs.refvolnumb=reference_vol
    # refvolnumber= pe.MapNode(interface=info_get.tMinMax(refvolnumb=reference_vol),
    #                        iterfield=['in_files'],
    #                        name='refvolnumber')

    # Wraps command **mcflirt**
    mcflirt = pe.MapNode(interface=fsl.MCFLIRT(interpolation="spline"),  #, stages=4), #stages 4: more accurate but slow
                         iterfield=['in_file','ref_vol'], # , 'ref_vol'], # make parametrizable
                         name='mcflirt')
    #TODO_ready set refernec volume number

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
    calculate_FD = pe.MapNode(utility.Function(input_names=['in_file'],
                                               output_names=['out_file'],
                                               function=calculate_FD_P),
                              iterfield=['in_file'],
                              name='calculate_FD')

    # compute mean FD
    meanFD = pe.MapNode(interface=utils_math.Txt2meanTxt,
                        iterfield=['in_file'],
                        name='meanFD')
    meanFD.inputs.axis = 0  # global mean

    pop_FD = pe.Node(interface=utils_convert.List2TxtFile,
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
    analysisflow.connect(inputspec, 'func', refvolnumber, 'in_files')
    analysisflow.connect(refvolnumber, 'refvolidx', mcflirt, 'ref_vol')
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
    analysisflow.connect(meanFD, 'mean_file', pop_FD, 'in_list')
    analysisflow.connect(pop_FD, 'txt_file', ds_fd, 'pop')

    return analysisflow

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