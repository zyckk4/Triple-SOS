import sympy as sp

from .sextic_symmetric import _sos_struct_sextic_hexagram_symmetric
from .utils import CyclicSum, CyclicProduct, _sum_y_exprs, _make_coeffs, inverse_substitution
from ...utils.roots.rationalize import rationalize_bound

a, b, c = sp.symbols('a b c')

def sos_struct_nonic(poly, coeff, recurrsion):
    """
    Nonic is polynomial of degree 9.

    Examples
    --------
    s(ac2(a-b)4(b-c)2)-5p(a-b)2p(a)

    s(20a6b2c+20a6bc2+20a5b4+40a5b3c-34a5b2c2-108a5bc3+20a5c4-34a4b4c-43a4b3c2+31a4b2c3+68a3b3c3)

    Reference
    -------
    [1] https://tieba.baidu.com/p/8457240407

    [2] https://tieba.baidu.com/p/7303219331
    """
    if not any(
        coeff(_) for _ in ((9,0,0),(8,1,0),(7,2,0),(6,3,0),(3,6,0),(2,7,0),(1,8,0),(7,1,1))
    ):
        if all(coeff((i,j,k)) == coeff((j,i,k)) for (i,j,k) in ((5,4,0),(6,2,1),(5,3,1))):
            return _sos_struct_nonic_hexagram_symmetric(poly, coeff, recurrsion)
        if (coeff((5,4,0)) == 0 and coeff((6,1,2)) == 0) or (coeff((4,5,0)) == 0 and coeff((6,2,1)) == 0):
            return _sos_struct_nonic_gear(poly, coeff, recurrsion)

    return None


