"""Dateclasses used by the package."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExposedPortDetails(object):
    """Dataclass for the exposed ports."""

    port: int
    protocol: str


@dataclass
class FileDetails(object):
    """Dataclass for the details of files to copy from a container."""

    filename: str
    path: str
    saved_path: Path
    saved_path_relative: Path
    symlink_filename: str
    symlink_path: str


@dataclass
class Response(object):
    """Dataclass to store command responses."""

    code: int
    stderr: str
    stdout: str
