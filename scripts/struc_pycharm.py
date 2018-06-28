import sys                                                         
sys.path.append("/home/balint/Dokumentumok/phd/github/")
# az importalasnal az ~_preproc utan a .fajlnev-et kell megadni
import nipype
import nipype.pipeline as pe
# import the defined workflows from the anat_preproc folder
import PUMI.anat_preproc.better as bet
import PUMI.anat_preproc.faster as fast
import PUMI.anat_preproc.anat2mni as anat2mni
import PUMI.anat_preproc.bbr as bbr
# import the necessary workflows from the func_preproc folder
import PUMI.func_preproc.onevol as onevol
# a workflown belul az altalunk az elso sorban definialt fgv nevet kell a . utan irni.
mybet=bet.bet_workflow()
myfast=fast.fast_workflow()
myanat2mni=anat2mni.anat2mni_workflow()
mybbr=bbr.bbr_workflow()
myonevol=onevol.onevol_workflow()
pickindex = lambda x, i: x[i]
#mybbrregist.run()
totalWorkflow=nipype.Workflow('totalWorkflow')
totalWorkflow.base_dir='.'
totalWorkflow.connect([(mybet,myfast,
			[('outputspec.brain',
			'inputspec.brain')]), (mybet,myanat2mni,
						[('outputspec.brain','inputspec.brain'),
						('outputspec.skull','inputspec.skull')]),
			(mybet,mybbr,
			[('outputspec.skull','inputspec.skull')]),
			(myfast,mybbr,
			[(('outputspec.probability_maps',pickindex,2),'inputspec.anat_wm_segmentation')]),
			(myonevol,mybbr,
			[('outputspec.func1vol','inputspec.func')])
		])

#totalWorkflow.run()

