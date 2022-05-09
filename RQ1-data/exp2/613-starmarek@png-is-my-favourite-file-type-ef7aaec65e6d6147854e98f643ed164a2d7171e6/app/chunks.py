import struct
import logging
from itertools import zip_longest
from contextlib import contextmanager
import calendar

try:
    from tabulate import tabulate
except ModuleNotFoundError:
    traceback.print_exc()
    print("\033[1;33mBefore you will debug, please delete 'venv' dir from project root and try again.\033[0m")
    exit(1)

log = logging.getLogger(__name__)

@contextmanager
def temporary_data_change(object_to_change, tmp_data):
    """It is used to temporarly switch 'data' attribute of chunks.

    Every chunk inherits __str__ method of base Chunk class. Thanks to that, command line prinitng
    is consistent, fairly simple and every chunk is printed IN THE SAME WAY. Nevertheless, chunks contain different information in theirs data field.
    Thats why sometimes we would like to print it in an individual manner.

    Thanks to this function, chunks can temporarly change their data field when executing their own overloaded __str__ method.

    Args:
        object_to_change: This must be a Chunk-based object whose data will be switched
        tmp_data: Data to be switched
    """
    original_data = getattr(object_to_change, 'data')
    setattr(object_to_change, 'data', tmp_data)
    try:
        yield
    finally:
        setattr(object_to_change, 'data', original_data)

class Chunk:
    """Base representation of PNG's chunk

    Setup the attributes and define printing standard.
    """
    # Constants below indicates how many bytes to read from a file. Data field is not included because it's not a constant.
    # DATA_FIELD_LEN is a value of self.length.
    LENGTH_FIELD_LEN = 4
    TYPE_FIELD_LEN = 4
    CRC_FIELD_LEN = 4

    def __init__(self, length, type_, data, crc):
        log.debug(f"Creating {type_.decode('utf-8')} chunk")
        self.length = length
        self.type_ = type_
        self.data = data
        self.crc = crc

    def __str__(self):
        try:
            if b'Xt' in self.type_:
                # Bytes containing text data. We check if chunk type matches one of text-containing chunks -> iTXt tEXt zTXt
                data = self.data.decode('utf-8')
            else:
                # Bytes containing hex data
                data = ' '.join(str(byte) for byte in self.data.hex(' ').split())
        except:
            # Some other __str__ method has manipulated the self.data and we want to leave it as it is
            data = self.data

        return (f"Length: {int.from_bytes(self.length, 'big')}\nType: {self.type_.decode('utf-8')}\n"
                    f"Data: {data}\nCRC: {self.crc.hex(' ')}\n")

class IHDR(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

        values = struct.unpack('>iibbbbb', self.data)
        self.width = values[0]
        self.height = values[1]
        self.bit_depth = values[2]
        self.color_type = values[3]
        self.compression_method = values[4]
        self.filter_method = values[5]
        self.interlace_method = values[6]

    def __str__(self):
        data = (f"Width: {self.width} | Height: {self.height} | BitDepth: {self.bit_depth} | ColorType: {self.color_type} | "
                            f"CompressionMethod: {self.compression_method} | FilterMethod: {self.filter_method} | InterlaceMethod {self.interlace_method}")
        with temporary_data_change(self, data):
            return super().__str__()

class PLTE(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

    def __str__(self):
        if self.data:
            # Data is not empty. That means that user have used the --plte flag and data should be printed in a decoded manner
            data = self.get_parsed_data()
        else:
            # Default behavior -> data is skipped, because often it is too long
            data = self.data
        with temporary_data_change(self, data):
            return super().__str__()

    def get_parsed_data(self):
        """Decode 'data' field of PLTE chunk and return it as a list of RGB pixel tuples
        """
        decoded_pixels = iter([int(byte, 16) for byte in self.data.hex(' ').split()])

        # zip_longest pack pixel chunks into 3-element RGB tuples using unpacked iterator
        return [pixel_tuple for pixel_tuple in zip_longest(*[decoded_pixels]*3)]

class IDAT(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

class IEND(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

    def __str__(self):
        with temporary_data_change(self, "\'\'"):
            # Explicitly print quotes to emphasise that data field is empty. If we would simply use str.decode('utf-8'), quotes wouldn't appear.
            return super().__str__()

class tIME(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

        values = struct.unpack('>hbbbbb', self.data)
        self.year = values[0]
        self.month = values[1]
        self.day = values[2]
        self.hour = values[3]
        self.minute = values[4]
        self.second = values[5]

    def __str__(self):
        data = f"Last modification: {self.day} {calendar.month_abbr[self.month]}. {self.year} {self.hour}:{self.minute}:{self.second}"
        with temporary_data_change(self, data):
            return super().__str__()

class gAMA(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

        # PNG specification says, that stored gamma value is multiplied by 100000
        self.gamma = int.from_bytes(data, 'big') / 100000
        if self.gamma == 0:
            log.warning("Gamma shouldn't have value 0!")

    def __str__(self):
        with temporary_data_change(self, self.gamma):
            return super().__str__()

class cHRM(Chunk):
    def __init__(self, length, type_, data, crc):
        super().__init__(length, type_, data, crc)

        values = struct.unpack('>iiiiiiii', self.data)
        # PNG specification says, that stored values are multiplied by 100000
        self.WPx = values[0] / 100000
        self.WPy = values[1] / 100000
        self.WPz = 1 - self.WPx - self.WPy
        self.Rx = values[2] / 100000
        self.Ry = values[3] / 100000
        self.Rz = 1 - self.Rx - self.Ry
        self.Gx = values[4] / 100000
        self.Gy = values[5] / 100000
        self.Gz = 1 - self.Gx - self.Gy
        self.Bx = values[6] / 100000
        self.By = values[7] / 100000
        self.Bz = 1 - self.Bx - self.By

    def __str__(self):
        table = tabulate([['x', self.Rx, self.Gx, self.Bx, self.WPx],
                          ['y', self.Ry, self.Gy, self.By, self.WPy],
                          ['z', self.WPz, self.Gz, self.Bz, self.WPz]],
                          headers=['', 'Red', 'Green', 'Blue', 'WhitePoint'],
                          tablefmt='orgtbl'
                        )
        with temporary_data_change(self, f'\n{table}'):
            return super().__str__()

"""Points raw chunk type to desired class type

When PNG is during reading/parsing process, newly read chunk must be somehow initialized whith appropriete class.
This dictionary is used as a look-up table by PNG-reading function.
If during parse process, incoming chunk will not be matched with any chunk from this dict -> then this chunk will be initialized with a base class -> Chunk.
"""
CHUNKTYPES = {
    b'IHDR': IHDR,
    b'PLTE': PLTE,
    b'IDAT': IDAT,
    b'IEND': IEND,
    b'tIME': tIME,
    b'gAMA': gAMA,
    b'cHRM': cHRM,
}