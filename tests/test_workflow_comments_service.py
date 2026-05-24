import unittest
from unittest.mock import patch

from services import workflow_comments_service as wcs


class WorkflowCommentsServiceTests(unittest.TestCase):
    def setUp(self):
        wcs._MEMORY.clear()
        self._client_patch = patch.object(wcs, "_client", return_value=None)
        self._client_patch.start()

    def tearDown(self):
        self._client_patch.stop()

    def test_add_and_list_in_memory(self):
        row = wcs.add_comment(
            "wf-test-1",
            author_id="user-1",
            author_name="Test User",
            author_role="FINANCE_MANAGER",
            text="Please review line 42.",
        )
        self.assertEqual(row["workflow_id"], "wf-test-1")
        self.assertIn("Please review", row["text"])
        comments = wcs.list_comments("wf-test-1")
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["author_name"], "Test User")


if __name__ == "__main__":
    unittest.main()
