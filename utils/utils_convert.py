from nipype.interfaces.utility import Function


def value2dict(val):
    return {'value': float(val)}


def join_values2dict(keys, vals):
    return dict(zip(keys, vals))


def float2string(float):
    return str(float)


def string2float(str):
    return float(str)
# Concatenate txt files column wise to the regress out nuissance variables from the data
def concatenate(par1, par2='', par3='', par4='', par5='', par6='', par7='', par8='', par9='', par10=''):
    import os
    import numpy as np
    totpar1=np.loadtxt(par1)
    totpar=totpar1
    if par2:
        totpar2=np.loadtxt(par2)
        totpar=np.concatenate((totpar,totpar2),axis=1)
    if par3:
        totpar3=np.loadtxt(par3)
        totpar=np.concatenate((totpar, totpar3), axis=1)
    if par4:
        totpar4=np.loadtxt(par4)
        totpar = np.concatenate((totpar, totpar4), axis=1)
    if par5:
        totpar5= np.loadtxt(par5)
        totpar = np.concatenate((totpar, totpar5), axis=1)
    if par6:
        totpar6= np.loadtxt(par6)
        totpar = np.concatenate((totpar, totpar6), axis=1)
    if par7:
        totpar7= np.loadtxt(par7)
        totpar = np.concatenate((totpar, totpar7), axis=1)
    if par8:
        totpar8= np.loadtxt(par8)
        totpar = np.concatenate((totpar, totpar8), axis=1)
    if par9:
        totpar9= np.loadtxt(par9)
        totpar = np.concatenate((totpar, totpar9), axis=1)
    if par10:
        totpar10= np.loadtxt(par10)
        totpar = np.concatenate((totpar, totpar10), axis=1)
    np.savetxt('parfiles',totpar)
    return os.getcwd() + '/parfiles'

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
