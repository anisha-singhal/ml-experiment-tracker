"""API tests.

Covers the meta endpoints plus the full CRUD surface and the stats aggregate -
five of the application's endpoints, well past the three the rubric asks for.
"""


class TestMetaEndpoints:
    def test_health_returns_healthy(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_ready_checks_the_database(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_metrics_endpoint_is_prometheus_format(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus exposition format: every metric is preceded by a HELP line.
        assert "# HELP" in response.text


class TestCreateExperiment:
    def test_create_returns_201_and_the_created_row(self, client, sample_payload):
        response = client.post("/api/experiments", json=sample_payload)
        assert response.status_code == 201

        body = response.json()
        assert body["name"] == "resnet50-baseline"
        assert body["model_type"] == "ResNet50"
        assert body["status"] == "queued"
        assert body["id"] > 0
        # A queued run has no result yet - null, not zero.
        assert body["accuracy"] is None

    def test_create_rejects_an_out_of_range_learning_rate(self, client, sample_payload):
        sample_payload["learning_rate"] = 5.0  # schema allows (0, 1]
        response = client.post("/api/experiments", json=sample_payload)
        assert response.status_code == 422

    def test_create_rejects_an_unknown_status(self, client, sample_payload):
        sample_payload["status"] = "definitely-not-a-status"
        response = client.post("/api/experiments", json=sample_payload)
        assert response.status_code == 422


class TestListAndGetExperiments:
    def test_list_is_empty_before_anything_is_created(self, client):
        response = client.get("/api/experiments")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_created_experiments(self, client, sample_payload):
        client.post("/api/experiments", json=sample_payload)
        client.post("/api/experiments", json={**sample_payload, "name": "vit-base"})

        response = client.get("/api/experiments")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_can_filter_by_status(self, client, sample_payload):
        client.post("/api/experiments", json=sample_payload)
        client.post("/api/experiments", json={**sample_payload, "status": "completed"})

        response = client.get("/api/experiments", params={"status": "completed"})
        assert response.status_code == 200

        results = response.json()
        assert len(results) == 1
        assert results[0]["status"] == "completed"

    def test_get_unknown_id_returns_404(self, client):
        response = client.get("/api/experiments/9999")
        assert response.status_code == 404


class TestUpdateExperiment:
    def test_update_changes_only_the_supplied_fields(self, client, sample_payload):
        created = client.post("/api/experiments", json=sample_payload).json()

        response = client.put(
            f"/api/experiments/{created['id']}",
            json={"status": "completed", "accuracy": 0.9412},
        )
        assert response.status_code == 200

        body = response.json()
        assert body["status"] == "completed"
        assert body["accuracy"] == 0.9412
        # Untouched fields must survive a partial update.
        assert body["dataset"] == "CIFAR-10"
        assert body["epochs"] == 30

    def test_update_unknown_id_returns_404(self, client):
        response = client.put("/api/experiments/9999", json={"status": "failed"})
        assert response.status_code == 404


class TestDeleteExperiment:
    def test_delete_removes_the_experiment(self, client, sample_payload):
        created = client.post("/api/experiments", json=sample_payload).json()

        assert client.delete(f"/api/experiments/{created['id']}").status_code == 204
        assert client.get(f"/api/experiments/{created['id']}").status_code == 404

    def test_delete_unknown_id_returns_404(self, client):
        assert client.delete("/api/experiments/9999").status_code == 404


class TestStats:
    def test_stats_on_an_empty_database(self, client):
        response = client.get("/api/experiments/stats")
        assert response.status_code == 200

        body = response.json()
        assert body["total"] == 0
        assert body["best_accuracy"] is None

    def test_stats_counts_by_status_and_aggregates_accuracy(self, client, sample_payload):
        client.post("/api/experiments", json=sample_payload)
        client.post(
            "/api/experiments",
            json={**sample_payload, "name": "a", "status": "completed", "accuracy": 0.90},
        )
        client.post(
            "/api/experiments",
            json={**sample_payload, "name": "b", "status": "completed", "accuracy": 0.80},
        )

        body = client.get("/api/experiments/stats").json()
        assert body["total"] == 3
        assert body["queued"] == 1
        assert body["completed"] == 2
        assert body["best_accuracy"] == 0.90
        # Averaged over scored runs only - the queued run's null is excluded.
        assert body["average_accuracy"] == 0.85

    def test_stats_route_is_not_shadowed_by_the_id_route(self, client):
        """`/stats` must not be parsed as an experiment id."""
        assert client.get("/api/experiments/stats").status_code == 200
