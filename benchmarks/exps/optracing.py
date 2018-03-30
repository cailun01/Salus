# -*- coding: future_fstrings -*-
"""
Collect data for optracing

Using alexnet_25 for 1 iteration

Scheduler: pack
Work conservation: True
Collected data: JCT
"""
from __future__ import absolute_import, print_function, division, unicode_literals

from absl import flags

from benchmarks.driver.server.config import presets
from benchmarks.driver.workload import WTL, Executor
from benchmarks.exps import run_seq, maybe_forced_preset, run_tf


FLAGS = flags.FLAGS


def main(argv):
    scfg = maybe_forced_preset(presets.OpTracing)

    def create_wl(ex):
        return WTL.create('alexnet', 25, 10, executor=ex)

    # Run alexnet_25 on TF
    wl = create_wl(Executor.TF)
    wl.env['TF_CPP_MIN_VLOG_LEVEL'] = '2'
    wl.env['TF_CPP_MIN_LOG_LEVEL'] = ''
    print(wl.env)
    run_tf(FLAGS.save_dir / 'tf', wl)

    # Run alexnet_25 on Salus
    wl = create_wl(Executor.Salus)
    run_seq(scfg.copy(output_dir=FLAGS.save_dir / "salus" / '1'), wl)

    # Run 2 alexnet_25 on Salus
    run_seq(scfg.copy(output_dir=FLAGS.save_dir / "salus" / '2'),
            create_wl(Executor.Salus),
            create_wl(Executor.Salus),
            )