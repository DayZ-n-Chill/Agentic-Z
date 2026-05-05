"""
ODOL P3D reader — parses binarized .p3d files (ODOL v28-73).
Ported from BisDLL-Arma-3 (Mekz0/Crip12, originally by T_D).

Usage:
    odol = ODOL.from_file("model.p3d")
    for lod in odol.lods:
        print(f"LOD res={lod.resolution}: {lod.vertex_count} verts, {len(lod.faces)} faces")
"""
import struct
from math_types import Vector3P, Matrix3P, Matrix4P
from bis_reader import BisReader


# ── Small data types ──

class ColorP:
    __slots__ = ('r', 'g', 'b', 'a')
    def __init__(self, r=0, g=0, b=0, a=0):
        self.r, self.g, self.b, self.a = r, g, b, a
    @classmethod
    def read(cls, reader):
        return cls(reader.read_float(), reader.read_float(),
                   reader.read_float(), reader.read_float())
    def __repr__(self):
        return f"RGBA({self.r:.2f},{self.g:.2f},{self.b:.2f},{self.a:.2f})"


class Proxy:
    __slots__ = ('model', 'transformation', 'sequence_id',
                 'named_selection_index', 'bone_index', 'section_index')
    @classmethod
    def read(cls, reader):
        p = cls()
        p.model = reader.read_asciiz()
        p.transformation = Matrix4P.read(reader)
        p.sequence_id = reader.read_int32()
        p.named_selection_index = reader.read_int32()
        p.bone_index = reader.read_int32()
        if reader.version >= 40:
            p.section_index = reader.read_int32()
        else:
            p.section_index = -1
        return p
    def __repr__(self):
        return f"Proxy({self.model}, pos={self.transformation.position})"


class Skeleton:
    __slots__ = ('name', 'is_discrete', 'bones', 'pivots_name')
    @classmethod
    def read(cls, reader):
        s = cls()
        s.name = reader.read_asciiz()
        s.is_discrete = False
        s.bones = []
        s.pivots_name = ''
        if s.name == '':
            return s
        if reader.version >= 23:
            s.is_discrete = reader.read_bool()
        n_bones = reader.read_int32()
        s.bones = []
        for _ in range(n_bones):
            bone_name = reader.read_asciiz()
            bone_parent = reader.read_asciiz()
            s.bones.append((bone_name, bone_parent))
        if reader.version > 40:
            s.pivots_name = reader.read_asciiz()
        return s
    def __repr__(self):
        return f"Skeleton({self.name}, {len(self.bones)} bones)"


class AnimationClass:
    """Single animation definition."""
    # AnimType enum
    ROTATION = 0; ROTATION_X = 1; ROTATION_Y = 2; ROTATION_Z = 3
    TRANSLATION = 4; TRANSLATION_X = 5; TRANSLATION_Y = 6; TRANSLATION_Z = 7
    DIRECT = 8; HIDE = 9

    __slots__ = ('anim_type', 'anim_name', 'anim_source',
                 'min_phase', 'max_phase', 'min_value', 'max_value',
                 'anim_period', 'init_phase', 'source_address',
                 'angle0', 'angle1', 'offset0', 'offset1',
                 'axis_pos', 'axis_dir', 'angle', 'axis_offset', 'hide_value')

    @classmethod
    def read(cls, reader):
        a = cls()
        a.anim_type = reader.read_uint32()
        a.anim_name = reader.read_asciiz()
        a.anim_source = reader.read_asciiz()
        a.min_phase = reader.read_float()
        a.max_phase = reader.read_float()
        a.min_value = reader.read_float()
        a.max_value = reader.read_float()
        a.anim_period = 0.0; a.init_phase = 0.0
        if reader.version >= 56:
            a.anim_period = reader.read_float()
            a.init_phase = reader.read_float()
        a.source_address = reader.read_uint32()

        a.angle0 = a.angle1 = a.offset0 = a.offset1 = 0.0
        a.axis_pos = a.axis_dir = None
        a.angle = a.axis_offset = a.hide_value = 0.0

        if a.anim_type in (0, 1, 2, 3):  # Rotation*
            a.angle0 = reader.read_float()
            a.angle1 = reader.read_float()
        elif a.anim_type in (4, 5, 6, 7):  # Translation*
            a.offset0 = reader.read_float()
            a.offset1 = reader.read_float()
        elif a.anim_type == 8:  # Direct
            a.axis_pos = Vector3P.read(reader)
            a.axis_dir = Vector3P.read(reader)
            a.angle = reader.read_float()
            a.axis_offset = reader.read_float()
        elif a.anim_type == 9:  # Hide
            a.hide_value = reader.read_float()
            if reader.version >= 55:
                reader.read_float()  # unknown
        return a


