"""
LZO1X stream decompressor for BI ODOL format.
Rewritten as iterative loop faithful to BisDLL-Arma-3 LZO.cs.

Key differences from standard LZO1X:
- No -16384 offset in M4 matches (BI variant)
- Stream-based: no compressed-size prefix, returns bytes consumed
"""


class LZOError(Exception):
    pass


M2_MAX_OFFSET = 2048


def decompress_lzo(data: bytes, offset: int, expected_size: int) -> tuple:
    """Public entry point: wraps the core decoder to also consume a trailing
    EOF marker (b'\\x11\\x00\\x00') if present.

    The pure-Python core can exit at op==expected_size mid-instruction without
    consuming the 3-byte EOF marker that some BI streams append after the
    final literal run. That off-by-3 then corrupts whatever field comes next
    in the parent stream (observed on dz/gear/containers/55galDrum.p3d
    LOD 2 UV0 → wrong n_uv_sets read → n_vertices=16M → LZO failure)."""
    result, consumed = _decompress_lzo_impl(data, offset, expected_size)
    end = offset + consumed
    if end + 3 <= len(data) and data[end] == 0x11 and data[end+1] == 0 and data[end+2] == 0:
        consumed += 3
    return result, consumed


def _decompress_lzo_impl(data: bytes, offset: int, expected_size: int) -> tuple:
    out = bytearray(expected_size)
    op = 0
    ip = offset

    t = data[ip]; ip += 1

    if t > 17:
        tt = t - 17
        if tt >= 4:
            for _ in range(tt):
                out[op] = data[ip]; op += 1; ip += 1
            t = data[ip]; ip += 1
            if t >= 16:
                return _match_then_literal(data, ip, t, out, op, expected_size, offset)
            # M1 after first literal
            ip, op = _do_m1(data, ip, t, out, op)
            tt = data[ip - 2] & 3
            if tt == 0:
                return _literal_loop(data, ip, out, op, expected_size, offset)
            for _ in range(tt):
                out[op] = data[ip]; op += 1; ip += 1
            t = data[ip]; ip += 1
            return _match_then_literal(data, ip, t, out, op, expected_size, offset)
        # tt < 4: treat as match trailer, fall through to match handling
        # Need initial M1 with the leftover t
        # Actually per C#: goto IL_37D (copy_match_trailer with tt bytes, then IL_50)
        for _ in range(tt):
            out[op] = data[ip]; op += 1; ip += 1
        return _literal_loop(data, ip, out, op, expected_size, offset)

    # t <= 17
    if t < 16:
        # Literal run
        if t == 0:
            while data[ip] == 0:
                t += 255; ip += 1
            t += 15 + data[ip]; ip += 1
        for _ in range(t + 3):
            out[op] = data[ip]; op += 1; ip += 1
        t = data[ip]; ip += 1
        if t >= 16:
            return _match_then_literal(data, ip, t, out, op, expected_size, offset)
        ip, op = _do_m1(data, ip, t, out, op)
        tt = data[ip - 2] & 3
        if tt == 0:
            return _literal_loop(data, ip, out, op, expected_size, offset)
        for _ in range(tt):
            out[op] = data[ip]; op += 1; ip += 1
        t = data[ip]; ip += 1
        return _match_then_literal(data, ip, t, out, op, expected_size, offset)
    else:
        return _match_then_literal(data, ip, t, out, op, expected_size, offset)


def _do_m1(data, ip, t, out, op):
    """M1 match: short back-reference after literal run."""
    m_pos = op - (1 + M2_MAX_OFFSET) - (t >> 2) - (data[ip] << 2)
    ip += 1
    if m_pos < 0 or m_pos >= op:
        raise LZOError(f"Lookbehind overrun (M1) m_pos={m_pos} op={op}")
    out[op] = out[m_pos]; op += 1
    out[op] = out[m_pos + 1]; op += 1
    out[op] = out[m_pos + 2]; op += 1
    return ip, op


def _literal_loop(data, ip, out, op, expected_size, ip_start):
    """Main loop: alternates between literal runs and match sequences."""
    while op < expected_size:
        t = data[ip]; ip += 1

        if t >= 16:
            ip, op, done = _do_match_sequence(data, ip, t, out, op, expected_size)
            if done:
                return bytes(out[:op]), ip - ip_start
            continue

        # Literal run
        if t == 0:
            while data[ip] == 0:
                t += 255; ip += 1
            t += 15 + data[ip]; ip += 1
        for _ in range(t + 3):
            out[op] = data[ip]; op += 1; ip += 1

        # After literal: check for M1
        t = data[ip]; ip += 1
        if t >= 16:
            ip, op, done = _do_match_sequence(data, ip, t, out, op, expected_size)
            if done:
                return bytes(out[:op]), ip - ip_start
            continue

        # M1 match
        ip, op = _do_m1(data, ip, t, out, op)
        tt = data[ip - 2] & 3
        if tt == 0:
            continue
        for _ in range(tt):
            out[op] = data[ip]; op += 1; ip += 1
        # After M1 trailer: next match
        t = data[ip]; ip += 1
        ip, op, done = _do_match_sequence(data, ip, t, out, op, expected_size)
        if done:
            return bytes(out[:op]), ip - ip_start

    return bytes(out[:op]), ip - ip_start


def _do_match_sequence(data, ip, t, out, op, expected_size):
    """Process one or more consecutive match instructions. Returns (ip, op, end_of_stream)."""
    while True:
        if t >= 64:
            # M2
            m_pos = op - 1 - ((t >> 2) & 7) - (data[ip] << 3)
            ip += 1
            m_len = (t >> 5) - 1
            if m_pos < 0 or m_pos >= op:
                raise LZOError(f"Lookbehind overrun (M2) m_pos={m_pos} op={op}")
        elif t >= 32:
            # M3
            m_len = t & 31
            if m_len == 0:
                while data[ip] == 0:
                    m_len += 255; ip += 1
                m_len += 31 + data[ip]; ip += 1
            m_pos = op - 1 - ((data[ip] >> 2) + (data[ip + 1] << 6))
            ip += 2
            if m_pos < 0 or m_pos >= op:
                raise LZOError(f"Lookbehind overrun (M3) m_pos={m_pos} op={op}")
        elif t >= 16:
            # M4 (BI variant: no -16384)
            m_pos = op - ((t & 8) << 11)
            m_len = t & 7
            if m_len == 0:
                while data[ip] == 0:
                    m_len += 255; ip += 1
                m_len += 7 + data[ip]; ip += 1
            m_pos -= (data[ip] >> 2) + (data[ip + 1] << 6)
            ip += 2
            if m_pos == op:
                return ip, op, True  # End of stream
            if m_pos < 0 or m_pos >= op:
                raise LZOError(f"Lookbehind overrun (M4) m_pos={m_pos} op={op}")
        else:
            raise LZOError(f"Unexpected t={t} < 16 in match sequence")

        # Copy match
        for j in range(m_len + 2):
            out[op] = out[m_pos + j]; op += 1

        # Trailer
        tt = data[ip - 2] & 3
        if tt == 0:
            return ip, op, False  # Back to literal loop

        for _ in range(tt):
            out[op] = data[ip]; op += 1; ip += 1

        # Next instruction
        t = data[ip]; ip += 1


def _match_then_literal(data, ip, t, out, op, expected_size, ip_start):
    """Enter match sequence then continue with literal loop."""
    ip, op, done = _do_match_sequence(data, ip, t, out, op, expected_size)
    if done:
        return bytes(out[:op]), ip - ip_start
    return _literal_loop(data, ip, out, op, expected_size, ip_start)
