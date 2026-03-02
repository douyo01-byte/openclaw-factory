```python
import numpy as np
from sklearn.decomposition import PCA

def large_scale_automatic_decomposition(data: np.ndarray, n_components: int = None):
    """
    Fully automatic large-scale data decomposition using PCA with variance-based component selection.

    Args:
        data (np.ndarray): 2D data array (samples x features).
        n_components (int, optional): Number of components. If None, select components automatically.

    Returns:
        np.ndarray: Transformed data (samples x components).
        PCA: Fitted PCA model.
    """
    pca = PCA(n_components=n_components or min(data.shape))
    pca.fit(data)
    if n_components is None:
        # Choose components to explain 95% variance automatically
        cum_var = np.cumsum(pca.explained_variance_ratio_)
        n_components = np.searchsorted(cum_var, 0.95) + 1
        pca = PCA(n_components=n_components).fit(data)
    return pca.transform(data), pca

if __name__ == "__main__":
    import sys
    import pandas as pd

    # Usage: python script.py input.csv output.npy
    data = pd.read_csv(sys.argv[1]).values
    transformed, model = large_scale_automatic_decomposition(data)
    np.save(sys.argv[2], transformed)
```
