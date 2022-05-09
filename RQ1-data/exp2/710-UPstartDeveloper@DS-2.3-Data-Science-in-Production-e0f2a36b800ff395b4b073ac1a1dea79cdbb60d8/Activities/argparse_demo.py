import math
import argparse


# instantiate the parser
parser = argparse.ArgumentParser(description='Calculate Cylinder volume')
parser.add_argument('-r', '--radius', type=int, metavar='', required=True, help='Radius of a Cylinder')
parser.add_argument('-H', '--height', type=int, metavar='', required=True, help='Height of cylinder')
# mutually exclusive group
group = parser.add_mutually_exclusive_group()
group.add_argument('-q', '--quiet', action='store_true', help='print quiet')
group.add_argument('-v', '--verbose', action='store_true', help='print verbose')

# get args
args = parser.parse_args()

# function
def cylinder_volume(radius, height):
    vol = (math.pi) * (radius ** 2) * (height)
    return vol


if __name__ == '__main__':
    volume = cylinder_volume(args.radius, args.height)
    if args.quiet:
        print(volume)
    elif args.verbose:
        print(f'Volume of a cylinder with radius {radius} amd height {height} is {volume}')
    else:
        print(f'Volume of a cylinder is {volume}')
    