class Animations:
    __slots__ = ('classes', 'bones2anims', 'anims2bones', 'axis_data')
    @classmethod
    def read(cls, reader):
        a = cls()
        n_classes = reader.read_int32()
        a.classes = [AnimationClass.read(reader) for _ in range(n_classes)]
        n_anim_lods = reader.read_int32()
        # Bones2Anims
        a.bones2anims = []
        for _ in range(n_anim_lods):
            n_bones = reader.read_uint32()
            lod_b2a = []
            for _ in range(n_bones):
                n_anims = reader.read_uint32()
                lod_b2a.append([reader.read_uint32() for _ in range(n_anims)])
            a.bones2anims.append(lod_b2a)
        # Anims2Bones + axis data
        a.anims2bones = []
        a.axis_data = []
        for i in range(n_anim_lods):
            lod_a2b = []
            lod_axes = []
            for k in range(n_classes):
                bone_idx = reader.read_int32()
                lod_a2b.append(bone_idx)
                if (bone_idx != -1 and
                    a.classes[k].anim_type != AnimationClass.DIRECT and
                    a.classes[k].anim_type != AnimationClass.HIDE):
                    axis = (Vector3P.read(reader), Vector3P.read(reader))
                    lod_axes.append(axis)
                else:
                    lod_axes.append(None)
            a.anims2bones.append(lod_a2b)
            a.axis_data.append(lod_axes)
        return a


# ── LOD sub-structures ──

class SubSkeletonIndexSet:
    @classmethod
    def read(cls, reader):
        return reader.read_int_array()  # count-prefixed int array


class VerySmallArray:
    """Fixed 12-byte struct: int count + 8 bytes data."""
    __slots__ = ('count', 'data')
    @classmethod
    def read(cls, reader):
        v = cls()
        v.count = reader.read_int32()
        v.data = reader.read_bytes(8)
        return v
    @property
    def pairs(self):
        """Return list of (selection_index, weight) tuples."""
        return [(self.data[i*2], self.data[i*2+1]) for i in range(self.count)]


class Polygon:
    __slots__ = ('vertex_indices',)
    @classmethod
    def read(cls, reader):
        p = cls()
        n = reader.read_byte()
        p.vertex_indices = [reader.read_vertex_index() for _ in range(n)]
        return p


class Section:
    __slots__ = ('face_lower', 'face_upper', 'min_bone', 'bones_count',
                 'texture_index', 'special', 'material_index', 'mat_name',
                 'area_over_tex', 'short_indices')

    @classmethod
    def read(cls, reader):
        s = cls()
        s.short_indices = reader.version < 69
        s.face_lower = reader.read_int32()
        s.face_upper = reader.read_int32()
        s.min_bone = reader.read_int32()
        s.bones_count = reader.read_int32()
        reader.read_uint32()  # unknown
        s.texture_index = reader.read_int16()
        s.special = reader.read_uint32()
        s.material_index = reader.read_int32()
        s.mat_name = ''
        if s.material_index == -1:
            s.mat_name = reader.read_asciiz()
        if reader.version >= 36:
            n_stages = reader.read_uint32()
            s.area_over_tex = [reader.read_float() for _ in range(n_stages)]
            if reader.version >= 67:
                n = reader.read_int32()
                if n >= 1:
                    for _ in range(11):
                        reader.read_float()
        else:
            s.area_over_tex = [reader.read_float()]
        return s

    def get_face_indices(self, faces):
        """Return list of face indices belonging to this section."""
        step = 8 if self.short_indices else 16
        extra = 2 if self.short_indices else 4
        acc = 0
        result = []
        for fi, face in enumerate(faces):
            if self.face_lower <= acc < self.face_upper:
                result.append(fi)
            acc += step
            if len(face.vertex_indices) == 4:
                acc += extra
            if acc >= self.face_upper:
                break
        return result