def _sos_struct_nonic_hexagram_symmetric(poly, coeff, recurrsion):
    """
    Observe that
    f(a,b,c) = s(c5(a-b)4) + x^2s(a2b2c(a-b)4) - 2xp(a)s(3a4b2-4a4bc+3a4c2-4a3b3+2a2b2c2) >= 0
    because
    f*s(ab(a-b)4) = p(a)(xs(ab(a-b)4) - s(3a4b2-4a4bc+3a4c2-4a3b3+2a2b2c2))^2 + R*p(a-b)^2
    where
    R(a,b,c) = p(a-b)^2*s(a)s(ab) + p(a)s((a-b)^2)s(a^2(b-c)^2) / 4 >= 0

    Examples
    -------
    s(a2b-abc)s(ab2-abc)s(a(b-c)2)-13p(a-b)2p(a)

    s(2a6b2c+2a6bc2+5a5b4-34a5b3c+30a5b2c2-34a5bc3+5a5c4+16a4b4c+19a4b3c2+19a4b2c3-30a3b3c3)
    """
    c1, c2, c3, c4, c5, c6 = [coeff(_) for _ in ((5,4,0),(6,2,1),(5,3,1),(4,4,1),(5,2,2),(4,3,2))]
    if c1 < 0 or c2 < 0:
        return None
    if c1 == 0:
        solution = recurrsion(poly.div((a*b*c).as_poly(a,b,c))[0])
        if solution is None:
            return None
        return CyclicProduct(a) * solution
    if c2 == 0:
        poly2 = CyclicSum(
            coeff((5,4,0)) * a**5*(b+c) + coeff((5,3,1)) * a**4*(b**2+c**2) + coeff((5,2,2)) * a**3*b**3\
            + coeff((4,4,1)) * a**4*b*c + coeff((4,3,2)) * a**3*b*c*(b+c)
        ).doit().as_poly(a,b,c) + (coeff((3,3,3)) * a**2*b**2*c**2).as_poly(a,b,c)
        solution = recurrsion(poly2)
        if solution is None:
            return None
        return inverse_substitution(solution, factor_degree = 1)

    def _compute_hexagram_coeffs(z):
        # Assume we subtract (c1)s(c5(a-b)4) +(c2)s(a2b2c(a-b)4) - 2zp(a)s(3a4b2-4a4bc+3a4c2-4a3b3+2a2b2c2) + wp(a-b)^2p(a)
        # where c1*c2 >= z^2
        # so that the remaining is a hexagram * p(a).
        w = c3 + 4*(c1 + c2) + 6*z
        c4_ = c4 - (-2*w+6*c2+8*z)
        c5_ = c5 - (-2*w+6*c1+8*z)
        c6_ = c6 - (2*w)
        return w, c4_, c5_, c6_


    def _compute_hexagram_discriminant(z):
        # We will check whether the hexagram is positive by discriminant
        # For details see _sos_struct_sextic_hexagram_symmetric

        w, c4_, c5_, c6_ = _compute_hexagram_coeffs(z)
        if w < 0 or c4_ < 0 or c5_ < 0:
            return False
        # print('z =', z, '(w,c4,c5,c6) =', (w, c4_, c5_, c6_))

        if c4_ == 0:
            return c5_ + c6_ >= 0
        if c5_ == 0:
            return c4_ + c6_ >= 0
        tolerance = 0 if isinstance(z, sp.Rational) else 1e-12
        if c4_*c5_ >= (c4_ + c5_ + c6_)**2 - tolerance or c4_ + c5_ + c6_ >= 0:
            return True
        return False

    z = sp.sqrt(c1*c2)
    if not isinstance(z, sp.Rational):
        z = z.n(20)
    if not _compute_hexagram_discriminant(z):
        return None
    if not isinstance(z, sp.Rational):
        for z_ in rationalize_bound(z, direction = -1, compulsory = True):
            if z_ < 0 or z_**2 > c1*c2:
                continue
            if _compute_hexagram_discriminant(z_):
                z = z_
                break
        else:
            return None

    # Now we have z >= 0 such that the hexagram is positive
    w, c4_, c5_, c6_ = _compute_hexagram_coeffs(z)
    c7_ = coeff((3,3,3)) + 6*w + 12*z
    hexgram_coeffs_ = {
        (3,3,0): c4_,
        (4,1,1): c5_,
        (3,2,1): c6_,
        (3,1,2): c6_,
        (2,2,2): c7_,
    }
    hexgram_coeffs = lambda _: hexgram_coeffs_.get(_, 0)
    hexagram = _sos_struct_sextic_hexagram_symmetric(hexgram_coeffs)
    if hexagram is None:
        return None

    ratio = z / c2
    c2_ratio2 = c2 * ratio**2
    solution = None
    if w >= 4* c2 * ratio:
        # Note that for simple case,
        # s(c5(a-b)4) + x^2s(a2b2c(a-b)4) - 2xp(a)s(3a4b2-4a4bc+3a4c2-4a3b3+2a2b2c2) + 4xp(a-b)^2p(a)
        # = s(c(a-b)4(xab-c2)2) >= 0
        solution = sp.Add(*[
            c2 * CyclicSum(c*(a-b)**4*(a*b - ratio*c**2)**2),
            (w - 4*c2*ratio) * CyclicProduct((a-b)**2) * CyclicProduct(a),
            (c1 - c2_ratio2) * CyclicSum(c**5*(a-b)**4),
            hexagram * CyclicProduct(a),
        ])

    elif w >= 0:
        p1 = a*b*(a-b)**4 - ratio * (3*a**4*b**2 - 4*a**4*b*c + 3*a**4*c**2 - 4*a**3*b**3 + 2*a**2*b**2*c**2)
        p1 = p1.expand().together().as_coeff_Mul()

        multiplier = CyclicSum(a*b*(a-b)**4)
        p2 = w * CyclicProduct(a) * multiplier\
            + c2_ratio2 * CyclicProduct((a-b)**2) * CyclicSum(a) * CyclicSum(a*b) \
            + c2_ratio2 / 4 * CyclicProduct(a) * CyclicSum((a-b)**2) * CyclicSum(a**2*(b-c)**2)
        p2 = p2.together().as_coeff_Mul()

        y = [
            p1[0]**2 * c2,
            c1 - c2_ratio2,
            p2[0],
            sp.S(1),
        ]
        exprs = [
            CyclicProduct(a) * CyclicSum(p1[1])**2,
            multiplier * CyclicSum(c**5*(a-b)**4),
            CyclicProduct((a-b)**2) * p2[1],
            hexagram * multiplier * CyclicProduct(a)
        ]
        solution = _sum_y_exprs(y, exprs) / multiplier
    
    return solution


