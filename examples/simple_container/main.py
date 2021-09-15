import os

from pydicom import dcmread

INPUT_DIR = os.environ["RAIVEN_INPUT_DIR"]
OUTPUT_DIR = os.environ["RAIVEN_OUTPUT_DIR"]


if __name__ == "__main__":
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            if file.endswith(".dcm"):
                ds = dcmread(os.path.join(root, file))

                pixels = ds.pixel_array
                pixels = pixels * 2
                ds.PixelData = pixels.tobytes()
                ds.save_as(os.path.join(OUTPUT_DIR, file))
