import csv
import logging
import os
import toml

from typing import Dict
from crontab import CronSlices

from transpiler.config import DescriptorConfig


class Descriptor:
    """
    The model class for a Descriptor.
    It validates and contains all data the descriptor contains.
    """
    def __init__(self, descriptor_data: Dict, config: DescriptorConfig):
        """
        Constructor
        :param descriptor_data: dict containing the data as loaded from the descriptor toml file
        :param config: DescriptorConfig
        """
        self.config = config

        try:
            self.instance_type = descriptor_data['hardware']['instance_type']
            self.strategy = descriptor_data['hardware']['strategy']
            self.docker_image = descriptor_data['env']['docker_image']
        except KeyError as e:
            raise KeyError(f'Required field is missing in the descriptor toml file: {e.args[0]}') from e

        self.scheduling = descriptor_data['info'].get('scheduling', 'single_run')

        self.distributed = 'distributed' in descriptor_data['hardware']
        distributed_data = descriptor_data['hardware'].get('distributed', {})
        self.num_instances = distributed_data.get('num_instances', 1)
        self.gpus_per_instance = self.get_instance_gpus(self.instance_type)

        self.extended_shm = descriptor_data['env'].get('extended_shm', True)
        self.privileged = descriptor_data['env'].get('privileged', False)
        self.benchmark_code = descriptor_data['ml'].get('benchmark_code', '')
        self.ml_args = descriptor_data['ml'].get('args', '')

        self.dataset = descriptor_data.get('data', {}).get('id', '')
        self.data_sources = descriptor_data.get('data', {}).get('sources', [])

        self._validate()

    @classmethod
    def from_toml_file(cls, toml_file: str, config: DescriptorConfig):
        """
        Constructor from toml file path
        :param config: Configuration values for the descriptor
        :param toml_file: TOML descriptor file path
        """
        descriptor_toml = toml.load(toml_file)
        return Descriptor(descriptor_toml, config)

    def _validate(self):
        """
        Validates that this descriptor is valid
        """
        if self.strategy.lower() not in self.config.valid_strategies:
            raise ValueError(f'Invalid strategy: {self.strategy} (must be one of {self.config.valid_strategies})')

        if self.distributed:
            if self.num_instances <= 1:
                logging.warning(f'Specified a distributed strategy but using {self.num_instances} nodes')

        if self.scheduling != 'single_run':
            if not CronSlices.is_valid(self.scheduling):
                raise ValueError(f'Invalid cron expression in scheduling field: {self.scheduling}. '
                                 f'Please use Kubernetes cron job syntax or "single_run" for non-periodic runs')

    def get_instance_gpus(self, instance_type: str) -> int:
        file_dir = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(file_dir, os.pardir, 'util', 'ec2_instance_info.csv'), mode='r') as infile:
            reader = csv.reader(infile)
            gpus_per_instance = {rows[0]: rows[1] for rows in reader}

        if instance_type in gpus_per_instance:
            return gpus_per_instance[instance_type]
        else:
            raise ValueError(f'Invalid instance type: {instance_type}')

    def find_data_source(self, uri: str):
        for source in self.data_sources:
            if source['uri'] == uri:
                return source
        else:
            raise ValueError(f'Could not find data source with uri: {uri} \n'
                             f'Data sources are: {self.data_sources}')
