"""
Unit tests for config loading functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from main import load_podcasts_config, create_podcast_config_mapping


@pytest.mark.unit
class TestConfigLoading:
    """Test config file loading."""
    
    def test_load_valid_config(self, sample_podcasts, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / "test_podcasts.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_podcasts, f)
        
        result = load_podcasts_config(config_file)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]['name'] == 'Test Podcast 1'
    
    def test_load_missing_config(self, tmp_path):
        """Test loading a non-existent config file."""
        config_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            load_podcasts_config(config_file)
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading an invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            load_podcasts_config(config_file)
    
    def test_load_non_list_config(self, tmp_path):
        """Test loading a config file that's not a list."""
        config_file = tmp_path / "not_list.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({"not": "a list"}, f)
        
        with pytest.raises(ValueError, match="must contain a list"):
            load_podcasts_config(config_file)
    
    def test_create_podcast_config_mapping(self, sample_podcasts, tmp_path):
        """Test creating podcast config mapping."""
        config_file = tmp_path / "test_podcasts.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_podcasts, f)
        
        mapping = create_podcast_config_mapping(config_file)
        
        assert isinstance(mapping, dict)
        assert 'Test Podcast 1' in mapping
        assert mapping['Test Podcast 1']['transcript_service'] == 'groq'
        assert mapping['Test Podcast 1']['model'] == 'whisper-large-v3'
        assert 'Test Podcast 2' not in mapping  # No transcript_option
        assert 'Test Podcast 3' in mapping
        assert mapping['Test Podcast 3']['transcript_service'] == 'whisper'
    
    def test_create_podcast_config_mapping_missing_file(self, tmp_path):
        """Test creating mapping from non-existent file."""
        config_file = tmp_path / "nonexistent.json"
        
        mapping = create_podcast_config_mapping(config_file)
        assert mapping == {}
    
    def test_transcript_option_parsing(self, sample_podcasts):
        """Test parsing transcript_option from config."""
        podcast1 = sample_podcasts[0]
        assert 'transcript_option' in podcast1
        assert podcast1['transcript_option']['transcript_service'] == 'groq'
        assert podcast1['transcript_option']['model'] == 'whisper-large-v3'
        
        podcast2 = sample_podcasts[1]
        assert 'transcript_option' not in podcast2
        
        podcast3 = sample_podcasts[2]
        assert 'transcript_option' in podcast3
        assert podcast3['transcript_option']['transcript_service'] == 'whisper'
        assert podcast3['transcript_option'].get('model') is None

