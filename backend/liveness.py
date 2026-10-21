"""Server-side Anti-Spoofing and Liveness Verification Engine (Phase 9 R11).

Provides multi-domain forensic checks on face thumbnails/crops:
1. Color dynamic range & chrominance std in HSV and YCrCb (catches monochrome & paper print attacks).
2. 2D Fourier power spectral analysis (catches screen display moiré patterns and halftone print dots).
3. Specular glare & reflection patches in HSV value channel (catches glass screens and glossy print reflection).
4. Spatial texture sharpness & Laplacian variance (catches flat / out-of-focus paper reproductions).
5. Cross-checks client-reported edge liveness scores against server-side analysis to detect edge bypass attempts.
"""

import base64
import logging
from typing import Optional, Tuple
import cv2
import numpy as np
from config import settings

logger = logging.getLogger(__name__)


def decode_image_b64(img_b64: Optional[str]) -> Optional[np.ndarray]:
    """Decode raw or data-URI base64 string to BGR OpenCV image."""
    if not img_b64:
        return None
    try:
        raw_str = img_b64
        if "base64," in raw_str:
            raw_str = raw_str.split("base64,", 1)[1]
        img_bytes = base64.b64decode(raw_str.strip())
        if len(img_bytes) < 16:
            return None
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as exc:
        logger.debug("Failed to decode base64 face image: %s", exc)
        return None


def verify_server_liveness_and_image(
    img_b64: Optional[str],
    edge_liveness_score: float = 0.0,
) -> Tuple[float, bool, str, Optional[np.ndarray]]:
    """
    Verify liveness on the server side using the face image.
    
    Returns:
        (final_liveness_score: float, is_spoof: bool, reason: str, decoded_image: Optional[np.ndarray])
    """
    threshold = getattr(settings, "liveness_alert_threshold", 0.45)
    edge_score = float(edge_liveness_score or 0.0)

    bgr = decode_image_b64(img_b64)
    if bgr is None or bgr.size == 0 or bgr.shape[0] < 8 or bgr.shape[1] < 8:
        # No image available for server-side verification: fall back to edge score
        is_spoof = (0.0 < edge_score < threshold)
        reason = f"Edge liveness below threshold ({edge_score:.2f} < {threshold:.2f})" if is_spoof else ""
        return edge_score, is_spoof, reason, None

    try:
        # 1. Color Dynamic Range & Chroma in YCrCb and HSV
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        cr = ycrcb[:, :, 1]
        cb = ycrcb[:, :, 2]
        cr_std = float(np.std(cr))
        cb_std = float(np.std(cb))

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        s_chan = hsv[:, :, 1]
        v_chan = hsv[:, :, 2]
        s_std = float(np.std(s_chan))
        s_mean = float(np.mean(s_chan))

        # Check for monochrome print or severely desaturated paper copy
        is_monochrome = (cr_std < 2.5 and cb_std < 2.5) or (s_std < 6.0 and s_mean < 25.0)
        if is_monochrome:
            chroma_score = 0.08
        else:
            chroma_score = float(np.clip((cr_std + cb_std + s_std) / 45.0, 0.15, 1.0))

        # 2. High-Frequency Fourier Spectral Analysis (Screen Moiré / Halftone Grid)
        # Periodic display pixel grids and print halftones create strong delta-harmonic spikes
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        f = np.fft.fft2(small_gray)
        fshift = np.fft.fftshift(f)
        mag_spectrum = np.log(np.abs(fshift) + 1.0)

        # High-frequency region (distance > 12 from DC center at 32, 32)
        cy, cx = 32, 32
        y, x = np.ogrid[:64, :64]
        dist_from_center = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        hf_mask = dist_from_center > 12
        hf_vals = mag_spectrum[hf_mask]
        hf_mean = float(np.mean(hf_vals)) + 1e-6
        hf_max = float(np.max(hf_vals))
        peak_to_mean = hf_max / hf_mean

        # Periodic screen grids produce sharp harmonic spikes (peak_to_mean >= 5.0)
        has_moire = peak_to_mean >= 5.5
        if has_moire:
            moire_score = max(0.08, 1.0 - (peak_to_mean / 20.0))
        else:
            moire_score = min(1.0, max(0.5, 1.0 - (peak_to_mean / 10.0)))

        # 3. Specular Glare / Reflection Highlights (Screen glass or glossy photo sheen)
        glare_pixels = int(np.sum(v_chan >= 252))
        total_pixels = v_chan.size
        glare_fraction = glare_pixels / float(total_pixels)
        has_glare = glare_fraction > 0.05
        if has_glare:
            glare_score = max(0.10, 1.0 - (glare_fraction * 12.0))
        else:
            glare_score = 1.0

        # 4. Texture Sharpness & Flatness (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_flat = lap_var < 8.0
        if is_flat:
            # Overly flat or heavily blurred paper reproduction
            texture_score = max(0.08, lap_var / 25.0)
        else:
            texture_score = min(1.0, lap_var / 60.0)

        # Composite Server Liveness Score
        server_score = round(
            float(
                np.clip(
                    (chroma_score * 0.35)
                    + (moire_score * 0.35)
                    + (glare_score * 0.15)
                    + (texture_score * 0.15),
                    0.0,
                    1.0,
                )
            ),
            3,
        )

        # 5. Client vs Server Cross-Verification
        is_spoof = False
        reasons = []

        if is_monochrome:
            reasons.append("Monochrome or low-saturation paper printout detected")

        if has_moire:
            reasons.append(f"Screen moiré / halftone grid harmonic detected (ratio: {peak_to_mean:.1f})")

        if has_glare:
            reasons.append(f"Specular screen/paper glare reflection detected ({glare_fraction*100:.1f}% pixels)")

        if is_flat:
            reasons.append(f"Flat/textureless printed medium detected (variance: {lap_var:.1f})")

        # Edge vs Server Mismatch Detection
        if edge_score > 0.65 and server_score < 0.38:
            reasons.append(
                f"Client-server liveness mismatch: Edge reported {edge_score:.2f} but server detected spoof artifacts ({server_score:.2f})"
            )
            final_score = server_score
        elif edge_score > 0.0:
            final_score = round(min(edge_score, server_score), 3)
        else:
            final_score = server_score

        if reasons or final_score < threshold:
            is_spoof = True
            # Adjust score downwards if spoofing artifacts detected
            final_score = min(final_score, 0.28)

        reason_str = "; ".join(reasons) if reasons else (
            f"Liveness score below threshold ({final_score:.2f} < {threshold:.2f})" if is_spoof else ""
        )

        return final_score, is_spoof, reason_str, bgr

    except Exception as exc:
        logger.warning("Error during server liveness analysis: %s", exc)
        is_spoof = (0.0 < edge_score < threshold)
        return edge_score, is_spoof, f"Liveness error: {exc}", bgr


