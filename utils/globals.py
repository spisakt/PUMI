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