class NamedSelection:
    __slots__ = ('name', 'selected_faces', 'is_sectional', 'sections',
                 'selected_vertices', 'vertex_weights')

    @classmethod
    def read(cls, reader):
        ns = cls()
        ns.name = reader.read_asciiz()
        ns.selected_faces = reader.read_compressed_vertex_index_array()
        reader.read_int32()  # always 0?
        ns.is_sectional = reader.read_bool()
        ns.sections = reader.read_compressed_int_array()
        ns.selected_vertices = reader.read_compressed_vertex_index_array()
        weight_size = reader.read_int32()
        ns.vertex_weights = reader.read_compressed(weight_size)
        return ns

    def __repr__(self):
        return (f"NamedSelection({self.name}, "
                f"{len(self.selected_vertices)} verts, "
                f"{len(self.selected_faces)} faces)")


class UVSet:
    __slots__ = ('is_discretized', 'min_u', 'min_v', 'max_u', 'max_v',
                 'n_vertices', 'default_fill', 'default_value', 'uv_raw')

    @classmethod
    def read(cls, reader, version):
        u = cls()
        u.is_discretized = False
        if version >= 45:
            u.is_discretized = True
            u.min_u = reader.read_float()
            u.min_v = reader.read_float()
            u.max_u = reader.read_float()
            u.max_v = reader.read_float()
        else:
            u.min_u = u.min_v = 0.0
            u.max_u = u.max_v = 1.0
        u.n_vertices = reader.read_uint32()
        u.default_fill = reader.read_bool()
        elem_size = 4 if version >= 45 else 8
        if u.default_fill:
            u.default_value = reader.read_bytes(elem_size)
            u.uv_raw = None
        else:
            u.default_value = None
            u.uv_raw = reader.read_compressed(u.n_vertices * elem_size)
        return u

    @property
    def uv_data(self):
        """Return flat float array [u0, v0, u1, v1, ...] for all vertices."""
        result = [0.0] * (self.n_vertices * 2)
        if self.is_discretized:
            scale_u = self.max_u - self.min_u
            scale_v = self.max_v - self.min_v
        else:
            scale_u = scale_v = 1.0

        def scale_val(raw_short, scale, min_val):
            return (1.52587890625e-05 * (raw_short + 32767) * scale) + min_val

        if self.default_fill:
            if self.is_discretized:
                du = scale_val(struct.unpack_from('<h', self.default_value, 0)[0], scale_u, self.min_u)
                dv = scale_val(struct.unpack_from('<h', self.default_value, 2)[0], scale_v, self.min_v)
            else:
                du = struct.unpack_from('<f', self.default_value, 0)[0]
                dv = struct.unpack_from('<f', self.default_value, 4)[0]
            for i in range(self.n_vertices):
                result[i * 2] = du
                result[i * 2 + 1] = dv
        else:
            for i in range(self.n_vertices):
                if self.is_discretized:
                    raw_u = struct.unpack_from('<h', self.uv_raw, i * 4)[0]
                    raw_v = struct.unpack_from('<h', self.uv_raw, i * 4 + 2)[0]
                    result[i * 2] = scale_val(raw_u, scale_u, self.min_u)
                    result[i * 2 + 1] = scale_val(raw_v, scale_v, self.min_v)
                else:
                    result[i * 2] = struct.unpack_from('<f', self.uv_raw, i * 8)[0]
                    result[i * 2 + 1] = struct.unpack_from('<f', self.uv_raw, i * 8 + 4)[0]
        return result


