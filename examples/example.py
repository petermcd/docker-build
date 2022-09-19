"""Example file."""
from pathlib import Path

from docker_build.docker import Docker
from docker_build.models import ExposedPortDetails

# This is an example of how to build the requirements for a container from an existing container.
path = Path('C:\\Users\\Peter\\Desktop\\')
docker = Docker(base_path=path, container_id='0e6b30933d1c', base_image='scratch')
docker.run(
    config_files=[
        '/etc/pam.d/sshd',
        '/etc/passwd',
        '/usr/etc/sshd_config',
    ],
    binaries=[
        '/bin/bash',
        '/usr/bin/mkdir',
        '/usr/bin/ssh-keygen',
        '/bin/sh',
        '/usr/sbin/sshd',
        '/usr/bin/ssh',
        '/usr/bin/sqlite3',
        '/lib/security/ssh_honeypot.so',
    ],
    commands=[
        'ssh-keygen -A',
        'mkdir /var/',
        'mkdir /var/log/',
        'mkdir /var/empty',
        'mkdir /var/empty/sshd',
        'mkdir /var/empty/sshd/etc',
        'mkdir /root/',
        'mkdir /root/.ssh/',
    ],
    exposed_ports=[
        ExposedPortDetails(port=22, protocol='tcp'),
        ExposedPortDetails(port=22, protocol='udp'),
    ]
)
