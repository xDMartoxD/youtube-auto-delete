"""
Tests de integración para endpoints de health.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests de integración para endpoints de health."""

    def test_health_check_basic(self, client: TestClient):
        """Test del health check básico."""
        # Act
        response = client.get("/api/health/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert data["service"] == "playlistmaster-api"

    def test_health_check_detailed(self, client: TestClient):
        """Test del health check detallado."""
        # Act
        response = client.get("/api/health/health/detailed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "dynamodb" in data["checks"]
        assert "google_api" in data["checks"]

    def test_metrics_endpoint(self, client: TestClient):
        """Test del endpoint de métricas."""
        # Act
        response = client.get("/api/health/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "metrics" in data

    def test_readiness_check(self, client: TestClient):
        """Test del readiness check."""
        # Act
        response = client.get("/api/health/ready")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
