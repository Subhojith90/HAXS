from __future__ import annotations

import numpy as np
import pytest

from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa


def test_dtwa_accepts_explicit_phase_points_and_refinement_substeps() -> None:
    graph = hypercubic_lattice((2,), False)
    occupancy = np.ones(2, dtype=bool)
    spins = np.array(
        [
            [[0.5, -0.5, -0.5], [0.5, -0.5, 0.5]],
            [[0.5, 0.5, -0.5], [0.5, 0.5, 0.5]],
        ],
        dtype=float,
    )
    result = run_dtwa(
        graph,
        np.array([0.0, 0.1]),
        initial_occupancy=occupancy,
        initial_spins=spins,
        integration_substeps=2,
        return_component_statistics=True,
    )
    assert result["deterministic_initial_spins"] is True
    assert result["integration_substeps"] == 2
    assert len(result["component_statistics"]) == 2
    assert result["component_statistics"][0]["n"] == 2


@pytest.mark.parametrize("substeps", [0, -1])
def test_dtwa_rejects_invalid_refinement(substeps: int) -> None:
    graph = hypercubic_lattice((2,), False)
    with pytest.raises(ValueError, match="integration_substeps"):
        run_dtwa(graph, np.array([0.0, 0.1]), integration_substeps=substeps)


def test_dtwa_rejects_wrong_explicit_phase_shape() -> None:
    graph = hypercubic_lattice((2,), False)
    with pytest.raises(ValueError, match="initial_spins"):
        run_dtwa(
            graph,
            np.array([0.0, 0.1]),
            initial_spins=np.zeros((2, 3, 3)),
        )
