"""Tests for AudioTool."""
import pytest
import os
from unittest.mock import patch

@pytest.mark.asyncio
async def test_audio_tool_wav_generation(tmp_path):
    from backend.tools.audio_tool import AudioTool
    tool = AudioTool()
    
    out_file = tmp_path / "test.wav"
    result = await tool.execute(
        action="generate_tone",
        frequency=440.0,
        duration=0.1,
        output_path=str(out_file)
    )
    
    assert result["success"] is True
    assert os.path.exists(out_file)
    
    # Verify WAV header
    with open(out_file, "rb") as f:
        header = f.read(4)
        assert header == b"RIFF"

@pytest.mark.asyncio
async def test_audio_tool_note_frequency():
    from backend.tools.audio_tool import AudioTool
    tool = AudioTool()
    
    result = await tool.execute(
        action="note_to_freq",
        note="A4"
    )
    assert result["success"] is True
    assert abs(result["frequency"] - 440.0) < 0.1

@pytest.mark.asyncio
async def test_audio_tool_invalid_action():
    from backend.tools.audio_tool import AudioTool
    tool = AudioTool()
    
    result = await tool.execute(action="invalid_action_xyz")
    assert result["success"] is False
