# Poetry Bundle Local Dependencies Plugin

## SonarCloud Status

[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=bugs)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)

[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=lucasvieirasilva_poetry-bundle-local-deps-plugin&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=lucasvieirasilva_poetry-bundle-local-deps-plugin)

Poetry plugin to bundle local dependencies (only path, not supported git or url) into a single package.

## Motivation

Poetry is a great tool to manage Python dependencies, and works perfectly when there only one pyproject in the repository, however, for many reasons, you may want to have multiple pyproject files in the same repository, and have local shared dependencies to avoid code duplication, however, when you want to distribute your package, the `poetry build` command generates the dist package referencing the local path, which does not work in other environments.

In some cases, you don't want to publish all the auxiliary packages, or if you are deploying your application to a Docker or an AWS Lambda, you also don't want to deal with resolving the local dependencies by yourself.

This plugin aims to solve this problem by intercepting the `poetry build` command and generating the dist package with the local dependencies and their dependencies bundled into a single package.

This plugin is lightweight version of [@nxlv/python](https://www.npmjs.com/package/@nxlv/python) Nx monorepo plugin.

## How it works

1. Intercept the `poetry build` command.
2. Create a temporary directory.
3. Copy all the project files to the temporary directory.
4. Read the `pyproject.toml` and find the local dependencies.
5. For each local dependency, copy the `pyproject.toml::tool.poetry.packages` to the temporary directory, (recursively if necessary).
6. Let Poetry build continue as usual (pointing to the temporary directory).
7. After the build is done, copy the generated dist package to the original directory.
8. Remove the temporary directory.

### Example

`package/a/pyproject.toml`

```toml
[tool.poetry]
name = "a"
version = "0.1.0"
description = ""

  [[tool.poetry.packages]]
  include = "a"

[tool.poetry.dependencies]
python = "^3.12"
b = { path = "../b", develop = true }
```

`package/b/pyproject.toml`

```toml
[tool.poetry]
name = "b"
version = "0.1.0"
description = ""

  [[tool.poetry.packages]]
  include = "b"

[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.32.3"
```

The standard behavior of `poetry build` would generate the following dist package:

`a-0.1.0.dist-info/METADATA`

```text
Metadata-Version: 2.1
Name: a
Version: 0.1.0
Summary:
Requires-Python: >=3.12,<4.0
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.12
Requires-Dist: b @ file:///Users/lucasvieira/Projects/poetry-bundle-local-deps-plugin-demo/packages/b
```

`a-0.1.0/`

```text
- a/*.py
- PKG-INFO
- pyproject.toml
```

Which would not work if you try to install it in another environment.

With this plugin, the dist package would be:

`a-0.1.0.dist-info/METADATA`

```text
Metadata-Version: 2.1
Name: a
Version: 0.1.0
Summary:
Requires-Python: >=3.12,<4.0
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.12
Requires-Dist: requests (>=2.32.3,<3.0.0)
```

`a-0.1.0/`

```text
- a/*.py
- b/*.py
- PKG-INFO
- pyproject.toml
```

Which would work in any environment, because all the dependencies are bundled into a single package.

## Install

`poetry self add poetry-bundle-local-deps-plugin`

## Usage

Enable the plugin in the `pyproject.toml`:

```toml
[tool.bundle_local_deps_config]
enabled = true
```

Run the `poetry build` command as usual.

## Contributing

- See our [Contributing Guide](CONTRIBUTING.md)

## Change Log

- See our [Change Log](CHANGELOG.md)
