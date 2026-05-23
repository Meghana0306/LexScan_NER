from services.job_queue import job_queue


def test_job_queue_runs_job():
    job_queue.reset()

    def work(value):
        return {"value": value, "ok": True}

    record = job_queue.submit(work, value=42)
    for _ in range(100):
        current = job_queue.get(record.job_id)
        if current and current.status in {"succeeded", "failed"}:
            break
    current = job_queue.get(record.job_id)
    assert current is not None
    assert current.status == "succeeded"
    assert current.result == {"value": 42, "ok": True}
    job_queue.reset()
