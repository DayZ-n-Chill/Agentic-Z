"""
LZSS decompressor for BI ODOL format.
Ported from BisDLL-Arma-3 LZSS.cs.

Same ring buffer algorithm as PAA (buffer size 4096, init 0x20),
but ODOL adds a 4-byte checksum at the end of compressed data.
"""
import struct


class LZSSError(Exception):
    pass


def decompress_lzss(data: bytes, offset: int, expected_size: int, 
                    use_signed_checksum: bool = False) -> tuple:
    """
    Decompress LZSS data from buffer starting at offset.
    
    Returns (decompressed_bytes, bytes_consumed) so caller can advance
    the stream position.
    
    Args:
        data: Input buffer
        offset: Start position in buffer
        expected_size: Expected decompressed size in bytes
        use_signed_checksum: Use signed byte addition for checksum (rare)
    """
    if expected_size == 0:
        return b'', 0

    ring = bytearray(4113)
    out = bytearray(expected_size)

    # Init ring buffer with spaces (0x20)
    for i in range(4078):
        ring[i] = 0x20

    ip = offset
    op = 0
    rp = 4078  # ring position
    checksum = 0
    remaining = expected_size
    flags = 0

    while remaining > 0:
        flags >>= 1
        if (flags & 256) == 0:
            flags = data[ip] | 0xFF00
            ip += 1

        if flags & 1:
            # Literal byte
            b = data[ip]; ip += 1
            if use_signed_checksum:
                checksum += struct.unpack('b', bytes([b]))[0]
            else:
                checksum += b
            out[op] = b; op += 1
            remaining -= 1
            ring[rp] = b
            rp = (rp + 1) & 0xFFF
        else:
            # Back-reference
            lo = data[ip]; ip += 1
            hi = data[ip]; ip += 1
            ref_pos = lo | ((hi & 0xF0) << 4)
            length = (hi & 0x0F) + 2

            if length + 1 > remaining:
                raise LZSSError("LZSS overflow")

            j = rp - ref_pos
            end = length + j
            while j <= end:
                b = ring[j & 0xFFF]
                if use_signed_checksum:
                    checksum += struct.unpack('b', bytes([b]))[0]
                else:
                    checksum += b
                out[op] = b; op += 1
                remaining -= 1
                ring[rp] = b
                rp = (rp + 1) & 0xFFF
                j += 1

    # Read and verify 4-byte checksum
    stored_checksum = struct.unpack('<i', data[ip:ip+4])[0]
    ip += 4
    
    # Truncate checksum to 32-bit signed
    checksum = struct.unpack('<i', struct.pack('<I', checksum & 0xFFFFFFFF))[0]
    
    if stored_checksum != checksum:
        raise LZSSError(f"LZSS checksum mismatch: stored={stored_checksum}, computed={checksum}")

    bytes_consumed = ip - offset
    return bytes(out), bytes_consumed
