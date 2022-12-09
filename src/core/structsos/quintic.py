from math import gcd

import sympy as sp

from ...utils.text_process import cycle_expansion
from ...utils.root_guess import rationalize
from .peeling import _merge_sos_results, FastPositiveChecker

def _sos_struct_quintic(poly, degree, coeff, recurrsion):
    multipliers, y, names = [], None, None

    if coeff((5,0,0)) == 0:
        if coeff((4,1,0)) == 0 and coeff((1,4,0)) >= 0:
            if coeff((3,2,0)) > 0 and coeff((2,3,0)) ** 2 <= 4 * coeff((1,4,0)) * coeff((3,2,0)):
                # https://tieba.baidu.com/p/6472739202
                u, x_, y_, z_, = sp.symbols('u'), coeff((1,4,0)) / coeff((3,2,0)), coeff((2,3,0)) / coeff((3,2,0)), coeff((3,1,1)) / coeff((3,2,0))
                u_, y__, z__, w__ = None, y_, z_, coeff((2,2,1)) / coeff((3,2,0)) + (x_ + y_ + z_ + 1)
                eq = (u**5*x_**2 - u**4*x_**2 - 2*u**3*x_ + u**2*(-x_**2 - x_*y_ + x_) + u*(-x_*y_ - 4*x_ - y_ + 1) - x_ - y_ - 2).as_poly(u)
                for root in sp.polys.roots(eq, cubics = False, quartics = False).keys():
                    if isinstance(root, sp.Rational) and root > .999:
                        u_ = root
                        v_ = (u_**3*x_ - u_**2*x_ + u_*x_ - u_ + x_ + 1) / (u_*x_ + 1)
                        if u_ >= (v_ - 1)**2 / 4 + 1:
                            z__ = (-2*u_**2*v_ + u_**2 + u_*v_ - v_**2)/(u_**3 - u_**2 - u_*v_ + u_ + 1)
                            break
                        u_ = None
                else:
                    for root in sp.polys.nroots(eq):
                        if root.is_real and root > .999:
                            u_ = root
                            v_ = (u_**3*x_ - u_**2*x_ + u_*x_ - u_ + x_ + 1) / (u_*x_ + 1)
                            if u_ >= (v_ - 1)**2 / 4 + 1:
                                break
                            u_ = None
                    if u_ is not None:
                        # approximate a rational number
                        direction = (u_**2*x_ - 1)*(3*u_**4*x_**2 + 2*u_**3*x_**2 + 4*u_**3*x_ - 3*u_**2*x_**2 + 3*u_**2*x_ - 6*u_*x_ - x_**2 + x_ - 3)
                        direction = -1 if direction > 0 else 1
                        u_numer = u_
                        for tol in (.3, .1, 3e-2, 3e-3, 3e-4, 3e-5, 3e-7, 3e-9):
                            u_ = sp.Rational(*rationalize(u_numer + direction * tol * 3, rounding = tol))
                            v_ = (u_**3*x_ - u_**2*x_ + u_*x_ - u_ + x_ + 1) / (u_*x_ + 1)
                            if u_ >= (v_ - 1)**2 / 4 + 1:
                                y__ = (u_**5*x_**2 - u_**4*x_**2 - 2*u_**3*x_ - u_**2*x_**2 + u_**2*x_ - 4*u_*x_ + u_ - x_ - 2)/((u_ + 1)*(u_*x_ + 1))
                                if y__ <= y_:
                                    z__ = (-2*u_**2*v_ + u_**2 + u_*v_ - v_**2)/(u_**3 - u_**2 - u_*v_ + u_ + 1)
                                    if z__ <= z_:
                                        break 
                            u_ = None


                if u_ is not None and isinstance(u_, sp.Rational):
                    # now both u_, v_ are rational
                    u, v = u_, v_
                    r = (u.q * v.q / sp.gcd(u.q, v.q)) # cancel the denominator is good
                    # r = 1
                    r2 = r ** 2

                    multipliers = [f'{r}*a*a+{r*(u+v+1)}*b*c']
                    names = [f'a*({r2*(-u*v + u + 2)}*a^2*b+{r2*(-u*v + u - v + 1)}*a*b^2+{r2*(-v-1)}*b^3+{r2*(-2*u + v**2 + 3)}*a^2*c'
                                + f'+{r2*(-4*u**2 + 4*u*v + 2*u - v**2 - 3*v)}*a*b*c+{r2*(2*u**2 - u*v + 3*u + v**2 + 2*v - 3)}*b^2*c'
                                + f'+{r2*(2*u**2 + u*v - 3*u - v - 1)}*a*c^2+{r2*(-2*u*v - 2*u - v**2 + 4*v - 1)}*b*c^2)^2',

                            f'a*({r*u}*a^2*b+{r*(u-1)}*a*b^2+{-r}*b^3+{r*(-v-1)}*a^2*c+{r*(-2*u+v)}*a*b*c+{r*(-u+v+1)}*b^2*c+{r*(u+1)}*a*c^2+{r*(1-v)}*b*c^2)^2',
                            f'a*b*c*(a*a-b*b+{u}*(a*b-a*c)+{v}*(b*c-a*b))^2',
                            f'({y_ - y__}*a+{(z_ - z__)/2}*c)*a*b*(b-c)^2*({r}*(a*a+b*b+c*c)+{r*(u+v+1)}*(a*b+b*c+c*a))',
                            f'a^2*b^2*c*({r}*(a*a+b*b+c*c)+{r*(u+v+1)}*(a*b+b*c+c*a))']

                    denom = (u**3 - u**2 - u*v + u + 1)
                    y = [1 / denom / 4 / r2 / r,
                        (4*u - v*v + 2*v - 5) / denom / 4 / r,
                        (u + v + 2) * (4*u + v - 4) / denom / 2 * r,
                        1 if y_ != y__ or z_ != z__ else 0,
                        w__]
                    print(y, names)

                    y = [_ * coeff((3,2,0)) for _ in y]


                if False:
                    # deprecated
                    if sp.ntheory.primetest.is_square(t.p) and sp.ntheory.primetest.is_square(t.q):
                        t, p_, q_ = coeff((3,2,0)), sp.sqrt(t.p), sp.sqrt(t.q)
                        x_ = p_ / q_
                        if coeff((2,3,0)) == -t * p_ / q_ * 2:
                            v = sp.symbols('v')
                            for root in sp.polys.roots(x_ * (v**3 - 3*v*v + 7*v - 13) + 4*(v + 1)).keys():
                                if isinstance(root, sp.Rational) and root >= -1:
                                    v = root
                                    break
                            else:
                                v = None
                            
                            if v is not None:
                                y_ = 4*(v**2-4*v+7)*(2*v**3-3*v**2+6*v-1)/(v**3-3*v**2+7*v-13)**2
                                diff = coeff((3,1,1)) / t - (-2*x_*x_ + 2*x_ - y_)
                                if diff >= 0:
                                    diff2 = coeff((2,2,1)) / t + diff - (x_*x_ + y_ - 1)
                                    if diff2 >= 0:
                                        if diff >= y_:
                                            # use trivial method
                                            diff -= y_
                                            y = [sp.S(1), diff / 2, diff2]
                                            y = [_ * t for _ in y]
                                            names = [f'a*b*b*(a-{x_}*b+{x_-1}*c)^2', 'a*b*c*(a-b)^2', 'a^2*b^2*c']
                                        else:
                                            u = (v*v - 2*v + 5) / 4
                                            multipliers = [f'(a*a+{(v*v + 2*v + 9)/4}*b*c)']
                                            y = [4/(v**3 - 3*v*v + 7*v - 13)**2, 8*(v*v - v + 1)*(v*v + 2*v + 13)/(v**3 - 3*v*v + 7*v - 13)**2,
                                                diff, diff2]
                                            y = [_ * t for _ in y]
                                            # names = [f'a*(({v**2-2*v+9}*b-{v**2-1}*c)*(a*a-b*b+{u}*(a*b-a*c)+{v}*(b*c-a*b))'
                                            #                     + f'+({2*(v+1)}*a+{v**2-4*v+7}*b)*(b*b-c*c+{u}*(b*c-a*b)+{v}*(c*a-b*c)))^2']
                                            names = [f'a*({-2*u*v-2*u+v**2-2*v+9}*a^2*b+{2*u*v+2*u-v**3+2*v**2-7*v+2}*a*b^2+{-2*v-2}*b^3'
                                                            + f'+{v**2+2*v+1}*a^2*c+{-2*u*v**2+4*u*v-6*u+2*v**3-6*v**2+4*v}*a*b*c'
                                                            + f'+{u*v**2-4*u*v+7*u+3*v**2+2*v-1}*b^2*c+{u*v**2-u-2*v-2}*a*c^2+{-v**3-v**2+5*v-7}*b*c^2)^2']
                                            names += [f'a*b*c*(a*a-b*b+{u}*(a*b-a*c)+{v}*(b*c-a*b))^2',
                                                        f'a*b*c*(a*a+{(v*v + 2*v + 9)/4}*b*c)*(a*a+b*b+c*c-a*b-b*c-c*a)',
                                                        f'a*b*c*(a*a+{(v*v + 2*v + 9)/4}*b*c)*(a*b+b*c+c*a)']

        elif coeff((1,4,0)) == 0 and coeff((4,1,0)) >= 0:
            # reflect the polynomial
            def new_coeff(c):
                return coeff((c[0], c[2], c[1]))
            multipliers, y, names = _sos_struct_quintic(None, 5, new_coeff, recurrsion)
            if y is not None:
                names = [_.translate({98: 99, 99: 98}) for _ in names]

        if y is None:
            # try hexagon
            multipliers = ['a*b']
            poly2 = poly * sp.polys.polytools.Poly('a*b+b*c+c*a')
            multipliers , y , names = _merge_sos_results(multipliers, y, names, recurrsion(poly2, 7))
    else:
        a = coeff((5,0,0))
        if a > 0:
            # try Schur to hexagon
            b = coeff((4,1,0))
            if b >= -2 * a:
                fpc = FastPositiveChecker()
                name = '(a^2+b^2+c^2-a*b-b*c-c*a)*a*(a-b)*(a-c)'
                poly2 = poly - a * sp.sympify(cycle_expansion(name))
                fpc.setPoly(poly2)
                if fpc.check() == 0:
                    y = [a]
                    names = [name]
                    multipliers , y , names = _merge_sos_results(multipliers, y, names, recurrsion(poly2, 5))
                if y is None and b >= -a:
                    name = 'a^3*(a-b)*(a-c)'
                    poly2 = poly - a * sp.sympify(cycle_expansion(name))
                    fpc.setPoly(poly2)
                    if fpc.check() == 0:
                        y = [a]
                        names = [name]
                        multipliers , y , names = _merge_sos_results(multipliers, y, names, recurrsion(poly2, 5))
                    
    return multipliers, y, names
