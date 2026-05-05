#!/usr/bin/env python3
"""
ODOL → MLOD Converter
Converts binarized DayZ/Arma .p3d files to editable MLOD format.
Uses our ODOL reader + py3d for MLOD writing.

Based on BisDLL Conversion.cs logic by T_D/Crip12.
"""
import sys
import os
import struct
import math
import collections

sys.path.insert(0, os.path.dirname(__file__))

from odol_reader import ODOL
import py3d


def convert_odol_to_mlod(odol):
    """Convert a parsed ODOL object to a py3d P3D (MLOD) object."""
    mlod = py3d.P3D()
    
    for i, src_lod in enumerate(odol.lods):
        dst_lod = convert_lod(odol, src_lod, i)
        mlod.lods.append(dst_lod)
    
    return mlod


def convert_lod(odol, src, lod_index):
    """Convert a single ODOL LOD to py3d LOD."""
    dst = py3d.LOD()
    dst.resolution = src.resolution
    
    # ── Points ──
    # ODOL vertices are relative to boundingCenter; MLOD uses absolute coords
    bc = odol.model_info.bounding_center
    offset = (bc.x, bc.y, bc.z)
    
    n_verts = len(src.vertices)
    for vi in range(n_verts):
        pt = py3d.Point()
        v = src.vertices[vi]
        pt.coords = (v.x + offset[0], v.y + offset[1], v.z + offset[2])
        # ClipFlags → PointFlags (simplified: store raw clip value)
        pt.flags = src.clip[vi] if src.clip and vi < len(src.clip) else 0
        dst.points.append(pt)
    
    # ── Face normals ──
    # ODOL has per-vertex normals; MLOD needs per-face normals.
    # We compute face normals from vertex positions.
    # First, build the face list, then compute normals.
    
    # ── Faces ──
    # ODOL groups faces into sections; each section references a material.
    # We iterate sections to assign texture/material per face.
    uv_data = None
    if src.uv_sets and src.uv_sets[0]:
        uv_data = src.uv_sets[0].uv_data
    
    face_list = []
    for section in src.sections:
        # Determine texture and material for this section
        textures = getattr(src, 'textures', [])
        materials = getattr(src, 'materials', [])
        
        tex_str = ''
        if hasattr(section, 'texture_index') and section.texture_index >= 0:
            if section.texture_index < len(textures):
                tex_str = textures[section.texture_index]
        
        mat_str = ''
        if hasattr(section, 'material_index') and section.material_index >= 0:
            if section.material_index < len(materials):
                mat_str = materials[section.material_index].material_name
        
        # Get face indices for this section
        face_indices = section.get_face_indices(src.faces)
        
        for fi in face_indices:
            if fi >= len(src.faces):
                continue
            polygon = src.faces[fi]
            n_face_verts = len(polygon.vertex_indices)  # 3 or 4
            
            # Build face
            face = py3d.Face(dst.points, dst.facenormals)
            face.texture = tex_str
            face.material = mat_str
            face.flags = 0
            
            face.vertices = []
            positions = []
            
            for k in range(n_face_verts):
                # ODOL stores in one winding; MLOD uses reversed
                vi = polygon.vertex_indices[n_face_verts - 1 - k]
                
                vert = py3d.Vertex(dst.points, dst.facenormals)
                vert.point_index = vi
                vert.normal_index = len(dst.facenormals)  # will be set after
                
                # UV data
                if uv_data and vi * 2 + 1 < len(uv_data):
                    vert.uv = (uv_data[vi * 2], uv_data[vi * 2 + 1])
                else:
                    vert.uv = (0.0, 0.0)
                
                face.vertices.append(vert)
                
                if vi < len(dst.points):
                    positions.append(dst.points[vi].coords)
            
            face_list.append(face)
            
            # Compute face normal from vertex positions
            fn = _compute_face_normal(positions)
            normal_idx = len(dst.facenormals)
            dst.facenormals.append(fn)
            for v in face.vertices:
                v.normal_index = normal_idx
    
    dst.faces = face_list
    
    # ── Named Selections ──
    # ODOL named selections reference vertex/face indices.
    # We need to map them to py3d Point/Face objects.
    for ns in src.named_selections:
        sel = py3d.Selection(dst.points, dst.faces)
        sel.points = {}
        sel.faces = {}
        
        # Vertex-based selection with weights
        if ns.selected_vertices and ns.vertex_weights:
            weights_bytes = ns.vertex_weights
            for idx_pos, vi in enumerate(ns.selected_vertices):
                if vi < len(dst.points) and idx_pos < len(weights_bytes):
                    w = weights_bytes[idx_pos]
                    if w > 0:
                        sel.points[dst.points[vi]] = 1  # simplified: selected=1
        
        # Face-based selection
        if ns.selected_faces:
            for fi in ns.selected_faces:
                # fi is an ODOL face index; we need to find the 
                # corresponding MLOD face. For now, use direct index
                # (valid when face ordering is preserved)
                if fi < len(dst.faces):
                    sel.faces[dst.faces[fi]] = 1
        
        dst.selections[ns.name] = sel
    
    # ── Properties ──
    for k, v in src.named_properties:
        dst.properties[k] = v
    
    # ── Mass ──
    # Mass is distributed across points in Geometry LOD (resolution ~1e13)
    if abs(src.resolution - 1e13) / 1e13 < 0.01:  # Geometry LOD
        total_mass = odol.model_info.mass
        if n_verts > 0 and total_mass > 0:
            mass_per_vert = total_mass / n_verts
            for pt in dst.points:
                pt.mass = mass_per_vert
    
    return dst


