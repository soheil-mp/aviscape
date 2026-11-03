# aviscape-dsp

Deterministic soundscape signal processing: spectrograms, acoustic indices, signal QA.

Part of [aviscape](../../README.md). See the [roadmap](../../ROADMAP.md) for what is planned.

## What is in it

| Module | Provides |
| :-- | :-- |
| `aviscape_dsp.audio` | `prepare()`: any PCM to a mono float64 `AudioFrame` at 22.05 kHz without DC offset |
| `aviscape_dsp.spectrum` | `spectrogram()`: one-sided PSD per frame (Hann, 512 samples, Parseval-preserving) |
| `aviscape_dsp.levels` | `rms()` and `rms_dbfs()` (AES17 dBFS) |
| `aviscape_dsp.qa` | Signal quality: clipping ratio, DC offset, peak and RMS dBFS, crest factor, digital silence, dropouts; `assess()` computes them all |
| `aviscape_dsp.noise` | Background noise per frequency bin from the histogram mode (Towsey, 2017) and the envelope SNR |
| `aviscape_dsp.indices` | `ndsi()` (Kasten et al., 2012); `temporal_entropy()`, `spectral_entropy()` and `acoustic_entropy()` (Sueur et al., 2008) |

```python
import numpy as np
from aviscape_dsp import ndsi, prepare, spectrogram

pcm = (np.random.default_rng(1).normal(0, 0.1, (48_000 * 5, 2)) * 32767).astype(np.int16)
frame = prepare(pcm, 48_000)  # stereo int16 at 48 kHz -> mono float64 at 22.05 kHz
print(ndsi(spectrogram(frame.samples, frame.sample_rate)))
```