def _sos_struct_nonic_gear(poly, coeff, recurrsion):
    """
    Solve problems like
    s(ac^2(a-b)^4(b-c)^2)-5p(a-b)^2p(a) >= 0

    There exists a very complicated solution by quadratic form.
    However, there exists much easier solution:
    s(c(a4b-3a3b2+5a3bc-3a3c2-a2b3-a2b2c-a2bc2+5ab3c-4ab2c2+4abc3-b3c2-b2c3)2)+6p(a)p(a-b)2s(a2-ab)+p(a)s(2a3b+a3c-6a2b2+3a2bc)2

    Examples
    -------
    s(a6b2c-a5b3c+a5c4-a4b3c2)

    s(ac2((b(a2-b2+1(ab-ac)+3(bc-ab)))+(((a2c-b2c)-2(a2b-abc)+5(ab2-abc))))2)

    References
    ----------
    [1] https://tieba.baidu.com/p/8457240407
    """
    if not (coeff((5,4,0)) == 0 and coeff((6,1,2)) == 0):
        # reflect the polynomial
        reflect_coeffs = lambda _: coeff((_[0], _[2], _[1]))
        solution = _sos_struct_nonic_gear(poly, reflect_coeffs, recurrsion)
        if solution is not None:
            solution = solution.xreplace({b:c, c:b})
        return solution
    if coeff((4,5,0)) == 0 or coeff((6,2,1)) == 0:
        return None

    if True:
        # First try easy cases
        # Consider the following:
        # s(ac^2((b(?(a^2-b^2)+?(ab-ac)+?(bc-ab)))+((?(a^2c-b^2c)+?(a^2b-abc)+?(ab^2-abc))))^2) >= 0
        # Note that b(ab-ac) and ab^2-abc are equivalent, we can merge two into one.

        # Coefficients of (a^2-b^2) and (a^2c-b^2c) are determined by the vertices.
        # Coefficients of (bc-ab) and (ab^2-abc) are determined by the inner hexagon.
        # Finally we choose proper coefficient of (ab-ac) so that the remaining is symmetric,
        # which would be easy to handle.

        # First normalize the coefficient so that coeff((4,5,0)) == 1
        c1, c2, c42, c33, c24 = coeff((4,5,0)), coeff((6,2,1)), coeff((5,3,1)), coeff((4,4,1)), coeff((3,5,1))
        c41, c32, c23 = coeff((5,2,2)), coeff((4,3,2)), coeff((3,4,2))
        c2, c42, c33, c24 = c2 / c1, c42 / c1, c33 / c1, c24 / c1
        c41, c32, c23 = c41 / c1, c32 / c1, c23 / c1
        if c1 < 0 or c2 < 0:
            return None
        c2_sqrt = sp.sqrt(c2)
        if not isinstance(c2_sqrt, sp.Rational):
            c2_sqrt = c2_sqrt.n(20)
        def _compute_params(z):
            # We expect that z^2 = c2 in the ideal case. However, when z is rational,
            # we perturb some s(ab^2c^2(a-b)^4) to make c2_sqrt rational.
            w = c2 - z**2
            c41_, c32_, c23_ = c41 + 3*w, c32 + 4*w, c23 - 6*w
            v = c24 / 2 - z # coeff of (a^2b-abc)
            u = 1 - c42 / 2 / z # coeff of (bc-ab)

            frac0, frac1 = -(-3*u**2 - 2*u*z + 6*u + 3*v**2 + 6*v*z - 2*v - (c32_ - c23_) + 2*z**2 - 2), (6*(u + v + z - 1))
            if frac1 == 0:
                if frac0 != 0:
                    x = sp.nan
                else:
                    # x = 2 - 2*z - u - v # deprecated
                    x = 1 - v + sp.sqrt(-u - v + 1)
                    if not isinstance(x, sp.Rational):
                        x = 1 - v
            else:
                x = frac0 / frac1
            c41_ = c41_ - (2*u*z + v**2 + 2*v*z - 2*x*z + z**2)
            c33_ = c33 - (u**2 - 2*u - 2*v - 2*x + 1)
            c32_ = c32_ - (-2*u**2 - 2*u*v + 2*u*x - 2*u*z + 4*u + v**2 + 4*v*x + 2*v*z + x**2 + 4*x*z - 2*x - 2)
            return (u,v,x), (c41_, c33_, c32_)

        vertex1 = _compute_params(c2_sqrt)
        vertex2 = _compute_params(-c2_sqrt)
        # linear combination of vertex 1 and 2

        def _check_valid_weight(vertex1, vertex2, w):
            if w is sp.nan or (not 0 <= w <= 1):
                return False
            # w * vertex1 + (1 - w) * vertex2
            c41_, c33_, c32_ = [w*vertex1[1][i] + (1-w)*vertex2[1][i] for i in range(3)]
            if c41_ < 0 or c33_ < 0:
                return False
            if c41_ + c33_ + c32_ >= 0 or c41_ * c33_ >= (c41_ + c33_ + c32_)**2:
                return True
            return False

        def _search_valid_weight(vertex1, vertex2):
            if vertex1[0][-1] is sp.nan or vertex2[0][-1] is sp.nan:
                return None
            x1, y1, z1 = vertex1[1]
            x2, y2, z2 = vertex2[1]
            candidates = [sp.S(0), sp.S(1), x2/(x2 - x1), y2/(y2 - y1)]
            for w_ in candidates:
                if _check_valid_weight(vertex1, vertex2, w_):
                    return w_
            
            # symmetric axis of a quadratic function
            g, h = x1 + y1 + z1, x2 + y2 + z2
            sym_axis = (2*g*h - 2*h**2 - x1*y2 - x2*y1 + 2*y1*y2)/(2*(-g**2 + 2*g*h - h**2 + x1*x2 - x1*y2 - x2*y1 + y1*y2))
            
            # t = sp.symbols('x')
            # eq = (x1*t + x2*(1-t))*(y1*t + y2*(1-t)) - (g*t + h*(1-t))**2
            # print(sp.latex(eq))
            if _check_valid_weight(vertex1, vertex2, sym_axis):
                return sym_axis

        w = _search_valid_weight(vertex1, vertex2)
        print('w =', w, 'z =', c2_sqrt, '\nVertex1 =', vertex1, '\nVertex2 =', vertex2)
        if w is not None:
            if not isinstance(c2_sqrt, sp.Rational):
                for z in rationalize_bound(c2_sqrt, direction = -1, compulsory = True):
                    if z >= 0 and z**2 <= c2:
                        vertex1 = _compute_params(z)
                        vertex2 = _compute_params(-z)
                        w = _search_valid_weight(vertex1, vertex2)
                        if w is not None:
                            break
                else:
                    z = None
            else:
                z = c2_sqrt

        if w is not None and z is not None:
            c41_, c33_, c32_ = [w*vertex1[1][i] + (1-w)*vertex2[1][i] for i in range(3)]
            hexagram_coeffs_ = {
                (4,1,1): c41_, (3,3,0): c33_, (3,2,1): c32_, (2,3,1): c32_,
                (2,2,2): (-c41_-c33_-c32_*2)*3 + poly(1,1,1)
            }
            hexagram_coeffs = lambda _: hexagram_coeffs_.get(_, sp.S(0))
            hexagram_solution = _sos_struct_sextic_hexagram_symmetric(hexagram_coeffs)
            if hexagram_solution is not None:
                def _get_ker(z, vertex, as_coeff_Mul = True):
                    u, v, x = vertex[0]
                    ker = b*(z*(a**2-b**2)+x*(a*b-a*c)+u*(b*c-a*b)) + a**2*c-b**2*c + v*(a**2*b-a*b*c)
                    if as_coeff_Mul:
                        ker = ker.expand().together().as_coeff_Mul()
                    return ker
                ker1 = _get_ker(z, vertex1)
                ker2 = _get_ker(-z, vertex2)
                y = [
                    ker1[0]**2 * w * c1,
                    ker2[0]**2 * (1-w) * c1,
                    (c2 - z**2) * c1,
                    c1
                ]
                exprs = [
                    CyclicSum(a*c**2*ker1[1]**2),
                    CyclicSum(a*c**2*ker2[1]**2),
                    CyclicSum(a*b**2*c**2*(a-b)**4),
                    hexagram_solution * CyclicProduct(a),
                ]
                return _sum_y_exprs(y, exprs)
