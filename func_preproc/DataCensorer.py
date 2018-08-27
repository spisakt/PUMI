def datacens_workflow(SinkTag="func_preproc", wf_name="data_censoring"):

    """

        Modified version of CPAC.scrubbing.scrubbing +
                            CPAC.generate_motion_statistics.generate_motion_statistics +
                            CPAC.func_preproc.func_preproc

    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/scrubbing/scrubbing.html`
    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/generate_motion_statistics/generate_motion_statistics.html`
    `source: https://fcp-indi.github.io/docs/developer/_modules/CPAC/func_preproc/func_preproc.html`

    Description:
        Do the data censoring on the 4D functional data. First, it calculates the framewise displacement according to Power's method. Second, it
        indexes the volumes which FD is in the upper part in percent(determined by the threshold variable which is 5% by default). Thirdly, it excludes those volumes and one volume
        before and 2 volumes after the indexed volume. The workflow returns a 4D scrubbed functional data.

    Workflow inputs:
        :param func: The reoriented,motion occrected, nuissance removed and bandpass filtered functional file.
        :param FD: the frame wise displacement calculated by the MotionCorrecter.py script
        :param threshold: threshold of FD volumes which should be excluded
        :param SinkDir:
        :param SinkTag: The output directory in which the returned images (see workflow outputs) could be found in a subdirectory directory specific for this workflow..

    Workflow outputs:

        :return: datacens_workflow - workflow




    Balint Kincses
    kincses.balint@med.u-szeged.hu
    2018


    References
    ----------

    .. [1] Power, J. D., Barnes, K. A., Snyder, A. Z., Schlaggar, B. L., & Petersen, S. E. (2012). Spurious
           but systematic correlations in functional connectivity MRI networks arise from subject motion. NeuroImage, 59(3),
           2142-2154. doi:10.1016/j.neuroimage.2011.10.018

    .. [2] Power, J. D., Barnes, K. A., Snyder, A. Z., Schlaggar, B. L., & Petersen, S. E. (2012). Steps
           toward optimizing motion artifact removal in functional connectivity MRI; a reply to Carp.
           NeuroImage. doi:10.1016/j.neuroimage.2012.03.017

    .. [3] Jenkinson, M., Bannister, P., Brady, M., Smith, S., 2002. Improved optimization for the robust
           and accurate linear registration and motion correction of brain images. Neuroimage 17, 825-841.

    """


    import os
    import nipype
    import nipype.pipeline as pe
    import nipype.interfaces.utility as utility
    import nipype.interfaces.io as io
    import PUMI.utils.globals as globals
    import PUMI.utils.QC as qc

    SinkDir = os.path.abspath(globals._SinkDir_ + "/" + SinkTag)
    if not os.path.exists(SinkDir):
        os.makedirs(SinkDir)

    # Identitiy mapping for input variables
    inputspec = pe.Node(utility.IdentityInterface(fields=['func',
                                                          'FD',
                                                          'threshold',]),
                        name='inputspec')
    inputspec.inputs.threshold = 5

    #TODO_ready check CPAC.generate_motion_statistics.generate_motion_statistics script. It may use the FD of Jenkinson to index volumes which violate the upper threhold limit, no matter what we set.
    # - we use the power method to calculate FD
    # Determine the indices of the upper part (which is defined by the threshold, deafult 5%) of values based on their FD values
    calc_upprperc = pe.MapNode(utility.Function(input_names=['in_file',
                                                        'threshold'],
                                           output_names=['frames_in_idx',
                                                         'percentFD'],
                                           function=calculate_upperpercent),
                               iterfield=['in_file'],
                             name='calculate_upperpercent')

    # Generate the weird input for the scrubbing procedure which is done in afni
    craft_scrub_input = pe.MapNode(utility.Function(input_names=['scrub_input', 'frames_in_1D_file'],
                                              output_names=['scrub_input_string'],
                                              function=get_indx),
                                   iterfield=['scrub_input', 'frames_in_1D_file'],
                                name='scrubbing_craft_input_string')
    # Scrub the image
    scrubbed_preprocessed = pe.MapNode(utility.Function(input_names=['scrub_input'],
                                                  output_names=['scrubbed_image'],
                                                  function=scrub_image),
                                       iterfield=['scrub_input'],
                                    name='scrubbed_preprocessed')

    myqc = qc.timecourse2png("timeseries", tag="040_censored")

    outputspec = pe.Node(utility.IdentityInterface(fields=['scrubbed_image', 'FD']),
                         name='outputspec')

    # save data out with Datasink
    ds=pe.Node(interface=io.DataSink(),name='ds')
    ds.inputs.base_directory=SinkDir


    #TODO_ready: some plot for qualitiy checking

    # Create workflow
    analysisflow = pe.Workflow(wf_name)
    ###Calculating mean Framewise Displacement (FD) as Power et al., 2012
    # Calculating frames to exclude and include after scrubbing
    analysisflow.connect(inputspec, 'FD', calc_upprperc, 'in_file')
    analysisflow.connect(inputspec, 'threshold', calc_upprperc, 'threshold')
    # Create the proper format for the scrubbing procedure
    analysisflow.connect(calc_upprperc, 'frames_in_idx', craft_scrub_input, 'frames_in_1D_file')
    analysisflow.connect(calc_upprperc, 'out_file', ds, 'numberofcens') # TODO save this in separet folder for QC
    analysisflow.connect(inputspec, 'func', craft_scrub_input, 'scrub_input')
    # Do the scubbing
    analysisflow.connect(craft_scrub_input, 'scrub_input_string', scrubbed_preprocessed, 'scrub_input')
    # Output
    analysisflow.connect(scrubbed_preprocessed, 'scrubbed_image', outputspec, 'scrubbed_image')
    analysisflow.connect(inputspec, 'FD', outputspec, 'FD')
    # Save a few files
    #analysisflow.connect(scrubbed_preprocessed, 'scrubbed_image', ds, 'scrubbed_image')
    #analysisflow.connect(calc_upprperc, 'percentFD', ds, 'scrubbed_image.@numberofvols')
    analysisflow.connect(scrubbed_preprocessed, 'scrubbed_image', myqc, 'inputspec.func')


    return analysisflow


