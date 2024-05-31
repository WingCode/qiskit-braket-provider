"""Tests for AWS Braket job."""

from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from braket.aws.aws_quantum_task import AwsQuantumTask
from qiskit.providers import JobStatus

from qiskit_braket_provider.providers import (
    AmazonBraketTask,
    AWSBraketJob,
    BraketLocalBackend,
    BraketQuantumTask,
)
from qiskit_braket_provider.providers.braket_quantum_task import retry_if_result_none
from tests.providers.mocks import MOCK_LOCAL_QUANTUM_TASK


class TestBraketTask(TestCase):
    """Tests BraketTask."""

    def test_retry_if_result_none(self):
        """Test when result is None"""
        assert retry_if_result_none(None) == True

    def _get_task(self):
        return BraketQuantumTask(
            backend=BraketLocalBackend(name="default"),
            task_id="AwesomeId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK],
            shots=10,
        )

    def test_task(self):
        """Tests task."""
        task = self._get_task()

        self.assertTrue(isinstance(task, BraketQuantumTask))
        self.assertEqual(None, task.submit())
        self.assertEqual(task.shots, 10)

        self.assertEqual(task.status(), JobStatus.DONE)

    def test_result(self):
        """Tests result."""
        task = self._get_task()

        self.assertEqual(task.result().job_id, "AwesomeId")
        self.assertEqual(task.result().results[0].data.counts, {"01": 1, "10": 2})
        self.assertEqual(task.result().results[0].data.memory, ["10", "10", "01"])
        self.assertEqual(task.result().results[0].status, "COMPLETED")
        self.assertEqual(task.result().results[0].shots, 3)
        self.assertEqual(task.result().get_memory(), ["10", "10", "01"])
    
    @patch('qiskit_braket_provider.providers.braket_quantum_task.AwsQuantumTaskBatch._retrieve_results')
    def test_task_result_is_none(self, mock_retrieve_results):
        """Tests result."""
        mock_retrieve_results.return_value = [None, None]

        task = BraketQuantumTask(
            backend=BraketLocalBackend(name="default"),
            task_id="AwesomeId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK, MOCK_LOCAL_QUANTUM_TASK],
            shots=10,
        )
        task.result()

        mock_retrieve_results.assert_called_once()

    def test_queue_position_for_local_quantum_task(self):
        """Tests job status when multiple task status is present."""
        task = BraketQuantumTask(
            backend=BraketLocalBackend(name="default"),
            task_id="MockId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK],
            shots=100,
        )
        message = "We don't provide queue information for the LocalQuantumTask."
        with pytest.raises(NotImplementedError, match=message):
            task.queue_position()


class TestAmazonBraketTask(TestCase):
    """Tests AmazonBraketTask."""

    def _get_task(self):
        return AmazonBraketTask(
            backend=BraketLocalBackend(name="default"),
            task_id="AwesomeId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK],
            shots=10,
        )

    def test_task(self):
        """Tests task."""
        task = self._get_task()

        self.assertTrue(isinstance(task, AmazonBraketTask))
        self.assertEqual(task.shots, 10)

        self.assertEqual(task.status(), JobStatus.DONE)

    def test_result(self):
        """Tests result."""
        task = self._get_task()

        self.assertEqual(task.result().job_id, "AwesomeId")
        self.assertEqual(task.result().results[0].data.counts, {"01": 1, "10": 2})
        self.assertEqual(task.result().results[0].data.memory, ["10", "10", "01"])
        self.assertEqual(task.result().results[0].status, "COMPLETED")
        self.assertEqual(task.result().results[0].shots, 3)
        self.assertEqual(task.result().get_memory(), ["10", "10", "01"])


class TestAWSBraketJob(TestCase):
    """Tests AWSBraketJob"""

    def _get_job(self):
        return AWSBraketJob(
            backend=BraketLocalBackend(name="default"),
            job_id="AwesomeId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK],
            shots=10,
        )

    def test_AWS_job(self):
        """Tests job."""
        job = self._get_job()

        self.assertTrue(isinstance(job, AWSBraketJob))
        self.assertEqual(job.shots, 10)

        self.assertEqual(job.result().job_id, "AwesomeId")
        self.assertEqual(job.status(), JobStatus.DONE)

    def test_AWS_result(self):
        """Tests result."""
        job = self._get_job()

        self.assertEqual(job.result().job_id, "AwesomeId")
        self.assertEqual(job.result().results[0].data.counts, {"01": 1, "10": 2})
        self.assertEqual(job.result().results[0].data.memory, ["10", "10", "01"])
        self.assertEqual(job.result().results[0].status, "COMPLETED")
        self.assertEqual(job.result().results[0].shots, 3)
        self.assertEqual(job.result().get_memory(), ["10", "10", "01"])


class TestBraketJobStatus:
    """Tests for Amazon Braket job status."""

    def _get_mock_aws_quantum_task(self, status: str) -> AwsQuantumTask:
        """
        Creates a mock AwsQuantumTask with the given status.
        Status can be one of "CREATED", "QUEUED", "RUNNING", "COMPLETED",
        "FAILED", "CANCELLING", "CANCELLED"
        """
        task = Mock(spec=AwsQuantumTask)
        task.state.return_value = status
        return task

    @pytest.mark.parametrize(
        "task_states, expected_status",
        [
            (["COMPLETED", "FAILED"], JobStatus.ERROR),
            (["COMPLETED", "CANCELLED"], JobStatus.CANCELLED),
            (["COMPLETED", "COMPLETED"], JobStatus.DONE),
            (["RUNNING", "RUNNING"], JobStatus.RUNNING),
            (["QUEUED", "QUEUED"], JobStatus.QUEUED),
        ],
    )
    def test_status(self, task_states, expected_status):
        """Tests job status when multiple task status is present."""
        job = AWSBraketJob(
            backend=BraketLocalBackend(name="default"),
            job_id="MockId",
            tasks=[MOCK_LOCAL_QUANTUM_TASK],
            shots=100,
        )
        job._tasks = Mock(spec=BraketQuantumTask)
        job._tasks = [self._get_mock_aws_quantum_task(state) for state in task_states]

        assert job.status() == expected_status
