# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]


### Added
- Scientific notation formatting for arbitrary columns when generating Latex
  tables in the `Table` class.
- Save CSV and Excel files in `DataFrameDescriber`.   Previously these were
  only available in the `DataDescriber` class.

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
[Unreleased]: https://github.com/plandes/datdesc/compare/v0.2.2...HEAD
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