class StageTexture:
    __slots__ = ('filter_type', 'texture', 'stage_id', 'use_world_env_map')
    @classmethod
    def read(cls, reader, mat_version):
        st = cls()
        st.filter_type = 0
        if mat_version >= 5:
            st.filter_type = reader.read_uint32()
        st.texture = reader.read_asciiz()
        st.stage_id = 0
        if mat_version >= 8:
            st.stage_id = reader.read_uint32()
        st.use_world_env_map = False
        if mat_version >= 11:
            st.use_world_env_map = reader.read_bool()
        return st


class StageTransform:
    __slots__ = ('uv_source', 'transformation')
    @classmethod
    def read(cls, reader):
        st = cls()
        st.uv_source = reader.read_uint32()
        st.transformation = Matrix4P.read(reader)
        return st


class EmbeddedMaterial:
    __slots__ = ('material_name', 'version', 'emissive', 'ambient',
                 'diffuse', 'forced_diffuse', 'specular', 'specular_copy',
                 'specular_power', 'pixel_shader', 'vertex_shader',
                 'main_light', 'fog_mode', 'surface_file',
                 'render_flags', 'n_render_flags',
                 'stage_textures', 'stage_transforms', 'stage_ti',
                 'dayz_extended')

    @classmethod
    def read(cls, reader):
        m = cls()
        m.material_name = reader.read_asciiz()
        m.version = reader.read_uint32()
        m.emissive = ColorP.read(reader)
        m.ambient = ColorP.read(reader)
        m.diffuse = ColorP.read(reader)
        m.forced_diffuse = ColorP.read(reader)
        m.specular = ColorP.read(reader)
        m.specular_copy = ColorP.read(reader)
        m.specular_power = reader.read_float()
        m.pixel_shader = reader.read_uint32()
        # DayZ material v20+: 25 extra floats (PBR extended data)
        m.dayz_extended = []
        if m.version >= 20:
            m.dayz_extended = [reader.read_float() for _ in range(25)]
        m.vertex_shader = reader.read_uint32()
        m.main_light = reader.read_uint32()
        m.fog_mode = reader.read_uint32()
        if m.version >= 20:
            reader.read_uint32()  # DayZ unknown, typically 1
        elif m.version == 3:
            reader.read_bool()
        m.surface_file = ''
        if m.version >= 6:
            m.surface_file = reader.read_asciiz()
        m.n_render_flags = 0; m.render_flags = 0
        if m.version >= 4:
            m.n_render_flags = reader.read_uint32()
            m.render_flags = reader.read_uint32()
        n_stages = 1; n_texgens = 1
        if m.version > 6:
            n_stages = reader.read_uint32()
        if m.version > 8:
            n_texgens = reader.read_uint32()
        m.stage_textures = []
        m.stage_transforms = []
        if m.version < 8:
            for _ in range(n_stages):
                m.stage_transforms.append(StageTransform.read(reader))
                m.stage_textures.append(StageTexture.read(reader, m.version))
        else:
            for _ in range(n_stages):
                m.stage_textures.append(StageTexture.read(reader, m.version))
            for _ in range(n_texgens):
                m.stage_transforms.append(StageTransform.read(reader))
        m.stage_ti = None
        if m.version >= 10:
            m.stage_ti = StageTexture.read(reader, m.version)
        return m

    def __repr__(self):
        return f"Material({self.material_name})"


class Keyframe:
    __slots__ = ('time', 'points')
    @classmethod
    def read(cls, reader):
        kf = cls()
        kf.time = reader.read_float()
        n = reader.read_uint32()
        kf.points = [Vector3P.read(reader) for _ in range(n)]
        return kf


class LoadableLodInfo:
    @classmethod
    def read(cls, reader):
        info = cls()
        info.n_faces = reader.read_int32()
        info.color = reader.read_uint32()
        info.special = reader.read_int32()
        info.or_hints = reader.read_uint32()
        if reader.version >= 39:
            info.has_skeleton = reader.read_bool()
        if reader.version >= 51:
            info.n_vertices = reader.read_int32()
            info.face_area = reader.read_float()
        return info


# ── ModelInfo ──

