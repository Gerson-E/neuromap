"""
Brain Age Prediction wrapper for TensorFlow model.
Uses USC's 3D CNN model to predict biological brain age from FreeSurfer-processed MRI.
"""

import sys
import numpy as np
from pathlib import Path
from typing import Optional
import tensorflow as tf

# Add model directory to path
MODEL_DIR = Path(__file__).parent.parent / "model"
sys.path.insert(0, str(MODEL_DIR))

# Import model utilities
from utils import dataLoader
from model import NativeSpacemodel


class BrainAgePredictor:
    """
    Singleton class for brain age prediction.

    Loads the TensorFlow model once and reuses it for multiple predictions.
    This is more efficient than reloading the model for each prediction.
    """

    _instance: Optional['BrainAgePredictor'] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self):
        """
        Load the TensorFlow model and weights.

        This is called once when the predictor is first instantiated.
        """
        print("Initializing Brain Age Predictor...")

        # Limit TensorFlow GPU memory growth (prevents OOM errors)
        self._configure_tensorflow()

        # Load model architecture
        print("Loading model architecture...")
        self._model = NativeSpacemodel.get_model()

        # Load trained weights
        model_weights = MODEL_DIR / "model" / "NativeSpaceWeight.h5"

        if not model_weights.exists():
            raise FileNotFoundError(
                f"Model weights not found at {model_weights}. "
                "Please ensure NativeSpaceWeight.h5 is present."
            )

        print(f"Loading model weights from {model_weights.name}...")
        self._model.load_weights(str(model_weights))

        print("✓ Brain Age Predictor initialized successfully!")

    def _configure_tensorflow(self):
        """Configure TensorFlow settings for optimal performance."""
        # Limit GPU memory usage
        physical_devices = tf.config.list_physical_devices('GPU')

        if physical_devices:
            try:
                for device in physical_devices:
                    tf.config.experimental.set_memory_growth(device, True)
                print(f"✓ Configured {len(physical_devices)} GPU(s) with memory growth")
            except RuntimeError as e:
                print(f"Warning: Could not configure GPU memory growth: {e}")
        else:
            print("Note: No GPU detected. Using CPU for inference.")

    def predict(self, brain_mgz_path: Path) -> float:
        """
        Predict brain age from a FreeSurfer-processed brain.mgz file.

        Args:
            brain_mgz_path: Path to brain.mgz file

        Returns:
            float: Predicted brain age in years

        Raises:
            FileNotFoundError: If brain.mgz not found
            ValueError: If brain volume dimensions are incorrect
            RuntimeError: If prediction fails
        """

        if not brain_mgz_path.exists():
            raise FileNotFoundError(f"Brain file not found: {brain_mgz_path}")

        print(f"\nPredicting brain age from: {brain_mgz_path.name}")

        try:
            # Load and preprocess brain volume
            print("Loading brain volume...")
            brains = dataLoader.dataLoader([str(brain_mgz_path)])

            # Validate shape
            n, h, w, d = brains.shape
            print(f"Loaded {n} brain(s) with shape: {h}x{w}x{d}")

            if h != 128 or w != 128 or d != 128:
                raise ValueError(
                    f"Expected brain volume of size 128³, got {h}x{w}x{d}. "
                    "Ensure dataLoader downsampling is working correctly."
                )

            # Run prediction
            print("Running inference...")
            predictions = self._model.predict(brains, verbose=0)

            # Extract predicted age
            predicted_age = float(predictions[0][0])

            print(f"✓ Predicted biological brain age: {predicted_age:.2f} years")

            return predicted_age

        except Exception as e:
            raise RuntimeError(f"Brain age prediction failed: {str(e)}")


class BrainAgePredictionError(Exception):
    """Custom exception for brain age prediction errors."""
    pass


def predict_brain_age(subject_id: str, subjects_dir: Optional[Path] = None) -> float:
    """
    Convenience function to predict brain age for a subject.

    Args:
        subject_id: FreeSurfer subject identifier
        subjects_dir: Optional path to subjects directory (defaults to backend/subjects)

    Returns:
        float: Predicted brain age in years

    Raises:
        BrainAgePredictionError: If prediction fails
    """

    # Determine subjects directory
    if subjects_dir is None:
        subjects_dir = Path(__file__).parent.parent / "subjects"

    # Locate brain.mgz
    brain_mgz = subjects_dir / subject_id / "mri" / "brain.mgz"

    if not brain_mgz.exists():
        raise BrainAgePredictionError(
            f"brain.mgz not found for subject {subject_id} at {brain_mgz}. "
            "Please run FreeSurfer preprocessing first."
        )

    try:
        # Get or create predictor instance
        predictor = BrainAgePredictor()

        # Run prediction
        predicted_age = predictor.predict(brain_mgz)

        return predicted_age

    except Exception as e:
        raise BrainAgePredictionError(f"Failed to predict brain age: {str(e)}")


def batch_predict(subject_ids: list[str], subjects_dir: Optional[Path] = None) -> dict[str, float]:
    """
    Predict brain age for multiple subjects in batch.

    Args:
        subject_ids: List of subject identifiers
        subjects_dir: Optional path to subjects directory

    Returns:
        dict: Dictionary mapping subject_id -> predicted_age
    """

    if subjects_dir is None:
        subjects_dir = Path(__file__).parent.parent / "subjects"

    results = {}

    # Initialize predictor once
    predictor = BrainAgePredictor()

    for subject_id in subject_ids:
        try:
            brain_mgz = subjects_dir / subject_id / "mri" / "brain.mgz"
            predicted_age = predictor.predict(brain_mgz)
            results[subject_id] = predicted_age
            print(f"✓ {subject_id}: {predicted_age:.2f} years")

        except Exception as e:
            print(f"✗ {subject_id}: Failed - {str(e)}")
            results[subject_id] = None

    return results


# Example usage
if __name__ == "__main__":
    # Test with existing subject
    test_subject = "002"

    print("="*60)
    print("Brain Age Prediction Test")
    print("="*60)

    try:
        predicted_age = predict_brain_age(test_subject)

        print(f"\nResults for subject {test_subject}:")
        print(f"  Predicted Brain Age: {predicted_age:.2f} years")

        # Example with chronological age
        chronological_age = 45  # Replace with actual age
        brain_age_gap = predicted_age - chronological_age

        print(f"  Chronological Age: {chronological_age} years")
        print(f"  Brain Age Gap: {brain_age_gap:+.2f} years")

        if brain_age_gap > 0:
            print(f"  → Brain appears {abs(brain_age_gap):.1f} years older")
        elif brain_age_gap < 0:
            print(f"  → Brain appears {abs(brain_age_gap):.1f} years younger")
        else:
            print("  → Brain age matches chronological age")

    except BrainAgePredictionError as e:
        print(f"\n✗ Error: {e}")

    print("="*60)
