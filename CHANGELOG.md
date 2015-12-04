# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.4.1] - 2015-12-04
### Added
- Prompt for automatic creation of databases when not using the auto-installer

### Fixed
- Resolved an installation issue with IPS versions 4.1.4+
- Fixed a MySQL query bug when dropping existing database tables for new installations


## [0.4.0] - 2015-10-27
### Added
- mysql command
- Install and configure the PHP XDebug extension on setup

### Changed
- Increased PHP upload_max_filesize and post_max_size to 1GB on setup


## [0.3.1] - 2015-10-01
### Added
- Generate a welcome message to be displayed on first login after setup
- ipsv man page
- Windows Vagrant script and portable putty executable added to release binaries

### Changed
- Clarified the IPS username / password prompts (Renamed to IPS Username/Password)

### Fixed
- Unlink Nginx default configuration in sites-enabled on setup


## [0.3.0] - 2015-10-01
### Added
- A fantastic spinning arrow
- Support for IPS 4.1 development builds with --version="latest_dev"
- delete command
- ProgressBar padding was fixed width where it should be dynamically adjusted

### Changed
- --force flag now actually serves its purpose properly
- www aliases will not be automatically generated for localhost and IP address domains
- Remove default Nginx server block on setup
- Replace init.d subprocess calls with service calls

### Fixed
- setup.py should be using install_requires, not requires


## [0.2.0] - 2015-09-29
### Added
- list command
- enable command
- disable command
- versions command
- Support for explicit version installations
- File logging

### Changed
- Major application structure and API refactoring

### Fixed
- Database transaction manager was not committing properly
- Various dev_tools installer bugfixes
- Minor color formatting bugfixes
