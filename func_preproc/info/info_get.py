from nipype.interfaces.utility import Function

def get_scan_info(in_file):
    """ Get useful scan-parameters.

    Function to extract some useful scan-parameters.

    Parameters
    ----------
    in_file : str
        Path to (functional!) nifti-image

    Returns
    -------
    TR : float
        Time-to-repetition of file
    """

    import nibabel as nib
    func = nib.load(in_file)
    header = func.header
    TR = header['pixdim'][4]
    return TR

def get_idx(in_files, stop_idx=None, start_idx=None):
    """
    Adapted from C-PAC (https://github.com/FCP-INDI/C-PAC)
    Method to get the first and the last slice for
    the functional run. It verifies the user specified
    first and last slice. If the values are not valid, it
    calculates and returns the very first and the last slice

    Parameters
    ----------
    in_file : string (nifti file)
       Path to input functional run

    stop_idx : int
        Last volume to be considered, specified by user
        in the configuration file

    stop_idx : int
        First volume to be considered, specified by user
        in the configuration file

    Returns
    -------
    stop_idx :  int
        Value of first slice to consider for the functional run

    start_idx : int
        Value of last slice to consider for the functional run

    """
    from nibabel import load

    # Init variables
    img = load(in_files)
    hdr = img.get_header()
    shape = hdr.get_data_shape()

    # Check to make sure the input file is 4-dimensional
    if len(shape) != 4:
        raise TypeError('Input nifti file: %s is not a 4D file' % in_files)
    # Grab the number of volumes
    nvols = int(hdr.get_data_shape()[3])
    lastvolidx=nvols-1

    if (start_idx == None) or (start_idx < 0) or (start_idx > (nvols - 1)):
        startidx = 0
    else:
        startidx = start_idx

    if (stop_idx == None) or (stop_idx > (nvols - 1)):
        stopidx = nvols - 1
    else:
        stopidx = stop_idx

    return stopidx, startidx, lastvolidx


TR = Function(input_names=['in_file'],
                       output_names=['TR'],
                       function=get_scan_info)


tMinMax = Function(input_names=['in_files', 'start_idx', 'stop_idx'],
                       output_names=['startidx', 'stopidx','lastvolidx'],
                       function=get_idx)

