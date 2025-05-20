def load_config(path='config.ini'):
    config = {}
    try:
        with open(path, 'r') as f:
            section = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    config[section] = {}
                elif '=' in line and section:
                    key, value = line.split('=', 1)
                    config[section][key.strip()] = value.strip()
        return config
    except Exception as e:
        print("Failed to load config:", e)
        return {}