class ODOL_ModelInfo:
    """Top-level model metadata. Contains bounding box, skeleton, mass, etc."""

    @classmethod
    def read(cls, reader, n_lods):
        mi = cls()
        v = reader.version
        mi.special = reader.read_int32()
        mi.bounding_sphere = reader.read_float()
        mi.geometry_sphere = reader.read_float()
        mi.remarks = reader.read_int32()
        mi.and_hints = reader.read_int32()
        mi.or_hints = reader.read_int32()
        mi.aiming_center = Vector3P.read(reader)
        mi.map_icon_color = reader.read_uint32()
        mi.map_selected_color = reader.read_uint32()
        mi.view_density = reader.read_float()
        mi.bbox_min = Vector3P.read(reader)
        mi.bbox_max = Vector3P.read(reader)
        mi.lod_density_coef = 0.0
        if v >= 70:
            mi.lod_density_coef = reader.read_float()
        mi.draw_importance = 0.0
        if v >= 71:
            mi.draw_importance = reader.read_float()
        mi.bbox_min_visual = Vector3P(0, 0, 0)
        mi.bbox_max_visual = Vector3P(0, 0, 0)
        if v >= 52:
            mi.bbox_min_visual = Vector3P.read(reader)
            mi.bbox_max_visual = Vector3P.read(reader)
        mi.bounding_center = Vector3P.read(reader)
        mi.geometry_center = Vector3P.read(reader)
        mi.center_of_mass = Vector3P.read(reader)
        mi.inv_inertia = Matrix3P.read(reader)
        mi.auto_center = reader.read_bool()
        mi.lock_auto_center = reader.read_bool()
        mi.can_occlude = reader.read_bool()
        mi.can_be_occluded = reader.read_bool()
        # DayZ: 5th bool (allowAnimation) always present
        mi.allow_animation = reader.read_bool()
        if v >= 73:
            mi.ai_covers = reader.read_bool()
        if (v >= 42 and v < 10000) or v >= 10042:
            mi.ht_min = reader.read_float()
            mi.ht_max = reader.read_float()
            mi.af_max = reader.read_float()
            mi.mf_max = reader.read_float()
        if (v >= 43 and v < 10000) or v >= 10043:
            mi.m_fact = reader.read_float()
            mi.t_body = reader.read_float()
        # DayZ: forceNotAlpha is uint32, not bool
        mi.force_not_alpha = 0
        if v >= 33:
            mi.force_not_alpha = reader.read_uint32()
        mi.sb_source = 0
        mi.prefer_shadow_volume = False
        if v >= 37:
            mi.sb_source = reader.read_int32()
            mi.prefer_shadow_volume = reader.read_bool()
        mi.shadow_offset = 0.0
        if v >= 48:
            mi.shadow_offset = reader.read_float()
        # DayZ: disableCover bool (wiki: "if version>=73 || dayz")
        mi.disable_cover = reader.read_bool()
        mi.animated = reader.read_bool()
        mi.skeleton = Skeleton.read(reader)
        mi.map_type = reader.read_byte()
        mi.mass_array = reader.read_compressed_float_array()
        mi.mass = reader.read_float()
        mi.inv_mass = reader.read_float()
        mi.armor = reader.read_float()
        mi.inv_armor = reader.read_float()
        mi.explosion_shielding = 0.0
        if v >= 72:
            mi.explosion_shielding = reader.read_float()
        if v >= 53:
            mi.geometry_simple = reader.read_byte()
        if v >= 54:
            mi.geometry_phys = reader.read_byte()
        mi.memory = reader.read_byte()
        mi.geometry = reader.read_byte()
        mi.geometry_fire = reader.read_byte()
        mi.geometry_view = reader.read_byte()
        mi.geometry_view_pilot = reader.read_byte()
        mi.geometry_view_gunner = reader.read_byte()
        reader.read_sbyte()  # unknown signed byte
        mi.geometry_view_cargo = reader.read_byte()
        mi.land_contact = reader.read_byte()
        mi.roadway = reader.read_byte()
        mi.paths = reader.read_byte()
        mi.hitpoints = reader.read_byte()
        mi.min_shadow = reader.read_uint32() & 0xFF
        mi.can_blend = False
        if v >= 38:
            mi.can_blend = reader.read_bool()
        mi.property_class = reader.read_asciiz()
        mi.property_damage = reader.read_asciiz()
        mi.property_frequent = reader.read_bool()
        if v >= 31:
            reader.read_uint32()  # unknown
        mi.preferred_shadow_volume_lod = []
        mi.preferred_shadow_buffer_lod = []
        mi.preferred_shadow_buffer_lod_vis = []
        if v >= 57:
            mi.preferred_shadow_volume_lod = [reader.read_int32() for _ in range(n_lods)]
            mi.preferred_shadow_buffer_lod = [reader.read_int32() for _ in range(n_lods)]
            mi.preferred_shadow_buffer_lod_vis = [reader.read_int32() for _ in range(n_lods)]
        return mi

    def __repr__(self):
        return (f"ModelInfo(mass={self.mass:.1f}, skeleton={self.skeleton}, "
                f"bbox={self.bbox_min}→{self.bbox_max})")


