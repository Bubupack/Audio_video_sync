"""Audio-video synchronization: align video motion peaks with audio peaks.

Usage:
    python main.py --audio music.mp3 --video clip.mp4 [--output-dir output]
"""
import argparse
import logging
import sys
from pathlib import Path

from audio_analysis import get_audio_peaks
from config import AppConfig
from media_info import get_media_info
from renderer import generate_final_video
from utils import validate_input_file, sanitize_filename, get_unique_output_path
from video_analysis import get_video_pics

logger = logging.getLogger(__name__)

VALID_AUDIO_EXTS = {".mp3", ".wav", ".flac"}
VALID_VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Synchronize video motion peaks with audio peaks."
    )
    parser.add_argument("--audio", required=True, type=Path, help="Path to audio file (mp3, wav, flac).")
    parser.add_argument("--video", required=True, type=Path, help="Path to video file (mp4, avi, mkv, mov).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where the final MKV is written (created if missing).",
    )
    return parser.parse_args(argv)


def configure_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_pipeline(args: argparse.Namespace) -> Path:
    """Execute the full synchronization pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Path to the generated output file.
    """
    validate_input_file(args.audio, VALID_AUDIO_EXTS, "audio")
    validate_input_file(args.video, VALID_VIDEO_EXTS, "video")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = AppConfig(output_dir=args.output_dir)

    logger.info("Loading media information...")
    media = get_media_info(args.audio, args.video, config)

    ratio = (
        media.video_duration_ms / media.audio_duration_ms
        if media.audio_duration_ms > 0
        else 1
    )
    config.video.min_distance_ms = max(100, min(int(config.audio.min_distance_ms * ratio), 2000))

    logger.info("Analyzing audio...")
    audio_peaks = get_audio_peaks(media.audio_samples, media.sample_rate, config.audio)
    target_count = len(audio_peaks)

    logger.info("Analyzing video motion...")
    video_peaks = get_video_pics(
        args.video, media.frame_count, media.fps, target_count, config.video
    )

    # --- NOUVELLE LOGIQUE DE NOMMAGE SÉCURISÉE ---
    raw_stem = f"{args.video.stem}_sync_{args.audio.stem}"
    safe_stem = sanitize_filename(raw_stem)
    
    output_path = get_unique_output_path(
        directory=args.output_dir,
        stem=safe_stem,
        suffix=f".{config.render.container}"
    )
    # ---------------------------------------------

    generate_final_video(
        args.video,
        args.audio,
        audio_peaks,
        video_peaks,
        media.audio_duration_ms,
        media.video_duration_ms,
        media.fps,
        media.frame_count,
        output_path,
        config.render,
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    """Program entry point.

    Returns:
        Process exit code (0 on success, non-zero on error).
    """
    configure_logging()
    args = parse_args(argv)
    try:
        output = run_pipeline(args)
        logger.info("Final video saved at: %s", output.resolve())
        return 0
    except FileNotFoundError as e:
        logger.error("Input file error: %s", e)
        return 2
    except ValueError as e:
        logger.error("Validation error: %s", e)
        return 3
    except BrokenPipeError as e:
        logger.error("Pipe error: %s", e)
        return 4
    except RuntimeError as e:
        logger.error("Processing error: %s", e)
        return 5
    except Exception as e:  # noqa: BLE001 — top-level safety net
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())