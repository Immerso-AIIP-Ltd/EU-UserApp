from locust import HttpUser, between, task


class AnalysisUser(HttpUser):
    """User that performs system analysis and monitoring tasks."""

    wait_time = between(1, 5)

    def on_start(self) -> None:
        self.headers = {
            "Content-Type": "application/json",
            "x-api-client": "android_app",
            "x-platform": "android",
            "x-app-version": "1.0.0",
            "x-country": "IN",
            "x-load-test-bypass": "LOAD_TEST_BYPASS_SECRET_123",
        }

    @task(3)
    def check_health(self) -> None:
        """Monitor generic health endpoint."""
        with self.client.get(
            "/user/v1/internal/monitoring/health",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.text}")

    @task(2)
    def check_redis_health(self) -> None:
        """Monitor Redis connectivity health."""
        with self.client.get(
            "/user/v1/internal/monitoring/redis_health",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Redis health check failed: {response.text}")

    @task(1)
    def check_cache_stats(self) -> None:
        """Monitor cache statistics."""
        with self.client.get(
            "/user/v1/internal/redis/cache/stats",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache stats check failed: {response.text}")
