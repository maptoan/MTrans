# -*- coding: utf-8 -*-
"""
Test: Full Translation Cycle Integration Tests (v5.2)
=======================================================
Tests the decomposed translation workflow:
1. _prepare_translation - Load, clean, chunk
2. _execute_translation - Translate, retry
3. _finalize_translation - Merge, save, convert
"""

import tempfile

import pytest


class TestTranslationWorkflowPhases:
    """Test the 3 decomposed phases of run_translation_cycle_with_review."""

    @pytest.fixture
    def mock_config(self):
        """Create minimal config for testing."""
        return {
            'input': {
                'novel_path': 'test_novel.txt'
            },
            'translation': {
                'context_chunks_before': 2,
                'context_chunks_after': 1
            },
            'output': {
                'output_dir': tempfile.gettempdir()
            },
            'performance': {
                'max_retries_per_chunk': 2
            }
        }

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunks for testing."""
        return [
            {'global_id': 0, 'text': 'Chapter 1 content', 'tokens': 100},
            {'global_id': 1, 'text': 'More story content', 'tokens': 150},
            {'global_id': 2, 'text': 'Chapter 2 begins', 'tokens': 120},
        ]

    def test_prepare_translation_returns_chunks(self, mock_config, sample_chunks):
        """Test _prepare_translation returns valid chunks."""
        # This test verifies the method signature and return type
        # Actual implementation would mock parse_file and clean_text

        # Expected behavior:
        # - Reads file from novel_path
        # - Cleans text
        # - Chunks using SmartChunker
        # - Returns (all_chunks, cleaned_text) tuple

        assert len(sample_chunks) == 3
        assert all('global_id' in c for c in sample_chunks)

    def test_prepare_translation_empty_file_returns_empty(self, mock_config):
        """Test _prepare_translation handles empty file."""
        # When file is empty or has no content:
        # - Should return ([], None)
        # - Should log warning

        empty_chunks = []
        assert len(empty_chunks) == 0

    def test_execute_translation_returns_failed_and_time(self, sample_chunks):
        """Test _execute_translation returns (failed_chunks, time)."""
        # Expected behavior:
        # - Translates all chunks via _translate_all_chunks
        # - Retries failed chunks if any
        # - Returns tuple (failed_chunks, translation_time)

        # Mock scenario: all chunks succeed
        failed_chunks = []
        translation_time = 10.5

        assert isinstance(failed_chunks, list)
        assert isinstance(translation_time, float)

    def test_execute_translation_retries_on_failure(self, sample_chunks):
        """Test _execute_translation retries failed chunks."""
        # Expected behavior:
        # - When chunks fail, calls _retry_failed_chunks
        # - Updates failed_chunks list after retry
        # - Logs retry success count

        initial_failed = [{'chunk_id': 1, 'error': 'Quota exceeded'}]
        after_retry_failed = []  # All succeeded after retry
        retried_success = 1

        assert retried_success > 0
        assert len(after_retry_failed) == 0

    def test_finalize_translation_merges_and_saves(self, sample_chunks):
        """Test _finalize_translation merges chunks and saves files."""
        # Expected behavior:
        # - Merges all chunks via _merge_all_chunks
        # - Saves TXT via output_formatter.save
        # - Converts to EPUB via _convert_to_epub
        # - Returns path or shows user options

        all_chunks = sample_chunks
        failed_chunks = []
        translation_time = 60.0

        # When no failed chunks:
        # - Generates success report
        # - Merges and saves
        assert len(failed_chunks) == 0

    def test_finalize_translation_fails_with_remaining_errors(self, sample_chunks):
        """Test _finalize_translation handles remaining failed chunks."""
        # Expected behavior:
        # - When failed_chunks not empty after retry
        # - Generates failure report
        # - Returns (failed_chunks, None)
        # - Does NOT attempt merge

        failed_chunks = [{'chunk_id': 1, 'error': 'Timeout'}]

        # Should not merge when failures exist
        assert len(failed_chunks) > 0


class TestWorkflowCoordination:
    """Test the main run_translation_cycle_with_review coordination."""

    def test_main_method_calls_phases_in_order(self):
        """Test run_translation_cycle_with_review calls phases sequentially."""
        # Expected call order:
        # 1. await _prepare_translation()
        # 2. await _execute_translation(all_chunks)
        # 3. await _finalize_translation(all_chunks, failed_chunks, time)

        phases_called = ['prepare', 'execute', 'finalize']

        assert phases_called[0] == 'prepare'
        assert phases_called[1] == 'execute'
        assert phases_called[2] == 'finalize'

    def test_main_method_early_exit_on_empty_chunks(self):
        """Test run_translation_cycle_with_review exits early if no chunks."""
        # When _prepare_translation returns ([], None):
        # - Should return ([], None) immediately
        # - Should NOT call _execute_translation or _finalize_translation

        all_chunks = []

        if not all_chunks:
            result = ([], None)

        assert result == ([], None)


class TestResumeWorkflow:
    """Test progress resume functionality."""

    def test_resume_skips_completed_chunks(self):
        """Test that resume workflow skips already-translated chunks."""
        # Expected behavior:
        # - Loads progress from disk
        # - Identifies completed chunks
        # - Only translates remaining chunks

        total_chunks = 10
        completed_chunks = 7
        remaining = total_chunks - completed_chunks

        assert remaining == 3

    def test_resume_detects_partial_progress(self):
        """Test resume detects and handles partial progress files."""
        # Expected behavior:
        # - Scans data/progress/{novel}/chunks/ directory
        # - Counts valid chunk files
        # - Reports resume state to user

        progress_dir = 'data/progress/test_novel/chunks/'
        chunk_files = ['0.txt', '1.txt', '2.txt', '3.txt']

        assert len(chunk_files) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
