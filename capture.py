"""Captura de regiões da tela como numpy arrays."""
import mss
import numpy as np


def grab_region(region):
    """Retorna ndarray BGRA (H,W,4). region = dict com x, y, width, height."""
    if region is None:
        return None
    bbox = {
        "left": int(region["x"]),
        "top": int(region["y"]),
        "width": int(region["width"]),
        "height": int(region["height"]),
    }
    with mss.mss() as sct:
        return np.array(sct.grab(bbox))
