#!/usr/bin/env python
# Copyright 2016 Criteo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Clean Command."""


import logging
import os
import sys
import progressbar

from biggraphite.cli import command
from biggraphite import metadata_cache

_DEV_NULL = open(os.devnull, "w")


class CommandClean(command.BaseCommand):
    """Clean BigGraphite metric metadata from old metrics."""

    NAME = "clean"
    HELP = "Clean the metric metadata."

    def __init__(self):
        """Constructor."""
        self.pbar = None

    def add_arguments(self, parser):
        """Add custom arguments."""
        parser.add_argument(
            "--clean-cache",
            help="clean cache",
            action='store_true'
        )
        parser.add_argument(
            "--clean-backend",
            help="clean backend",
            action='store_true'
        )
        parser.add_argument(
            "--quiet", action="store_const", default=False, const=True,
            help="Show no output unless there are problems."
        )
        parser.add_argument(
            "--max-age",
            help="Specify the age of metrics in seconds to evict"
                 " (ie: 3600 to delete older than one hour metrics)",
            type=int,
            default=24 * 60 * 60,
            action='store'
        )
        parser.add_argument(
            "--start-key",
            help="Start key.",
        )
        parser.add_argument(
            "--end-key",
            help="End key.",
        )
        parser.add_argument(
            "--shard",
            help="Shard number.",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--nshards",
            help="Number of shards.",
            type=int,
            default=1,
        )

    def run(self, accessor, opts, on_progress=None):
        """Run some cleanups.

        See command.BaseCommand
        """
        out_fd = sys.stderr
        if opts.quiet:
            out_fd = _DEV_NULL

        if self.pbar is None:
            self.pbar = progressbar.ProgressBar(fd=out_fd,
                                                redirect_stderr=False)
        self.pbar.start()

        if on_progress is None:
            def _on_progress(done, total):
                self.pbar.max_value = total
                self.pbar.update(done)
            on_progress = _on_progress

        with accessor as bg_acc:
            if opts.clean_cache:
                if opts.storage_dir:
                    settings = {"path": opts.storage_dir, "ttl": opts.max_age}

                    logging.info("Cleaning cache from %s", settings)
                    with metadata_cache.DiskCache(bg_acc, settings) as cache:
                        cache.clean()
                else:
                    logging.error('Cannot clean disk cache because storage_dir'
                                  ' is empty')

            if opts.clean_backend:
                logging.info("Cleaning backend, removing things before %d",
                             opts.max_age)
                bg_acc.clean(opts.max_age,
                             shard=opts.shard, nshards=opts.nshards,
                             start_key=opts.start_key,
                             end_key=opts.end_key,
                             callback_on_progress=on_progress)

        self.pbar.finish()
