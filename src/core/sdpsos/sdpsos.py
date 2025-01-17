from copy import deepcopy
from typing import List, Optional, Union, Tuple, Dict

import sympy as sp

from .utils import (
    solve_undetermined_linear, split_vector,
    indented_print
)
from .solver import SDPProblem, SDPProblemEmpty
from .manifold import RootSubspace, _REDUCE_KWARGS, coefficient_matrix, add_cyclic_constraints
from .solution import create_solution_from_M, SolutionSDP
from ...utils.basis_generator import arraylize, arraylize_sp
from ...utils.polytools import deg


class SOSProblem():
    """
    Helper class for SDPSOS. See details at SOSProblem.solve.

    Assume that a polynomial can be written in the form v^T @ M @ v.
    Sometimes there are implicit constraints that M = Q @ S @ Q.T where Q is a rational matrix.
    So we can solve the problem on S first and then restore it back to M.

    To summarize, it is about solving for S >> 0 such that
    eq @ vec(S) = vec(P) where P is determined by the target polynomial.
    """
    def __init__(self, 
            poly,
            manifold = None,
            verbose_manifold = True
        ):
        self.poly = poly
        self.poly_degree = deg(poly)

        info = {'major': None, 'minor': None, 'multiplier': None}
        self.Q = deepcopy(info)
        self.deg = deepcopy(info)
        self.M = deepcopy(info)

        self.eq = deepcopy(info)
        self.vecP = None

        self.S_ = deepcopy(info)
        self.sdp = SDPProblemEmpty()


        if manifold is None:
            manifold = RootSubspace(poly)
        self.manifold = manifold

        if verbose_manifold:
            print(manifold)


    def _masked_dims(self, filter_zero = False):
        return self.sdp._masked_dims(filter_zero=filter_zero)

    def _not_none_keys(self):
        return self.sdp._not_none_keys()

    @property
    def masked_rows(self):
        return self.sdp.masked_rows

    @property
    def S(self):
        return self.sdp.S

    @property
    def y(self):
        return self.sdp.y

    def S_from_y(self, *args, **kwargs):
        return self.sdp.S_from_y(*args, **kwargs)

    def set_masked_rows(self, *args, **kwargs):
        return self.sdp.set_masked_rows(*args, **kwargs)

    def pad_masked_rows(self, *args, **kwargs):
        return self.sdp.pad_masked_rows(*args, **kwargs)


    def __getitem__(self, key):
        return getattr(self, key)


    def _compute_perp_space(self, minor = 0) -> Dict[str, sp.Matrix]:
        """
        Construct the perpendicular space of the problem.
        """
        self.Q = {'major': None, 'minor': None, 'multiplier': None}

        # positive indicates whether we solve the problem on R+ or R
        degree = self.poly_degree
        positive = not (degree % 2 == 0 and minor == 0)
        manifold = self.manifold
        self.deg['major'] = degree // 2
        self.Q['major'] = manifold.perp_space(minor = 0, positive = positive)

        if minor and degree > 2:
            self.deg['minor'] = degree // 2 - 1
            self.Q['minor'] = manifold.perp_space(minor = 1, positive = positive)

        return self.Q


    def _compute_equation(self, cyclic_constraint = True) -> Tuple[sp.Matrix, sp.Matrix]:
        """
        Construct the problem eq @ vec(S) = vec(M) where S is what we solved for.
        Return eq, vecM.
        """
        degree = self.poly_degree
        for key in self.Q.keys():
            Q = self.Q[key]
            if Q is not None and Q.shape[1] > 0:
                eq = coefficient_matrix(Q, self.deg[key], **_REDUCE_KWARGS[(degree%2, key)])
                self.eq[key] = eq
            else:
                self.Q[key] = None

        self.vecP = arraylize_sp(self.poly, cyc = False)
        
        if cyclic_constraint:
            add_cyclic_constraints(self)

        eq = sp.Matrix.hstack(*filter(lambda x: x is not None, self.eq.values()))
        return eq, self.vecP


    def _compute_subspace(self, eq, vecM) -> SDPProblem:
        """
        Given eq @ vec(S) = vec(M), if we want to solve S, then we can
        see that S = x0 + space * y where x0 is a particular solution and y is arbitrary.
        """
        # we have eq @ vecS = vecM
        # so that vecS = x0 + space * y where x0 is a particular solution and y is arbitrary
        x0, space = solve_undetermined_linear(eq, vecM)
        keys = [k for k, v in self.Q.items() if v is not None]
        splits = split_vector([self.Q[k].shape[1] for k in keys])

        self.sdp = SDPProblem(x0, space, splits, keys=keys)
        return self.sdp

 
    def construct_problem(self, minor = 0, cyclic_constraint = True, verbose = True) -> Tuple[sp.Matrix, sp.Matrix, List[slice]]:
        """
        Construct the symbolic representation of the problem.
        """
        Q = self._compute_perp_space(minor = minor)
        eq, vecP = self._compute_equation(cyclic_constraint = cyclic_constraint)
        sdp = self._compute_subspace(eq, vecP)
        return sdp


    def solve(self,
            minor: bool = False,
            cyclic_constraint: bool = True,
            skip_construct_subspace: bool = False,
            method: str = 'trivial',
            allow_numer: bool = False,
            verbose: bool = False
        ) -> bool:
        """
        Solve a polynomial SOS problem with SDP.

        Parameters
        ----------
        minor : bool
            For a problem of even degree, if it holds for all real numbers, it might be in the 
            form of sum of squares. However, if it only holds for positive real numbers, then
            it might be in the form of \sum (...)^2 + \sum ab(...)^2. Note that we have an
            additional term in the latter, which is called the minor term. If we need to 
            add the minor term, please set `minor = True`.
        cyclic_constraint : bool
            Whether to add cyclic constraint the problem. This reduces the degree of freedom.
        method : str
            The method to solve the SDP problem. Currently supports:
            'partial deflation' and 'relax' and 'trivial'.
        skip_construct_subspace : bool
            Whether to skip the computation of the subspace. This is useful when we have
            already computed the subspace and want to solve the problem with different
            sdp configurations.
        allow_numer : bool
            Whether to allow numerical solution. If True, then the function will return numerical solution
            if the rational solution does not exist.
        verbose : bool
            If True, print the information of the solving process.

        Returns
        -------
        bool
            Whether the problem is solved successfully. It can also be accessed by `sdp_problem.success`.
        """
        if not skip_construct_subspace:
            try:
                self.construct_problem(minor = minor, cyclic_constraint = cyclic_constraint, verbose = verbose)
            except:
                if verbose:
                    print('Linear system no solution. Please higher the degree by multiplying something %s.'%(
                        'or use the minor term' if not minor else ''
                    ))
                return False


        if verbose:
            print('Matrix shape: %s'%(str(
                    {k: '{}/{}'.format(v, self.Q[k].shape[0])
                        for k, v in self._masked_dims(filter_zero = True).items()}
                ).replace("'", '')))
            print('Degree of freedom: %d'%(self.sdp.dof))

        # Main SOS solver
        sos_result = self.sdp.solve(
            method = method,
            allow_numer = allow_numer,
            verbose = verbose
        )

        if not sos_result.success:
            return False
        self.M = self.compute_M(self.S)

        return True


    def compute_M(self, S: Dict[str, sp.Matrix]) -> Dict[str, sp.Matrix]:
        """
        Restore M = Q @ S @ Q.T from S.
        """
        M = {}
        self.S_ = {}
        for key in self._not_none_keys():
            self.S_[key] = self.pad_masked_rows(S, key)
            M[key] = self.Q[key] * self.S_[key] * self.Q[key].T
        return M


    def as_solution(self, 
            y: Optional[sp.Matrix] = None,
            decompose_method: str = 'raw',
            cyc: bool = True,
            factor_result: bool = True
        ) -> SolutionSDP:
        """
        Wrap the matrix form solution to a SolutionSDP object.
        Note that the decomposition of a quadratic form is not unique.

        Parameters
        ----------
        y : Optional[sp.Matrix]
            The y vector. If None, then we use the solution of the SDP problem.
        decompose_method : str
            One of 'raw' or 'reduce'. The default is 'raw'.
        cyc : bool
            Whether to convert the solution to a cyclic sum.
        factor_result : bool
            Whether to factorize the result. The default is True.

        Returns
        ----------
        solution : SolutionSDP
            SDP solution.
        """

        if y is None:
            S = self.S_
            M = self.M
            if (not S) or not any(S.values()):
                raise ValueError('The problem is not solved yet.')
        else:
            S = self.S_from_y(y)
            M = self.compute_M(S)

        return create_solution_from_M(
            poly = self.poly,
            S = S,
            Q = self.Q,
            M = M,
            decompose_method = decompose_method,
            cyc = cyc,
            factor_result = factor_result,
        )