def verify_server_liveness(
    img_b64: Optional[str],
    edge_liveness_score: float = 0.0,
) -> Tuple[float, bool, str]:
    """Convenience wrapper returning (final_score, is_spoof, reason)."""
    score, is_spoof, reason, _ = verify_server_liveness_and_image(img_b64, edge_liveness_score)
    return score, is_spoof, reason


def compute_server_face_quality(bgr: np.ndarray, confidence: float = 50.0) -> float:
    """
    Compute aggregate face quality (0-100) from decoded face crop and detection confidence.
    """
    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        size = float(min(h, w))
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        lum = float(np.mean(gray))
        contrast = float(np.std(gray))

        s_size = min(100.0, max(0.0, (size - 16) / 96.0 * 100.0))
        s_conf = min(100.0, max(0.0, float(confidence or 50.0)))
        s_sharp = min(100.0, max(0.0, lap_var / 3.0))

        if 50 <= lum <= 190:
            s_lum = 100.0
        else:
            dist = min(abs(lum - 50), abs(lum - 190))
            s_lum = max(0.0, 100.0 - (dist * 1.5))
        s_contrast = min(100.0, max(0.0, contrast * 2.2))

        quality = (
            (s_size * 0.20)
            + (s_conf * 0.25)
            + (s_sharp * 0.25)
            + (s_lum * 0.15)
            + (s_contrast * 0.15)
        )
        return round(float(np.clip(quality, 0.0, 100.0)), 1)
    except Exception:
        return round(float(confidence or 50.0), 1)
