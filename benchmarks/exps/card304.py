# -*- coding: future_fstrings -*-
#
# Copyright 2019 Peifeng Yu <peifeng@umich.edu>
# 
# This file is part of Salus
# (see https://github.com/SymbioticLab/Salus).
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Card 304: Experiment one inference job with one training job

Record inference latency. Compare inference job latency running along vs. running with a training job.

The latency should be measured with increasing throughput (qps) for the inference job.

Collected data: inference per iteration speed (latency), training throughput (derived from per iteration speed)
"""
from __future__ import absolute_import, print_function, division, unicode_literals

import tempfile
from typing import Sequence

from absl import flags
import logging
import os

from benchmarks.driver.server.config import presets
from benchmarks.driver.workload import WTL, Executor
from benchmarks.driver.utils.compatiblity import pathlib
from benchmarks.exps import (
    run_seq, maybe_forced_preset, RunFn, Pause, wait_on_pipe, release_on_pipe,
    case_switch_main,
    run_tfdist, run_tf
)


FLAGS = flags.FLAGS
logger = logging.getLogger(__name__)


def set_env(wl):
    wl.env['SALUS_TFBENCH_EVAL_INTERVAL'] = '0'
    wl.env['SALUS_TFBENCH_EVAL_RAND_FACTOR'] = '0'
    wl.env['SALUS_TFBENCH_EVAL_BLOCK'] = 'true'

    model_dir = pathlib.Path('~/../symbiotic/peifeng/tf_cnn_benchmarks_models/legacy_checkpoint_models')
    model_dir = model_dir.expanduser().resolve()
    wl.env['SALUS_TFBENCH_EVAL_MODEL_DIR'] = model_dir


def salus(argv):
    # type: (Sequence[str]) -> None
    scfg = maybe_forced_preset(presets.MostEfficient)

    name = "alexneteval"
    if len(argv) > 1:
        name = argv[0]
    batch_sizes = [int(v) for v in argv[1:]]

    if not batch_sizes:
        batch_sizes = [1, 2, 4, 8]

    batch_num = 300
    # batch_sizes = [1, 2, 4, 8, 16, 32]
    # batch_sizes = [1024, 1536, 2048, 4096]
    for idx, bs in enumerate(batch_sizes):
        with tempfile.TemporaryDirectory() as td:
            # create a background training job, the batch number has no effect here,
            # only used to distinguish different runs
            trainWl = WTL.create('inception4', 50, 100 + idx, executor=Executor.Salus)
            # make sure it runs long enough
            trainWl.env['SALUS_ITER_SECONDS'] = '300'

            # create a pipe to signal trainWl
            pipetrain = str(pathlib.Path(td).joinpath('fifotrain'))
            os.mkfifo(pipetrain)
            trainWl.env['SALUS_WAIT_FOR_SIGNAL'] = pipetrain

            # create the foreground inference job
            wl = WTL.create(name, bs, batch_num, executor=Executor.Salus)
            set_env(wl)
            wl.env['SALUS_ITER_SECONDS'] = '150'

            pipe = str(pathlib.Path(td).joinpath('fifo'))
            os.mkfifo(pipe)
            wl.env['SALUS_WAIT_FOR_SIGNAL'] = pipe

            run_seq(scfg.copy(output_dir=FLAGS.save_dir / "salus" / (name + "-inception4")),
                    trainWl,  # start the background job
                    wl,  # start the foreground job
                    # wait for both jobs to be ready
                    RunFn(lambda *args, **kwargs: wait_on_pipe(pipetrain)),
                    RunFn(lambda *args, **kwargs: wait_on_pipe(pipe)),
                    # start train job
                    RunFn(lambda *args, **kwargs: release_on_pipe(pipetrain)),
                    # wait 10 seconds
                    Pause(10),
                    # release inference job
                    RunFn(lambda *args, **kwargs: release_on_pipe(pipe)),
                    # run_seq automatically join all jobs at the end of the sequence
                    )


def tfdist(argv):
    # type: (Sequence[str]) -> None
    name = "alexneteval"
    if len(argv) > 1:
        name = argv[0]
    batch_sizes = [int(v) for v in argv[1:]]

    if not batch_sizes:
        batch_sizes = [1, 2, 4, 8]

    batch_num = 300
    # batch_sizes = [1, 2, 4, 8, 16, 32]
    # batch_sizes = [1024, 1536, 2048, 4096]
    for idx, bs in enumerate(batch_sizes):
        with tempfile.TemporaryDirectory() as td:
            # create a background training job, the batch number has no effect here,
            # only used to distinguish different runs
            trainWl = WTL.create('inception4', 50, 100 + idx, executor=Executor.TFDist)
            # make sure it runs long enough
            trainWl.env['SALUS_ITER_SECONDS'] = '300'

            # create a pipe to signal trainWl
            pipetrain = str(pathlib.Path(td).joinpath('fifotrain'))
            os.mkfifo(pipetrain)
            trainWl.env['SALUS_WAIT_FOR_SIGNAL'] = pipetrain

            # create the foreground inference job
            wl = WTL.create(name, bs, batch_num, executor=Executor.TFDist)
            set_env(wl)
            wl.env['SALUS_ITER_SECONDS'] = '150'

            pipe = str(pathlib.Path(td).joinpath('fifo'))
            os.mkfifo(pipe)
            wl.env['SALUS_WAIT_FOR_SIGNAL'] = pipe

            run_tfdist(FLAGS.save_dir / "tfdist" / (name + "-inception4"),
                       trainWl,  # start the background job
                       wl,  # start the foreground job
                       # wait for both jobs to be ready
                       RunFn(lambda *args, **kwargs: wait_on_pipe(pipetrain)),
                       RunFn(lambda *args, **kwargs: wait_on_pipe(pipe)),
                       # start train job
                       RunFn(lambda *args, **kwargs: release_on_pipe(pipetrain)),
                       # wait 10 seconds
                       Pause(10),
                       # release inference job
                       RunFn(lambda *args, **kwargs: release_on_pipe(pipe)),
                       # run_seq automatically join all jobs at the end of the sequence
                       )


def tfmps(argv):
    # type: (Sequence[str]) -> None
    name = "alexneteval"
    if len(argv) > 1:
        name = argv[0]
    batch_sizes = [int(v) for v in argv[1:]]

    if not batch_sizes:
        batch_sizes = [1, 2, 4, 8]

    batch_num = 300
    # batch_sizes = [1, 2, 4, 8, 16, 32]
    # batch_sizes = [1024, 1536, 2048, 4096]
    for idx, bs in enumerate(batch_sizes):
        with tempfile.TemporaryDirectory() as td:
            # create a background training job, the batch number has no effect here,
            # only used to distinguish different runs
            trainWl = WTL.create('inception4', 50, 100 + idx, executor=Executor.TF)
            # make sure it runs long enough
            trainWl.env['SALUS_ITER_SECONDS'] = '300'
            trainWl.extra_args += ['--min_mem']

            # create a pipe to signal trainWl
            pipetrain = str(pathlib.Path(td).joinpath('fifotrain'))
            os.mkfifo(pipetrain)
            trainWl.env['SALUS_WAIT_FOR_SIGNAL'] = pipetrain

            # create the foreground inference job
            wl = WTL.create(name, bs, batch_num, executor=Executor.TF)
            set_env(wl)
            wl.env['SALUS_ITER_SECONDS'] = '150'
            wl.extra_args += ['--min_mem']

            pipe = str(pathlib.Path(td).joinpath('fifo'))
            os.mkfifo(pipe)
            wl.env['SALUS_WAIT_FOR_SIGNAL'] = pipe

            run_tf(FLAGS.save_dir / "tfmps" / (name + "-inception4"),
                   trainWl,  # start the background job
                   wl,  # start the foreground job
                   # wait for both jobs to be ready
                   RunFn(lambda *args, **kwargs: wait_on_pipe(pipetrain)),
                   RunFn(lambda *args, **kwargs: wait_on_pipe(pipe)),
                   # start train job
                   RunFn(lambda *args, **kwargs: release_on_pipe(pipetrain)),
                   # wait 10 seconds
                   Pause(10),
                   # release inference job
                   RunFn(lambda *args, **kwargs: release_on_pipe(pipe)),
                   # run_seq automatically join all jobs at the end of the sequence
                   )


def tfmps2(argv):
    # type: (Sequence[str]) -> None
    name = "alexneteval"
    if len(argv) > 1:
        name = argv[0]
    batch_sizes = [int(v) for v in argv[1:]]

    if not batch_sizes:
        batch_sizes = [1, 2, 4, 8]

    batch_num = 300
    # batch_sizes = [1, 2, 4, 8, 16, 32]
    # batch_sizes = [1024, 1536, 2048, 4096]
    for idx, bs in enumerate(batch_sizes):
        with tempfile.TemporaryDirectory() as td:
            # create a background training job, the batch number has no effect here,
            # only used to distinguish different runs
            trainWl = WTL.create('inception4', 50, 100 + idx, executor=Executor.TF)
            # make sure it runs long enough
            trainWl.env['SALUS_ITER_SECONDS'] = '300'
            trainWl.extra_args += ['--min_mem']

            # create a pipe to signal trainWl
            pipetrain = str(pathlib.Path(td).joinpath('fifotrain'))
            os.mkfifo(pipetrain)
            trainWl.env['SALUS_WAIT_FOR_SIGNAL'] = pipetrain

            # create the foreground inference job
            wl = WTL.create(name, bs, batch_num, executor=Executor.TF)
            set_env(wl)
            wl.env['SALUS_ITER_SECONDS'] = '150'
            wl.extra_args += ['--min_mem']

            pipe = str(pathlib.Path(td).joinpath('fifo'))
            os.mkfifo(pipe)
            wl.env['SALUS_WAIT_FOR_SIGNAL'] = pipe

            run_tf(FLAGS.save_dir / "tfmps2" / (name + "-inception4"),
                   wl,  # start the foreground job
                   Pause(20),
                   trainWl,  # start the background job
                   # wait for both jobs to be ready
                   RunFn(lambda *args, **kwargs: wait_on_pipe(pipetrain)),
                   RunFn(lambda *args, **kwargs: wait_on_pipe(pipe)),
                   # start train job
                   RunFn(lambda *args, **kwargs: release_on_pipe(pipetrain)),
                   # wait 10 seconds
                   Pause(10),
                   # release inference job
                   RunFn(lambda *args, **kwargs: release_on_pipe(pipe)),
                   # run_seq automatically join all jobs at the end of the sequence
                   )


@case_switch_main
def main():
    return salus, tfdist, tfmps, tfmps2
