"""acacia: tools to interact with Acacia datastore."""

import os
from configparser import ConfigParser
from pathlib import Path

import h5py
from loguru import logger
from rclone_python import rclone
from rclone_python.remote_types import RemoteTypes

from ska_ost_low_uv.io import read_uvx


class AcaciaStorage(object):
    """rclone wrapper for acacia access."""

    def __init__(self, config: str = 'acacia'):
        """Initialize AcaciaStorage object.

        Load client ID and secret keys
        Reads config from ~/.config/rclone/rclone.conf

        Args:
            config (str): Name of config to read. Default 'acacia'
        """
        self.config = config
        self.endpoint = 'https://ingest.pawsey.org.au'
        self.provider = 'Ceph'
        self.load_keys()

    def load_keys(self, rclone_config_path: str = None, config: str = 'acacia'):
        if rclone_config_path is None:
            rclone_config_path = Path.home() / '.config/rclone/rclone.conf'

        config = ConfigParser()
        config.read(rclone_config_path)
        try:
            self.secret_id = config['acacia']['access_key_id']
        except KeyError:
            logger.warning('No access key ID found in rclone config.')
            self.secret_id = None
        try:
            self.secret_key = config['acacia']['secret_access_key']
        except KeyError:
            logger.warning('No secret access key found in rclone config.')
            self.secret_key = None

    def add_keys(self, secret_id: str, secret_key: str, config_name: str = 'acacia'):
        """Create acacia config in .config/rclone/rclone.conf."""
        rclone_config = {
            'provider': self.provider,
            'endpoint': self.endpoint,
            'access_key_id': secret_id,
            'secret_access_key': secret_key,
        }
        rclone.create_remote(config_name, RemoteTypes.s3, **rclone_config)

    def download_obs(self, bucket: str, eb_code: str, dest: str = './'):
        """Download an observation from acacia.

        Args:
            bucket (str): name of bucket, e.g. 'aavs3'
            eb_code (str): Execution block ID (observation name)
            dest (str): Destination to save to
        """
        src_path = f'{self.config}:{bucket}/product/{eb_code}'

        dest_path = os.path.join(dest, eb_code)
        os.mkdir(dest_path)

        rclone.copy(src_path, dest_path)

    def get_url(self, bucket: str, fpath: str, debug: bool = True) -> str:
        url = f'{self.endpoint}/{bucket}/{fpath}'
        if debug:
            logger.debug(f'URL: {url}')
        return url

    def get_h5(self, bucket: str, fpath: str, debug: bool = False):
        """Load HDF5 as a virtual file, directly from acacia."""
        if debug:
            logger.debug('Setting up h5py debug trace')
            h5py._errors.unsilence_errors()

        url = self.get_url(bucket, fpath, debug)

        h5 = h5py.File(
            url,
            driver='ros3',
            aws_region=bytes('unused', 'utf-8'),
            secret_id=bytes(self.secret_id, 'utf-8'),
            secret_key=bytes(self.secret_key, 'utf-8'),
        )

        return h5

    def read_uvx(self, bucket: str, fpath: str, debug: bool = False):
        """Load UVX data directly from Acacia."""
        h5 = self.get_h5(bucket, fpath, debug)
        uvx = read_uvx(h5)
        return uvx


if __name__ == '__main__':
    acacia = AcaciaStorage()
    acacia.download_obs('aavs3', 'eb-local-20231024-936411817')
