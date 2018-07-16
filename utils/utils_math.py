from nipype.interfaces.utility import Function


def add_two(a, b):
    return float(a)+float(b)


def sum_list(in_list):
    return sum(in_list)


def sub_two(a,b):
    return float(a)-float(b)


def abs_val(x):
    return abs(x)

def sec2sigmaV(TR, highpasssec):
    sigmaV=highpasssec/(2*TR)
    return sigmaV



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

Sec2sigmaV = Function(input_names=['TR', 'highpasssec'],
                       output_names=['sigmaV'],
                       function=sec2sigmaV)