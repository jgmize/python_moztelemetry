#!/usr/bin/env python
# encoding: utf-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import division

import requests
import histogram_tools
import pandas as pd
import numpy as np
import re

from functools32 import lru_cache

@lru_cache(maxsize=512)
def _fetch_histograms_definition(revision):
    uri = (revision + "/toolkit/components/telemetry/Histograms.json").replace("rev", "raw-file")
    return requests.get(uri).json()

class Histogram:
    """ A class representing a histogram. """

    def __init__(self, name, instance, revision="https://hg.mozilla.org/mozilla-central/rev/tip"):
        """ Initialize a histogram from its name and a telemetry submission. """

        histograms_definition = _fetch_histograms_definition(revision)
        histogram_name = re.sub("^STARTUP_", "", name)

        self.definition = histogram_tools.Histogram(name, histograms_definition[histogram_name])
        self.kind = self.definition.kind()
        self.name = name

        if isinstance(instance, list) or isinstance(instance, np.ndarray) or isinstance(instance, pd.Series):
            if len(instance) == self.definition.n_buckets():
                values = instance
            else:
                values = instance[:-5]
            self.buckets = pd.Series(values, index=self.definition.ranges())
        else:
            entries = {int(k): v for k, v in instance["values"].items()}
            self.buckets = pd.Series(entries, index=self.definition.ranges()).fillna(0)

    def __str__(self):
        """ Returns a string representation of the histogram. """
        return str(self.buckets)

    def get_value(self, only_median=False):
        """
        Returns a scalar for flag and count histograms. Otherwise it returns either the
        raw histogram represented as a pandas Series or just the median if only_median
        is True.
        """

        if self.kind in ["exponential", "linear", "enumerated", "boolean"]:
            return self.percentile(50) if only_median else self.buckets
        elif self.kind == "count":
            return self.buckets[0]
        elif self.kind == "flag":
            return self.buckets[1] == 1
        else:
            assert(False) # Unsupported histogram kind

    def get_definition(self):
        """ Returns the definition of the histogram. """
        return self.definition

    def percentile(self, percentile):
        """ Returns the nth percentile of the histogram. """
        assert(percentile >= 0 and percentile <= 100)
        assert(self.kind in ["exponential", "linear", "enumerated", "boolean"])

        fraction = percentile/100
        to_count = fraction*self.buckets.sum()
        percentile_bucket = 0

        for percentile_bucket in range(len(self.buckets)):
            freq = self.buckets.values[percentile_bucket]
            if to_count - freq <= 0:
                break
            to_count -= freq

        if percentile_bucket == len(self.buckets) - 1:
            return float('nan')

        percentile_frequency = self.buckets.values[percentile_bucket]
        percentile_lower_boundary = self.buckets.index[percentile_bucket]
        width = self.buckets.index[percentile_bucket + 1] - self.buckets.index[percentile_bucket]
        return percentile_lower_boundary + width*to_count/percentile_frequency

    def __add__(self, other):
        return Histogram(self.name, self.buckets + other.buckets)


if __name__ == "__main__":
    # Histogram without revision
    Histogram("HTTPCONNMGR_USED_SPECULATIVE_CONN", [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0.693147182464599, 0.480453014373779, -1, -1])

    # Histogram with revision
    Histogram("HTTPCONNMGR_USED_SPECULATIVE_CONN", [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0.693147182464599, 0.480453014373779, -1, -1], "https://hg.mozilla.org/mozilla-central/rev/37ddc5e2eb72")

    # Startup histogram
    Histogram("STARTUP_HTTPCONNMGR_USED_SPECULATIVE_CONN", [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0.693147182464599, 0.480453014373779, -1, -1])