# ── LOD ──

class LOD:
    """Single LOD within an ODOL file."""

    @classmethod
    def read(cls, reader, resolution):
        lod = cls()
        v = reader.version
        lod.resolution = resolution
        lod.proxies = reader.read_array(lambda: Proxy.read(reader))
        lod.sub_skeletons_to_skeleton = reader.read_int_array()
        n_skel_sets = reader.read_int32()
        lod.skeleton_to_sub_skeleton = [reader.read_int_array() for _ in range(n_skel_sets)]

        lod.clip_old = None
        lod.vertex_count_hint = 0
        if v >= 50:
            lod.vertex_count_hint = reader.read_uint32()
        else:
            lod.clip_old = reader.read_condensed_int_array()

        lod.face_area = 0.0
        if v >= 51:
            lod.face_area = reader.read_float()

        lod.or_hints = reader.read_int32()
        lod.and_hints = reader.read_int32()
        lod.b_min = Vector3P.read(reader)
        lod.b_max = Vector3P.read(reader)
        lod.b_center = Vector3P.read(reader)
        lod.b_radius = reader.read_float()

        lod.textures = reader.read_string_array()
        n_materials = reader.read_int32()
        lod.materials = [EmbeddedMaterial.read(reader) for _ in range(n_materials)]

        lod.point_to_vertex = reader.read_compressed_vertex_index_array()
        lod.vertex_to_point = reader.read_compressed_vertex_index_array()

        # Polygons
        n_faces = reader.read_uint32()
        reader.read_uint32()  # offset to sections (unused)
        reader.read_uint16()  # always 0
        lod.faces = [Polygon.read(reader) for _ in range(n_faces)]

        n_sections = reader.read_int32()
        lod.sections = [Section.read(reader) for _ in range(n_sections)]

        n_ns = reader.read_int32()
        lod.named_selections = [NamedSelection.read(reader) for _ in range(n_ns)]

        n_props = reader.read_uint32()
        lod.named_properties = []
        for _ in range(n_props):
            k = reader.read_asciiz()
            val = reader.read_asciiz()
            lod.named_properties.append((k, val))

        n_frames = reader.read_int32()
        lod.frames = [Keyframe.read(reader) for _ in range(n_frames)]

        lod.color_top = reader.read_int32()
        lod.color = reader.read_int32()
        lod.special = reader.read_int32()
        lod.vertex_bone_ref_is_simple = reader.read_bool()
        lod.size_of_rest_data = reader.read_uint32()

        lod.clip = None
        if v >= 50:
            lod.clip = reader.read_condensed_int_array()

        # UV sets
        uv0 = UVSet.read(reader, v)
        n_uv_sets = reader.read_uint32()
        if n_uv_sets == 0:
            lod.uv_sets = [uv0]
        else:
            lod.uv_sets = [None] * n_uv_sets
            lod.uv_sets[0] = uv0
            for i in range(1, n_uv_sets):
                lod.uv_sets[i] = UVSet.read(reader, v)

        # Vertices (compressed)
        n_verts = reader.read_int32()
        vert_data = reader.read_compressed(n_verts * 12)
        sub = reader.sub_reader(vert_data)
        lod.vertices = [Vector3P.read(sub) for _ in range(n_verts)]

        # Normals
        if v >= 45:
            # Compressed normals (4 bytes each)
            n_normals = reader.read_int32()
            if reader.read_bool():
                # Default fill
                val = reader.read_int32()
                lod.normals = [Vector3P.read_compressed_from_int(val)] * n_normals
            else:
                norm_data = reader.read_compressed(n_normals * 4)
                lod.normals = []
                for i in range(n_normals):
                    raw = struct.unpack_from('<I', norm_data, i * 4)[0]
                    lod.normals.append(Vector3P.read_compressed_from_int(raw))
        else:
            lod.normals = reader.read_condensed_array(
                lambda r: Vector3P.read(r), 12)

        # ST coords (tangent/binormal)
        if v >= 45:
            n_st = reader.read_int32()
            reader.read_compressed(n_st * 8)  # skip compressed STPairs
        else:
            n_st = reader.read_int32()
            reader.read_compressed(n_st * 24)

        # Vertex bone refs (AnimationRTWeight = VerySmallArray = 12 bytes)
        n_vbr = reader.read_int32()
        vbr_data = reader.read_compressed(n_vbr * 12)
        sub = reader.sub_reader(vbr_data)
        lod.vertex_bone_ref = [VerySmallArray.read(sub) for _ in range(n_vbr)]

        # Neighbor bone refs (32 bytes each)
        n_nbr = reader.read_int32()
        reader.read_compressed(n_nbr * 32)  # skip for now

        if v >= 67:
            reader.read_uint32()
        if v >= 68:
            reader.read_byte()

        return lod

    @property
    def vertex_count(self):
        return len(self.vertices)

    def __repr__(self):
        return (f"LOD(res={self.resolution:.0f}, "
                f"{self.vertex_count} verts, {len(self.faces)} faces, "
                f"{len(self.named_selections)} selections)")


