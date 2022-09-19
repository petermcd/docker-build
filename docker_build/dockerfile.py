"""Module to build dockerfiles."""
from pathlib import Path
from typing import Union

from docker_build.models import ExposedPortDetails, FileDetails


class Dockerfile(object):
    """Class to handle building a Dockerfile."""

    __slots__ = (
        '_base_image',
        '_commands',
        '_exposed_ports',
        '_files',
    )

    def __init__(self, base_image: str):
        """
        Initialise Dockerfile.

        Args:
            base_image: The image to base the new image from
        """
        self._base_image = base_image
        self._commands: list[str] = []
        self._exposed_ports: list[ExposedPortDetails] = []
        self._files: list[FileDetails] = []

    def add_commands(self, commands: Union[str, list[str]]):
        """
        Add commands.

        Args:
            commands: Command as a string or a List of commands to add
        """
        if type(commands) == list:
            self._commands += commands
            return
        if type(commands) == str:
            self._commands.append(commands)
            return

    def add_exposed_ports(self, exposed_ports: Union[ExposedPortDetails, list[ExposedPortDetails]]):
        """
        Add exposed ports.

        Args:
            exposed_ports: Instance or a List of instances of ExposedPortDetails to add
        """
        if type(exposed_ports) == list:
            self._exposed_ports += exposed_ports
            return
        if type(exposed_ports) == ExposedPortDetails:
            self._exposed_ports.append(exposed_ports)
            return

    def add_files(self, files: Union[FileDetails, list[FileDetails]]):
        """
        Add files that will be copied to the container.

        Args:
            files: Instance or a List of instances of FileDetails to add
        """
        if type(files) == list:
            self._files += files
            return
        if type(files) == FileDetails:
            self._files.append(files)
            return

    def build(self, save_path: Path):
        """
        Build the dockerfile and save it in the specified path.

        Args:
            save_path: Path and filename to save the Dockerfile too
        """
        output = f'FROM {self._base_image}\n\n'

        for file in self._files:
            file_path = str(file.saved_path_relative).replace('\\', '/')
            output += f'COPY {file_path} {file.path}/{file.filename}\n'

        output += '\n'

        for command in self._commands:
            output += f'RUN {command}\n'

        output += '\n'

        for exposed_port in self._exposed_ports:
            output += f'EXPOSE {exposed_port.port}'
            if exposed_port.protocol:
                output += f'/{exposed_port.protocol}'
            output += '\n'

        with open(save_path.joinpath('Dockerfile'), 'w') as fh:
            fh.write(output)

    def file_exists(self, file: FileDetails) -> bool:
        """
        Check if a file is already added.

        Args:
            file: File to check

        Returns:
            True if added, otherwise false
        """
        return any(
            added_file.filename == file.filename and added_file.path == file.path
            for added_file in self._files
        )
