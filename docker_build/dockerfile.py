"""Module to build dockerfiles."""
from pathlib import Path

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
        Initialize Dockerfile.

        Args:
            base_image: The image to base the new image from
        """
        self._base_image = base_image
        self._commands: list[str] = []
        self._exposed_ports: list[ExposedPortDetails] = []
        self._files: list[FileDetails] = []

    def add_commands(self, commands: str | list[str]):
        """
        Add commands.

        Args:
            commands: Command as a string or a List of commands to add
        """
        if isinstance(commands, list):
            self._commands += commands
            return
        if isinstance(commands, str):
            self._commands.append(commands)

    def add_exposed_ports(self, exposed_ports: ExposedPortDetails | list[ExposedPortDetails]):
        """
        Add exposed ports.

        Args:
            exposed_ports: Instance or a List of instances ExposedPortDetails to add
        """
        if isinstance(exposed_ports, list):
            self._exposed_ports += exposed_ports
            return
        if isinstance(exposed_ports, ExposedPortDetails):
            self._exposed_ports.append(exposed_ports)

    def add_files(self, files: FileDetails | list[FileDetails]):
        """
        Add files that will be copied to the container.

        Args:
            files: Instance or a List of instances FileDetails to add
        """
        if isinstance(files, list):
            self._files += files
            return
        if isinstance(files, FileDetails):
            self._files.append(files)

    def build(self, save_path: Path, entry_point: str | None = None):
        """
        Build the dockerfile and save it in the specified path.

        Args:
            save_path: Path and filename to save the Dockerfile too
            entry_point: Entry point to be set in the container
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

        if entry_point:
            output += f'ENTRYPOINT {entry_point}\n'

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
