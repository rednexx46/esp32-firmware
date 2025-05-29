BUFFER_FILE = "buffer.txt"

def load_buffer():
    buf = []
    try:
        with open(BUFFER_FILE, "r") as f:
            for line in f:
                buf.append(line.strip().encode())
        print(f"[BUFFER] Loaded {len(buf)} items.")
    except:
        print("[BUFFER] No buffer file found.")
    return buf

def save_buffer(buf):
    try:
        with open(BUFFER_FILE, "w") as f:
            for item in buf:
                f.write(item.decode() + "\n")
        print(f"[BUFFER] Saved {len(buf)} items.")
    except Exception as e:
        print(f"[BUFFER] Save error: {e}")