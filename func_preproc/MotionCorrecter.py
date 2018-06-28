def mc_workflow(func="/home/balint/Dokumentumok/phd/essen/PAINTER/probe/s002/func_data.nii.gz",
                SinkDir = ".",
                SinkTag = "func_preproc",
                WorkingDirectory="."):

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
        The reason of this is because the last volume is closest to the fieldmap.
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow..

    Workflow outputs:




        :return: mc_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    """
    #TODO maximum displacement file is a default output in AFNI 3dvolreg, however, in FSL McFLIRT I am not sure if this is equal to the rms_files output
    # import relevant packages
    import sys
    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.fsl as fsl
    import PUMI.func_preproc.info.info_get as info_get
    import nipype.interfaces.io as io

    # This is a Nipype generator. Warning, here be dragons.
    # !/usr/bin/env python
    SinkDir = os.path.abspath(SinkDir + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)


    # Basic interface class generates identity mappings
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'ref_vol',
                                                          'save_plots',
                                                          'stats_imgs']),
                        name='inputspec')
    inputspec.inputs.func=func

    inputspec.inputs.save_plots=True
    inputspec.inputs.stats_imgs=True

    # add the number of volumes in the functional data
    lastvolnum = pe.Node(interface=info_get.tMinMax,
                      name='lastvolnum')

    # Wraps command **mcflirt**
    mcflirt = pe.Node(interface=fsl.MCFLIRT(),
                      name='mcflirt')
    #mcflirt.inputs.out_file='mc_'
    mcflirt.inputs.dof=6
    mcflirt.inputs.save_mats=True
    mcflirt.inputs.save_plots=True
    mcflirt.inputs.save_rms=True
    mcflirt.inputs.stats_imgs=True

    # Calculate Friston24 parameters
    calc_friston = pe.Node(utility.Function(input_names=['in_file'],
                                            output_names=['out_file'],
                                            function=calc_friston_twenty_four),
                           name='calc_friston')


    # Basic interface class generates identity mappings
    outputspec = pe.Node(utility.IdentityInterface(fields=['func_out_file',
                                                           'first24_file',
                                                           'mat_file',
                                                           'mvpar_file']),
                         name='outputspec')

    # save data out with Datasink
    ds=pe.Node(interface=io.DataSink(),name='ds')
    ds.inputs.base_directory=SinkDir

    #TODO set the proper images which has to be saved in a the datasink specified directory
    # Create a workflow to connect all those nodes
    analysisflow = nipype.Workflow('mcWorkflow')
    analysisflow.base_dir = WorkingDirectory
    analysisflow.connect(inputspec, 'func', mcflirt, 'in_file')
    analysisflow.connect(inputspec, 'func', lastvolnum, 'in_files')
    analysisflow.connect(lastvolnum, 'lastvolidx', mcflirt, 'ref_vol')
    analysisflow.connect(mcflirt, 'par_file', calc_friston, 'in_file')
    analysisflow.connect(mcflirt, 'out_file', outputspec, 'func_out_file')
    analysisflow.connect(mcflirt, 'mat_file', outputspec, 'mat_file')
    analysisflow.connect(mcflirt, 'par_file', outputspec, 'mvpar_file')
    analysisflow.connect(mcflirt, 'out_file', ds, 'mc')
    analysisflow.connect(mcflirt, 'par_file', ds, 'mc.@par_file')
    analysisflow.connect(mcflirt, 'std_img', ds, 'mc.@std_img')
    analysisflow.connect(mcflirt, 'rms_files', ds, 'mc.@rms_file')
    analysisflow.connect(mcflirt, 'variance_img', ds, 'mc.@variance_img')
    analysisflow.connect(calc_friston, 'out_file', outputspec, 'first24_file')
    analysisflow.connect(calc_friston, 'out_file', ds, 'first24_file')


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
        np.savetxt(new_file, new_data, fmt='%0.8f', delimiter=' ')

        return new_file