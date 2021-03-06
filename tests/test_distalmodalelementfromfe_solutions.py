import unittest
from numpy import zeros, linspace
from numpy.testing import assert_array_equal, assert_array_almost_equal
from mbwind import System, Integrator, DistalModalElementFromFE
from beamfe import BeamFE


class TestDistalModalElementFromFE_static_solutions(unittest.TestCase):
    EI = 28.2e6
    m = 23.1
    L = 40.0
    damping_coeff = 0.2

    def setUp(self):
        x = linspace(0, self.L, 15)
        fe = BeamFE(x, density=self.m, EA=0, EIy=self.EI, EIz=0)
        fe.set_boundary_conditions('C', 'C')
        fe.set_dofs([False, False, True, False, True, False])
        beam = DistalModalElementFromFE('beam', fe, num_modes=1,
                                        damping=self.damping_coeff)

        system = System()
        system.add_leaf(beam)
        system.setup()
        system.update_kinematics()

        self.beam, self.system = beam, system

    def test_number_of_states(self):
        # 2 nodes       -> 12 states
        # 6 constraints -> 6  states
        # 3 dofs        -> 3  states  (2 attachment modes, 1 normal mode)
        self.assertEqual(len(self.system.qd), 21)
        self.assertEqual(len(self.system.qd.dofs), 3)

    def test_solution_without_force(self):
        # Static equilibrium should not move with no forces
        self.system.find_equilibrium()
        assert_array_equal(self.system.q.dofs[:], 0)
        assert_array_equal(self.beam.xstrain, 0)

        solution = integrate(self.system)
        assert_array_equal(solution, 0)

    def test_solution_with_force(self):
        Fz = 20.3
        loading = zeros((15, 3))
        loading[:, 2] = Fz
        self.beam.loading = loading
        self.system.find_equilibrium()

        expected_tip_defl = Fz * (self.L ** 4) / (8 * self.EI)
        tip_defl = self.beam.elastic_deflections()[-1, 2]
        assert_array_almost_equal(tip_defl, expected_tip_defl, decimal=2)

        # Now integrating in time should not change solution
        solution = integrate(self.system)
        assert_array_almost_equal(solution[0], solution[-1])

    def test_solution_with_force_applied_in_callback(self):
        Fz = 20.3
        loading = zeros((15, 3))
        loading[:, 2] = Fz
        self.beam.loading = loading
        self.system.find_equilibrium()

        expected_tip_defl = Fz * (self.L ** 4) / (8 * self.EI)
        tip_defl = self.beam.elastic_deflections()[-1, 2]
        assert_array_almost_equal(tip_defl, expected_tip_defl, decimal=2)

        # Now integrating in time should not change solution
        self.beam.loading = None

        def callback(system, time, q_struct, q_other):
            #self.beam.apply_distributed_loading(loading)
            self.beam.loading = loading
            print(self.beam.applied_stress)
            return []
        solution = integrate(self.system, callback)
        assert_array_almost_equal(solution[0], solution[-1])


def integrate(system, callback=None):
    integ = Integrator(system)
    t, y = integ.integrate(10, 0.5, nprint=None, callback=callback)
    return y[0]