# ── Main ODOL class ──

class ODOL:
    """Parsed ODOL P3D file."""

    def __init__(self):
        self.version = 0
        self.app_id = 0
        self.muzzle_flash = ''
        self.n_lods = 0
        self.resolutions = []
        self.model_info = None
        self.has_anims = False
        self.animations = None
        self.lods = []

    @classmethod
    def from_file(cls, path):
        reader = BisReader.from_file(path)
        # Auto-detect ODOL signature (may be inside a container)
        cls._seek_odol(reader)
        return cls._read(reader)

    @classmethod
    def from_bytes(cls, data):
        reader = BisReader(data)
        cls._seek_odol(reader)
        return cls._read(reader)

    @classmethod
    def _seek_odol(cls, reader):
        """Find ODOL signature, handling container files with padding."""
        if reader.data[reader.position:reader.position+4] == b'ODOL':
            return  # Already at ODOL
        # Search for ODOL signature
        idx = reader.data.find(b'ODOL', reader.position)
        if idx >= 0:
            reader.position = idx
        else:
            raise ValueError("ODOL signature not found in file")

    @classmethod
    def _read(cls, reader):
        odol = cls()

        sig = reader.read_ascii(4)
        if sig != 'ODOL':
            raise ValueError(f"Not an ODOL file (signature: {sig})")

        odol.version = reader.read_uint32()
        if odol.version > 73:
            raise ValueError(f"Unknown ODOL version: {odol.version}")
        if odol.version < 28:
            raise ValueError(f"ODOL version too old: {odol.version}")

        reader.version = odol.version
        if odol.version >= 44:
            reader.use_lzo = True
        if odol.version >= 64:
            reader.use_compression_flag = True

        if odol.version >= 59:
            odol.app_id = reader.read_uint32()
        if odol.version >= 58:
            odol.muzzle_flash = reader.read_asciiz()

        odol.n_lods = reader.read_int32()
        odol.resolutions = [reader.read_float() for _ in range(odol.n_lods)]

        odol.model_info = ODOL_ModelInfo.read(reader, odol.n_lods)

        odol.has_anims = False
        odol.animations = None
        if odol.version >= 30:
            # DayZ quirk: hasAnims byte may or may not be present, AND
            # Animations data may follow even without an explicit hasAnims byte
            # (observed on dz/gear/containers/55galDrum.p3d — barrel model).
            # Strategy: try every plausible interpretation and pick the one
            # whose resulting LOD address table is consistent with the file.
            file_size = len(reader.data)
            saved = reader.position
            n = odol.n_lods

            def _try_lod_addrs(pos):
                """Return True iff a LOD address table starting at pos is valid:
                start/end inside file bounds, end >= start, permanent in {0,1}."""
                end_table = pos + n * 4 + n * 4 + n
                if end_table > file_size:
                    return False
                ls = [struct.unpack_from('<I', reader.data, pos + i*4)[0] for i in range(n)]
                le_off = pos + n*4
                le = [struct.unpack_from('<I', reader.data, le_off + i*4)[0] for i in range(n)]
                pm_off = le_off + n*4
                pm = [reader.data[pm_off + i] for i in range(n)]
                for s, e in zip(ls, le):
                    if s == 0 or s >= file_size or e > file_size or e < s:
                        return False
                if any(p not in (0, 1) for p in pm):
                    return False
                return True

            byte_at_saved = reader.data[saved]
            # Candidate A: hasAnims byte = 0 → LOD addrs at saved+1
            ok_a = _try_lod_addrs(saved + 1)
            # Candidate B: hasAnims byte = 1 → Animations from saved+1, then LOD addrs
            ok_b = False; pos_after_b = None
            if byte_at_saved == 1:
                try:
                    reader.position = saved + 1
                    Animations.read(reader)
                    pos_after_b = reader.position
                    ok_b = _try_lod_addrs(pos_after_b)
                except Exception:
                    ok_b = False
                reader.position = saved
            # Candidate C: NO hasAnims byte — Animations starts directly at saved
            ok_c = False; pos_after_c = None
            try:
                reader.position = saved
                Animations.read(reader)
                pos_after_c = reader.position
                ok_c = _try_lod_addrs(pos_after_c)
            except Exception:
                ok_c = False
            reader.position = saved
            # Candidate D: LOD addrs start directly at saved (no anims field at all)
            ok_d = _try_lod_addrs(saved)

            # Priority: B (canonical) > C (DayZ no-byte anims) > A (no-anims byte=0) > D (raw)
            if ok_b:
                reader.position = saved + 1
                odol.has_anims = True
                odol.animations = Animations.read(reader)
            elif ok_c:
                reader.position = saved
                odol.has_anims = True
                odol.animations = Animations.read(reader)
            elif ok_a:
                reader.position = saved + 1
            elif ok_d:
                reader.position = saved
            else:
                # Fall back to original heuristic for edge cases none of A-D detected.
                reader.position = saved
                has_anims_byte = reader.read_bool()
                if has_anims_byte:
                    peek_n_classes = struct.unpack_from('<I', reader.data, reader.position)[0]
                    if peek_n_classes < 10000:
                        odol.has_anims = True
                        odol.animations = Animations.read(reader)
                    else:
                        reader.position = saved
                else:
                    peek_first = struct.unpack_from('<I', reader.data, reader.position)[0]
                    if peek_first > file_size:
                        reader.position = saved

        # LOD addresses
        lod_start = [reader.read_uint32() for _ in range(odol.n_lods)]
        lod_end = [reader.read_uint32() for _ in range(odol.n_lods)]
        permanent = [reader.read_bool() for _ in range(odol.n_lods)]

        # Read LODs
        odol.lods = []
        saved_pos = reader.position
        for i in range(odol.n_lods):
            if not permanent[i]:
                # Read LoadableLodInfo
                LoadableLodInfo.read(reader)
                saved_pos = reader.position

            reader.position = lod_start[i]
            lod = LOD.read(reader, odol.resolutions[i])
            odol.lods.append(lod)
            reader.position = saved_pos

        return odol

    def __repr__(self):
        return (f"ODOL(v{self.version}, {self.n_lods} LODs, "
                f"mass={self.model_info.mass:.1f})")
