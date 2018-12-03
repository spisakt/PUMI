#!/usr/bin/env python
# start it like: scripts/generate_gantt_chart.py
# from the project folder
import PUMI.utils.resource_profiler as rp
rp.generate_gantt_chart('/Users/tspisak/Dropbox/comp/PAINTeR/szeged/run_stats.log', cores=8)