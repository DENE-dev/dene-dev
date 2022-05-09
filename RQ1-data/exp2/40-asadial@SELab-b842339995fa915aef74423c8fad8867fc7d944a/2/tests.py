import unittest


class RectangleUnitTest(unittest.TestCase):
    def test_rectangle_area(self):
        rectangle: Rectangle = Rectangle(height=3, width=2)
        self.assertEqual(rectangle.compute_area(), 6)