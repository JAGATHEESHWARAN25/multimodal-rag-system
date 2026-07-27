import unittest
import sys
import subprocess
import time
import urllib.request
import json
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from app.core.text_clean import OCRTextCleaner
from app.core.chunking import RecursiveTextSplitter, package_document_chunks

class TestTextCleaningAndChunking(unittest.TestCase):
    
    def test_hyphen_reassembly(self):
        text = "This is an im-\nplementation of offline retrieval-augmented generation."
        expected = "This is an implementation of offline retrieval-augmented generation."
        self.assertEqual(OCRTextCleaner.reassemble_hyphenated_words(text), expected)

    def test_junk_characters_removal(self):
        text = "Name | : John Smith _ \nDate ~ : 2026-07-12 \\"
        # Non-printable characters and solitary pipes/underscores should be removed
        cleaned = OCRTextCleaner.remove_junk_characters(text)
        self.assertNotIn("|", cleaned)
        self.assertNotIn("_", cleaned)
        self.assertIn("Name", cleaned)
        self.assertIn("John Smith", cleaned)

    def test_whitespace_normalization(self):
        text = "Hello\t\t   World!   This    is a   test.\n\n\n\nParagraph 2"
        cleaned = OCRTextCleaner.normalize_whitespaces(text)
        self.assertEqual(cleaned, "Hello World! This is a test.\n\nParagraph 2")

    def test_recursive_splitter_boundaries(self):
        # Generate text of 1200 characters with paragraphs
        paragraphs = ["Paragraph number one with text. " * 5, "Paragraph number two with text. " * 5, "Paragraph number three with text. " * 5]
        text = "\n\n".join(paragraphs)
        
        splitter = RecursiveTextSplitter(chunk_size=300, chunk_overlap=30)
        chunks = splitter.split_text(text)
        
        self.assertTrue(len(chunks) > 1)
        for i, chunk in enumerate(chunks):
            self.assertTrue(len(chunk) <= 300, f"Chunk {i} size {len(chunk)} exceeds limit 300")
            if i > 0:
                # Check overlap: some characters from previous chunk should be in the current one
                prev_end = chunks[i-1][-15:]
                curr_start = chunk[:50]
                # Try finding some common words
                words = [w for w in prev_end.split() if len(w) > 4]
                if words:
                    self.assertTrue(any(w in curr_start for w in words), f"Chunk overlap boundary missing between chunk {i-1} and {i}")

def encode_multipart_formdata(files):
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

def run_integration_api_test():
    print("\n" + "=" * 60)
    print("STARTING INTEGRATION API TESTS FOR TEXT CHUNKING")
    print("=" * 60)
    
    # 1. Start server
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
        return False
        
    failures = 0
    uploaded_id = None
    
    try:
        # Ingest image
        print("\nTest Case 1: Uploading a document image")
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        body, headers = encode_multipart_formdata([("chunk_test.png", dummy_png, "image/png")])
        req = urllib.request.Request("http://127.0.0.1:8000/api/upload", data=body, headers=headers, method="POST")
        
        with urllib.request.urlopen(req) as res:
            if res.status == 201:
                records = json.loads(res.read().decode("utf-8"))
                uploaded_id = records[0]["id"]
                print(f"  STATUS: PASSED (Uploaded ID: {uploaded_id})")
            else:
                print(f"  STATUS: FAILED (Returned status {res.status})")
                failures += 1
                
        # Trigger OCR (which will fail because of missing Tesseract, but will transition to Failed)
        # Note: If status is 'Failed', we can test that requesting /chunks returns a 400 Bad Request
        # which validates that chunks are only served for Completed records!
        print("\nTest Case 2: Triggering OCR pipeline (expected failure state)")
        if uploaded_id:
            req_ocr = urllib.request.Request(f"http://127.0.0.1:8000/api/images/{uploaded_id}/ocr", method="POST")
            with urllib.request.urlopen(req_ocr) as res:
                print("  STATUS: PASSED (OCR triggered successfully)")
            
            # Poll status to change to 'Failed'
            for _ in range(10):
                time.sleep(1)
                req_chk = urllib.request.Request("http://127.0.0.1:8000/api/images")
                with urllib.request.urlopen(req_chk) as res_chk:
                    list_data = json.loads(res_chk.read().decode("utf-8"))
                    record = next((item for item in list_data if item["id"] == uploaded_id), None)
                    if record and record["status"] in ("Completed", "Failed"):
                        break
                        
        # Test Case 3: Verify /chunks rejection for non-Completed status
        print("\nTest Case 3: Requesting chunks for non-Completed document")
        if uploaded_id:
            try:
                req_chunks = urllib.request.Request(f"http://127.0.0.1:8000/api/images/{uploaded_id}/ocr/chunks")
                with urllib.request.urlopen(req_chunks) as res:
                    print("  STATUS: FAILED (Server returned chunks for a Failed document!)")
                    failures += 1
            except urllib.error.HTTPError as e:
                if e.code == 400:
                    err_msg = json.loads(e.read().decode("utf-8")).get("detail", "")
                    print(f"  STATUS: PASSED (Rejection code 400 returned: '{err_msg}')")
                else:
                    print(f"  STATUS: FAILED (Server returned status {e.code} instead of 400)")
                    failures += 1
                    
        # Cleanup
        if uploaded_id:
            req_del = urllib.request.Request(f"http://127.0.0.1:8000/api/images/{uploaded_id}", method="DELETE")
            with urllib.request.urlopen(req_del) as res:
                pass
                
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
        
    return failures == 0

if __name__ == "__main__":
    # 1. Run unit tests
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTextCleaningAndChunking)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    unit_ok = result.wasSuccessful()
    
    # 2. Run integration API tests
    integration_ok = run_integration_api_test()
    
    sys.exit(0 if (unit_ok and integration_ok) else 1)