def calculate_upperpercent(in_file,threshold, frames_before=1, frames_after=2):
    import os
    import numpy as np
    from numpy import loadtxt
    # Receives the FD file to calculate the upper percent of violating volumes
    powersFD_data = loadtxt(in_file)
    powersFD_data[0] = 0
    sortedpwrsFDdata = sorted(powersFD_data)
    limitvalueindex = int(len(sortedpwrsFDdata) * threshold / 100)
    limitvalue = sortedpwrsFDdata[len(sortedpwrsFDdata) - limitvalueindex]
    frames_in_idx = np.argwhere(powersFD_data < limitvalue)[:,0]
    frames_out = np.argwhere(powersFD_data >= limitvalue)[:, 0]
    extra_indices = []
    for i in frames_out:

        # remove preceding frames
        if i > 0:
            count = 1
            while count <= frames_before:
                extra_indices.append(i - count)
                count += 1

        # remove following frames
        count = 1
        while count <= frames_after:
            extra_indices.append(i + count)
            count += 1

    indices_out = list(set(frames_out) | set(extra_indices))
    indices_out.sort()
    frames_in_idx=np.setdiff1d(frames_in_idx, indices_out)
    frames_in_idx_str = ','.join(str(x) for x in frames_in_idx)
    frames_in_idx = frames_in_idx_str.split()

    count = np.float(powersFD_data[powersFD_data > limitvalue].size)
    percentFD = (count * 100 / (len(powersFD_data) + 1))

    out_file = os.path.join(os.getcwd(), 'numberofcensoredvolumes.txt')
    f = open(out_file, 'w')
    f.write("%.3f," % (percentFD))
    f.close()

    return frames_in_idx, percentFD, out_file

def get_indx(scrub_input, frames_in_1D_file):
    """
    Method to get the list of time
    frames that are to be included

    Parameters
    ----------
    in_file : string
        path to file containing the valid time frames

    Returns
    -------
    scrub_input_string : string
        input string for 3dCalc in scrubbing workflow,
        looks something like " 4dfile.nii.gz[0,1,2,..100] "

    """

    #f = open(frames_in_1D_file, 'r')
    #line = f.readline()
    #line = line.strip(',')
    frames_in_idx_str = '[' + ','.join(str(x) for x in frames_in_1D_file) + ']'
    #if line:
    #    indx = map(int, line.split(","))
    #else:
     #   raise Exception("No time points remaining after scrubbing.")
    #f.close()

    #scrub_input_string = scrub_input + str(indx).replace(" ", "")
    scrub_input_string = scrub_input + frames_in_idx_str
    return scrub_input_string

def scrub_image(scrub_input):
    """
    Method to run 3dcalc in order to scrub the image. This is used instead of
    the Nipype interface for 3dcalc because functionality is needed for
    specifying an input file with specifically-selected volumes. For example:
        input.nii.gz[2,3,4,..98], etc.

    Parameters
    ----------
    scrub_input : string
        path to 4D file to be scrubbed, plus with selected volumes to be
        included

    Returns
    -------
    scrubbed_image : string
        path to the scrubbed 4D file

    """

    import os

    os.system("3dcalc -a %s -expr 'a' -prefix scrubbed_preprocessed.nii.gz" % scrub_input)

    scrubbed_image = os.path.join(os.getcwd(), "scrubbed_preprocessed.nii.gz")

    return scrubbed_image



