from nipype.interfaces.utility import Function

def get_slice_times(in_files):
    """ Get useful scan-parameters for slice-timing correction.

    Function to extract some useful scan-parameters fpr slice-tim ing correction.
    If parameters are inappropriate (or slice timing correction was alread performed
    eg. by Chris Rorden's dcm2nii, than AFNI will not do any slice timing correction on the data )

    Parameters
    ----------
    in_file : str
        Path to (functional!) nifti-image

    Returns
   --------
    slice_times: vector of relative slice times
    """

    try:
        import nibabel as nib
        func = nib.load(in_files)
        header = func.header
        slicetimes = header.get_slice_times()
    except:
        return ("Unkown")
    return slicetimes  # a tuple with slice times

import sys
import nipype
import nipype.pipeline as pe
from nipype.interfaces.utility import Function


Timing = Function(input_names=['in_files'],
                       output_names=['slicetimes'],
                       function=get_slice_times)