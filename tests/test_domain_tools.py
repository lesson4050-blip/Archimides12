"""
Tests for the 3 domain expansion tools:
  - AudioSynthTool  (offline, pure stdlib)
  - BioTool         (mocked HTTP)
  - FinanceTool     (mocked HTTP)
"""
import os
import wave
import struct
import tempfile
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ═════════════════════════════════════════════════════════════════════
# AudioSynthTool — full offline tests (no network, no mocks needed)
# ═════════════════════════════════════════════════════════════════════

from backend.tools.audio_synth_tool import (
    AudioSynthTool, _note_to_freq, _waveform, _adsr, _to_wav,
)


class TestNoteToFreq:
    def test_a4_is_440(self):
        assert abs(_note_to_freq("A4") - 440.0) < 0.01

    def test_a5_is_880(self):
        assert abs(_note_to_freq("A5") - 880.0) < 0.01

    def test_middle_c(self):
        assert abs(_note_to_freq("C4") - 261.63) < 0.1

    def test_sharp_note(self):
        f = _note_to_freq("C#4")
        assert 270 < f < 280  # C#4 ≈ 277.18

    def test_flat_alias(self):
        assert abs(_note_to_freq("Bb3") - _note_to_freq("A#3")) < 0.001

    def test_rest_is_zero(self):
        assert _note_to_freq("R") == 0.0
        assert _note_to_freq("") == 0.0

    def test_invalid_note_raises(self):
        with pytest.raises(ValueError):
            _note_to_freq("X9")


class TestWaveform:
    def test_sine_zero_at_zero(self):
        assert abs(_waveform(440, 0.0, "sine")) < 0.001

    def test_square_is_binary(self):
        for t in [0.0001, 0.0005, 0.001, 0.002]:
            v = _waveform(440, t, "square")
            assert v in (1.0, -1.0)

    def test_sawtooth_range(self):
        for t in [0.0, 0.0005, 0.001]:
            v = _waveform(440, t, "sawtooth")
            assert -1.0 <= v <= 1.0

    def test_triangle_range(self):
        for t in [0.0, 0.0005, 0.001]:
            v = _waveform(440, t, "triangle")
            assert -1.0 <= v <= 1.0

    def test_zero_freq_is_silent(self):
        assert _waveform(0, 0.5, "sine") == 0.0


class TestADSR:
    def test_attack_starts_at_zero(self):
        assert _adsr(0, 44100, 44100) == 0.0

    def test_sustain_level(self):
        # Well into sustain phase (middle of 1 second)
        v = _adsr(22050, 44100, 44100, a=0.01, d=0.05, s_level=0.7, r=0.05)
        assert abs(v - 0.7) < 0.05

    def test_release_decays(self):
        # Last sample should be near zero
        v = _adsr(44099, 44100, 44100, r=0.05)
        assert v < 0.1


class TestToWav:
    def test_produces_valid_wav(self):
        samples = [0.0] * 100
        data = _to_wav(samples, 44100)
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"

    def test_correct_params(self):
        samples = [0.5, -0.5] * 1000
        data = _to_wav(samples, 22050)
        # Parse with stdlib to verify
        import io
        with wave.open(io.BytesIO(data), "rb") as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            assert w.getframerate() == 22050
            assert w.getnframes() == 2000

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _to_wav([], 44100)


