# Copyright 2017-2018 TensorHub, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division

import click

from guild import click_util
from . import runs_support

@click.command(name="sync")
@runs_support.runs_arg
@click.option(
    "-w", "--watch",
    is_flag=True,
    help="Watch a remote run and synchronize in the background.")
@runs_support.op_and_label_filters
@runs_support.scope_options

@click_util.use_args
@click_util.render_doc

def sync(args):
    """Synchronize remote runs.

    A remote run is an operation that runs on another system. Guild
    keeps track of where each remote run is located and can
    synchronize with it. This includes downloading files generated by
    the run as well as updating run status.

    By default, Guild synchronizes once with the remote run and
    exits. If you want to automatically synchronize with the run while
    watching its output, use the `--watch` option.

    You can only watch one running operation at a time. If you don't
    specify a RUN with the `--watch` option, Guild will watch the most
    recently started running operation.

    When a remote status stops (it finished successfully, is
    stopped, or exits with an error), Guild will no longer
    synchronize with it.

    You can synchronize specific runs by selecting them using `RUN`
    arguments. For more information, see SELECTING RUNS and FILTERING
    topics below.

    {{ runs_support.runs_arg }}

    If a `RUN` argument is not specified, ``:`` is assumed (all runs
    are selected).

    {{ runs_support.op_and_label_filters }}
    {{ runs_support.scope_options }}

    """
    from . import sync_impl
    sync_impl.main(args)
