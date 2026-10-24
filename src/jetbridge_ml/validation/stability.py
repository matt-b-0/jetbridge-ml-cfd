"""Controlled finite-difference stability examples, separate from OpenFOAM physics."""
import numpy as np


def diffusion_laplacian(intervals: int) -> np.ndarray:
    """Return the unscaled 1D central-difference Laplacian on interior nodes.

    Parameters
    ----------
    intervals : int
        Number of equal subintervals on [0, 1], at least three.

    Returns
    -------
    numpy.ndarray
        Symmetric (intervals-1, intervals-1) matrix with -2, 1, 1 stencil.
        Perturbations have homogeneous Dirichlet endpoints.
    """
    if not isinstance(intervals, (int, np.integer)) or intervals < 3:
        raise ValueError("intervals must be an integer >= 3")
    n = intervals - 1
    return np.diag(-2.0*np.ones(n)) + np.diag(np.ones(n-1), 1) + np.diag(np.ones(n-1), -1)


def heat_evolution(intervals: int, r: float, theta: float, steps: int, initial):
    """Advance a diffusion perturbation with a theta time-stepping scheme.

    Parameters
    ----------
    intervals : int
        Equal subintervals on the unit interval.
    r : float
        Diffusion number alpha*dt/dx**2, positive.
    theta : float
        0 for FTCS, 1 for implicit Euler, 0.5 for Crank-Nicolson.
    steps : int
        Positive integer number of time steps.
    initial : array-like
        Finite perturbation at interior nodes, shape (intervals-1,).

    Returns
    -------
    tuple
        Dimensionless times tau=alpha*t/L**2, interior perturbation history,
        and the exact finite-grid spectral radius of the update matrix.
        A linear fixed-temperature background may be added after solving.
    """
    lap = diffusion_laplacian(intervals)
    u = np.asarray(initial, float)
    if not np.isfinite(r) or r <= 0 or not np.isfinite(theta) or not 0 <= theta <= 1:
        raise ValueError("r must be positive and theta between zero and one")
    if not isinstance(steps, (int, np.integer)) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if u.shape != (intervals-1,) or not np.isfinite(u).all():
        raise ValueError("initial must contain one finite value per interior node")
    identity = np.eye(len(lap))
    update = np.linalg.solve(identity-theta*r*lap, identity+(1-theta)*r*lap)
    eigenvalues = np.linalg.eigvalsh(lap)
    amplification = (1+(1-theta)*r*eigenvalues)/(1-theta*r*eigenvalues)
    history = np.empty((steps+1, len(u)))
    history[0] = u
    for step in range(steps):
        history[step+1] = update @ history[step]
    return np.arange(steps+1)*r/intervals**2, history, float(max(abs(amplification)))


def weighted_jacobi(matrix, rhs, omega: float, steps: int, initial=None):
    """Solve a linear system iteratively and expose error-amplification diagnostics.

    Parameters
    ----------
    matrix : array-like
        Finite square system matrix with nonzero diagonal.
    rhs : array-like
        Finite right-hand side.
    omega : float
        Positive relaxation weight.
    steps : int
        Positive number of iterations.
    initial : array-like, optional
        Initial solution estimate; zero by default.

    Returns
    -------
    tuple
        Solution history, relative residual history (absolute if rhs=0),
        and spectral radius of I-omega*D**(-1)*A. No convergence is assumed.
    """
    a, b = np.asarray(matrix, float), np.asarray(rhs, float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or b.shape != (len(a),) or len(a) == 0:
        raise ValueError("Expected a nonempty square system")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(np.diag(a) == 0):
        raise ValueError("Finite system and nonzero diagonal required")
    if not np.isfinite(omega) or omega <= 0 or not isinstance(steps, (int,np.integer)) or steps < 1:
        raise ValueError("Positive omega and integer steps required")
    u = np.zeros_like(b) if initial is None else np.asarray(initial, float).copy()
    if u.shape != b.shape or not np.isfinite(u).all():
        raise ValueError("Invalid initial estimate")
    diagonal = np.diag(a)
    update = np.eye(len(a))-omega*a/diagonal[:,None]
    rho = float(max(abs(np.linalg.eigvals(update))))
    scale = np.linalg.norm(b) or 1.0
    history = np.empty((steps+1,len(b)))
    residual = np.empty(steps+1)
    history[0] = u
    residual[0] = np.linalg.norm(b-a@u)/scale
    for step in range(steps):
        u = u + omega*(b-a@u)/diagonal
        history[step+1] = u
        residual[step+1] = np.linalg.norm(b-a@u)/scale
    return history, residual, rho
