
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server

class TestFileServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name).resolve()

        self.workspace_patch = patch.object(
            server, "WORKSPACE", self.workspace
        )
        self.workspace_patch.start()

    def tearDown(self):
        self.workspace_patch.stop()
        self.temp_dir.cleanup()

    def test_safe_path_allows_workspace_file(self):
        path = server.safe_path("notes.txt")
        self.assertEqual(path, self.workspace / "notes.txt")

    def test_safe_path_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            server.safe_path("../outside.txt")

    def test_write_file_creates_new_file(self):
        result = server.write_file("notes.txt", "Hello!")
        self.assertIn("Successfully wrote file", result)
        self.assertEqual(
            (self.workspace / "notes.txt").read_text(encoding="utf-8"),
            "Hello!",
        )

    def test_write_file_refuses_to_overwrite(self):
        (self.workspace / "notes.txt").write_text(
            "Original", encoding="utf-8"
        )

        result = server.write_file("notes.txt", "Changed")

        self.assertIn("already exists", result)
        self.assertEqual(
            (self.workspace / "notes.txt").read_text(encoding="utf-8"),
            "Original",
        )

    def test_read_file_returns_contents(self):
        (self.workspace / "notes.txt").write_text(
            "Hello!", encoding="utf-8"
        )

        self.assertEqual(server.read_file("notes.txt"), "Hello!")

    def test_edit_file_replaces_unique_text(self):
        (self.workspace / "notes.txt").write_text(
            "Hello world", encoding="utf-8"
        )

        result = server.edit_file("notes.txt", "world", "MCP")

        self.assertIn("Successfully edited file", result)
        self.assertEqual(
            (self.workspace / "notes.txt").read_text(encoding="utf-8"),
            "Hello MCP",
        )

    def test_edit_file_rejects_ambiguous_text(self):
        (self.workspace / "notes.txt").write_text(
            "hello hello", encoding="utf-8"
        )

        result = server.edit_file("notes.txt", "hello", "bye")

        self.assertIn("multiple times", result)

    def test_search_files_finds_matching_text(self):
        (self.workspace / "notes.txt").write_text(
            "Testing the MCP server", encoding="utf-8"
        )

        result = server.search_files("MCP server")

        self.assertIn("notes.txt:1", result)

    def test_repo_map_lists_workspace_files(self):
        (self.workspace / "notes.txt").write_text(
            "Hello!", encoding="utf-8"
        )

        result = server.repo_map()

        self.assertIn("notes.txt", result)

    def test_start_session_creates_handoff(self):
        result = server.start_session("Test cross-session handoff")

        self.assertIn("Session handoff created", result)
        self.assertTrue(
            (self.workspace / "handoffs" / "current_session.md").is_file()
        )

    def test_start_session_refuses_overwrite(self):
        server.start_session("First task")

        result = server.start_session("Second task")

        self.assertIn("already exists", result)

    def test_update_project_state_creates_section(self):
        result = server.update_project_state(
            "Testing", "Automated tests are running."
        )

        self.assertIn("successfully", result.lower())

        state = (
            self.workspace / "handoffs" / "project_state.md"
        ).read_text(encoding="utf-8")

        self.assertIn("## Testing", state)
        self.assertIn("Automated tests are running.", state)

    def test_update_project_state_updates_existing_section(self):
        server.update_project_state("Testing", "First version")
        server.update_project_state("Testing", "Updated version")

        state = (
            self.workspace / "handoffs" / "project_state.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Updated version", state)
        self.assertNotIn("First version", state)

    def test_save_checkpoint_creates_file(self):
        result = server.save_checkpoint(
            "Test task", "Created tests", "Review documentation"
        )

        self.assertIn("Checkpoint saved", result)
        self.assertTrue(
            (self.workspace / "handoffs" / "checkpoint.md").is_file()
        )

    def test_save_checkpoint_refuses_overwrite(self):
        server.save_checkpoint("First task", "Started", "Finish")

        result = server.save_checkpoint(
            "Second task", "More work", "More remaining"
        )

        self.assertIn("already exists", result)

    def test_read_file_missing_file(self):
        result = server.read_file("missing.txt")
        self.assertIn("file not found", result)

    def test_edit_file_text_not_found(self):
        (self.workspace / "notes.txt").write_text(
            "Hello world", encoding="utf-8"
        )

        result = server.edit_file("notes.txt", "goodbye", "MCP")
        self.assertIn("not found", result)

    def test_search_files_rejects_empty_query(self):
        result = server.search_files("   ")
        self.assertIn("cannot be empty", result)

    def test_start_session_rejects_empty_task(self):
        result = server.start_session("   ")
        self.assertIn("cannot be empty", result)

    def test_update_project_state_rejects_empty_section(self):
        result = server.update_project_state("", "Some content")
        self.assertIn("cannot be empty", result)

    def test_update_project_state_does_not_match_partial_heading(self):
        server.update_project_state("Testing", "Keep this content")
        server.update_project_state("Test", "Separate section")

        state = (
            self.workspace / "handoffs" / "project_state.md"
        ).read_text(encoding="utf-8")

        self.assertIn("## Testing\nKeep this content", state)
        self.assertIn("## Test\nSeparate section", state)

if __name__ == "__main__":
    unittest.main()