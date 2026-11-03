import cv2

images = [
    ("day05_074929", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691472927_031db4d3.jpg"),
    ("day25_111710", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691498529_11ea154d.jpg"),
    ("day25_082531", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691507380_0ab78b78.jpg"),
    ("day25_073018", r"C:\Users\mkiru\.gemini\antigravity\brain\dfddef8a-f7b0-40de-8369-234a8d44ad7a\.user_uploaded\media_1793691515766_abd9f4c3.jpg"),
]

for label, p in images:
    img = cv2.imread(p)
    h, w = img.shape[:2]
    # Let's see the white box on the wall. Looking at the images, it's roughly near x=150-250 or x=200-300?
    # Wait, in the image:
    # Left is RO water tank (white tank on stand)
    # Next is blue cylinders
    # Next is RO membrane skid
    # On the wall behind/above the RO skid is the white switch box!
    # Let's find where the white box is in normalized coordinates.