def SDPSOS(
        poly: sp.Poly,
        minor: Union[List[bool], bool] = [False, True],
        degree_limit: int = 12,
        cyclic_constraint = True,
        method: str = 'trivial',
        allow_numer: bool = False,
        decompose_method: str = 'raw',
        factor_result: bool = True,
        verbose: bool = True,
        **kwargs
    ) -> Optional[SolutionSDP]:
    """
    Solve a polynomial SOS problem with SDP.

    Although the theory of numerical solution to sum of squares using SDP (semidefinite programming)
    is well established, there exists certain limitations in practice. One of the most major
    concerns is that we need accurate, rational solution rather a numerical one. One might argue 
    that SDP is convex and we could perturb a solution to get a rational, interior one. However,
    this is not always the case. If the feasible set of SDP is convex but not full-rank, then
    our solution might be on the boundary of the feasible set. In this case, perturbation does
    not work.

    To handle the problem, we need to derive the true low-rank subspace of the feasible set in advance
    and perform SDP on the subspace. Take Vasile's inequality as an example, s(a^2)^2 - 3s(a^3b) >= 0
    has four equality cases. If it can be written as a positive definite matrix M, then we have
    x'Mx = 0 at these four points. This leads to Mx = 0 for these four vectors. As a result, the 
    semidefinite matrix M lies on a subspace perpendicular to these four vectors. We can assume 
    M = QSQ' where Q is the nullspace of the four vectors x, so that the problem is reduced to find S.

    Hence the key problem is to find the root and construct such Q. Also, in our algorithm, the Q
    is constructed as a rational matrix, so that a rational solution to S converts back to a rational
    solution to M. We must note that the equality cases might not be rational as in Vasile's inequality.
    However, the cyclic sum of its permutations is rational. So we can use the linear combination of 
    x and its permutations, which would be rational, to construct Q. This requires knowledge of 
    algebraic numbers and minimal polynomials.

    For more flexible usage, please use
    ```
        sdp_problem = SOSProblem(poly)
        sdp_problem.solve(**kwargs)
        solution = sdp_problem.as_solution()
    ```

    Parameters
    ----------
    poly : sp.Poly
        Polynomial to be solved.
    minor : Union[List[bool], bool]
        For a problem of even degree, if it holds for all real numbers, it might be in the
        form of sum of squares. However, if it only holds for positive real numbers, then
        it might be in the form of \sum (...)^2 + \sum ab(...)^2. Note that we have an
        additional term in the latter, which is called the minor term. If we need to
        add the minor term, please set minor = True.
        The function also supports multiple trials. The default is [False, True], which
        first tries to solve the problem without the minor term.
    degree_limit : int
        The maximum degree of the polynomial to be solved. When the degree is too high,
        return None.
    cyclic_constraint : bool
        Whether to add cyclic constraint the problem. This reduces the degree of freedom.
    method : str
        The method to solve the SDP problem. Currently supports:
        'partial deflation' and 'relax' and 'trivial'.
    allow_numer : bool
        Whether to allow numerical solution. If True, then the function will return numerical solution
        if the rational solution does not exist.
    decompose_method : str
        One of 'raw' or 'reduce'. The default is 'raw'.
    factor_result : bool
        Whether to factorize the result. The default is True.
    verbose : bool
        If True, print the information of the problem.
    """
    degree = deg(poly)
    if degree > degree_limit or degree < 2:
        return None
    if not (poly.domain in (sp.polys.ZZ, sp.polys.QQ)):
        return None

    sdp_problem = SOSProblem(poly, verbose_manifold=verbose)

    if isinstance(minor, (bool, int)):
        minor = [minor]

    for minor_ in minor:
        if verbose:
            print('SDP Minor = %d:'%minor_)

        with indented_print(verbose = verbose):
            try:
                success = sdp_problem.solve(
                    minor = minor_,
                    cyclic_constraint = cyclic_constraint,
                    method = method,
                    allow_numer = allow_numer,
                    verbose = verbose
                )
                if success:
                    # We can also pass in **M
                    return sdp_problem.as_solution(
                        decompose_method = decompose_method, 
                        factor_result = factor_result
                    )
                    if verbose:
                        print('Success.')
            except Exception as e:
                if verbose:
                    print(e)
            if verbose:
                print('Failed.')

    return None