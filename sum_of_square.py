# author: https://github.com/ForeverHaibara 

from basis_generator import * 
from root_guess import *
from text_process import *

from scipy.optimize import linprog
from scipy.optimize import OptimizeWarning
from itertools import product
import warnings



def UpDegree(poly, n, updeg):
    """
    Generator that returns 
    """
    
    for m in range(n, updeg+1):
        codeg = m - n 
        if codeg > 0:
            multiplier = sp.polys.polytools.Poly(f'a^{codeg}+b^{codeg}+c^{codeg}')
        else:
            multiplier = 1
        
        yield multiplier, poly * multiplier, m 

def SOS(poly, tangents = [], maxiter = 5000, roots = [], tangent_points = [], updeg = 10,
        silent = False, show_tangents = True, show_roots = True,
        mod = None, verifytol = 1e-8,
        precision = 6, linefeed = 2):
    '''
    Represent a cyclic, homogenous, 3-variable (a,b,c) polynomial into Sum of Squares form.

    Params
    -------
    tangents: list of str, e.g. ['a+b-c']
        Additional tangent inputs.

    maxiter: unsigned int
        Maximum iteration in searching roots. Set to zero to disable root searching. 

    roots: list of tuple, e.g. [(1/3,1/3)]
        A list of initial root guess (a,b)  (where WLOG c = 1 by homogenousity). 

    tangent_points: list of tuple, e.g. [(1/3,1/3)]
        An additional list of tangent points based on which the tangents are automatically generated.

    updeg: int
        If one try fail, it will automatically multiply the polynomial by \sum (a^t) and retry. 
        Repeat until it has reached the degree of {updeg} and still fails.
    
    silent: bool
        If silent == true, then no information will be printed. Dominates other printing settings.

    show_tangents: bool
        Whether to print out the adopted tangents.

    show_roots: bool
        Whether to print out the potential roots or local minima.
    
    mod: unsigned int / tuples ...
        Denominator guesses for approximating the coefficients into fractions.

    verifytol: float
        Each coefficient of the SOS result must be close to the accurate coefficient with bound 
        {verifytol}.

    precision: unsigned int
        Decimal precision of displaying result.

    linefeed: unsigned int
        Feed a new line every certain terms, no linefeed if set to zero.

    Return
    -------
    result: str
        The result of SOS. If it is an empty string, it means that it has failed.
    '''
    warns = []

    original_poly = poly
    retry = True

    # get the polynomial from text and obtain the degree
    poly = PreprocessText(poly,cyc=True)
    n = deg(poly)
    original_n = n 

    if type(tangents) == str:
        tangents = [tangents]
    tangents += ['a2-bc','a3-bc2','a3-b2c']

    if type(tangent_points) == tuple:
        tangent_points = [tangent_points]
    
    # search the roots
    strict_roots = []
    if maxiter:
        roots, strict_roots = findroot(poly, maxiter=maxiter, roots=roots)
        if show_roots and not silent:
            print('Roots =',roots)
        
        roots += tangent_points

        # generate the tangents
        tangents += root_tangents(roots)
        if show_tangents and not silent:
            print('Tangents =',tangents)

    while retry:
        if type(poly) == str:
            poly = PreprocessText(poly,cyc=True)
            n = deg(poly)
        
        dict_monom , inv_monom = generate_expr(n)

        # generate basis with degree n
        names, polys, basis = generate_basis(n,dict_monom,inv_monom,tangents,strict_roots)
        b = arraylize(poly,dict_monom,inv_monom)
        
        # reduce the basis according to the strict roots
        names, polys, basis = reduce_basis(n, dict_monom, inv_monom, names, polys, basis, strict_roots)
        x = None
        
        if len(names) > 0:
            with warnings.catch_warnings(record=True) as __warns:
                warnings.simplefilter('once')
                try:
                    x = linprog(np.ones(basis.shape[0]), A_eq=basis.T, b_eq=b, method='simplex')
                #, options={'tol':1e-9})
                except:
                    pass
                warns += __warns
    
        if len(names) == 0 or x is None or not x.success:
            if not silent:
                print(f'Failed with degree {n}, basis size = {len(names)} x {len(inv_monom)}')
            if n < updeg:
                # move up a degree and retry!
                n += 1
                poly = f's(a{n - original_n})(' + original_poly + ')'
            else:
                if not silent:
                    for warn in warns:
                        if issubclass(warn.category, OptimizeWarning):
                            #warnings.warn('Unstable Computation')
                            print('Warning: Unstable computation due to too large basis or coefficients.')
                            break
                return ''
        else: # success
            retry = 0

    # Approximates the coefficients to fractions if possible
    rounding = 0.1
    y = rationalize_array(x.x, rounding=rounding, mod=mod, reliable=True)

    # check if the approximation works, if not, cut down the rounding and retry
    # while (not verify(y,polys,poly,tol=verifytol)) and rounding > 1e-9:
    #     rounding *= 0.1
    #     y = rationalize_array(x.x, rounding=rounding, mod=mod, reliable=True)
        
    # Filter out zero coefficients
    index = list(filter(lambda i: y[i][0] !=0 , list(range(len(y)))))
    y = [y[i] for i in index]
    names = [names[i] for i in index]
    polys = [polys[i] for i in index]

    # verify whether the equation is strict
    if not verify(y, polys, poly, 0): 
        # backsubstitude to re-solve the coefficients
        equal = False 
        try:
            b2 = arraylize_sp(poly,dict_monom,inv_monom)
            basis = sp.Matrix([arraylize_sp(poly,dict_monom,inv_monom) for poly in polys])
            basis = basis.reshape(len(polys), b2.shape[0]).T
        
            new_y = basis.LUsolve(b2)
            new_y = [(r.p, r.q) for r in new_y]
            for coeff in new_y:
                if coeff[0] < 0:
                    break 
            else:
                if verify(new_y, polys, poly, 0):
                    equal = True 
                    y = new_y
                
                    # Filter out zero coefficients
                    index = list(filter(lambda i: y[i][0] !=0 , list(range(len(y)))))
                    y = [y[i] for i in index]
                    names = [names[i] for i in index]
                    polys = [polys[i] for i in index]
        except:
            pass             
    else:
        equal = True 
    
    # obtain the LaTeX format
    result = prettyprint(y, names, precision=precision, linefeed=linefeed)
    if not silent:
        print(result)

    return result

if __name__ == '__main__':
    s = r'(21675abcs(a)3+250s(a2b)s(a)3-185193abcs(a2b))/250'
    x = SOS(s,[],maxiter=1,precision=10,updeg=10)