import os
from fractions import Fraction as Fr

import pygambit
import pytest

from tests.sequence_form_helper import solve_via_sequence_form

FIXTURES_DIR = "tests/fixtures/efg"
FILES = [
    os.path.join(FIXTURES_DIR, f)
    for f in os.listdir(FIXTURES_DIR)
    if os.path.isfile(os.path.join(FIXTURES_DIR, f))
]


@pytest.mark.parametrize("file_path", FILES)
def test_with_max_regret(file_path):
    game = pygambit.read_efg(file_path)

    x_probs, y_probs = solve_via_sequence_form(game)

    profile = game.mixed_behavior_profile([x_probs, y_probs], rational=True)
    max_r = profile.max_regret()

    assert max_r == Fr(0)
