"""
Math types for BI P3D format: Vector3P, Matrix3P, Matrix4P.
Ported from BisDLL-Arma-3 (Mekz0/Crip12).
"""
import math
import struct


class Vector3P:
    """3D vector (float x, y, z). Used for vertices, normals, positions."""

    __slots__ = ('x', 'y', 'z')

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @classmethod
    def read(cls, f):
        """Read 3 floats (12 bytes) from binary stream or BisReader."""
        if hasattr(f, 'read_float'):
            # BisReader
            return cls(f.read_float(), f.read_float(), f.read_float())
        # File-like
        data = f.read(12)
        x, y, z = struct.unpack('<fff', data)
        return cls(x, y, z)

    @classmethod
    def read_compressed(cls, f):
        """Read compressed normal (4 bytes → 3 floats, 10 bits each)."""
        val = struct.unpack('<I', f.read(4))[0]
        return cls.read_compressed_from_int(val)

    @classmethod
    def read_compressed_from_int(cls, val):
        """Decode compressed normal from a 32-bit int."""
        ix = val & 0x3FF
        iy = (val >> 10) & 0x3FF
        iz = (val >> 20) & 0x3FF
        if ix > 511: ix -= 1024
        if iy > 511: iy -= 1024
        if iz > 511: iz -= 1024
        scale = -1.0 / 511.0
        return cls(ix * scale, iy * scale, iz * scale)

    @property
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self):
        ln = self.length
        if ln > 0:
            self.x /= ln
            self.y /= ln
            self.z /= ln

    def distance(self, other):
        d = self - other
        return d.length

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def __add__(self, other):
        return Vector3P(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3P(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self):
        return Vector3P(-self.x, -self.y, -self.z)

    def __mul__(self, scalar):
        return Vector3P(self.x * scalar, self.y * scalar, self.z * scalar)

    def __eq__(self, other):
        if not isinstance(other, Vector3P):
            return False
        eps = 0.05
        return (abs(self.x - other.x) < eps and
                abs(self.y - other.y) < eps and
                abs(self.z - other.z) < eps)

    def __getitem__(self, i):
        return (self.x, self.y, self.z)[i]

    def __setitem__(self, i, val):
        if i == 0: self.x = val
        elif i == 1: self.y = val
        elif i == 2: self.z = val

    def __repr__(self):
        return f"Vector3P({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"

    def write(self, f):
        f.write(struct.pack('<fff', self.x, self.y, self.z))


class Matrix3P:
    """3x3 orientation matrix. Columns: Aside, Up, Dir (each a Vector3P)."""

    __slots__ = ('columns',)

    def __init__(self, aside=None, up=None, dir_=None):
        self.columns = [
            aside or Vector3P(),
            up or Vector3P(),
            dir_ or Vector3P(),
        ]

    @classmethod
    def read(cls, f):
        """Read 9 floats (36 bytes): aside(3), up(3), dir(3)."""
        return cls(Vector3P.read(f), Vector3P.read(f), Vector3P.read(f))

    @property
    def aside(self): return self.columns[0]
    @property
    def up(self): return self.columns[1]
    @property
    def dir(self): return self.columns[2]

    def __getitem__(self, col):
        return self.columns[col]

    def __repr__(self):
        return f"Matrix3P(aside={self.aside}, up={self.up}, dir={self.dir})"

    def write(self, f):
        self.aside.write(f)
        self.up.write(f)
        self.dir.write(f)


class Matrix4P:
    """4x3 transformation matrix: 3x3 orientation + Vector3P position.
    Used for proxy transformations."""

    __slots__ = ('orientation', 'position')

    def __init__(self, orientation=None, position=None):
        self.orientation = orientation or Matrix3P()
        self.position = position or Vector3P()

    @classmethod
    def read(cls, f):
        """Read 12 floats (48 bytes): orientation(9) + position(3)."""
        return cls(Matrix3P.read(f), Vector3P.read(f))

    def __repr__(self):
        return f"Matrix4P(pos={self.position}, orient={self.orientation})"

    def write(self, f):
        self.orientation.write(f)
        self.position.write(f)
