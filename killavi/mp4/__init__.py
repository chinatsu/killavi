import bitstring
import sys

"""
Video Object Plane and Video Plane with Short Header:

    vop_fcode_forward:      This is a 3-bit unsigned integer taking values from 1 to 7; the value of zero is forbidden.
                            It is used in decoding of motion vectors.
    vop_fcode_backward:     This is a 3-bit unsigned integer taking values from 1 to 7; the value of zero is forbidden.
                            It is used in decoding of motion vectors.

Motion vector:

    horizontal_mv_data:     This is a variable length code, as defined in table_b12, which is used in motion vector decoding.
    vertical_mv_data:       This is a variable length code, as defined in table_b12, which is used in motion vector decoding.
    horizontal_mv_residual: This is an unsigned integer which is used in motion vector decoding. The number of bits in the bitstream for
                            horizontal_mv_residual, r_size, is derived from either vop_fcode_forward or vop_fcode_backward as follows;
                                r_size = vop_fcode_forward - 1   or   r_size = vop_fcode_backward - 1
    vertical_mv_residual:   This is an unsigned integer which is used in motion vector decoding. The number of bits in the bitstream for
                            vertical_mv_residual, r_size, is derived from either vop_fcode_forward or vop_fcode_backward as follows;
                                r_size = vop_fcode_forward - 1   or   r_size = vop_fcode_backward - 1
"""

"""
Video Object Plane notes:
    vop_start_code:     8 bytes # always 0x000001B6
    vop_coding_type:    2 bytes
"""

class MP4:
    def __init__(self, bitstream):
        self.bitstream = bitstring.ConstBitStream(bytes=bitstream)
        self.vop_start_code = self.bitstream.read(32)
        if self.vop_start_code != '0x000001B6':
            print("Malformed header")
            sys.exit(0)
        self.vop_coding_type = self.bitstream.read(2)
        self.modulo_time_base = self.bitstream.read('bin:1') # modulo_time_base?
        print(self.modulo_time_base)
        self.bitstream.read('bin:1')
        self.bitstream.read('bin:1')
        self.bitstream.read('bin:1')
        self.bitstream.read('bin:1')
        #print(self.bitstream.read('uint:13'))
        #print(self.bitstream.read('uint:13'))



table_b12 = {
    -16.0: 0b0000000000101,
    -15.5: 0b0000000000111,
    -15.0: 0b000000000101,
    -14.5: 0b000000000111,
    -14.0: 0b000000001001,
    -13.5: 0b000000001011,
    -13.0: 0b000000001101,
    -12.5: 0b000000001111,
    -12.0: 0b00000001001,
    -11.5: 0b00000001011,
    -11.0: 0b00000001101,
    -10.5: 0b00000001111,
    -10.0: 0b00000010001,
    -9.5:  0b00000010011,
    -9.0:  0b00000010101,
    -8.5:  0b00000010111,
    -8.0:  0b00000011001,
    -7.5:  0b00000011011,
    -7.0:  0b00000011101,
    -6.5:  0b00000011111,
    -6.0:  0b00000100001,
    -5.5:  0b00000100011,
    -5.0:  0b0000010011,
    -4.5:  0b0000010101,
    -4.0:  0b0000010111,
    -3.5:  0b00000111,
    -3.0:  0b00001001,
    -2.5:  0b00001011,
    -2.0:  0b0000111,
    -1.5:  0b00011,
    -1.0:  0b0011,
    -0.5:  0b011,
     0.0:  0b1,
     0.5:  0b010,
     1.0:  0b0010,
     1.5:  0b00010,
     2.0:  0b0000110,
     2.5:  0b00001010,
     3.0:  0b00001000,
     3.5:  0b00000110,
     4.0:  0b0000010110,
     4.5:  0b0000010100,
     5.0:  0b0000010010,
     5.5:  0b00000100010,
     6.0:  0b00000100000,
     6.5:  0b00000011110,
     7.0:  0b00000011100,
     7.5:  0b00000011010,
     8.0:  0b00000011000,
     8.5:  0b00000010110,
     9.0:  0b00000010100,
     9.5:  0b00000010010,
     10.0: 0b00000010000,
     10.5: 0b00000001110,
     11.0: 0b00000001100,
     11.5: 0b00000001010,
     12.0: 0b00000001000,
     12.5: 0b000000001110,
     13.0: 0b000000001100,
     13.5: 0b000000001010,
     14.0: 0b000000001000,
     14.5: 0b000000000110,
     15.0: 0b000000000100,
     15.5: 0b0000000000110,
     16.0: 0b0000000000100
}