class TestAudioSynthTool:
    @pytest.fixture
    def tool(self):
        return AudioSynthTool()

    @pytest.fixture
    def tmp_path_wav(self, tmp_path):
        return str(tmp_path / "test.wav")

    @pytest.mark.asyncio
    async def test_tone_creates_wav(self, tool, tmp_path_wav):
        result = await tool.execute(
            action="tone", frequency=440, duration=0.1,
            waveform="sine", output_path=tmp_path_wav,
        )
        assert result["success"] is True
        assert os.path.exists(tmp_path_wav)
        with wave.open(tmp_path_wav, "rb") as w:
            assert w.getframerate() == 44100
            assert w.getnchannels() == 1

    @pytest.mark.asyncio
    async def test_tone_bad_frequency(self, tool):
        result = await tool.execute(action="tone", frequency=-10)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_melody_default(self, tool, tmp_path_wav):
        result = await tool.execute(
            action="melody", output_path=tmp_path_wav,
        )
        assert result["success"] is True
        assert os.path.exists(tmp_path_wav)

    @pytest.mark.asyncio
    async def test_melody_custom(self, tool, tmp_path_wav):
        result = await tool.execute(
            action="melody",
            notes=[
                {"note": "C4", "duration": 0.1},
                {"note": "R", "duration": 0.05},
                {"note": "E4", "duration": 0.1},
            ],
            output_path=tmp_path_wav,
        )
        assert result["success"] is True
        assert "C4" in result["output"]

    @pytest.mark.asyncio
    async def test_chord(self, tool, tmp_path_wav):
        result = await tool.execute(
            action="chord",
            notes=[{"note": "C4"}, {"note": "E4"}, {"note": "G4"}],
            duration=0.2,
            output_path=tmp_path_wav,
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_dtmf(self, tool, tmp_path_wav):
        result = await tool.execute(
            action="dtmf", digits="123#",
            output_path=tmp_path_wav,
        )
        assert result["success"] is True
        assert "123#" in result["output"]

    @pytest.mark.asyncio
    async def test_dtmf_no_digits(self, tool):
        result = await tool.execute(action="dtmf", digits="")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_note_freq(self, tool):
        result = await tool.execute(action="note_freq")
        assert result["success"] is True
        assert "440" in result["output"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute(action="nope")
        assert result["success"] is False


# ═════════════════════════════════════════════════════════════════════
# BioTool — mocked HTTP (no real network calls in CI)
# ═════════════════════════════════════════════════════════════════════

from backend.tools.bio_tool import BioTool

MOCK_UNIPROT_RESPONSE = {
    "primaryAccession": "P04637",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 393, "molWeight": 43653},
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Acts as a tumor suppressor in many tumor types."}],
        }
    ],
}


class TestBioTool:
    @pytest.fixture
    def tool(self):
        return BioTool()

    @pytest.mark.asyncio
    async def test_protein_info_missing_id(self, tool):
        result = await tool.execute(action="protein_info")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_protein_info_mocked(self, tool):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=MOCK_UNIPROT_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(action="protein_info", identifier="P04637")

        assert result["success"] is True
        assert "p53" in result["output"]
        assert "TP53" in result["output"]
        assert "393" in result["output"]

    @pytest.mark.asyncio
    async def test_alphafold_missing_id(self, tool):
        result = await tool.execute(action="alphafold")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_compound_missing_args(self, tool):
        result = await tool.execute(action="compound")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute(action="nope")
        assert result["success"] is False


# ═════════════════════════════════════════════════════════════════════
# FinanceTool — mocked HTTP
# ═════════════════════════════════════════════════════════════════════

from backend.tools.finance_tool import FinanceTool

MOCK_COINGECKO_RESPONSE = [
    {
        "name": "Bitcoin",
        "symbol": "btc",
        "current_price": 67000.42,
        "price_change_percentage_24h": 2.5,
        "price_change_percentage_1h_in_currency": 0.3,
        "price_change_percentage_7d_in_currency": -1.2,
        "market_cap": 1300000000000,
        "total_volume": 25000000000,
        "high_24h": 68000,
        "low_24h": 65500,
        "ath": 73000,
        "ath_change_percentage": -8.2,
        "market_cap_rank": 1,
    }
]

MOCK_FNG_RESPONSE = {
    "data": [
        {"value": "25", "value_classification": "Extreme Fear", "timestamp": "1714100000"},
        {"value": "30", "value_classification": "Fear", "timestamp": "1714013600"},
    ]
}


class TestFinanceTool:
    @pytest.fixture
    def tool(self):
        return FinanceTool()

    @pytest.mark.asyncio
    async def test_crypto_mocked(self, tool):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=MOCK_COINGECKO_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(action="crypto", symbol="bitcoin")

        assert result["success"] is True
        assert "Bitcoin" in result["output"]
        assert "67" in result["output"]  # price contains 67xxx

    @pytest.mark.asyncio
    async def test_crypto_not_found(self, tool):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=[])

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(action="crypto", symbol="notacoin")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_fear_greed_mocked(self, tool):
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=MOCK_FNG_RESPONSE)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool.execute(action="fear_greed")

        assert result["success"] is True
        assert "Fear" in result["output"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute(action="nope")
        assert result["success"] is False
