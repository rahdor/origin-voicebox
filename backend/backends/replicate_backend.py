"""
Replicate backend for TTS - uses Replicate's GPU infrastructure.
"""

import os
import base64
import httpx
import numpy as np
from typing import Optional, Tuple, List
import tempfile
import soundfile as sf
import io

try:
    import replicate
except ImportError:
    replicate = None


class ReplicateTTSBackend:
    """TTS backend using Replicate's hosted Qwen3-TTS model."""

    MODEL_ID = "qwen/qwen3-tts"

    def __init__(self):
        self._loaded = False
        self._client = None

    async def load_model_async(self, model_size: str = "1.7b") -> None:
        """
        Initialize Replicate client.
        Model runs on Replicate's GPUs, no local loading needed.
        """
        if replicate is None:
            raise ImportError("replicate package not installed. Run: pip install replicate")

        api_token = os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY")
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN or REPLICATE_API_KEY environment variable not set")

        self._client = replicate.Client(api_token=api_token)
        self._loaded = True

    # Alias for compatibility
    load_model = load_model_async

    async def create_voice_prompt(
        self,
        audio_path: str,
        reference_text: str,
        use_cache: bool = True,
    ) -> Tuple[dict, bool]:
        """
        Create voice prompt from reference audio.
        For Replicate, we store the audio as base64 to send with requests.
        """
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }.get(ext, "audio/wav")

        voice_prompt = {
            "audio_base64": audio_base64,
            "audio_mime_type": mime_type,
            "reference_text": reference_text,
            "backend": "replicate",
        }

        return voice_prompt, False

    async def combine_voice_prompts(
        self,
        audio_paths: List[str],
        reference_texts: List[str],
    ) -> Tuple[np.ndarray, str]:
        """Combine multiple voice prompts by concatenating audio."""
        import librosa

        combined_audio = []
        sample_rate = None

        for path in audio_paths:
            audio, sr = librosa.load(path, sr=None)
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=sample_rate)
            combined_audio.append(audio)

        combined = np.concatenate(combined_audio)
        combined_text = " ".join(reference_texts)

        return combined, combined_text

    async def generate(
        self,
        text: str,
        voice_prompt: dict,
        language: str = "en",
        seed: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Generate audio using Replicate's Qwen3-TTS."""
        print(f"DEBUG replicate generate: voice_prompt type={type(voice_prompt)}")
        print(f"DEBUG replicate generate: voice_prompt keys={voice_prompt.keys() if voice_prompt else 'None'}")
        print(f"DEBUG replicate generate: has audio_base64={voice_prompt.get('audio_base64') is not None if voice_prompt else False}")

        if not self._loaded:
            await self.load_model_async()

        # Validate voice_prompt has required audio data
        if not voice_prompt.get("audio_base64"):
            print(f"DEBUG replicate generate: FAILING - audio_base64 value={voice_prompt.get('audio_base64')}")
            raise ValueError("Reference audio is required for voice_clone mode")

        print("DEBUG replicate generate: validation passed, building input_data")

        # Use data URI format for reference audio
        audio_base64 = voice_prompt['audio_base64']
        mime_type = voice_prompt.get("audio_mime_type", "audio/wav")
        ref_audio_uri = f"data:{mime_type};base64,{audio_base64}"
        print(f"DEBUG replicate generate: ref_audio_uri length={len(ref_audio_uri)}")

        input_data = {
            "text": text,
            "mode": "Clone",  # Replicate expects "Clone" not "voice_clone"
            "ref_audio": ref_audio_uri,
        }

        if voice_prompt.get("reference_text"):
            input_data["ref_text"] = voice_prompt["reference_text"]

        if seed is not None:
            input_data["seed"] = seed

        print(f"DEBUG replicate generate: input_data keys={input_data.keys()}")
        print(f"DEBUG replicate generate: mode={input_data['mode']}")
        print(f"DEBUG replicate generate: calling _run_replicate with text={text[:50]}")
        try:
            output = await self._run_replicate(input_data)
            print(f"DEBUG replicate generate: got output type={type(output)}")
            audio_array, sample_rate = await self._download_audio(output)
            print(f"DEBUG replicate generate: download complete, sr={sample_rate}")
        except Exception as e:
            print(f"DEBUG replicate generate: ERROR - {type(e).__name__}: {e}")
            raise

        return audio_array, sample_rate

    async def _run_replicate(self, input_data: dict):
        """Run the model on Replicate."""
        import asyncio

        loop = asyncio.get_event_loop()

        def run_sync():
            return self._client.run(self.MODEL_ID, input=input_data)

        output = await loop.run_in_executor(None, run_sync)
        return output

    async def _download_audio(self, output) -> Tuple[np.ndarray, int]:
        """Download audio from Replicate output URL."""
        if isinstance(output, str):
            audio_url = output
        elif hasattr(output, '__iter__'):
            audio_url = list(output)[0] if output else None
        else:
            audio_url = str(output)

        if not audio_url:
            raise ValueError("No audio URL returned from Replicate")

        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=60.0)
            response.raise_for_status()
            audio_bytes = response.content

        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes))

        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)

        return audio_array.astype(np.float32), sample_rate

    def unload_model(self) -> None:
        """No local model to unload."""
        self._loaded = False
        self._client = None

    def is_loaded(self) -> bool:
        """Check if client is initialized."""
        return self._loaded

    def _get_model_path(self, model_size: str) -> str:
        """Return the Replicate model ID."""
        return self.MODEL_ID


class ReplicateSTTBackend:
    """STT backend using Replicate's Whisper."""

    def __init__(self):
        self._loaded = False

    async def load_model_async(self, model_size: str = "base") -> None:
        self._loaded = True

    # Alias for compatibility
    load_model = load_model_async

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> str:
        """Transcribe audio using Replicate's Whisper."""
        if replicate is None:
            raise ImportError("replicate package not installed")

        api_token = os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY")
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN or REPLICATE_API_KEY not set")

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        client = replicate.Client(api_token=api_token)
        output = client.run(
            "openai/whisper:4d50797290df275329f202e48c76360b3f22b08d28c196cbc54600319435f8d2",
            input={
                "audio": f"data:audio/wav;base64,{audio_base64}",
                "language": language or "en",
            }
        )

        if isinstance(output, dict):
            return output.get("transcription", "")
        return str(output)

    def unload_model(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded
