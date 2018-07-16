#!/usr/bin/env python
import PUMI.utils.Concat as conc

conc=conc.concat_workflow(2)
conc.inputs.inputspec.par1="abc"
conc.inputs.inputspec.par2="def"

conc.write_graph('graph-orig.dot', graph2use='orig', simple_form=True);
conc.write_graph('graph-exec-detailed.dot', graph2use='exec', simple_form=False);
conc.write_graph('graph.dot', graph2use='colored');
conc.run()