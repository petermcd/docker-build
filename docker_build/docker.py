"""Module to handle building docker containers."""
import subprocess
from dataclasses import dataclass
from os.path import split
from subprocess import PIPE

BINARY_DIRECTORY = 'copied_files/binaries/'
CONFIG_DIRECTORY = 'copied_files/config/'


@dataclass
class FileDetails:
    """Dataclass for the details of files to copy from a container."""

    filename: str
    path: str
    symlink_filename: str
    symlink_path: str


@dataclass
class Response(object):
    """Data class to store command responses."""

    code: int
    stderr: str
    stdout: str


class DockerException(Exception):
    """Standard Docker exception."""


class Docker(object):
    """Class to handle building a new docker container."""

    __slots__ = (
        '_base_image',
        '_commands',
        '_container_id',
        '_copied_binaries',
        '_copied_config',
        '_exposed_ports',
    )

    def __init__(self, container_id: str, base_image: str):
        """
        Initialise Docker.

        Args:
            container_id: The container ID to work from
            base_image: The image we will build onto
        """
        self._container_id = container_id
        self._base_image = base_image
        self._commands: list[str] = []
        self._copied_binaries: dict[str, FileDetails] = {}
        self._copied_config: dict[str, FileDetails] = {}
        self._exposed_ports: list[str] = []

    def run(self, config_files: list[str], binaries: list[str], exposed_ports: list[str], commands: list[str]):
        """
        Build a dockerfile based on the inputs.

        Args:
            config_files: List of config files to copy out of the origin container
            binaries: List of binaries files to copy out of the origin container
            exposed_ports: Ports to be be exposed
            commands: List of commands to be ran during making of the container
        """
        self._exposed_ports = exposed_ports
        self._commands = commands
        self._process_binaries(binaries=binaries)
        self._process_config_files(config_files=config_files)
        self._build_dockerfile()

    def _build_dockerfile(self):
        """Build a Dockerfile from the retrieved information."""
        output = f'FROM {self._base_image}\n\n'

        for binary_key in self._copied_binaries.keys():
            binary_file_details = self._copied_binaries[binary_key]
            output += (
                f'COPY {BINARY_DIRECTORY}{binary_file_details.filename} ',
                f'{binary_file_details.path}/{binary_file_details.filename}\n'
            )

        output += '\n'

        for config_key in self._copied_config.keys():
            config_file_details = self._copied_config[config_key]
            output += (
                f'COPY {CONFIG_DIRECTORY}{config_file_details.filename} ',
                f'{config_file_details.path}/{config_file_details.filename}\n'
            )

        output += '\n'

        for command in self._commands:
            output += f'RUN {command}\n'

        output += '\n'

        for exposed_port in self._exposed_ports:
            output += f'EXPOSE {exposed_port}\n'

        with open('Dockerfile', 'w') as fh:
            fh.write(output)

    def _copy_file(self, file_details: FileDetails, save_folder: str):
        """
        Copy file from the container.

        Args:
            file_details: Details about the file to be copied
        """
        file_path: str = f'{file_details.path}/{file_details.filename}'
        if file_details.symlink_path:
            file_path = f'{file_details.symlink_path}/{file_details.symlink_filename}'
        command = [
            'docker',
            'cp',
            f'{self._container_id}:{file_path}',
            f'./{save_folder}/{file_details.filename}',
        ]
        self._run_command(command=command)

    def _get_file_origin(self, filename: str) -> FileDetails:
        """
        Locate the original path for the file.

        Args:
            filename: Filename to search for

        Returns:
            Real path and filename
        """
        ls_command = [
            'docker',
            'exec',
            self._container_id,
            'ls',
            '-la',
            filename,
        ]
        try:
            ls_response = self._run_command(command=ls_command)
        except DockerException:
            raise FileNotFoundError(f'{filename} could not be found')
        binary_ls_split = ls_response.stdout.strip().split(' ')
        path, filename = split(filename)
        binary_details = FileDetails(
            filename=filename,
            path=path,
            symlink_filename='',
            symlink_path='',
        )
        if binary_ls_split[-2] != '->':
            return binary_details
        symlink_filename = split(binary_ls_split[-1])[-1]
        find_command = [
            'docker',
            'exec',
            self._container_id,
            'find',
            '/',
            '-name',
            symlink_filename,
        ]
        find_response = self._run_command(command=find_command)
        binary_details.symlink_filename = symlink_filename
        find_stdout_lines = find_response.stdout.splitlines()
        if len(find_stdout_lines) > 1:
            find_path = '/'
            for find_stdout_line in find_stdout_lines:
                if find_stdout_line.startswith('/lib/') or\
                        find_stdout_line.startswith('/usr/bin/') or\
                        find_stdout_line.startswith('/usr/sbin/') or\
                        find_stdout_line.startswith('/usr/lib/'):
                    find_path = find_stdout_line
                    break

        else:
            find_path = find_stdout_lines[0]
        binary_details.symlink_path = split(find_path)[0]
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
            line_split = line.split(' ')
            if not line or line_split[1] != '=>':
                file_ldd_path = line_split[0]
            else:
                file_ldd_path = line_split[2]
            try:
                file_details = self._get_file_origin(
                    filename=file_ldd_path
                )
            except FileNotFoundError:
                continue
            full_path = f'{file_details.path}/{file_details.filename}'
            self._copy_file(file_details=file_details, save_folder=BINARY_DIRECTORY)
            self._copied_binaries[full_path] = file_details

    def _process_binaries(self, binaries: list[str]):
        """
        Process and copy binary files.

        Args:
            binaries: List of binary files to process
        """
        for binary in binaries:
            command = [
                'docker',
                'exec',
                self._container_id,
                'ldd',
                binary,
            ]
            command_output = self._run_command(command=command)
            self._parse_ldd(command_output.stdout)
            file_details = self._get_file_origin(
                filename=binary
            )
            full_path = f'{file_details.path}/{file_details.filename}'
            if full_path not in self._copied_binaries:
                self._copy_file(file_details=file_details, save_folder=BINARY_DIRECTORY)
                self._copied_binaries[full_path] = file_details

    def _process_config_files(self, config_files: list[str]):
        """
        Process and copy config files.

        Args:
            config_files: List of config files to process
        """
        for config_file in config_files:

            file_details = self._get_file_origin(
                filename=config_file
            )
            full_path = f'{file_details.path}/{file_details.filename}'
            if full_path not in self._copied_config:
                self._copy_file(file_details=file_details, save_folder=CONFIG_DIRECTORY)
                self._copied_config[full_path] = file_details

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