def _compute_face_normal(positions):
    """Compute face normal from 3+ vertex positions."""
    if len(positions) < 3:
        return (0.0, 1.0, 0.0)
    
    # Use first 3 vertices
    p0, p1, p2 = positions[0], positions[1], positions[2]
    
    # Edge vectors
    e1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
    e2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
    
    # Cross product
    nx = e1[1]*e2[2] - e1[2]*e2[1]
    ny = e1[2]*e2[0] - e1[0]*e2[2]
    nz = e1[0]*e2[1] - e1[1]*e2[0]
    
    # Normalize
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length < 1e-10:
        return (0.0, 1.0, 0.0)
    
    return (nx/length, ny/length, nz/length)


def main():
    if len(sys.argv) < 2:
        print("Usage: odol_to_mlod.py <input.p3d> [output.p3d]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.p3d', '_mlod.p3d')
    
    print(f"Reading ODOL: {input_path}")
    odol = ODOL.from_file(input_path)
    print(f"  {odol}")
    
    print(f"Converting to MLOD...")
    mlod = convert_odol_to_mlod(odol)
    print(f"  {len(mlod.lods)} LODs converted")
    
    for i, lod in enumerate(mlod.lods):
        print(f"    LOD {i}: res={lod.resolution:.0f}, "
              f"{len(lod.points)} pts, {len(lod.faces)} faces, "
              f"{len(lod.facenormals)} normals, "
              f"{len(lod.selections)} sels")
    
    print(f"Writing MLOD: {output_path}")
    with open(output_path, 'wb') as f:
        mlod.write(f)
    
    file_size = os.path.getsize(output_path)
    print(f"  Written {file_size} bytes")
    
    # Verify by re-reading
    print(f"Verifying...")
    with open(output_path, 'rb') as f:
        verify = py3d.P3D(f)
    print(f"  Read back {len(verify.lods)} LODs")
    for i, lod in enumerate(verify.lods):
        print(f"    LOD {i}: {len(lod.points)} pts, {len(lod.faces)} faces, "
              f"{len(lod.selections)} sels, res={lod.resolution:.0f}")
    
    print("Done!")


if __name__ == '__main__':
    main()
