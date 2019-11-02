<!---
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
-->
# Change Log
All notable changes to this project will be documented in this file. This change log follows the conventions of [keepachangelog.com](http://keepachangelog.com/).

## [Unreleased]
### Changed
- Add a new arity to `make-widget-async` to provide a different widget shape.

## [0.1.1] - 2019-03-29
### Changed
- Documentation on how to make the widgets.

### Removed
- `make-widget-sync` - we're all async, all the time.

### Fixed
- Fixed widget maker to keep working when daylight savings switches over.

## 0.1.0 - 2019-03-29
### Added
- Files from the new template.
- Widget maker public API - `make-widget-sync`.

[Unreleased]: https://github.com/your-name/bai-bff/compare/0.1.1...HEAD
[0.1.1]: https://github.com/your-name/bai-bff/compare/0.1.0...0.1.1
