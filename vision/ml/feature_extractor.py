import cv2
import numpy as np
from typing import Tuple, Optional
from vision.ml.model_config import PreprocessingConfig, HOGConfig


class FeatureExtractor:
    """Extracts normalized HOG feature vectors from eye images."""

    def __init__(
        self,
        prep_config: Optional[PreprocessingConfig] = None,
        hog_config: Optional[HOGConfig] = None
    ):
        self.prep_config = prep_config or PreprocessingConfig()
        self.hog_config = hog_config or HOGConfig()

        self.hog = cv2.HOGDescriptor(
            self.hog_config.win_size,
            self.hog_config.block_size,
            self.hog_config.block_stride,
            self.hog_config.cell_size,
            self.hog_config.nbins
        )

    def preprocess_image(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Preprocesses input image (BGR or Grayscale) to target dimensions with histogram equalization."""
        if img is None or img.size == 0:
            return None

        # Convert to Grayscale if required
        if self.prep_config.grayscale:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
        else:
            gray = img

        # Histogram equalization for contrast normalization
        if self.prep_config.equalize_hist and len(gray.shape) == 2:
            gray = cv2.equalizeHist(gray)

        # Resize to consistent resolution
        resized = cv2.resize(gray, self.prep_config.target_size, interpolation=cv2.INTER_AREA)
        return resized

    def extract_features(self, img: np.ndarray) -> np.ndarray:
        """Processes an image and returns a 1D float32 feature array."""
        proc = self.preprocess_image(img)
        if proc is None:
            return np.zeros(self.feature_dim, dtype=np.float32)

        desc = self.hog.compute(proc)
        if desc is None:
            return np.zeros(self.feature_dim, dtype=np.float32)

        return desc.flatten().astype(np.float32)

    @property
    def feature_dim(self) -> int:
        """
        Calculates HOG feature dimensionality:
        blocks_x = (64 - 16)/8 + 1 = 7
        blocks_y = (64 - 16)/8 + 1 = 7
        total_blocks = 49
        cells_per_block = 4
        nbins = 9
        total = 49 * 4 * 9 = 1764 features
        """
        bx = (self.hog_config.win_size[0] - self.hog_config.block_size[0]) // self.hog_config.block_stride[0] + 1
        by = (self.hog_config.win_size[1] - self.hog_config.block_size[1]) // self.hog_config.block_stride[1] + 1
        cells = (self.hog_config.block_size[0] // self.hog_config.cell_size[0]) * (self.hog_config.block_size[1] // self.hog_config.cell_size[1])
        return bx * by * cells * self.hog_config.nbins
