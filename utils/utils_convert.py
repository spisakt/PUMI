from nipype.interfaces.utility import Function

def value2dict(val):
    return {'value': float(val)}


def join_values2dict(keys, vals):
    return dict(zip(keys, vals))


def float2string(float):
    return str(float)


def string2float(str):
    return float(str)

def concatenate(*arg):
    import numpy as np
    return np.concatenate(arg,axis=1)

###############################################

Val2Dict = Function(input_names=['val'],
                       output_names=['dict'],
                       function=value2dict)

JoinVal2Dict = Function(input_names=['keys', 'vals'],
                       output_names=['dict'],
                       function=join_values2dict)

Float2Str = Function(input_names=['float'],
                       output_names=['str'],
                       function=float2string)

Str2Float = Function(input_names=['str'],
                       output_names=['float'],
                       function=string2float)

Concatenate= Function(input_names=['args'],
                 output_names=['matrix'],
                 function=concatenate)