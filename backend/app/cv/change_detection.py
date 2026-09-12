"""Phase 11 (docs/BUILD-PLAN.md 7.11): differencing/thresholding change
detection — TRD §4/§7.11's stated baseline (a Siamese U-Net is explicitly
named stretch scope, not attempted here).

Real, not built: sourcing an actual before/after Sentinel-2 pair needs
Copernicus/Sentinel Hub credentials this session doesn't have — the same
class of constraint as Phase 3's GSI/IMD data and Phase 7's OSRM binary.
Rather than skip the CV work entirely, this generates one curated
synthetic before/after pair (a base terrain texture, then the same
texture with an added high-reflectance patch simulating a landslide
scar) and runs the *real* pipeline against it: real OpenCV differencing,
Otsu thresholding, contour extraction, and pixel-to-geographic coordinate
conversion — genuine CV code with a labeled-synthetic input, not a fake
result. Uses a hand-rolled linear pixel<->lon/lat transform instead of
rasterio/GeoTIFF (TRD §4 names rasterio for this component) — a scope cut
to avoid rasterio's GDAL dependency weight in an already dependency-heavy
image build; the geometry math is the same either way, just not embedded
in the file's own metadata.
"""
import cv2
import numpy as np

# Anchored near ZN-01 (Upper Ridge, a real landslide zone per Phase 3's
# seeded data) — same centroid the seed data already uses.
ORIGIN_LON, ORIGIN_LAT = 93.005, 25.175
PIXEL_SIZE_DEG = 0.0001  # ~11m/px at this latitude
IMAGE_SIZE = 200  # 200x200 px, single-band (grayscale reflectance proxy)


def pixel_to_lonlat(col: float, row: float) -> tuple[float, float]:
    lon = ORIGIN_LON + col * PIXEL_SIZE_DEG
    lat = ORIGIN_LAT - row * PIXEL_SIZE_DEG  # row increases downward; lat decreases downward on a north-up image
    return lon, lat


def generate_sample_pair(seed: int = 1) -> tuple[bytes, bytes]:
    """The one curated before/after pair (rule 6 — clearly synthetic, not
    presented as a real satellite pass)."""
    rng = np.random.default_rng(seed)
    before = np.clip(100 + rng.normal(0, 8, size=(IMAGE_SIZE, IMAGE_SIZE)), 0, 255).astype(np.uint8)

    after = before.copy()
    # Simulated landslide scar: a patch of distinctly higher reflectance
    # (bare soil/debris vs. vegetation), roughly centered in the frame.
    after[70:130, 55:125] = np.clip(after[70:130, 55:125].astype(int) + 95, 0, 255).astype(np.uint8)

    ok1, before_png = cv2.imencode(".png", before)
    ok2, after_png = cv2.imencode(".png", after)
    if not (ok1 and ok2):
        raise RuntimeError("failed to encode sample imagery")
    return before_png.tobytes(), after_png.tobytes()


def run_change_detection(before_bytes: bytes, after_bytes: bytes) -> tuple[dict | None, float]:
    """Real differencing/thresholding/contour pipeline. Returns (GeoJSON
    MultiPolygon of the detected change area, confidence) or (None, 0.0)
    if thresholding finds no change region."""
    before = cv2.imdecode(np.frombuffer(before_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    after = cv2.imdecode(np.frombuffer(after_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    if before is None or after is None or before.shape != after.shape:
        raise ValueError("before/after images must decode to the same dimensions")

    diff = cv2.absdiff(after, before)
    _, mask = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= 9]  # drop single-pixel noise
    if not contours:
        return None, 0.0

    polygons = []
    for contour in contours:
        points = contour.reshape(-1, 2)  # (col, row) pairs
        ring = [pixel_to_lonlat(float(col), float(row)) for col, row in points]
        if len(ring) < 3:
            continue
        ring.append(ring[0])  # close the ring
        polygons.append([ring])

    if not polygons:
        return None, 0.0

    confidence = float((mask > 0).sum()) / float(mask.size)
    geojson = {"type": "MultiPolygon", "coordinates": polygons}
    return geojson, round(confidence, 4)
