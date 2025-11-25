# Describe and optimize data

[![PyPI][pypi-badge]][pypi-link]
[![Python 3.11][python311-badge]][python311-link]
[![Python 3.12][python311-badge]][python312-link]
[![Build Status][build-badge]][build-link]

In this package, Pythonic objects are used to easily (un)serialize to create
LaTeX tables, figures and Excel files.  The API and command-line program
describes data in tables with metadata and using YAML and CSV files and
integrates with [Pandas].  The paths to the CSV files to create tables from and
their metadata is given as a YAML configuration file.

Features:
* Create LaTeX tables (with captions) and Excel files (with notes) of tabular
  metadata from CSV files.
* Create LaTeX friendly encapsulated postscript (`.eps`) files from CSV files.
* Data and metadata is viewable in a nice format with paging in a web browser
  using the [Render program].
* Usable as an API during data collection for research projects.


<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
## Table of Contents

- [Documentation](#documentation)
- [Obtaining](#obtaining)
- [Usage](#usage)
    - [Tables](#tables)
    - [Figures](#figures)
- [Changelog](#changelog)
- [Community](#community)
- [License](#license)

<!-- markdown-toc end -->


## Documentation

See the [full documentation](https://plandes.github.io/datdesc/index.html).
The [API reference](https://plandes.github.io/datdesc/api.html) is also
available.


## Obtaining

The library can be installed with pip from the [pypi] repository:
```bash
pip3 install zensols.datdesc
```

Binaries are also available on [pypi].


## Usage

The library can be used as a Python API to programmatically create tables,
figures, and/or represent tabular data.  However, it also has a very robust
command-line that is intended by be used by [GNU make].  The command-line can
be used to create on the fly LaTeX `.sty` files that are generated as commands
and figures are generated as Encapsulated Postscript (`.eps`) files.

The YAML file format is used to create both tables and figures.  Parameters are
both files or both directories when using directories, only files that match
`*-table.yml` are considered on the command line.


### Tables

First create the table's configuration file.  For example, to create a Latex
`.sty` file from the CSV file `test-resources/section-id.csv` using the first
column as the index (makes that column go away) using a variable size and
placement, use:
```yaml
intercodertab:
  type: one_column
  path: test-resources/section-id.csv
  caption: >-
    Krippendorff’s ...
  single_column: true
  uses: zentable
  read_params:
    index_col: 0
  tabulate_params:
    disable_numparse: true
  replace_nan: ' '
  blank_columns: [0]
  bold_cells: [[0, 0], [1, 0], [2, 0], [3, 0]]
```

Some of these fields include:

* **index_col**: clears column 0 and
* **bold_cells**: make certain cells bold
* **disable_numparse** tells the `tabulate` module not reformat numbers

See the [Table] class for a full listing of options.


### Figures

Figures can be generated in any format supported by [matplotlib] (namely
`.eps`, `.svg`, and `.pdf`).  Figures are configured in a very similar fashion
to [tables](#tables).  The configuration also points to a CSV file, but
describes the plot.

The primary difference is that the YAML is parsed using the [Zensols parsing
rules] so the string `path: target` will be given to a new [Plot] instance as a
[pathlib.Path].

A bar plot is configured below:
```yaml
irisFig:
  image_dir: 'path: target'
  seaborn:
    style:
      style: darkgrid
      rc:
        axes.facecolor: 'str: .9'
    context:
      context: 'paper'
      font_scale: 1.3
  plots:
    - type: bar
      data: 'dataframe: test-resources/fig/iris.csv'
      title: 'Iris Splits'
      x_column_name: ds_type
      y_column_name: count
      core_pre: |
        plot.data = plot.data.groupby('ds_type').agg({'ds_type': 'count'}).\
          rename(columns={'ds_type': 'count'}).reset_index()
```
This configuration meaning:
* The top level `irisFig` creates a [Figure] instance, and when used with the
  command line, outputs this root level string as the name in the `image_dir`
  directory.
* The `image_dir` tells where to write the image.  This should be left out when
  invoking from the command-line to allow it to decide where to write the file.
* The `seaborn` section configures the [seaborn] module.
* The plots are a *list* of [Plot] instances that, like the [Figure] level, are
  populated with all the values.
* The `code` (optionally) allows the massaging of the [Pandas] dataframe
  (pointed to by `data`).  This feature also exists for [Table].

Other plot configuration examples are given in the [test
cases](test-resources/fig) directory.  See the [Figure] and [Plot] classes for
a full listing of options.


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## Community

Please star this repository and let me know how and where you use this API.
Contributions as pull requests, feedback and any input is welcome.


## License

[MIT License](LICENSE.md)

Copyright (c) 2023 - 2025 Paul Landes


<!-- links -->
[pypi]: https://pypi.org/project/zensols.datdesc/
[pypi-link]: https://pypi.python.org/pypi/zensols.datdesc
[pypi-badge]: https://img.shields.io/pypi/v/zensols.datdesc.svg
[python311-badge]: https://img.shields.io/badge/python-3.11-blue.svg
[python311-link]: https://www.python.org/downloads/release/python-3110
[python312-badge]: https://img.shields.io/badge/python-3.12-blue.svg
[python312-link]: https://www.python.org/downloads/release/python-3120
[build-badge]: https://github.com/plandes/datdesc/workflows/CI/badge.svg
[build-link]: https://github.com/plandes/datdesc/actions

[GNU make]: https://www.gnu.org/software/make/
[matplotlib]: https://matplotlib.org
[seaborn]: http://seaborn.pydata.org
[hyperopt]: http://hyperopt.github.io/hyperopt/
[pathlib.Path]: https://docs.python.org/3/library/pathlib.html
[Pandas]: https://pandas.pydata.org

[Zensols parsing rules]: https://plandes.github.io/util/doc/config.html#parsing
[Render program]: https://github.com/plandes/rend

[Table]: api/zensols.datdesc.html#zensols.datdesc.table.Table
[Figure]: api/zensols.datdesc.html#zensols.datdesc.figure.Figure
[Plot]: api/zensols.datdesc.html#zensols.datdesc.figure.Plot
