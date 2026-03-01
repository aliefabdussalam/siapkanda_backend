"""
Backend API Tests for Kementerian Transmigrasi Dashboard
Tests: Auth, Directives CRUD, Stats, Values endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login with correct password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "password": "admin123"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        print(f"Login success: {data}")
    
    def test_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("Login correctly rejected invalid password")


class TestStats:
    """Stats endpoint tests"""
    
    def test_get_stats_all(self):
        """Test getting all stats without filters"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_directives" in data
        assert "in_progress" in data
        assert "implemented" in data
        assert "pending" in data
        assert "total_regions" in data
        print(f"Stats: {data}")
    
    def test_get_stats_by_type_kementerian(self):
        """Test getting stats filtered by kementerian type"""
        response = requests.get(f"{BASE_URL}/api/stats", params={"type": "kementerian"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_directives" in data
        print(f"Kementerian stats: {data}")
    
    def test_get_stats_by_type_dapil(self):
        """Test getting stats filtered by dapil type"""
        response = requests.get(f"{BASE_URL}/api/stats", params={"type": "dapil"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_directives" in data
        print(f"Dapil stats: {data}")


class TestDirectives:
    """Directives CRUD tests"""
    
    def test_get_all_directives(self):
        """Test fetching all directives"""
        response = requests.get(f"{BASE_URL}/api/directives")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} directives")
    
    def test_get_directives_by_type_kementerian(self):
        """Test filtering directives by kementerian type"""
        response = requests.get(f"{BASE_URL}/api/directives", params={"type": "kementerian"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # Verify all returned directives have the correct type
        for directive in data:
            assert directive.get("type") == "kementerian"
        print(f"Found {len(data)} kementerian directives")
    
    def test_get_directives_by_type_dapil(self):
        """Test filtering directives by dapil type"""
        response = requests.get(f"{BASE_URL}/api/directives", params={"type": "dapil"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        for directive in data:
            assert directive.get("type") == "dapil"
        print(f"Found {len(data)} dapil directives")
    
    def test_create_directive_and_verify(self):
        """Test creating a new directive and verifying persistence"""
        create_payload = {
            "title": "TEST_Directive_Create",
            "description": "Test description for verification",
            "status": "pending",
            "type": "kementerian",
            "value": "Test Kementerian",
            "region": "Jakarta",
            "start_date": "2026-01-15",
            "end_date": "2026-02-15"
        }
        
        # Create
        response = requests.post(f"{BASE_URL}/api/directives", json=create_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        created = response.json()
        
        assert created["title"] == create_payload["title"]
        assert created["description"] == create_payload["description"]
        assert created["status"] == create_payload["status"]
        assert "id" in created
        
        directive_id = created["id"]
        print(f"Created directive with ID: {directive_id}")
        
        # Verify with GET
        get_response = requests.get(f"{BASE_URL}/api/directives/{directive_id}")
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}: {get_response.text}"
        fetched = get_response.json()
        assert fetched["title"] == create_payload["title"]
        print(f"Verified directive exists: {fetched['title']}")
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/directives/{directive_id}")
        assert delete_response.status_code == 200
        print(f"Cleaned up test directive")
    
    def test_update_directive_status(self):
        """Test updating directive status via PATCH endpoint"""
        # First, create a test directive
        create_payload = {
            "title": "TEST_Status_Update",
            "description": "Test for status update",
            "status": "pending",
            "type": "kementerian",
            "value": "Test Kementerian",
            "region": "Jakarta",
            "start_date": "2026-01-15",
            "end_date": "2026-02-15"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/directives", json=create_payload)
        assert create_response.status_code == 200
        created = create_response.json()
        directive_id = created["id"]
        
        # Update status
        update_response = requests.patch(
            f"{BASE_URL}/api/directives/{directive_id}/status",
            json={"status": "in_progress"}
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        updated = update_response.json()
        assert updated["status"] == "in_progress"
        print(f"Status updated to: {updated['status']}")
        
        # Verify with GET
        get_response = requests.get(f"{BASE_URL}/api/directives/{directive_id}")
        fetched = get_response.json()
        assert fetched["status"] == "in_progress"
        print("Status change verified via GET")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/directives/{directive_id}")
    
    def test_update_directive_full(self):
        """Test full directive update via PUT endpoint"""
        # Create test directive
        create_payload = {
            "title": "TEST_Full_Update",
            "description": "Original description",
            "status": "pending",
            "type": "kementerian",
            "value": "Original Value",
            "region": "Jakarta",
            "start_date": "2026-01-15",
            "end_date": "2026-02-15"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/directives", json=create_payload)
        created = create_response.json()
        directive_id = created["id"]
        
        # Full update
        update_payload = {
            "title": "TEST_Full_Update_Modified",
            "description": "Modified description"
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/directives/{directive_id}",
            json=update_payload
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["title"] == update_payload["title"]
        assert updated["description"] == update_payload["description"]
        print(f"Full update verified: {updated['title']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/directives/{directive_id}")
    
    def test_delete_directive(self):
        """Test deleting a directive"""
        # Create test directive
        create_payload = {
            "title": "TEST_Delete",
            "description": "To be deleted",
            "status": "pending",
            "type": "dapil",
            "value": "Test Dapil",
            "region": "Jakarta",
            "start_date": "2026-01-15",
            "end_date": "2026-02-15"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/directives", json=create_payload)
        created = create_response.json()
        directive_id = created["id"]
        
        # Delete
        delete_response = requests.delete(f"{BASE_URL}/api/directives/{directive_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["success"] == True
        print("Directive deleted successfully")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/directives/{directive_id}")
        assert get_response.status_code == 404
        print("Deletion verified - directive not found")
    
    def test_get_nonexistent_directive(self):
        """Test getting a directive that doesn't exist"""
        response = requests.get(f"{BASE_URL}/api/directives/nonexistent-id-12345")
        assert response.status_code == 404


class TestValues:
    """Values and regions endpoints tests"""
    
    def test_get_values_kementerian(self):
        """Test getting values for kementerian type"""
        response = requests.get(f"{BASE_URL}/api/values", params={"type": "kementerian"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "values" in data
        assert isinstance(data["values"], list)
        print(f"Kementerian values: {data['values']}")
    
    def test_get_values_dapil(self):
        """Test getting values for dapil type"""
        response = requests.get(f"{BASE_URL}/api/values", params={"type": "dapil"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "values" in data
        assert isinstance(data["values"], list)
        print(f"Dapil values: {data['values']}")
    
    def test_get_regions(self):
        """Test getting all regions"""
        response = requests.get(f"{BASE_URL}/api/regions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "regions" in data
        assert isinstance(data["regions"], list)
        print(f"Regions: {data['regions']}")


class TestDirectiveFiltering:
    """Test directive filtering combinations"""
    
    def test_filter_by_status(self):
        """Test filtering directives by status"""
        for status in ["pending", "in_progress", "implemented"]:
            response = requests.get(f"{BASE_URL}/api/directives", params={"status": status})
            assert response.status_code == 200
            data = response.json()
            for directive in data:
                assert directive.get("status") == status
            print(f"Found {len(data)} directives with status '{status}'")
    
    def test_filter_by_type_and_status(self):
        """Test filtering by both type and status"""
        response = requests.get(
            f"{BASE_URL}/api/directives",
            params={"type": "kementerian", "status": "in_progress"}
        )
        assert response.status_code == 200
        data = response.json()
        for directive in data:
            assert directive.get("type") == "kementerian"
            assert directive.get("status") == "in_progress"
        print(f"Found {len(data)} kementerian directives in progress")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
