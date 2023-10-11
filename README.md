# Describe and optimize data

[![PyPI][pypi-badge]][pypi-link]
[![Python 3.9][python39-badge]][python39-link]
[![Python 3.10][python310-badge]][python310-link]
[![Build Status][build-badge]][build-link]

This API and command line program describes data in tables with metadata and
generate LaTeX tables in a `.sty` file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.  Paraemters are both files or both directories.  When using directories,
only files that match `*-table.yml` are considered.  In addition, the described
data can be hyperparameter metadata, which can be optimized with the
[hyperparameter module](#hyperparameters).

Features:
* Associate metadata with each column in a Pandas DataFrame.
* DataFrame metadata is used to format LaTeX data and exported to Excel as
  column header notes.
* Data and metadata is viewable in a nice format with paging in a web browser
  using the [Render program].
* Usable as an API during data collection for research projects.


## Documentation

See the [full documentation](https://plandes.github.io/datdesc/index.html).
The [API reference](https://plandes.github.io/datdesc/api.html) is also
available.


## Obtaining

The easiest way to install the command line program is via the `pip` installer:
```bash
pip3 install zensols.datdesc
```

Binaries are also available on [pypi].


## Usage

First create the table's configuration file.  For example, to create a Latex
`.sty` file from the CSV file `test-resources/section-id.csv` using the first
column as the index (makes that column go away) using a variable size and
placement, use:
```yaml
intercodertab:
  path: test-resources/section-id.csv
  caption: >-
    Krippendorff’s ...
  size: VAR
  placement: VAR
  single_column: true
  uses: zentable
  read_kwargs:
    index_col: 0
  write_kwargs:
    disable_numparse: true
  replace_nan: ' '
  blank_columns: [0]
  bold_cells: [[0, 0], [1, 0], [2, 0], [3, 0]]
```

Some of these fields include:

* **placement**: the placement (i.e. `h!`), which `VAR` means to create the
  command with a variable to use as the first parameter
* **size**: the font size (i.e. `small`), which `VAR` means to create the
  command with a variable to use as the second parameter
* **index_col**: clears column 0 and
* **bold_cells**: make certain cells bold
* **disable_numparse** tells the `tabulate` module not reformat numbers

See the [Table] class for a full listing of options.


## Hyperparameters

Hyperparameter metadata: access and documentation.  This package was designed
for the following purposes:

* Provide a basic scaffolding to update model hyperparameters such as
  [hyperopt].
* Generate LaTeX tables of the hyperparamers and their descriptions for
  academic papers.

Access to the hyperparameters via the API is done by calling the *set* or
*model* levels with a *dotted path notation* string.  For example, `svm.C`
first navigates to model `svm`, then to the hyperparameter named `C`.

A command line access to create LaTeX tables from the hyperparameter
definitions is available with the `hyper` action.  An example of a
hyperparameter set (a grouping of models that in turn have hyperparameters)
follows:
```yaml
svm:
  doc: 'support vector machine'
  params:
    kernel:
      type: choice
      choices: [radial, linear]
      doc: 'maps the observations into some feature space'
    C:
      type: float
      doc: 'regularization parameter'
    max_iter:
      type: int
      doc: 'number of iterations'
      value: 20
      interval: [1, 30]
```
In the example, the `svm` model has hyperparameters `kernel`, `C` and
`max_iter`.  The `kernel` type is set as a choice, which is a string that has
the constraints of matching a string in the list.  The `C` hyperparameter is a
floating point number, and the `max_iter` is an integer that must be between 1
and 30.

In this next example, the `k_means` model uses the string `k-means` in human
readable documentation, which can be Python generated code in a `dataclass`.
```yaml
k_means:
  desc: k-means
  doc: 'k-means clustering'
  params:
    n_clusters:
      type: int
      doc: 'number of clusters'
    copy_x:
      type: bool
      value: True
      doc: 'When pre-computing distances it is more numerically accurate to center the data first'
    strata:
      type: list
      doc: 'An array of stratified hyperparameters (made up for test cases).'
      value: [1, 2]
    kwargs:
      type: dict
      doc: 'Model keyword arguments (made up for test cases).'
      value:
        learning_rate: 0.01
        epochs: 3
```


## Changelog

An extensive changelog is available [here](CHANGELOG.md).


## License

[MIT License](LICENSE.md)

Copyright (c) 2023 Paul Landes


<!-- links -->
[pypi]: https://pypi.org/project/zensols.datdesc/
[pypi-link]: https://pypi.python.org/pypi/zensols.datdesc
[pypi-badge]: https://img.shields.io/pypi/v/zensols.datdesc.svg
[python39-badge]: https://img.shields.io/badge/python-3.9-blue.svg
[python39-link]: https://www.python.org/downloads/release/python-390
[python310-badge]: https://img.shields.io/badge/python-3.10-blue.svg
[python310-link]: https://www.python.org/downloads/release/python-310
[build-badge]: https://github.com/plandes/datdesc/workflows/CI/badge.svg
[build-link]: https://github.com/plandes/datdesc/actions

[hyperopt]: http://hyperopt.github.io/hyperopt/
[Render program]: https://github.com/plandes/rend

[Table]: api/zensols.datdesc.html#zensols.datdesc.table.Table
