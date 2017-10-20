#!/usr/bin/env python
# encoding: utf-8
#
# maskbit.py
#
# @Author: Brett Andrews <andrews>
# @Date:   2017-10-06 10:10:00
# @Last modified by:   andrews
# @Last modified time: 2017-10-20 16:10:18

from __future__ import division, print_function, absolute_import

import os

import numpy as np
import pandas as pd

import marvin
from marvin.utils.general.yanny import yanny


def _read_maskbit_schemas():
    """Read all available SDSS Maskbit schemas from yanny file.

    Returns:
        Record Array: all bits for all schemas.
    """
    path_maskbits = os.path.join(os.path.dirname(marvin.__file__), 'data', 'sdssMaskbits.par')
    sdss_maskbits = yanny(path_maskbits, np=True)
    return sdss_maskbits['MASKBITS']


def get_available_maskbits():
    """Get names of available Maskbit schemas from yanny file.

    Returns:
        list: Names of available Maskbits.
    """
    maskbits = _read_maskbit_schemas()
    return sorted(set([it[0] for it in maskbits]))


class Maskbit(object):
    """A class representing a maskbit.

    Parameters:
        schema (DataFrame):
            Maskbit schema.
        name (str):
            Name of maskbit.
        description (str):
            Description of maskbit.
    """

    def __init__(self, name, schema=None, description=None):

        self.name = name
        self.schema = schema if schema is not None else self._load_schema(name)
        self.description = description if description is not None else None
        self.mask = None

    def __repr__(self):
        return '<Maskbit {0!r}>\n{1!r}'.format(self.name, self.schema)

    def _load_schema(self, flag_name):
        """Load SDSS Maskbit schema from yanny file.

        Parameters:
            flag_name (str):
                Name of flag.

        Returns:
            DataFrame: Schema of flag.
        """
        maskbits = _read_maskbit_schemas()
        flag = maskbits[maskbits['flag'] == flag_name]

        return pd.DataFrame(flag[['bit', 'label', 'description']])

    @property
    def bits(self):
        return self.values_to_bits() if self.mask is not None else None

    @property
    def labels(self):
        return self.values_to_labels() if self.mask is not None else None

    def values_to_bits(self, values=None):
        """Convert mask values to a list of bits set.

        Parameters:
            values (int or array):
                Mask values. If ``None``, apply to entire
                ``Maskbit.mask`` array.  Default is ``None``.

        Returns:
            list:
                Bits that are set.

        Example:
            >>> maps = Maps(plateifu='8485-1901')
            >>> ha = maps['emline_gflux_ha_6564']
            >>> ha.pixmask.values_to_bits()
            [[[0, 1, 4, 30],
              [0, 1, 4, 30],
              ...
              [0, 1, 4, 30]]]
        """
        assert (self.mask is not None) or (values is not None), 'Must provide values.'

        values = np.array(self.mask) if values is None else np.array(values)
        ndim = values.ndim

        assert ndim <= 2, '`value` must be int, 1-D array, or 2-D array.'

        # expand up to 2 dimensions
        while values.ndim < 2:
            values = np.array([values])

        # create list of list of lists of bits set
        bits_set = []
        for ii in range(values.shape[0]):
            row = []
            for jj in range(values.shape[1]):
                row.append(self._value_to_bits(values[ii, jj], self.schema.bit.values))
            bits_set.append(row)

        # condense back down to initial dimensions
        for __ in range(2 - ndim):
            bits_set = bits_set[0]

        return bits_set

    def _value_to_bits(self, value, bits_all):
        """Convert mask value to a list of bits.

        Parameters:
            value (int):
                Mask value.
            bits_all (array):
                All bits for flag.

        Returns:
            list:
                Bits that are set.
        """
        return [it for it in bits_all if int(value) & (1 << it)]

    def values_to_labels(self, values=None):
        """Convert mask values to a list of the labels of bits set.

        Parameters:
            values (int or array):
                Mask values. If ``None``, apply to entire
                ``Maskbit.mask`` array.  Default is ``None``.

        Returns:
            list:
                Bits that are set.

        Example:
            >>> maps = Maps(plateifu='8485-1901')
            >>> ha = maps['emline_gflux_ha_6564']
            >>> ha.pixmask.values_to_labels()
            [[['NOCOV', 'LOWCOV', 'NOVALUE', 'DONOTUSE'],
              ['NOCOV', 'LOWCOV', 'NOVALUE', 'DONOTUSE'],
               ...
              ['NOCOV', 'LOWCOV', 'NOVALUE', 'DONOTUSE']]]
        """
        bits_set = self.values_to_bits(values=values)
        labels_set = self._bits_to_labels(bits_set)
        return labels_set

    def _bits_to_labels(self, nested):
        """Recursively convert a nested list of bits to labels.

        Parameters:
            nested (list):
                Nested list of bits.

        Returns:
            list: Nested list of labels.
        """
        # Base condition
        if isinstance(nested, (int, np.integer)):
            return self.schema.label[self.schema.bit == nested].values[0]

        return [self._bits_to_labels(it) for it in nested]

    def labels_to_value(self, labels):
        """Convert bit labels into a bit value.

        Parameters:
            labels (str or list):
                Labels of bits to set.

        Returns:
            int: Integer bit value.

        Example:
            >>> maps = Maps(plateifu='8485-1901')
            >>> ha = maps['emline_gflux_ha_6564']
            >>> ha.pixmask._labels_to_value('DONOTUSE')
            1073741824

            >>> ha.pixmask._labels_to_value(['NOCOV', 'LOWCOV'])
            3
        """
        if isinstance(labels, str):
            labels = [labels]

        bit_values = [self.schema.bit[self.schema.label == label].values[0] for label in labels]
        return np.sum([2**value for value in bit_values])

    def labels_to_bits(self, labels):
        """Convert bit labels into a bits.

        Parameters:
            labels (str or list):
                Labels of bits.

        Returns:
            list: Bits that corresponds to the lables.

        Example:
            >>> maps = Maps(plateifu='8485-1901')
            >>> ha = maps['emline_gflux_ha_6564']
            >>> ha.pixmask._labels_to_bits('DONOTUSE')
            [30]

            >>> ha.pixmask._labels_to_value(['NOCOV', 'LOWCOV'])
            [0, 1]
        """
        return self.values_to_bits(self.labels_to_value(labels))

    def get_mask(self, labels, mask=None, dtype=int):
        """Create mask from a list of labels.

        If ``dtype`` is ``int``, then ``get_mask`` can effectively
        perform an OR or AND operation.  However, if ``dtype`` is
        ``bool``, then ``get_mask`` does an OR.

        Parameters:
            labels (str or list):
                Labels of bits.
            mask (int or array):
                User-defined mask. If ``None``, use ``self.mask``.
                Default is ``None``.
            dtype:
                Output dtype, which must be either ``int`` or ``bool``.
                Default is ``int``.

        Returns:
            array: Mask for given labels.

        Example:
            >>> maps = Maps(plateifu='8485-1901')
            >>> ha = maps['emline_gflux_ha_6564']
            >>> ha.pixmask.get_mask(['NOCOV', 'LOWCOV'])
            array([[3, 3, 3, ..., 3, 3, 3],
                   ...,
                   [3, 3, 3, ..., 3, 3, 3]])

            >>> ha.pixmask.get_mask(['NOCOV', 'LOWCOV'], dtype=bool)
            array([[ True,  True,  True, ...,  True,  True,  True],
                   ...,
                   [ True,  True,  True, ...,  True,  True,  True]], dtype=bool)
        """
        assert dtype in [int, bool], '``dtype`` must be either ``int`` or ``bool``.'

        bits = self.labels_to_bits(labels)
        mask = mask if mask is not None else self.mask
        return np.sum([mask & 2**bit for bit in bits], axis=0).astype(dtype)
