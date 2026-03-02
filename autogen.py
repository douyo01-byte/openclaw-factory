```python
# large_scale_decomposition.py

def large_scale_decomposition(data, components):
    """
    Perform fully automated large-scale decomposition on input data.

    Args:
        data (list[float] or numpy.ndarray): Input signal or dataset.
        components (int): Number of components to decompose into.

    Returns:
        list[numpy.ndarray]: List of decomposed components.
    """
    import numpy as np
    from scipy.linalg import svd

    data = np.asarray(data)
    if data.ndim != 1:
        raise ValueError("Input data must be 1-D array or list.")

    # Create trajectory matrix for SSA-like decomposition
    n = len(data)
    L = n // (components + 1) or 2
    K = n - L + 1
    X = np.column_stack([data[i:i+L] for i in range(K)])

    # SVD
    U, s, Vh = svd(X, full_matrices=False)
    U = U[:, :components]
    s = s[:components]
    Vh = Vh[:components, :]

    # Reconstruct components
    components_list = []
    for i in range(components):
        Xi = s[i] * np.outer(U[:, i], Vh[i])
        # Diagonal averaging
        component = np.zeros(n)
        count = np.zeros(n)
        for diag in range(-L+1, K):
            vals = np.diag(Xi, k=diag)
            idxs = range(max(0, -diag), min(L, K - diag))
            pos = [j + j + diag for j in idxs]
            for p, v in zip(pos, vals):
                component[p] += v
                count[p] += 1
        component /= count
        components_list.append(component)

    return components_list


if __name__ == "__main__":
    import numpy as np

    # Example usage
    t = np.linspace(0, 10, 500)
    signal = np.sin(t) + 0.5 * np.sin(3*t) + 0.2 * np.random.randn(500)
    comps = large_scale_decomposition(signal, 3)
    for i, c in enumerate(comps, 1):
        print(f"Component {i} mean: {np.mean(c):.4f}")
```
