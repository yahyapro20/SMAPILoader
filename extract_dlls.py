import struct, os, sys, lz4.block

def extract(data, out_dir):
    if data[:4] != b'XABA':
        raise ValueError("No XABA header")
    ver = struct.unpack_from('<I', data, 4)[0]
    local_cnt = struct.unpack_from('<I', data, 8)[0]
    global_cnt = struct.unpack_from('<I', data, 12)[0]
    off = 32
    if ver >= 2:
        off += global_cnt * 12
    entry_sz = 28 if ver >= 2 else 24
    entries = []
    for i in range(local_cnt):
        f = struct.unpack_from('<7I' if ver >= 2 else '<6I', data, off)
        entries.append((f[1], f[2]) if ver >= 2 else (f[0], f[1]))
        off += entry_sz
    names = []
    for i in range(local_cnt):
        nlen = struct.unpack_from('=B', data, off)[0]
        off += 1
        names.append(data[off:off+nlen].decode('utf-8'))
        off += nlen
    data_start = struct.unpack_from('<I', data, 20)[0]
    os.makedirs(out_dir, exist_ok=True)
    for idx, (h, raw_len) in enumerate(entries):
        name = names[idx] if idx < len(names) else f"u{idx}"
        raw = data[data_start:data_start+raw_len]
        data_start += raw_len
        if len(raw) >= 12 and raw[:4] == b'XALZ':
            usz = struct.unpack_from('<I', raw, 4)[0]
            raw = lz4.block.decompress(raw[12:], uncompressed_size=usz)
        out_path = os.path.join(out_dir, name)
        with open(out_path, 'wb') as f:
            f.write(raw)
        print(f"  {name}: {len(raw)} bytes -> {out_path}")

def main():
    blob_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "DependenciesDll"

    with open(blob_path, 'rb') as f:
        data = f.read()

    print(f"Blob size: {len(data)} bytes")
    print(f"First 16 bytes: {data[:16].hex()}")

    # Method 1: Direct XABA search
    idx = data.find(b'XABA')
    if idx >= 0:
        print(f"\nMethod 1: XABA found at offset {idx}")
        try:
            extract(data[idx:], out_dir)
            print("SUCCESS")
            return
        except Exception as e:
            print(f"Method 1 failed: {e}")

    # Method 2: ELF .payload section
    print("\nMethod 2: Trying ELF .payload...")
    try:
        if data[:4] != b'\x7fELF':
            raise ValueError("Not ELF")
        is64 = data[4] == 2
        e_shoff = struct.unpack_from('=Q' if is64 else '=I', data, 0x28 if is64 else 0x20)[0]
        e_shentsize = struct.unpack_from('=H', data, 0x3A if is64 else 0x2E)[0]
        e_shnum = struct.unpack_from('=H', data, 0x3C if is64 else 0x30)[0]
        e_shstrndx = struct.unpack_from('=H', data, 0x3E if is64 else 0x32)[0]
        shstr_off = e_shoff + e_shentsize * e_shstrndx
        shstr_addr = struct.unpack_from('=Q' if is64 else '=I', data, shstr_off + (0x18 if is64 else 0x16))[0]
        for i in range(e_shnum):
            off = e_shoff + e_shentsize * i
            sh_name = struct.unpack_from('=I', data, off)[0]
            sh_offset = struct.unpack_from('=Q' if is64 else '=I', data, off + (0x18 if is64 else 0x10))[0]
            sh_size = struct.unpack_from('=Q' if is64 else '=I', data, off + (0x20 if is64 else 0x14))[0]
            name_bytes = data[shstr_addr+sh_name:shstr_addr+sh_name+50]
            name = name_bytes.split(b'\x00')[0].decode('utf-8', 'ignore')
            if name == ".payload":
                extract(data[sh_offset:sh_offset+sh_size], out_dir)
                print("SUCCESS")
                return
        raise ValueError("No .payload section")
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # Method 3: Brute force
    print("\nMethod 3: Brute force scan...")
    idx = 0
    while True:
        idx = data.find(b'XABA', idx + 1)
        if idx < 0:
            break
        try:
            extract(data[idx:], out_dir)
            print(f"SUCCESS at offset {idx}")
            return
        except:
            pass

    print("\nERROR: All extraction methods failed!")
    sys.exit(1)

if __name__ == "__main__":
    main()
