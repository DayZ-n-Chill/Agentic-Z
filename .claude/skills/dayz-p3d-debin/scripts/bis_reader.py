"""
Versioned binary reader for BI ODOL format.
Ported from BisDLL-Arma-3 BinaryReaderEx.cs.

Handles:
- Version-dependent reading logic
- LZO and LZSS compressed arrays (the "1024 rule")
- Condensed arrays (fill-or-compressed)
- Compressed RLE indices
- Compact integers
"""
import struct
import io
from lzo_decompress import decompress_lzo
from lzss_decompress import decompress_lzss

# Try to use native python-lzo for better reliability
try:
    import lzo as _native_lzo
    _HAS_NATIVE_LZO = True
except ImportError:
    _HAS_NATIVE_LZO = False


class BisReader:
    """Binary reader with BI format awareness."""

    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.pos = offset
        self.version = 0
        self.use_lzo = False          # version >= 44
        self.use_compression_flag = False  # version >= 64

    @classmethod
    def from_file(cls, path: str):
        with open(path, 'rb') as f:
            return cls(f.read())

    # ── Position ──

    @property
    def position(self):
        return self.pos

    @position.setter
    def position(self, val):
        self.pos = val

    @property
    def remaining(self):
        return len(self.data) - self.pos

    # ── Primitives ──

    def read_bytes(self, n: int) -> bytes:
        result = self.data[self.pos:self.pos + n]
        self.pos += n
        return result

    def read_byte(self) -> int:
        val = self.data[self.pos]
        self.pos += 1
        return val

    def read_bool(self) -> bool:
        return self.read_byte() != 0

    def read_sbyte(self) -> int:
        val = struct.unpack_from('<b', self.data, self.pos)[0]
        self.pos += 1
        return val

    def read_int16(self) -> int:
        val = struct.unpack_from('<h', self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_uint16(self) -> int:
        val = struct.unpack_from('<H', self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_int32(self) -> int:
        val = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_uint32(self) -> int:
        val = struct.unpack_from('<I', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_uint24(self) -> int:
        b0 = self.data[self.pos]
        b1 = self.data[self.pos + 1]
        b2 = self.data[self.pos + 2]
        self.pos += 3
        return b0 + (b1 << 8) + (b2 << 16)

    def read_float(self) -> float:
        val = struct.unpack_from('<f', self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_ascii(self, count: int) -> str:
        result = self.data[self.pos:self.pos + count].decode('ascii', errors='replace')
        self.pos += count
        return result

    def read_asciiz(self) -> str:
        """Read null-terminated string."""
        end = self.data.index(0, self.pos)
        result = self.data[self.pos:end].decode('ascii', errors='replace')
        self.pos = end + 1
        return result

    # ── Compact integer (variable-length) ──

    def read_compact_int(self) -> int:
        val = self.read_byte()
        if val & 128:
            val2 = self.read_byte()
            val += (val2 - 1) * 128
        return val

    # ── Arrays ──

    def read_array(self, read_fn, count=None):
        """Read array with count prefix (or explicit count)."""
        if count is None:
            count = self.read_int32()
        return [read_fn() for _ in range(count)]

    def read_float_array(self, count=None):
        return self.read_array(self.read_float, count)

    def read_int_array(self, count=None):
        return self.read_array(self.read_int32, count)

    def read_uint_array(self, count=None):
        return self.read_array(self.read_uint32, count)

    def read_string_array(self, count=None):
        return self.read_array(self.read_asciiz, count)

    # ── Vertex index (version-dependent size) ──

    def read_vertex_index(self) -> int:
        """Read vertex index: int32 for version >= 69, else uint16 (0xFFFF → -1)."""
        if self.version >= 69:
            return self.read_int32()
        val = self.read_uint16()
        return -1 if val == 0xFFFF else val

    def read_compressed_vertex_index_array(self):
        """Read compressed array of vertex indices."""
        if self.version >= 69:
            return self.read_compressed_array(lambda r: r.read_int32(), 4)
        def read_vi(r):
            v = r.read_uint16()
            return -1 if v == 0xFFFF else v
        return self.read_compressed_array(read_vi, 2)

    # ── Compression ──

    def read_compressed(self, expected_size: int) -> bytes:
        """Read compressed data (LZO or LZSS depending on version)."""
        if expected_size == 0:
            return b''
        if self.use_lzo:
            return self._read_lzo(expected_size)
        return self._read_lzss(expected_size)

    def _read_lzo(self, expected_size: int) -> bytes:
        """Read LZO compressed block with 1024-rule or compression flag."""
        is_compressed = expected_size >= 1024
        if self.use_compression_flag:
            is_compressed = self.read_bool()
        if not is_compressed:
            return self.read_bytes(expected_size)

        # Try pure-Python first (it tracks consumed bytes precisely)
        try:
            result, consumed = decompress_lzo(self.data, self.pos, expected_size)
            self.pos += consumed
            return result
        except Exception:
            pass

        # Fallback: native python-lzo with binary search for consumed size
        if _HAS_NATIVE_LZO:
            remaining = len(self.data) - self.pos
            # Try with all remaining data
            chunk = bytes(self.data[self.pos:self.pos + remaining])
            try:
                result = _native_lzo.decompress(chunk, False, expected_size,
                                                algorithm='LZO1X')
                # Binary search for exact compressed size
                lo, hi = 1, remaining
                while lo < hi:
                    mid = (lo + hi) // 2
                    try:
                        _native_lzo.decompress(chunk[:mid], False,
                                               expected_size, algorithm='LZO1X')
                        hi = mid
                    except _native_lzo.error:
                        lo = mid + 1
                self.pos += lo
                return result
            except _native_lzo.error:
                pass

        raise RuntimeError(
            f"LZO decompression failed at pos={self.pos}, "
            f"expected_size={expected_size}"
        )

    def _read_lzss(self, expected_size: int) -> bytes:
        """Read LZSS compressed block with 1024-rule."""
        if expected_size < 1024:
            return self.read_bytes(expected_size)
        result, consumed = decompress_lzss(self.data, self.pos, expected_size)
        self.pos += consumed
        return result

    # ── Compressed arrays ──

    def read_compressed_array(self, read_fn, elem_size: int, count=None):
        """Read compressed array: count + compressed blob → sub-reader."""
        if count is None:
            count = self.read_int32()
        expected_size = count * elem_size
        decompressed = self.read_compressed(expected_size)
        sub = BisReader(decompressed)
        sub.version = self.version
        sub.use_lzo = self.use_lzo
        sub.use_compression_flag = self.use_compression_flag
        return [read_fn(sub) for _ in range(count)]

    def read_compressed_short_array(self):
        return self.read_compressed_array(lambda r: r.read_int16(), 2)

    def read_compressed_int_array(self):
        return self.read_compressed_array(lambda r: r.read_int32(), 4)

    def read_compressed_float_array(self):
        return self.read_compressed_array(lambda r: r.read_float(), 4)

    # ── Condensed arrays (fill-or-compressed) ──

    def read_condensed_array(self, read_fn, elem_size: int):
        """Read condensed array: count + default_fill flag.
        If default_fill: single value fills all.
        Else: compressed array."""
        count = self.read_int32()
        if self.read_bool():
            # Default fill: single value for all
            val = read_fn(self)
            return [val] * count
        # Compressed
        expected_size = count * elem_size
        decompressed = self.read_compressed(expected_size)
        sub = BisReader(decompressed)
        sub.version = self.version
        sub.use_lzo = self.use_lzo
        sub.use_compression_flag = self.use_compression_flag
        return [read_fn(sub) for _ in range(count)]

    def read_condensed_int_array(self):
        return self.read_condensed_array(lambda r: r.read_int32(), 4)

    # ── Compressed indices (RLE) ──

    def read_compressed_indices(self, bytes_to_read: int, expected_count: int) -> bytes:
        """Read RLE-compressed index array."""
        out = bytearray(expected_count)
        op = 0
        for _ in range(bytes_to_read):
            b = self.read_byte()
            if b & 128:
                run_len = b - 127
                fill = self.read_byte()
                for _ in range(run_len):
                    out[op] = fill; op += 1
            else:
                literal_len = b + 1
                for _ in range(literal_len):
                    out[op] = self.read_byte(); op += 1
        return bytes(out)

    # ── Grid compressed (skip) ──

    def skip_grid_compressed(self) -> int:
        """Skip grid-compressed data, return bytes skipped."""
        start = self.pos
        bits = self.read_uint16()
        for _ in range(16):
            if bits & 1:
                self.skip_grid_compressed()
            else:
                self.pos += 4
            bits >>= 1
        return self.pos - start

    # ── Utility ──

    def sub_reader(self, data: bytes):
        """Create a child reader sharing version settings."""
        r = BisReader(data)
        r.version = self.version
        r.use_lzo = self.use_lzo
        r.use_compression_flag = self.use_compression_flag
        return r

    def __repr__(self):
        return (f"BisReader(pos={self.pos}, version={self.version}, "
                f"remaining={self.remaining})")
