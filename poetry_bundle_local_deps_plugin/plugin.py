import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, TypedDict

import cleo.events.console_command_event
import cleo.events.console_events
import cleo.events.event_dispatcher
import cleo.io.io
import cleo.io.outputs.output
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.factory import Factory
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.toml import TOMLFile
from tomlkit import TOMLDocument

defaults_to_ignore = {
    "*.pyc",
    "__pycache__",
    ".venv",
    ".mypy_cache",
    "node_modules",
    ".git",
}


class PluginConfig(TypedDict):
    enabled: bool
    ignore_patterns: list[str]


class BundleLocalDependenciesPlugin(ApplicationPlugin):
    def __init__(self):
        self.poetry = None
        self.application = None

    def activate(self, application: Application):
        application.event_dispatcher.add_listener(cleo.events.console_events.COMMAND, self.event_listener)

        self.poetry = application.poetry
        self.application = application

    def event_listener(
        self,
        event: cleo.events.console_command_event.ConsoleCommandEvent,
        event_name: str,
        dispatcher: cleo.events.event_dispatcher.EventDispatcher,
    ) -> None:
        if isinstance(event.command, BuildCommand):
            event.io.write_line("Building the package")
            new_command = BundleBuildCommand()
            new_command.set_application(event.command.application)
            new_command.set_poetry(event.command.poetry)
            new_command.set_env(event.command.env)
            new_command.configure()
            new_command._io = event.io
            event.command.handle = new_command.handle


class BundleBuildCommand(BuildCommand):
    def __init__(self):
        super().__init__()
        self.config: PluginConfig = {}

    def bundle_dependency(
        self,
        source_dir: Path,
        temp_dir: str,
        pyproject: TOMLDocument,
        root_pyproject: Optional[TOMLDocument] = None,
        level: int = 0,
    ) -> TOMLDocument:
        final_pyproject = pyproject if root_pyproject is None else root_pyproject

        main_dependencies = self._get_main_dependencies(pyproject)
        for name, version_or_config in {**main_dependencies}.items():
            if isinstance(version_or_config, dict) and version_or_config["path"]:
                self.line(
                    f"{' ' * level}- Bundling local dependency <c1>{name}</c1>",
                    verbosity=cleo.io.outputs.output.Verbosity.NORMAL,
                )

                dep_pyproject_path = source_dir.joinpath(Path(version_or_config["path"]), "pyproject.toml")

                if dep_pyproject_path.exists():
                    dep_pyproject = TOMLFile(dep_pyproject_path).read()
                    dep_packages = dep_pyproject["tool"]["poetry"].get("packages", [])
                    for package in dep_packages:
                        package_from = package.get("from", "")
                        dep_source_dir = dep_pyproject_path.parent.joinpath(package_from, package["include"])
                        dep_dest_dir = os.path.join(temp_dir, package_from, package["include"])

                        self.line(
                            f"{' ' * level} - Copying <c1>{dep_source_dir}</c1> to <c1>{dep_dest_dir}</c1>",
                            verbosity=cleo.io.outputs.output.Verbosity.DEBUG,
                        )
                        shutil.copytree(
                            dep_source_dir,
                            dep_dest_dir,
                            ignore=shutil.ignore_patterns(*self.config["ignore_patterns"]),
                            dirs_exist_ok=True,
                        )

                        del pyproject["tool"]["poetry"]["dependencies"][name]
                        final_packages = final_pyproject["tool"]["poetry"].get("packages", [])
                        if package not in final_packages:
                            final_packages.append({**package})

                        final_pyproject["tool"]["poetry"]["packages"] = final_packages

                        for dep_name, dep_version_or_config in {**self._get_main_dependencies(dep_pyproject)}.items():
                            if dep_name == "python":
                                continue

                            if isinstance(dep_version_or_config, dict) and "path" in dep_version_or_config:
                                self.bundle_dependency(
                                    source_dir,
                                    temp_dir,
                                    dep_pyproject,
                                    root_pyproject=pyproject if root_pyproject is None else root_pyproject,
                                    level=level + 1,
                                )
                            elif isinstance(dep_version_or_config, str) or (
                                isinstance(dep_version_or_config, dict) and "path" not in dep_version_or_config
                            ):
                                version = (
                                    isinstance(dep_version_or_config, dict)
                                    and dep_version_or_config.get("version")
                                    or dep_version_or_config
                                )

                                self.line(
                                    f"{' ' * level} - Adding dependency <c1>{dep_name}=={version}</c1>",
                                    verbosity=cleo.io.outputs.output.Verbosity.NORMAL,
                                )

                                final_deps = final_pyproject["tool"]["poetry"].get("dependencies", {})
                                final_deps[dep_name] = dep_version_or_config
                                final_pyproject["tool"]["poetry"]["dependencies"] = final_deps

        return final_pyproject

    def _get_main_dependencies(self, pyproject: TOMLDocument) -> dict:
        return pyproject["tool"]["poetry"].get("dependencies", {})

    def handle(self):
        source_dir = self.poetry.file.path.absolute().parent
        pyproject_plugin_config = self.poetry.pyproject.data["tool"].get("bundle_local_deps_config", {})
        self.config = {
            "enabled": pyproject_plugin_config.get("enabled", False),
            "ignore_patterns": pyproject_plugin_config.get("ignore_patterns", defaults_to_ignore),
        }

        if not self.config["enabled"]:
            return super().handle()

        temp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        self.line(
            f"Copying project <c1>{source_dir}</c1> to <c1>{temp_dir}</c1>",
            verbosity=cleo.io.outputs.output.Verbosity.DEBUG,
        )

        shutil.copytree(
            source_dir.as_posix(),
            temp_dir,
            ignore=shutil.ignore_patterns(*self.config["ignore_patterns"]),
            dirs_exist_ok=True,
        )

        final_pyproject = self.bundle_dependency(
            source_dir, temp_dir, TOMLFile(os.path.join(temp_dir, "pyproject.toml")).read()
        )

        TOMLFile(os.path.join(temp_dir, "pyproject.toml")).write(final_pyproject)

        temp_poetry = Factory().create_poetry(temp_dir)
        self.set_poetry(temp_poetry)

        super().handle()
        output_dir = self.option("output", "dist")
        shutil.rmtree(source_dir.joinpath(output_dir), ignore_errors=True)
        shutil.copytree(os.path.join(temp_dir, output_dir), source_dir.joinpath(output_dir), dirs_exist_ok=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
