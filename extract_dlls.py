import struct, os, sys

try:
    import lz4.block
except ImportError:
    print("ERROR: pip install lz4")
    sys.exit(1)

def list_elf_sections(data):
    """List all ELF sections and find which ones start with XABA"""
    if data[:4] != b'\x7fELF':
        return []

    is64 = data[4] == 2
    if is64:
        e_shoff = struct.unpack_from('=Q', data, 0x28)[0]
        e_shentsize = struct.unpack_from('=H', data, 0x3A)[0]
        e_shnum = struct.unpack_from('=H', data, 0x3C)[0]
        e_shstrndx = struct.unpack_from('=H', data, 0x3E)[0]
    else:
        e_shoff = struct.unpack_from('=I', data, 0x20)[0]
        e_shentsize = struct.unpack_from('=H', data, 0x2E)[0]
        e_shnum = struct.unpack_from('=H', data, 0x30)[0]
        e_shstrndx = struct.unpack_from('=H', data, 0x32)[0]

    shstr_off = e_shoff + e_shentsize * e_shstrndx
    shstr_addr = struct.unpack_from('=Q' if is64 else '=I', data, shstr_off + (0x18 if is64 else 0x16))[0]

    xaba_sections = []
    for i in range(e_shnum):
        off = e_shoff + e_shentsize * i
        sh_name = struct.unpack_from('=I', data, off)[0]
        sh_offset = struct.unpack_from('=Q' if is64 else '=I', data, off + (0x18 if is64 else 0x10))[0]
        sh_size = struct.unpack_from('=Q' if is64 else '=I', data, off + (0x20 if is64 else 0x14))[0]

        name = data[shstr_addr + sh_name:shstr_addr + sh_name + 50]
        name = name.split(b'\x00')[0].decode('utf-8', errors='ignore')

        if sh_offset + 4 <= len(data) and data[sh_offset:sh_offset+4] == b'XABA':
            xaba_sections.append((name, sh_offset, sh_size))
            print(f"  [ELF Section] {name}: offset={sh_offset}, size={sh_size}")

    return xaba_sections

def extract_from_offset(data, offset, out_dir):
    """Extract assemblies from XABA at given offset"""
    P = data[offset:]
    if P[:4] != b'XABA':
        raise ValueError("No XABA at offset")

    ver = struct.unpack_from('<I', P, 4)[0]
    local_cnt = struct.unpack_from('<I', P, 8)[0]
    global_cnt = struct.unpack_from('<I', P, 12)[0]
    data_start = struct.unpack_from('<I', P, 20)[0]

    print(f"  Version: {ver}, local_cnt: {local_cnt}, global_cnt: {global_cnt}, data_start: {data_start}")

    off = 32
    if ver >= 2:
        off += global_cnt * 12

    entry_sz = 28 if ver >= 2 else 24

    entries = []
    for i in range(local_cnt):
        f = struct.unpack_from('<7I' if ver >= 2 else '<6I', P, off)
        entries.append((f[1], f[2]) if ver >= 2 else (f[0], f[1]))
        off += entry_sz

    names = []
    for i in range(local_cnt):
        if off >= len(P):
            names.append(f"unknown_{i}")
            continue
        nlen = struct.unpack_from('=B', P, off)[0]
        off += 1
        if off + nlen > len(P):
            names.append(f"unknown_{i}")
            continue
        name_bytes = P[off:off+nlen]
        try:
            name = name_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                name = name_bytes.decode('latin-1')
            except:
                name = f"unknown_{i}"
        names.append(name)
        off += nlen

    print(f"  Names: {names}")

    os.makedirs(out_dir, exist_ok=True)
    needed = ["StardewValley.dll", "StardewValley.GameData.dll", "MonoGame.Framework.dll"]

    for idx, (h, raw_len) in enumerate(entries):
        name = names[idx] if idx < len(names) else f"u{idx}"
        if data_start + raw_len > len(P):
            print(f"  SKIP {name}: data overflow")
            continue
        raw = P[data_start:data_start+raw_len]
        data_start += raw_len
        if len(raw) >= 12 and raw[:4] == b'XALZ':
            usz = struct.unpack_from('<I', raw, 4)[0]
            raw = lz4.block.decompress(raw[12:], uncompressed_size=usz)
        out_path = os.path.join(out_dir, name)
        with open(out_path, 'wb') as f:
            f.write(raw)
        print(f"  -> {name}: {len(raw)} bytes")

    ok = all(os.path.exists(os.path.join(out_dir, n)) and os.path.getsize(os.path.join(out_dir, n)) > 100 for n in needed)
    return ok

def main():
    blob_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "DependenciesDll"

    with open(blob_path, 'rb') as f:
        data = f.read()

    print(f"[INFO] Blob size: {len(data)} bytes")
    print(f"[INFO] First 16 bytes: {data[:16].hex()}")

    # Method 1: ELF sections with XABA
    print("\n[INFO] Method 1: Scanning ELF sections...")
    sections = list_elf_sections(data)

    for name, offset, size in sections:
        print(f"\n[INFO] Trying section '{name}' at offset {offset}...")
        try:
            if extract_from_offset(data, offset, out_dir):
                print("\n[SUCCESS] Method 1!")
                return
        except Exception as e:
            print(f"  Failed: {e}")

    # Method 2: All XABA occurrences
    print("\n[INFO] Method 2: Brute-force XABA scan...")
    idx = 0
    count = 0
    while True:
        idx = data.find(b'XABA', idx + 1)
        if idx < 0 or count > 100:
            break
        count += 1
        print(f"\n[INFO] Trying XABA at offset {idx}...")
        try:
            if extract_from_offset(data, idx, out_dir):
                print(f"\n[SUCCESS] Method 2 at offset {idx}!")
                return
        except Exception as e:
            print(f"  Failed: {e}")

    print("\n[ERROR] All methods failed!")
    sys.exit(1)

if __name__ == "__main__":
    main()
