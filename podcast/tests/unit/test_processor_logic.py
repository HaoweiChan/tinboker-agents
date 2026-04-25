"""
Unit tests for EpisodeProcessor logic.
"""

from pathlib import Path

import pytest

from src.pipeline import PipelineConfig, PipelineContext, EpisodeProcessor


@pytest.mark.unit
class TestProcessorLogic:
    """Test EpisodeProcessor logic."""
    
    def test_clear_episode_context_clears_all_fields(self, base_config, base_context):
        """Test that _clear_episode_context clears all episode-specific fields."""
        processor = EpisodeProcessor(base_config, base_context)
        
        # Set some values in context
        base_context.episode_data = {'title': 'Test Episode'}
        base_context.episode_id = 'test_id'
        base_context.mp3_path = Path('/tmp/test.mp3')
        base_context.transcript_text = 'Test transcript'
        base_context.transcript_words = [{'word': 'test'}]
        base_context.transcript_sentences = []
        base_context.summary_result = {'summary_text': 'Test summary'}
        base_context.spotify_metadata = {'spotify_id': 'test'}
        base_context.gcs_urls = {'mp3_url': 'gs://test/test.mp3'}
        base_context.podcast_name = 'Test Podcast'
        base_context.language = 'zh'
        base_context.created_time = None
        base_context.tags = ['tag1', 'tag2']
        base_context.tickers = ['AAPL']
        base_context.validation_results = {'test': True}
        
        # Clear context
        processor._clear_episode_context()
        
        # Verify all fields are cleared
        assert base_context.episode_data is None
        assert base_context.episode_id is None
        assert base_context.mp3_path is None
        assert base_context.transcript_text is None
        assert base_context.transcript_words is None
        assert base_context.transcript_sentences is None
        assert base_context.summary_result is None
        assert base_context.spotify_metadata is None
        assert base_context.gcs_urls is None
        assert base_context.podcast_name == ""
        assert base_context.language == "en"
        assert base_context.created_time is None
        assert base_context.tags == []
        assert base_context.tickers == []
        assert base_context.validation_results == {}
        
        # Verify services are preserved
        assert base_context.firebase_service is not None
        assert base_context.gcs_service is not None
        assert base_context.stt_service is not None
        assert base_context.summarize_service is not None
    
    def test_should_skip_episode_normal_mode_not_processed(self, base_config, base_context):
        """Test _should_skip_episode in normal mode when episode is not processed."""
        processor = EpisodeProcessor(base_config, base_context)
        
        # No existing episode
        base_context.episode_id = None
        base_context.gcs_urls = None
        
        episode_data = {'title': 'New Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_normal_mode_fully_processed(self, base_config, base_context):
        """Test _should_skip_episode in normal mode when episode is fully processed."""
        processor = EpisodeProcessor(base_config, base_context)
        
        # Existing episode with all URLs
        base_context.episode_id = 'test_id'
        base_context.gcs_urls = {
            'mp3_url': 'gs://test/test.mp3',
            'transcript_url': 'gs://test/test.json',
            'summary_url': 'gs://test/test.md',
            'summary_image_url': 'gs://test/test.svg'
        }
        
        episode_data = {'title': 'Existing Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is True
    
    def test_should_skip_episode_rerun_from_download(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=download."""
        base_config.rerun_from = "download"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Even if episode exists, should not skip
        base_context.episode_id = 'test_id'
        base_context.gcs_urls = {
            'mp3_url': 'gs://test/test.mp3',
            'transcript_url': 'gs://test/test.json',
            'summary_url': 'gs://test/test.md',
            'summary_image_url': 'gs://test/test.svg'
        }
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_rerun_from_transcribe(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=transcribe."""
        base_config.rerun_from = "transcribe"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Should not skip even if episode exists
        base_context.episode_id = 'test_id'
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_rerun_from_summarize_with_transcript(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=summarize when transcript exists."""
        base_config.rerun_from = "summarize"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Episode exists with transcript
        base_context.episode_id = 'test_id'
        base_context.transcript_text = 'Test transcript'
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_rerun_from_summarize_no_transcript(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=summarize when transcript missing."""
        base_config.rerun_from = "summarize"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Episode exists but no transcript
        base_context.episode_id = 'test_id'
        base_context.transcript_text = None
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is True
    
    def test_should_skip_episode_rerun_from_upload_with_urls(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=upload when URLs exist."""
        base_config.rerun_from = "upload"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Episode exists with URLs
        base_context.episode_id = 'test_id'
        base_context.gcs_urls = {'mp3_url': 'gs://test/test.mp3'}
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_rerun_from_upload_no_urls(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=upload when URLs missing."""
        base_config.rerun_from = "upload"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Episode exists but no URLs
        base_context.episode_id = 'test_id'
        base_context.gcs_urls = None
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is True
    
    def test_should_skip_episode_rerun_from_validate_with_episode(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=validate when episode exists."""
        base_config.rerun_from = "validate"
        processor = EpisodeProcessor(base_config, base_context)
        
        # Episode exists
        base_context.episode_id = 'test_id'
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is False
    
    def test_should_skip_episode_rerun_from_validate_no_episode(self, base_config, base_context):
        """Test _should_skip_episode with rerun_from=validate when episode missing."""
        base_config.rerun_from = "validate"
        processor = EpisodeProcessor(base_config, base_context)
        
        # No episode
        base_context.episode_id = None
        
        episode_data = {'title': 'Episode', 'episodeNumber': 1}
        should_skip = processor._should_skip_episode(episode_data)
        
        assert should_skip is True
    
    def test_load_existing_data_loads_gcs_urls(self, base_config, base_context, sample_firestore_episode):
        """Test that _load_existing_data loads GCS URLs from Firestore."""
        processor = EpisodeProcessor(base_config, base_context)
        
        # Mock Firebase to return existing episode
        base_context.firebase_service.get_episode_by_fields.return_value = sample_firestore_episode
        
        episode_data = {
            'title': sample_firestore_episode['episode_title'],
            'episodeNumber': sample_firestore_episode['episode_number']
        }
        
        processor._load_existing_data(episode_data)
        
        # Verify GCS URLs are loaded
        assert base_context.episode_id == sample_firestore_episode['id']
        assert base_context.gcs_urls is not None
        assert base_context.gcs_urls['mp3_url'] == sample_firestore_episode['mp3_url']
        assert base_context.gcs_urls['transcript_url'] == sample_firestore_episode['transcript_url']
    
    def test_load_existing_data_clears_when_no_episode(self, base_config, base_context):
        """Test that _load_existing_data clears context when no episode found."""
        processor = EpisodeProcessor(base_config, base_context)
        
        # Set some values
        base_context.episode_id = 'old_id'
        base_context.gcs_urls = {'mp3_url': 'gs://old/test.mp3'}
        
        # Mock Firebase to return None
        base_context.firebase_service.get_episode_by_fields.return_value = None
        
        episode_data = {'title': 'New Episode', 'episodeNumber': 1}
        processor._load_existing_data(episode_data)
        
        # Verify context is cleared
        assert base_context.episode_id is None
        assert base_context.gcs_urls is None

