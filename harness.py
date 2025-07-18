#!/usr/bin/env python

from zensols.cli import ConfigurationImporterCliHarness

if (__name__ == '__main__'):
    harness = ConfigurationImporterCliHarness(
        src_dir_name='src',
        app_factory_class='zensols.datdesc.ApplicationFactory',
        proto_args='proto',
        proto_factory_kwargs={'reload_pattern': r'^zensols.datdesc'},
    )
    harness.run()
