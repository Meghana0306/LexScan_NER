from locust import HttpUser, between, task


class LexScanUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def languages(self):
        self.client.get("/api/languages")

    @task(1)
    def health(self):
        self.client.get("/api/health")
