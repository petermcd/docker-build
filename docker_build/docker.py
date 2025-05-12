"""Module to handle building docker containers."""
import subprocess
from os.path import split
from pathlib import Path
from subprocess import PIPE

from docker_build.dockerfile import Dockerfile
from docker_build.exceptions import DockerException
from docker_build.models import ExposedPortDetails, FileDetails, Response

BINARY_DIRECTORY = 'binaries/'
CONFIG_DIRECTORY = 'config/'


class Docker(object):
    """Class to handle building a new docker container."""

    __slots__ = (
        '_base_image',
        '_base_path',
        '_container_id',
        '_dockerfile',
    )

    def __init__(self, base_path: Path, container_id: str, base_image: str):
        """
        Initialize Docker.

        Args:
            base_path: Path to save files too
            container_id: The container ID to work from
            base_image: The image we will build onto
        """
        self._dockerfile: Dockerfile = Dockerfile(base_image=base_image)
        self._base_path: Path = base_path
        self._container_id: str = container_id

        binary_directory: Path = Path(base_path, BINARY_DIRECTORY)
        config_directory: Path = Path(base_path, CONFIG_DIRECTORY)

        binary_directory.mkdir(parents=True, exist_ok=True)
        config_directory.mkdir(parents=True, exist_ok=True)

    def run(
            self,
            config_files: list[str],
            binaries: list[str],
            exposed_ports: list[ExposedPortDetails],
            commands: list[str],
            entry_point: str | None = None,
    ):
        """
        Build a dockerfile based on the inputs.

        Args:
            config_files: List of config files to copy out of the origin container
            binaries: List of binary files to copy out of the origin container
            exposed_ports: Ports to be exposed
            commands: List of commands to be run during making of the container
            entry_point: Entry point to be set in the container
        """
        self._dockerfile.add_commands(commands=commands)
        self._dockerfile.add_exposed_ports(exposed_ports=exposed_ports)

        self._process_binaries(binaries=binaries)
        self._process_config_files(config_files=config_files)

        self._dockerfile.build(save_path=self._base_path, entry_point=entry_point)

    def _copy_file(self, file_details: FileDetails):
        """
        Copy a file from the container.

        Args:
            file_details: Details about the file to be copied
        """
        if self._dockerfile.file_exists(file=file_details):
            return

        source_path: str = f'{file_details.path}/{file_details.filename}'
        if file_details.symlink:
            source_path = file_details.symlink
        command: list[str] = [
            'docker',
            'cp',
            f'{self._container_id}:{source_path}',
            f'{file_details.saved_path}',
        ]
        self._run_command(command=command)
        self._dockerfile.add_files(files=file_details)

    def _get_file_origin(self, file: str) -> FileDetails:
        """
        Locate the original path for the file.

        Args:
            file: Filename and path to search for

        Returns:
            Real path and filename
        """
        ls_command: list[str] = [
            'docker',
            'exec',
            self._container_id,
            'ls',
            '-la',
            file,
        ]
        try:
            ls_response = self._run_command(command=ls_command)
        except DockerException as exc:
            raise FileNotFoundError(f'{file} could not be found') from exc
        binary_ls_split = ls_response.stdout.strip().split()
        path, filename = split(file)
        symlink_path = ''
        if binary_ls_split[0].startswith('l'):
            file_path_command = [
                'docker',
                'exec',
                self._container_id,
                'realpath',
                file,
            ]
            symlink_path = self._run_command(command=file_path_command).stdout.strip()

        binary_details = FileDetails(
            filename=filename,
            path=path,
            saved_path=Path(),
            saved_path_relative=Path(),
            symlink=symlink_path,
        )

        return binary_details

    def _parse_ldd(self, output: str):
        """
        Parse the output of ldd.

        Args:
            output: Output received from LDD command

        Returns:
            Dict of requirements
        """
        lines = output.splitlines()
        is_first: bool = True
        for line in lines:
            if is_first:
                is_first = False
                continue
            line = line.strip()
            line_split = line.split()
            if not line or line_split[1] != '=>':
                file_ldd_path = line_split[0]
            else:
                file_ldd_path = line_split[2]
            try:
                file_details = self._get_file_origin(
                    file=file_ldd_path
                )
                file_details.saved_path = Path(self._base_path, BINARY_DIRECTORY, file_details.filename)
                file_details.saved_path_relative = Path('./', BINARY_DIRECTORY, file_details.filename)
            except FileNotFoundError:
                continue
            self._copy_file(file_details=file_details)

    def _process_binaries(self, binaries: list[str]):
        """
        Process and copy binary files.

        Args:
            binaries: List of binary files to process
        """
        for binary in binaries:
            command: list[str] = [
                'docker',
                'exec',
                self._container_id,
                'ldd',
                binary,
            ]
            command_output = self._run_command(command=command)
            self._parse_ldd(command_output.stdout)
            file_details = self._get_file_origin(
                file=binary
            )
            file_details.saved_path = Path(self._base_path, BINARY_DIRECTORY, file_details.filename)
            file_details.saved_path_relative = Path('./', BINARY_DIRECTORY, file_details.filename)
            self._copy_file(file_details=file_details)

    def _process_config_files(self, config_files: list[str]):
        """
        Process and copy config files.

        Args:
            config_files: List of config files to process
        """
        for config_file in config_files:
            file_details = self._get_file_origin(
                file=config_file
            )
            file_details.saved_path = Path(self._base_path, CONFIG_DIRECTORY, file_details.filename)
            file_details.saved_path_relative = Path('./', CONFIG_DIRECTORY, file_details.filename)
            self._copy_file(file_details=file_details)

    @staticmethod
    def _run_command(command: list[str]) -> Response:
        """
        Run a command against docker.

        Args:
            command: LIst of command parts to run

        Returns:
            Response data class
        """
        result = subprocess.run(command, stderr=PIPE, stdout=PIPE)
        if result.returncode != 0:
            raise DockerException(f'Command failed to run - {" ".join(command)}')
        return Response(
            code=result.returncode,
            stderr=result.stderr.decode('utf8'),
            stdout=result.stdout.decode('utf8'),
        )
