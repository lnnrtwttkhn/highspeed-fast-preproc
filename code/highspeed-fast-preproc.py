import sys
import nest_asyncio
from preproc.functions import setup, get_data
from preproc.workflows import workflow_main, write_graph
nest_asyncio.apply()

cfg = setup()
try:
    __file__
    cfg['code_execution'] = 'terminal'
except NameError:
    cfg['code_execution'] = 'interactive'

if cfg['code_execution'] == 'terminal':
    get_data(cfg=cfg)
    # unlock_data()

wf_main = workflow_main(cfg)
write_graph(wf=wf_main, wf_name=wf_main.name, cfg=cfg)
if 'darwin' in sys.platform:
    wf_main.run(plugin='Linear')
elif 'linux' in sys.platform:
    wf_main.run(plugin='SLURM', plugin_args=dict(template=cfg['job_template']))
