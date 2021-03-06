from .. import sampling as samp
from .. import util as ut
from .. import nn as nn
from . import base as b
import pandas as pd
import numpy as np


class TimeSeriesMAERandomSampler(b.ActionBase):
    """ MAE Random Sampler

    Perform a MAE random sampling over the list of architectures or over a
    search space definition passed in the Configuration.

    Mandatory parameters:
    architectures or (listing_class and listing_params)
    data_loader_class and data_loader_params
    min_look_back
    max_look_back
    nn_builder_class
    num_samples

    Optional:
    output_logger_class and output_logger_params
    **any other set of params supported by the classes/functions
    """
    def __init__(self,
                 seed=1234,
                 verbose=0):
        super().__init__(seed, verbose)

    def _is_valid_config(self,
                         **config):
        if ('architectures' not in config and
                'listing_class' not in config):
            return False
        if 'listing_class' in config:
            if not issubclass(config['listing_class'],
                              samp.ArchitectureListing):
                return False
            if 'listing_params' not in config:
                return False
        if 'data_loader_class' in config:
            if not issubclass(config['data_loader_class'],
                              ut.DataLoader):
                return False
            if 'data_loader_params' not in config:
                return False
        else:
            return False
        if ('min_look_back' not in config or
                config['min_look_back'] < 1):
            return False
        if ('max_look_back' not in config or
                config['max_look_back'] < config['min_look_back']):
            return False
        if ('nn_builder_class' not in config or
                not issubclass(config['nn_builder_class'],
                               nn.NNBuilder)):
            return False
        if ('num_samples' not in config or
                config['num_samples'] < 1):
            return False
        return True

    def do_action(self,
                  **kwargs):
        if not self._is_valid_config(**kwargs):
            raise Exception('The configuration is not valid')
        if ('output_logger_class' in kwargs and
                'output_logger_params' in kwargs):
            self._set_output(kwargs['output_logger_class'],
                             kwargs['output_logger_params'])
        data_loader = kwargs['data_loader_class']()
        data_loader.load(**kwargs['data_loader_params'])
        dataset = data_loader.dataset
        layer_in = dataset.input_dim
        layer_out = dataset.output_dim
        architectures = None
        if 'listing_class' in kwargs:
            listing = kwargs['listing_class']()
            architectures = listing.list_architectures(
                **kwargs['listing_params'])
        else:
            architectures = kwargs['architectures']
        if architectures is None:
            raise Exception('No architectures found')
        nn_builder = kwargs['nn_builder_class']()
        for architecture in architectures:
            # Build the network
            layers = [layer_in] + architecture + [layer_out]
            model = nn_builder.build_model(layers,
                                           verbose=self.verbose,
                                           **kwargs)
            # do the sampling
            for look_back in range(kwargs['min_look_back'],
                                   kwargs['max_look_back']+1):
                sampler = samp.MAERandomSampling(self.seed)
                dataset.testing_data.look_back = look_back
                metrics = sampler.fit(model=model,
                                      data=dataset.testing_data,
                                      **kwargs)
                results = {}
                results['metrics'] = metrics
                results['architecture'] = layers
                results['look_back'] = look_back
                self._output(**results)
                if self.verbose:
                    print(results)
            del model
