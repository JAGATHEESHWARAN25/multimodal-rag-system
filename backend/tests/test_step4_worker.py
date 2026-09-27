import pytest
import asyncio
from app.models.database import db_manager
from app.core.background_worker import HardenedBackgroundWorker

def test_stale_job_recovery():
    # Insert a dummy job stuck in PROCESSING
    job_id = db_manager.create_background_job("doc_stale_test")
    db_manager.update_job_status(job_id, "PROCESSING")

    recovered = db_manager.recover_stale_jobs(stale_seconds=0) # Force immediate stale match
    assert recovered >= 1

    queued = db_manager.get_queued_jobs()
    job_ids = [j["id"] for j in queued]
    assert job_id in job_ids

def test_job_cancellation():
    job_id = db_manager.create_background_job("doc_cancel_test")
    success = db_manager.cancel_background_job(job_id)
    assert success is True

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_worker_start_stop():
    worker = HardenedBackgroundWorker(max_concurrent_jobs=1)
    await worker.start()
    assert worker.is_running is True
    await worker.stop()
    assert worker.is_running is False
