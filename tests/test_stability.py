"""Verify reduced schemes against known eigenmodes and convergence orders."""
import numpy as np
import pytest

from jetbridge_ml.validation.stability import diffusion_laplacian, heat_evolution, weighted_jacobi


@pytest.mark.parametrize("theta",[0,.5,1])
def test_diffusion_matches_exact_discrete_mode_amplification(theta):
    n=16
    k=5
    x=np.arange(1,n)/n
    mode=np.sin(k*np.pi*x)
    r=.3
    g=(1-4*(1-theta)*r*np.sin(k*np.pi/(2*n))**2)/(1+4*theta*r*np.sin(k*np.pi/(2*n))**2)
    tau,history,_=heat_evolution(n,r,theta,4,mode)
    np.testing.assert_allclose(history[-1],g**4*mode,atol=1e-13)
    assert tau[-1]==pytest.approx(4*r/n**2)


def test_explicit_diffusion_stability_boundary():
    n=20
    mode=np.sin((n-1)*np.pi*np.arange(1,n)/n)
    _,stable,rho_stable=heat_evolution(n,.25,0,20,mode)
    _,unstable,rho_unstable=heat_evolution(n,.75,0,20,mode)
    assert rho_stable<1<rho_unstable
    assert np.linalg.norm(stable[-1])<np.linalg.norm(mode)
    assert np.linalg.norm(unstable[-1])>1000*np.linalg.norm(mode)


def test_crank_nicolson_bounded_oscillation_and_implicit_damping():
    n=20
    mode=np.sin((n-1)*np.pi*np.arange(1,n)/n)
    _,cn,cn_rho=heat_evolution(n,5,.5,4,mode)
    _,be,be_rho=heat_evolution(n,5,1,4,mode)
    amplitude_cn=cn@mode/(mode@mode)
    amplitude_be=be@mode/(mode@mode)
    assert np.all(amplitude_cn[:-1]*amplitude_cn[1:]<0)
    assert np.all(amplitude_be>0)
    assert cn_rho<1 and be_rho<1
    assert abs(amplitude_be[-1])<abs(amplitude_cn[-1])


@pytest.mark.parametrize("theta,order",[(1,1),(.5,2)])
def test_temporal_order_against_semidiscrete_exact_solution(theta,order):
    n=20
    x=np.arange(1,n)/n
    mode=np.sin(np.pi*x)
    end=.02
    exact=mode*np.exp(-4*n*n*np.sin(np.pi/(2*n))**2*end)
    errors=[]
    for steps in (16,32):
        _,history,_=heat_evolution(n,end*n*n/steps,theta,steps,mode)
        errors.append(np.linalg.norm(history[-1]-exact))
    measured=np.log2(errors[0]/errors[1])
    assert measured==pytest.approx(order,abs=.03)


def test_central_difference_eigenvalue_has_second_order_error():
    errors=[]
    for n in (20,40):
        mode=np.sin(np.pi*np.arange(1,n)/n)
        approximation=n*n*diffusion_laplacian(n)@mode
        errors.append(np.linalg.norm(approximation+np.pi*np.pi*mode)/np.sqrt(n-1))
    assert np.log2(errors[0]/errors[1])==pytest.approx(2,abs=.03)


def test_jacobi_converges_to_independent_known_solution():
    history,residual,rho=weighted_jacobi([[2,-1],[-1,2]],[1,1],.5,100)
    np.testing.assert_allclose(history[-1],[1,1],atol=1e-11)
    assert residual[-1]<1e-11
    assert rho==pytest.approx(.75)


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        heat_evolution(20,-1,0,10,np.zeros(19))
    with pytest.raises(ValueError):
        weighted_jacobi([[0,1],[1,1]],[1,1],.5,10)
