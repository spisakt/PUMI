import os

_SinkDir_ = "."
_QCDir_ = "QC"
_FSLDIR_ = os.environ['FSLDIR']

class _RegType_:
    FSL = 1
    ANTS = 2

#DEFAULTS:
_fsl_bet_fract_int_thr_anat_ = 0.5
_fsl_bet_fract_int_thr_func_ = 0.3
_fsl_bet_vertical_gradient_ = 0

# Reference volume for motion correction
class _RefVolPos_:
    first=1
    middle=2
    last=3

#reference resolution could be changed here
_brainref="/data/standard/MNI152_T1_2mm_brain.nii.gz"
_headref="/data/standard/MNI152_T1_2mm.nii.gz"
_brainref_mask="/data/standard/MNI152_T1_2mm_brain_mask_dil.nii.gz"