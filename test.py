from network import *

import unittest
import os

class TestBufferSize(unittest.TestCase):
    def test_same_size_three_times(self):
        b = BufferSize(1024)
        sizes = []
        sizes.append(b.getSize())
        b.addHistory(2)
        sizes.append(b.getSize())
        b.addHistory(1.9)
        sizes.append(b.getSize())
        b.addHistory(2.1)
        for x in sizes:
            self.assertEqual(x, 1024)
    def test_strictly_increasing_size(self):
        b = BufferSize(1024)
        sizes = []
        for i in range(1, 13): #1 - 12
            sizes.append(b.getSize())
            b.addHistory(1/i)
        

        expected = [1024, 1024, 1024, 2048, 2048, 2048, 1024 *4, 1024 *4, 1024 *4, 1024 *8 , 1024 *8, 1024 *8]
        self.assertEqual(sizes, expected)

    def test_equilibrium(self):
        b = BufferSize(1024)
        sizes = []
        for i in range(1, 10): #1 - 9
            sizes.append(b.getSize())
            b.addHistory(1/i)

        sizes.append(b.getSize())
        b.addHistory(.15)
        sizes.append(b.getSize())
        b.addHistory(.15)
        sizes.append(b.getSize())
        b.addHistory(.15)
        sizes.append(b.getSize())
        b.addHistory(.1)
        sizes.append(b.getSize())
        b.addHistory(.1)
        sizes.append(b.getSize())
        b.addHistory(.1)
        sizes.append(b.getSize())
        b.addHistory(.09)
        sizes.append(b.getSize())
        b.addHistory(.09)
        sizes.append(b.getSize())
        b.addHistory(.09)

        expected = [1024, 1024, 1024, 2048, 2048, 2048, 1024 *4, 1024 *4, 1024 *4, 1024 *8 , 1024 *8, 1024 *8, 1024 *6, 1024 *6, 1024 *6, 1024 *5, 1024 *5, 1024 *5]
        self.assertEqual(sizes, expected)   



if __name__ == '__main__':
    unittest.main()