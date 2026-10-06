import struct
import zlib


def encode_bgra(data, width, height):
    """Encode top-down 32-bit native pixels without storing a temporary screenshot."""
    if len(data) != width * height * 4 or width <= 0 or height <= 0:
        raise ValueError('Invalid native image dimensions')
    rows=[]
    for y in range(height):
        row=data[y*width*4:(y+1)*width*4]
        rgb=bytearray(width*3)
        rgb[0::3]=row[2::4];rgb[1::3]=row[1::4];rgb[2::3]=row[0::4]
        rows.append(b'\x00'+rgb)
    def chunk(kind,body):
        return struct.pack('!I',len(body))+kind+body+struct.pack('!I',zlib.crc32(kind+body)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
