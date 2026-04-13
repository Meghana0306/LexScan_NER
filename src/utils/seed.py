"""
seed.py
───────
Set all random seeds for full reproducibility.

Usage:
    from src.utils.seed import set_seed
    set_seed(42)
"""

import os
import random
import numpy as np
import torch


def set_seed(seed: int = 42) -> None:
    """
    Set random seeds for Python, NumPy, and PyTorch.
    Call this at the very start of every training/evaluation script.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # Makes CUDA deterministic (slightly slower but reproducible)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"✅ All seeds set to {seed}")
