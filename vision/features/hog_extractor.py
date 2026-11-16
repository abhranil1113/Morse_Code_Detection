import cv2
import numpy as np


class HOGFeatureExtractor:
    """Extracts Histogram of Oriented Gradients (HOG) descriptors from normalized eye crops."""

    def __init__(
        self,
        win_size=(32, 32),
        block_size=(16, 16),
        block_stride=(8, 8),
        cell_size=(8, 8),
        nbins=9
    ):
        self.win_size = win_size
        self.hog = cv2.HOGDescriptor(
            win_size,
            block_size,
            block_stride,
            cell_size,
            nbins
        )

    def extract(self, img_gray: np.ndarray) -> np.ndarray:
        """
        Compute HOG feature vector for a single grayscale eye image.
        Returns a 1D numpy array of shape (N_features,).
        """
        if img_gray is None:
            return np.zeros(self.feature_dim, dtype=np.float32)

        if img_gray.shape != self.win_size:
            img_gray = cv2.resize(img_gray, self.win_size, interpolation=cv2.INTER_AREA)

        descriptor = self.hog.compute(img_gray)
        if descriptor is None:
            return np.zeros(self.feature_dim, dtype=np.float32)

        return descriptor.flatten().astype(np.float32)

    @property
    def feature_dim(self) -> int:
        """Calculates expected dimension of HOG descriptor for (32, 32) window."""
        # blocks = ((32-16)/8 + 1) * ((32-16)/8 + 1) = 3 * 3 = 9 blocks
        # cells per block = (16/8)*(16/8) = 4
        # bins = 9 -> 9 * 4 * 9 = 324 features
        return 324
