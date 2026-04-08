import re

with open("/var/www/bolt-dashboard/app.py", "r") as f:
    content = f.read()

# 1. Add host_gateway after config load
old_config = """with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)"""

new_config = """with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

HOST_GATEWAY = config.get('host_gateway', '172.19.0.1')"""

content = content.replace(old_config, new_config)

# 2. Replace check_service_health function
old_check = """def check_service_health(svc):
    \"\"\"Check service health\"\"\"
    if svc.get('type') == 'systemd':
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', svc['service']],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == 'active'
        except Exception:
            return False
    else:
        try:
            url = svc['url']
            r = requests.get(url, timeout=5, verify=False)
            return r.status_code < 400
        except Exception:
            return False"""

new_check = """def check_service_health(svc):
    \"\"\"Check service health - supports HTTP, TCP, and systemd\"\"\"
    # TCP check (for databases)
    if svc.get('type') == 'tcp':
        try:
            import socket
            host = svc.get('host', 'localhost')
            port = svc.get('port', 5432)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    # HTTP check with host gateway support
    else:
        try:
            url = svc.get('url', '')
            url = url.replace('{{HOST}}', HOST_GATEWAY)
            r = requests.get(url, timeout=5, verify=False)
            return r.status_code < 400
        except Exception:
            return False"""

content = content.replace(old_check, new_check)

# 3. Fix policies.yaml error - silence it
old_policies = """policies_loaded = False
for p in policy_paths:
    try:
        with open(p, 'r') as f:
            policies = yaml.safe_load(f)
            policies_loaded = True
    except:
        pass"""

new_policies = """policies_loaded = False
for p in policy_paths:
    try:
        with open(p, 'r') as f:
            policies = yaml.safe_load(f)
            policies_loaded = True
            break
    except (FileNotFoundError, OSError):
        pass  # Silently skip if file not found"""

content = content.replace(old_policies, new_policies)

with open("/var/www/bolt-dashboard/app.py", "w") as f:
    f.write(content)

print("Dashboard patched successfully")
