# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import unittest

# importing this module adds various methods to the IndexIVF and IndexNSG objects...
import altid
import faiss
import numpy as np
from faiss.contrib.datasets import SyntheticDataset
from faiss.contrib.inspect_tools import get_NSG_neighbors


class TestCompressedNSG(unittest.TestCase):

    def test_compact_bit(self):
        self.do_test(altid.CompactBitNSGGraph)

    def test_elias_fano(self):
        self.do_test(altid.EliasFanoNSGGraph)

    def test_roc_graph(self):
        self.do_test(altid.ROCNSGGraph)

    def do_test(self, graph_class):

        ds = SyntheticDataset(32, 0, 1000, 10)

        index = faiss.index_factory(ds.d, "NSG32,Flat")
        index.add(ds.get_database())
        Dref, Iref = index.search(ds.get_queries(), 10)

        # Get the original graph
        original_graph = index.nsg.get_final_graph()
        
        # Extract neighbors data as numpy array
        neighbors = np.zeros((original_graph.N, original_graph.K), dtype='int32')
        faiss.memcpy(
            faiss.swig_ptr(neighbors),
            original_graph.data,
            neighbors.nbytes
        )
        
        # Create a new graph from scratch
        new_graph = altid.FinalNSGGraph(faiss.swig_ptr(neighbors), original_graph.N, original_graph.K)
        new_graph.own_fields = False  # Important: don't try to free the memory
        
        # Create compressed graph
        compactbit_graph = graph_class(new_graph)
        
        # Replace in the index
        index.nsg.replace_final_graph(compactbit_graph)

        D, I = index.search(ds.get_queries(), 10)

        np.testing.assert_array_equal(I, Iref)
        np.testing.assert_array_equal(D, Dref)


class TestSearchTraced(unittest.TestCase):

    def test_traced(self):
        ds = SyntheticDataset(32, 0, 10000, 10)

        index_nsg = faiss.index_factory(ds.d, "NSG32,Flat")
        index_nsg.add(ds.get_database())
        q = ds.get_queries()[:1]  # just one query
        Dref, Iref = index_nsg.search(q, 10)

        D, I, trace = index_nsg.search_and_trace(q, 10)
        np.testing.assert_array_equal(I, Iref)
        np.testing.assert_array_equal(D, Dref)

        # at least, all result vectors should be in the trace
        assert set(I.ravel().tolist()) <= set(trace)
