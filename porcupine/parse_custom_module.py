from __future__ import print_function
import sys
import inspect
import importlib
import os.path as op
import json
from nipype2json import node2json
from nipype.interfaces.utility import Function

"""
This is a modified vesrion of Porcupine's parse_custom_module.
It creates a JSON with "category" according to the directory system in PUMI.
It takes input modules from porucipine/porcupanize.txt (customizable with -m)
and appends it to porcupine/PUMI2Porcupine.JSON.

Example usage:
#cd into PUMI dir
python porcupine/parse_custom_module.py
"""

def custommodule2json(porcupanize, verbose, add_path):



    jsons = []

    with open(porcupanize, "r") as f:
        modules = f.readlines()

        for module_path in modules:
            module_path = module_path.strip('\n')
            moduledir = op.dirname(module_path)
            sys.path.append(moduledir)
            tags = moduledir.split("/")
            print(module_path)
            module_to_import = op.basename(module_path).replace('.py', '')
            module = importlib.import_module(module_to_import)
            module_name = module.__name__
            print("Parsing custom module %s ..." % module_name)

            for node in dir(module):
                node_inst = getattr(module, node)

                if isinstance(node_inst, Function):

                    name = str(node)

                    if verbose:
                        print("Adding node '%s'" % name)

                    mpath = module_path if add_path else None
                    thisjson = node2json(node_inst, node_name=name, custom_node=True,
                              module=module_name, module_path=mpath)
                    thisjson["category"] = ["PUMI"] + tags
                    thisjson["import"] = "import PUMI." + ".".join(tags) + "." + module_name + " as " + module_name
                    thisjson["title"]["code"][0]["argument"]["import"] = thisjson["import"]
                    print(thisjson["import"])
                    jsons.append(thisjson)

    outfn = op.abspath('porcupine/PUMI2Porcupine.JSON')
    print("Writing nodes to %s ..." % outfn, end='')
    with open(outfn, 'w') as outfile:
        json.dump({'nodes': jsons}, outfile, sort_keys=False, indent=2)
    print(' done.')


if __name__ == '__main__':

    from argparse import ArgumentParser
    parser = ArgumentParser(description='Parse custom modules w/Nipype nodes.')
    parser.add_argument('-m', dest='module', type=str,
                        help="Module list to parse  (text file)", default="porcupine/porcupanize.txt" )
    parser.add_argument('-v', dest='verbose', action='store_true',
                        help="Print much more output ...")
    parser.add_argument('-a', dest='add_path', action='store_true',
                        help=('Whether to add the absolute path of the module '
                              'to the Nipype-script; if False (default), the '
                              'module is NOT added to the PYTHON_PATH, and '
                              'should thus be located in the directory from '
                              'which the pipeline is run'))
    args = parser.parse_args()
    custommodule2json(args.module, args.verbose, args.add_path)
