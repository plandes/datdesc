# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]


### Added
- Radar (a.k.a. spider) plot for figure generation.
- Add configuration to figure legend and subplot parameters.
- More booktabs generated tables control:
  - configurable rules for booktabs tables
  - configurable by line generated table line removal for more control


## [1.3.3] - 2025-10-07
### Changed
- Bug fix `None not callable` when formatting a column with thousands comma.
- Fix Pandas "empty or all-NA" warning.


## [1.3.2] - 2025-07-16
### Changed
- Fix Excel column labeling bug.


## [1.3.1] - 2025-07-16
### Added
- `DataFrameDescriber.column_descriptions` property for column metadata
  mappings.


## [1.3.0] - 2025-07-15
### Removed
- `DataDescriber.{output_path,csv_dir,yaml_dir}` paths. Now specific paths of
  where to save data is provided to `save*` methods.

### Changed
- `DataDescriber` `save*` methods expect specific paths of where data is saved.

### Added
- `DataDescriptor` JSON serialization.
- Serialized files can be input files to the CLI.


## [1.2.3] - 2025-07-15
### Changed
- Add `DataDescriber` derive and derive index meta methods.


## [1.2.2] - 2025-06-22
### Changed
- Pin `numpy` to 1.26.


## [1.2.1] - 2025-06-20
### Changed
- Upgrade [pandas] to 2.3.0.


## [1.2.0] - 2025-06-14
### Removed
- `Table.column_evals` and its functionality.  This has been replaced with
  `code_pre`, `code_post`, `code_format`, which are far more robust.
### Added
- `Table` provides a way to only output the table data using `type: only_data`.
- `Table` provides to subset the row data with `row_range: [<start>, <end>]`.
- `Table` formats as a LaTeX *booktabs* table with `booktabs: true`.
- `Table` can now round and format thousands.


## [1.1.3] - 2025-05-29
### Added
- Add file name mangle options in `DataFrameDescriber`.


## [1.1.2] - 2025-04-11
Refactor release, but still compatible with [1.1.1].

### Added
- A new feature to set variables with `\newcommand` from table values, which
  can then be used in the paper text.

### Changed
- Replaced Python templates with `jinja2`.
- Moved `Table` YAML serialization and file output to `TableFactory` for
  symmetry.
- `Table` YAML has logical field ordering.
- Added `Table.type` to allow for table re-serialization.
- Renamed CLI action name `show` to `showtab`.
- Generated tables use reverse camel notation.
- `DataFrameDescriber.tab_name` property was refactored into the method
  `get_table_name()`.
- Recover from table generation errors.  Instead, log the error, add the error
  in the `.tex` file, and keep processing.
- Fix two column slack `tabularx` bug.


## [1.1.1] - 2025-02-01
### Added
- A Pandas dataframe `zensols.persist.Stash` implementation that saves as CSV
  files.

### Changed
- Switch from Python 2 to jinja2 templates.
- Fixed non-determinate unit test case failure.


## [1.1.0] - 2025-01-11
### Removed
- Support for Python 3.10.

### Changed
- Upgraded to [zensols.util] version 1.15.


## [1.0.0] - 2025-01-06
Major feature update to switch to template rather than code-based generation
methods.

### Removed
- `Table` class and YAML attribute removed:
  * `df_code_pre`
  * `df_code`

### Added
- Definition of table templates and parameters passed to generation commands.
- A method to transpose the data, column and row metadata in
  `DataFrameDescriber.transpose`.

### Changed
- Changed from Python code to template based LaTeX tables.  The type of table
  to generate is given by a new `type` attribute in the `Table` class and YAML
  files.
- `Table` class and YAML attribute renamed:
  * `df_code_exec_pre` to `code_pre`
  * `df_code_exec` to `code_post`


## [0.2.3] - 2024-07-13
### Added
- Scientific notation formatting for arbitrary columns when generating Latex
  tables in the `Table` class.
- Save CSV and Excel files in `DataFrameDescriber`.   Previously these were
  only available in the `DataDescriber` class.
- A table that only outputs a `tabular` environment, which is useful when the a
  "floating" `table` is not permitted in environments such as `minipage`.

### Changed
- Fixed a bug with bolding max values in generated Latex tables.


## [0.2.2] - 2024-03-05
### Added
- A metadata like method in a data describer that describes what data it has.
- Pretty print functionality.


## [0.2.1] - 2023-12-29
### Added
- Index metadata for the `DataFrameDescriber` class.

### Changed
- Bugs and fixes resulting from the [pandas] 2.1 upgrade.


## [0.2.0] - 2023-12-05
### Changed
- Upgrade to [zensols.util] version 1.14.
- Upgrade to [pandas] 2.1 and `tabulate` 0.9.x.

### Added
- Support for Python 3.11.

### Removed
- Support for Python 3.9


## [0.1.1] - 2023-11-30
Feature release.

### Changed
- Saving `DataFrameDescriber` as Excel no longer require the file extension.
- Fail when trying to clobber `DataFrameDescriber` metadata and columns.

### Added
- Methods to "re-hydrate" `DataDescriber` and `DataFrameDescriber` instances
  previously dumped to the file system.
- Method (`DataFrameDescriber.format_table`) to format the dataframe's table
  using `Table`.
- CLI feature to write formatted tables using YAML and CSV files as an Excel
  file.
- Feature to save `DataFrameDescriber` as Excel from the command line.


## [0.1.0] - 2023-08-16
Downstream moderate risk update release.

### Changes
- Capitalize columns


## [0.0.3] - 2023-06-10
### Changed
- Bug fixes


## [0.0.1] - 2023-02-01
### Added
- Initial version.


<!-- links -->
[Unreleased]: https://github.com/plandes/datdesc/compare/v1.3.3...HEAD
[1.3.3]: https://github.com/plandes/datdesc/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/plandes/datdesc/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/plandes/datdesc/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/plandes/datdesc/compare/v1.2.3...v1.3.0
[1.2.3]: https://github.com/plandes/datdesc/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/plandes/datdesc/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/plandes/datdesc/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/plandes/datdesc/compare/v1.1.3...v1.2.0
[1.1.3]: https://github.com/plandes/datdesc/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/plandes/datdesc/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/plandes/datdesc/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/plandes/datdesc/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/plandes/datdesc/compare/v0.2.3...v1.0.0
[0.2.3]: https://github.com/plandes/datdesc/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/plandes/datdesc/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/plandes/datdesc/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/plandes/datdesc/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/plandes/datdesc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/plandes/datdesc/compare/v0.0.3...v0.1.0
[0.0.3]: https://github.com/plandes/datdesc/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/plandes/datdesc/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/plandes/datdesc/compare/v0.0.0...v0.0.1

[zensols.util]: https://github.com/plandes/util
[pandas]: https://pandas.pydata.org
