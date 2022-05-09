import unittest

from .rectangle import Rectangle


class RectangleUnitTest(unittest.TestCase):
    def test_rectangle_area(self):
        rectangle: Rectangle = Rectangle(height=3, width=2)
        self.assertEqual(rectangle.compute_area(), 6)

    def test_rectangle_set_height(self):
        rectangle: Rectangle = Rectangle(height=3, width=2)
        rectangle.set_height(5)
        self.assertEqual(rectangle.get_height(), 5)

    def test_rectangle_set_width(self):
        rectangle: Rectangle = Rectangle(height=3, width=2)
        rectangle.set_width(1)
        self.assertEqual(rectangle.get_width(), 1)


class SquareUnitTest(unittest.TestCase):
    def test_square_area(self):
        square: Square = Square(length=2)
        self.assertEqual(square.compute_area(), 4)

    def test_square_set_length(self):
        square: Square = Square(length=2)
        square.set_length(length=3)
        self.assertEqual(square.get_length(), 3)