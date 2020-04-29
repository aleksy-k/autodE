from autode.atoms import Atom
from autode.transition_states.templates import get_ts_templates
from autode.transition_states.ts_guess import TSguess
from autode.bond_rearrangement import BondRearrangement
from autode.transition_states.transition_state import TransitionState
from autode.molecule import Reactant, Product
from autode.complex import ReactantComplex, ProductComplex
from autode.config import Config
from autode.calculation import Calculation
from autode.wrappers.ORCA import ORCA
from autode.transition_states.base import imag_mode_links_reactant_products
import os
here = os.path.dirname(os.path.abspath(__file__))
method = ORCA()
method.available = True

ch3cl = Reactant(charge=0, mult=1, atoms=[Atom('Cl', 1.63664, 0.02010, -0.05829),
                                          Atom('C', -0.14524, -0.00136, 0.00498),
                                          Atom('H', -0.52169, -0.54637, -0.86809),
                                          Atom('H', -0.45804, -0.50420, 0.92747),
                                          Atom('H', -0.51166, 1.03181, -0.00597)])
f = Reactant(charge=-1, mult=1, atoms=[Atom('F', 4.0, 0.0, 0.0)])
reac_complex = ReactantComplex(f, ch3cl)

ch3f = Product(charge=0, mult=1, atoms=[Atom('C', -0.05250, 0.00047, -0.00636),
                                        Atom('F', 1.31229, -0.01702, 0.16350),
                                        Atom('H', -0.54993, -0.04452, 0.97526),
                                        Atom('H', -0.34815, 0.92748, -0.52199),
                                        Atom('H', -0.36172, -0.86651, -0.61030)])
cl = Product(charge=-1, mult=1, atoms=[Atom('Cl', 4.0, 0.0, 0.0)])
product_complex = ProductComplex(ch3f, cl)

tsguess = TSguess(reactant=reac_complex, product=product_complex,
                  atoms=[Atom('F', -2.66092, -0.01426, 0.09700),
                         Atom('Cl', 1.46795, 0.05788, -0.06166),
                         Atom('C', -0.66317, -0.01826, 0.02488),
                         Atom('H', -0.78315, -0.58679, -0.88975),
                         Atom('H', -0.70611, -0.54149, 0.97313),
                         Atom('H', -0.80305, 1.05409, 0.00503)])

tsguess.bond_rearrangement = BondRearrangement(breaking_bonds=[(2, 1)],
                                               forming_bonds=[(0, 2)])

ts = TransitionState(ts_guess=tsguess)


def test_ts_guess_class():
    os.chdir(os.path.join(here, 'data'))

    assert tsguess.reactant.n_atoms == 6
    assert tsguess.product.n_atoms == 6

    # C -- Cl distance should be long
    assert tsguess.product.get_distance(0, 5) > 3.0

    assert tsguess.calc is None
    assert hasattr(tsguess, 'bond_rearrangement')
    assert tsguess.bond_rearrangement is not None

    # TS guess should at least initially only have the bonds in the reactant
    assert tsguess.graph.number_of_edges() == 4

    assert tsguess.could_have_correct_imag_mode(method=method)
    assert tsguess.has_correct_imag_mode()

    os.chdir(here)


def test_links_reacs_prods():
    os.chdir(os.path.join(here, 'data'))

    tsguess.calc = Calculation(name=tsguess.name + '_hess', molecule=tsguess, method=method,
                               keywords_list=method.keywords.hess, n_cores=Config.n_cores)
    # Should find the completed calculation output
    tsguess.calc.run()

    assert imag_mode_links_reactant_products(calc=tsguess.calc,
                                             reactant_graph=reac_complex.graph,
                                             product_graph=product_complex.graph,
                                             method=method)

    os.chdir(here)
