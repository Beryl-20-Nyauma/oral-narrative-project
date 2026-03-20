# Test Fixtures

This directory contains test fixtures for manual and integration testing.

## Generating Fixtures

Run the generation script:

```bash
cd backend
python tests/fixtures/generate_fixtures.py
```

This creates:
- `sample.wav` - 5 second sine wave audio (440Hz)
- `silent.wav` - 5 second silent audio
- `short.wav` - 1 second audio
- `no_face.mp4` - 5 second video without a face

## Adding Your Own Fixtures

For realistic testing, add:

| File | Description | Size |
|------|-------------|------|
| `sample_with_face.mp4` | 5-10 sec video with clear face | < 5 MB |
| `speech.wav` | Audio with actual speech | < 1 MB |

## Usage in Tests

```python
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_with_real_audio():
    audio_path = FIXTURES_DIR / "sample.wav"
    if audio_path.exists():
        result = analyze_audio_features(str(audio_path))
        assert result is not None
```

## Note

Unit tests use mocks and don't require these fixtures.
Fixtures are for manual testing and integration verification.
