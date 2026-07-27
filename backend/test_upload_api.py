import subprocess
import time
import urllib.request
import urllib.error
import json
import sys
import os
import signal
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

def encode_multipart_formdata(files):
    """Encodes files into multipart/form-data payload natively using standard bytes operations."""
    boundary = b'----WebKitFormBoundary7MA4YWxkTrZu0gW'
    lines = []
    for filename, content, mime_type in files:
        lines.append(b'--' + boundary)
        lines.append(f'Content-Disposition: form-data; name="files"; filename="{filename}"'.encode('utf-8'))
        lines.append(f'Content-Type: {mime_type}'.encode('utf-8'))
        lines.append(b'')
        lines.append(content)
    lines.append(b'--' + boundary + b'--')
    lines.append(b'')
    body = b'\r\n'.join(lines)
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary.decode("utf-8")}',
        'Content-Length': str(len(body))
    }
    return body, headers

def run_tests():
    print("=" * 60)
    print("STARTING IMAGE UPLOAD MODULE API TESTS")
    print("=" * 60)

    cmd = ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"]
    print("Starting FastAPI Uvicorn server...")
    server_proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).resolve().parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(3)
    
    if server_proc.poll() is not None:
        print("CRITICAL: Failed to start uvicorn backend server.")
        stdout, stderr = server_proc.communicate()
        print(f"Stderr: {stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

    failures = 0
    uploaded_id = None
    
    try:
        print("\nTest Case 1: Checking /api/health")
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/health")
            with urllib.request.urlopen(req) as res:
                body = json.loads(res.read().decode("utf-8"))
                if body.get("status") == "healthy":
                    print("  STATUS: PASSED")
                else:
                    print(f"  STATUS: FAILED (Unexpected body: {body})")
                    failures += 1
        except Exception as e:
            print(f"  STATUS: FAILED (Connection error: {str(e)})")
            failures += 1

        print("\nTest Case 2: Rejecting illegal extension (.txt)")
        try:
            dummy_txt = b"Hello, this is a plain text file."
            body, headers = encode_multipart_formdata([("test.txt", dummy_txt, "text/plain")])
            req = urllib.request.Request("http://127.0.0.1:8000/api/upload", data=body, headers=headers, method="POST")
            
            try:
                with urllib.request.urlopen(req) as res:
                    print("  STATUS: FAILED (Server accepted invalid text file)")
                    failures += 1
            except urllib.error.HTTPError as e:
                if e.code == 400:
                    err_msg = json.loads(e.read().decode("utf-8")).get("detail", "")
                    print(f"  STATUS: PASSED (Correctly rejected: '{err_msg}')")
                else:
                    print(f"  STATUS: FAILED (Server returned status {e.code} instead of 400)")
                    failures += 1
        except Exception as e:
            print(f"  STATUS: FAILED (Error: {str(e)})")
            failures += 1

        print("\nTest Case 3: Uploading valid PNG image")
        try:
            dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            body, headers = encode_multipart_formdata([("sih_test.png", dummy_png, "image/png")])
            req = urllib.request.Request("http://127.0.0.1:8000/api/upload", data=body, headers=headers, method="POST")
            
            with urllib.request.urlopen(req) as res:
                if res.status == 201:
                    records = json.loads(res.read().decode("utf-8"))
                    uploaded_id = records[0]["id"]
                    print(f"  STATUS: PASSED (Successfully uploaded. Registered ID: {uploaded_id})")
                else:
                    print(f"  STATUS: FAILED (Upload returned status {res.status})")
                    failures += 1
        except Exception as e:
            print(f"  STATUS: FAILED (Error: {str(e)})")
            failures += 1

        print("\nTest Case 4: Querying uploaded images list")
        if uploaded_id:
            try:
                req = urllib.request.Request("http://127.0.0.1:8000/api/images")
                with urllib.request.urlopen(req) as res:
                    list_data = json.loads(res.read().decode("utf-8"))
                    found = any(item["id"] == uploaded_id for item in list_data)
                    if found:
                        print("  STATUS: PASSED")
                    else:
                        print("  STATUS: FAILED (Uploaded image ID not found in registry list)")
                        failures += 1
            except Exception as e:
                print(f"  STATUS: FAILED (Error: {str(e)})")
                failures += 1
        else:
            print("  STATUS: SKIPPED (No uploaded image ID from Case 3)")
            failures += 1

        print("\nTest Case 5: Servicing raw image preview stream")
        if uploaded_id:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:8000/api/images/{uploaded_id}/raw")
                with urllib.request.urlopen(req) as res:
                    if res.status == 200 and len(res.read()) > 0:
                        print("  STATUS: PASSED")
                    else:
                        print("  STATUS: FAILED (Serving returned empty body or status error)")
                        failures += 1
            except Exception as e:
                print(f"  STATUS: FAILED (Error: {str(e)})")
                failures += 1
        else:
            print("  STATUS: SKIPPED")
            failures += 1

        print("\nTest Case 6: Deleting uploaded image")
        if uploaded_id:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:8000/api/images/{uploaded_id}", method="DELETE")
                with urllib.request.urlopen(req) as res:
                    body = json.loads(res.read().decode("utf-8"))
                    if res.status == 200 and "success" in body.get("message", "").lower():

                        req_check = urllib.request.Request("http://127.0.0.1:8000/api/images")
                        with urllib.request.urlopen(req_check) as res_check:
                            list_data = json.loads(res_check.read().decode("utf-8"))
                            still_exists = any(item["id"] == uploaded_id for item in list_data)
                            if not still_exists:
                                print("  STATUS: PASSED (Successfully deleted from disk & db)")
                            else:
                                print("  STATUS: FAILED (File record still present in DB)")
                                failures += 1
                    else:
                        print(f"  STATUS: FAILED (Delete returned: {body})")
                        failures += 1
            except Exception as e:
                print(f"  STATUS: FAILED (Error: {str(e)})")
                failures += 1
        else:
            print("  STATUS: SKIPPED")
            failures += 1

    finally:

        print("\nStopping FastAPI server...")

        try:
            server_proc.terminate()
            server_proc.wait(timeout=5)
        except Exception:
            try:
                server_proc.kill()
            except Exception:
                pass
        print("Server stopped.")

    print("-" * 60)
    if failures == 0:
        print("ALL API TESTS PASSED SUCCESSFULLY!")
    else:
        print(f"{failures} API TEST(S) FAILED.")
    print("=" * 60)
    
    return failures == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
