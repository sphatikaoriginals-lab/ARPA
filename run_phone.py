import subprocess
import time
from pyngrok import ngrok

# 1. FastAPI Server background me start karein
print("[*] Starting ARPA Server on port 8000...")
server_process = subprocess.Popen(["py", "-m", "uvicorn", "api:app", "--port", "8000"])

time.sleep(2)

# 2. HTTPS Tunnel create karein
print("[*] Generating Secure HTTPS link for phone camera...")
public_url = ngrok.connect(8000)

print("=" * 65)
print("★ ARPA LIVE PHONE ACCESS URL:")
print(f"  --> {public_url} <--")
print("=" * 65)
print("Apne phone ke Chrome / Safari browser me yeh URL open karein.")

try:
    server_process.wait()
except KeyboardInterrupt:
    print("\n[*] Shutting down tunnel and server...")
    ngrok.disconnect(public_url.public_url)
    server_process.terminate()