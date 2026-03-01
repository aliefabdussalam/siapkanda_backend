"""
Backend API Tests for File Attachments Feature
Tests: Upload, retrieve, and verify file attachments on directives
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test file content - a small PNG image (1x1 pixel transparent)
TEST_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
TEST_PNG_BYTES = base64.b64decode(TEST_PNG_BASE64)

# Test PDF content (minimal valid PDF)
TEST_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [] /Count 0 >>
endobj
xref
0 3
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
trailer
<< /Size 3 /Root 1 0 R >>
startxref
111
%%EOF"""


class TestAttachmentUpload:
    """Tests for file attachment upload feature"""
    
    @pytest.fixture(autouse=True)
    def setup_directive(self):
        """Create a test directive for attachment tests"""
        create_payload = {
            "title": "TEST_Attachment_Directive",
            "description": "Test directive for attachment upload",
            "status": "pending",
            "type": "kementerian",
            "value": "Test Kementerian",
            "region": "Jakarta",
            "start_date": "2026-01-15",
            "end_date": "2026-02-15"
        }
        response = requests.post(f"{BASE_URL}/api/directives", json=create_payload)
        assert response.status_code == 200, f"Failed to create test directive: {response.text}"
        self.directive_id = response.json()["id"]
        yield
        # Cleanup after tests
        requests.delete(f"{BASE_URL}/api/directives/{self.directive_id}")
    
    def test_upload_image_attachment(self):
        """Test uploading an image file as attachment"""
        files = {
            'file': ('test_image.png', TEST_PNG_BYTES, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/directives/{self.directive_id}/attachments",
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        print(f"Image upload success: {data}")
        
        # Verify attachment was added
        get_response = requests.get(f"{BASE_URL}/api/directives/{self.directive_id}")
        assert get_response.status_code == 200
        directive = get_response.json()
        
        assert "attachments" in directive
        assert len(directive["attachments"]) == 1
        attachment = directive["attachments"][0]
        assert attachment["filename"] == "test_image.png"
        assert attachment["content_type"] == "image/png"
        assert "data" in attachment
        assert attachment["size"] > 0
        print(f"Verified attachment: {attachment['filename']} ({attachment['size']} bytes)")
    
    def test_upload_pdf_attachment(self):
        """Test uploading a PDF file as attachment"""
        files = {
            'file': ('test_document.pdf', TEST_PDF_BYTES, 'application/pdf')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/directives/{self.directive_id}/attachments",
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] == True
        print(f"PDF upload success: {data}")
        
        # Verify attachment
        get_response = requests.get(f"{BASE_URL}/api/directives/{self.directive_id}")
        directive = get_response.json()
        
        assert len(directive["attachments"]) == 1
        attachment = directive["attachments"][0]
        assert attachment["filename"] == "test_document.pdf"
        assert attachment["content_type"] == "application/pdf"
        print(f"Verified PDF attachment: {attachment['filename']}")
    
    def test_upload_multiple_attachments(self):
        """Test uploading multiple files to the same directive"""
        # Upload first file
        files1 = {'file': ('image1.png', TEST_PNG_BYTES, 'image/png')}
        response1 = requests.post(
            f"{BASE_URL}/api/directives/{self.directive_id}/attachments",
            files=files1
        )
        assert response1.status_code == 200
        
        # Upload second file
        files2 = {'file': ('document.pdf', TEST_PDF_BYTES, 'application/pdf')}
        response2 = requests.post(
            f"{BASE_URL}/api/directives/{self.directive_id}/attachments",
            files=files2
        )
        assert response2.status_code == 200
        
        # Verify both attachments exist
        get_response = requests.get(f"{BASE_URL}/api/directives/{self.directive_id}")
        directive = get_response.json()
        
        assert len(directive["attachments"]) == 2
        filenames = [a["filename"] for a in directive["attachments"]]
        assert "image1.png" in filenames
        assert "document.pdf" in filenames
        print(f"Multiple attachments verified: {filenames}")
    
    def test_upload_to_nonexistent_directive(self):
        """Test uploading attachment to non-existent directive returns 404"""
        files = {'file': ('test.png', TEST_PNG_BYTES, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/api/directives/nonexistent-id-12345/attachments",
            files=files
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for non-existent directive")


class TestExistingAttachments:
    """Tests for verifying existing attachments in database"""
    
    def test_get_directives_with_attachments(self):
        """Test that directives endpoint returns attachments data"""
        response = requests.get(f"{BASE_URL}/api/directives")
        assert response.status_code == 200
        directives = response.json()
        
        # Find directive with attachments
        directives_with_attachments = [d for d in directives if d.get("attachments") and len(d["attachments"]) > 0]
        
        if len(directives_with_attachments) > 0:
            print(f"Found {len(directives_with_attachments)} directive(s) with attachments")
            for d in directives_with_attachments:
                print(f"  - {d['title']}: {len(d['attachments'])} attachment(s)")
                for att in d["attachments"]:
                    assert "filename" in att
                    assert "content_type" in att
                    assert "data" in att
                    assert "size" in att
                    print(f"    * {att['filename']} ({att['content_type']}, {att['size']} bytes)")
        else:
            print("No directives with attachments found in database")
    
    def test_attachment_data_structure(self):
        """Test attachment data structure in directive"""
        response = requests.get(f"{BASE_URL}/api/directives")
        assert response.status_code == 200
        directives = response.json()
        
        for directive in directives:
            if directive.get("attachments"):
                for attachment in directive["attachments"]:
                    # Verify required fields
                    assert "filename" in attachment, f"Missing filename in attachment"
                    assert "content_type" in attachment, f"Missing content_type in attachment"
                    assert "data" in attachment, f"Missing data in attachment"
                    assert "size" in attachment, f"Missing size in attachment"
                    
                    # Verify data is base64 encoded
                    try:
                        decoded = base64.b64decode(attachment["data"])
                        assert len(decoded) > 0
                    except Exception as e:
                        pytest.fail(f"Invalid base64 data in attachment: {e}")
                    
                    print(f"Verified attachment structure: {attachment['filename']}")


class TestSpecificDirectiveWithAttachment:
    """Test the specific directive mentioned as having attachment"""
    
    def test_find_directive_with_test_attachment(self):
        """Find the directive 'Pembangunan Infrastruktur Jalan Tol Trans Jawa' with attachment"""
        response = requests.get(f"{BASE_URL}/api/directives")
        assert response.status_code == 200
        directives = response.json()
        
        # Find the specific directive mentioned in test request
        target_directive = None
        for d in directives:
            if "Pembangunan Infrastruktur" in d.get("title", "") or "Jalan Tol" in d.get("title", ""):
                target_directive = d
                break
        
        if target_directive:
            print(f"Found target directive: {target_directive['title']}")
            if target_directive.get("attachments") and len(target_directive["attachments"]) > 0:
                print(f"  Attachments count: {len(target_directive['attachments'])}")
                for att in target_directive["attachments"]:
                    print(f"  - {att['filename']} ({att['content_type']})")
                    # Verify image attachment
                    if att["content_type"].startswith("image/"):
                        assert len(att["data"]) > 0
                        print(f"    Image data verified ({att['size']} bytes)")
            else:
                print("  No attachments found on this directive")
        else:
            print("Target directive not found - may have different name or not exist")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
