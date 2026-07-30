def test_trajectory_fraction_uses_within_divided_by_repetitions():
 between=0.016202494964781308
 within=0.13397322893556862
 reps=6.0
 expected=(within/reps)/(between+within/reps)
 naive=within/(between+within)
 assert 0.57 < expected < 0.59
 assert naive > 0.89
 assert expected < naive
