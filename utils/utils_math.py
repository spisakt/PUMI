from nipype.interfaces.utility import Function


def add_two(a, b):
    return float(a)+float(b)


def sum_list(in_list):
    return sum(in_list)


def sub_two(a,b):
    return float(a)-float(b)


def abs_val(x):
    return abs(x)

def sec2sigmaV(TR, sec):
    sigmaV=sec/(2*TR)
    return sigmaV

# calculates colmeans, rowmenas or global mean, depenxding on the 'axis' parameter
# and saves it to another txt
def txt2MeanTxt(in_file, axis=None, header=False):
    import numpy as np
    import os
    if header:
        print "drop first line"
        data = np.loadtxt(in_file, skiprows=1) #header -> dropline
    else:
        print "don't drop first line"
        data = np.loadtxt(in_file)
    mean = data.mean(axis=axis)
    np.savetxt('mean.txt', [mean])
    return os.getcwd() + '/mean.txt'

def txt2MaxTxt(in_file, axis=None, header=False):
    import numpy as np
    import os
    if header:
        print "drop first line"
        data = np.loadtxt(in_file, skiprows=1) #header -> dropline
    else:
        print "don't drop first line"
        data = np.loadtxt(in_file)
    mean = data.max(axis=axis)
    np.savetxt('max.txt', [mean])
    return os.getcwd() + '/max.txt'


###############################################

AddTwo = Function(input_names=['a', 'b'],
                       output_names=['sum'],
                       function=add_two)

SumList = Function(input_names=['in_list'],
                       output_names=['sum'],
                       function=sum_list)

SubTwo = Function(input_names=['a', 'b'],
                       output_names=['dif'],
                       function=sub_two)

Abs = Function(input_names=['x'],
                       output_names=['abs'],
                       function=abs_val)

Sec2sigmaV = Function(input_names=['TR', 'sec'],
                       output_names=['sigmaV'],
                       function=sec2sigmaV)

Txt2meanTxt = Function(input_names=['in_file', 'axis', 'header'],
                       output_names=['mean_file'],
                       function=txt2MeanTxt)

Txt2maxTxt = Function(input_names=['in_file', 'axis', 'header'],
                       output_names=['max_file'],
                       function=txt2MaxTxt)