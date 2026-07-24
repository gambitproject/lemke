from collections import defaultdict
from fractions import Fraction as Fr

from lemke.lemke import lcp, runlemke

EMPTY: tuple[()] = ()  # empty sequence

PLAYER_1 = "Player 1"
PLAYER_2 = "Player 2"


def lcp_from_data(M: list[list[Fr]], q: list[Fr], d: list[Fr]) -> lcp:
    """Creates an LCP instance with given M, q, d."""

    n = len(q)
    if len(d) != n:
        raise ValueError("q and d must have the same length")
    if len(M) != n:
        raise ValueError("M must have as many rows as q")
    if any(len(row) != n for row in M):
        raise ValueError("M must be a square matrix")

    lcp_instance = lcp(n)
    lcp_instance.M = [[Fr(x) for x in row] for row in M]
    lcp_instance.q = [Fr(x) for x in q]
    lcp_instance.d = [Fr(x) for x in d]

    return lcp_instance


def build_sequence_form_lcp(game):
    """
    Construct the sequence-form LCP for a 2-player extensive-form game.

    Returns:
        M, q: LCP matrix and vector.
        ns1, ns2: Number of sequences for each player.
        infoset_to_parent1, infoset_to_parent2: Infoset-to-parent-sequence mappings.
        idx1, idx2: Sequence-to-index mappings.
    """

    #         .  -A  Et -Et  .  .            .
    #        -Bt  .  .   .  Ft -Ft           .
    #   M =  -E   .  .   .   .  .       q =  e
    #         E   .  .   .   .  .           -e
    #         .  -F  .   .   .  .            f
    #         .   F  .   .   .  .           -f

    p1 = game.players[PLAYER_1]
    p2 = game.players[PLAYER_2]

    # sequences for each player (infoset, action)
    seqs1, seqs2 = [EMPTY], [EMPTY]

    # parent mapping {infoset: parent sequence}
    infoset_to_parent1 = {}
    infoset_to_parent2 = {}

    # payoffs {(sequence1, sequence2): [sum_u1, sum_u2]}
    payoff = defaultdict(lambda: [Fr(0), Fr(0)])

    def dfs(node, s1, s2, prob, u1=Fr(0), u2=Fr(0)):
        # accumulate payoffs from outcome nodes along the path
        if node.outcome:
            u1 += Fr(node.outcome[p1])
            u2 += Fr(node.outcome[p2])

        # save payoff when a leaf is reached
        if node.is_terminal:
            key = (s1, s2)

            # subtract max_payoff to ensure the payoff matrix is non-positive
            # this makes Lemke's algorithm find a solution & not end on a secondary ray
            payoff[key][0] += prob * (u1 - Fr(game.max_payoff))
            payoff[key][1] += prob * (u2 - Fr(game.max_payoff))

            return

        if node.player == p1:
            h = node.infoset
            if h not in infoset_to_parent1:
                infoset_to_parent1[h] = s1
                for a in h.actions:
                    seqs1.append(s1 + ((h, a),))

            for action, child in zip(h.actions, node.children):
                dfs(child, s1 + ((h, action),), s2, prob, u1, u2)

        elif node.player == p2:
            h = node.infoset
            if h not in infoset_to_parent2:
                infoset_to_parent2[h] = s2
                for a in h.actions:
                    seqs2.append(s2 + ((h, a),))

            for action, child in zip(h.actions, node.children):
                dfs(child, s1, s2 + ((h, action),), prob, u1, u2)

        # chance node
        else:
            for action, child in zip(node.infoset.actions, node.children):
                dfs(child, s1, s2, (prob * Fr(action.prob)), u1, u2)

        # end of dfs

    dfs(game.root, EMPTY, EMPTY, Fr(1))

    # number of sequences
    ns1 = len(seqs1)
    ns2 = len(seqs2)

    # number of info sets
    ni1 = len(infoset_to_parent1) + 1
    ni2 = len(infoset_to_parent2) + 1

    # sequence indices
    idx1 = {s: i for i, s in enumerate(seqs1)}
    idx2 = {s: j for j, s in enumerate(seqs2)}

    # total dimension for LCP
    total_dim = ns1 + ns2 + 2 * ni1 + 2 * ni2

    M = [[Fr(0) for _ in range(total_dim)] for _ in range(total_dim)]
    q = [Fr(0) for _ in range(total_dim)]

    # offsets for filling M matrix
    o1 = 0
    o2 = ns1
    o3 = ns1 + ns2
    o4 = ns1 + ns2 + ni1
    o5 = ns1 + ns2 + 2 * ni1
    o6 = ns1 + ns2 + 2 * ni1 + ni2

    # fill payoffs
    for (s1, s2), (u1, u2) in payoff.items():
        i, j = idx1[s1], idx2[s2]
        M[o1 + i][o2 + j] = -u1  # -A
        M[o2 + j][o1 + i] = -u2  # -Bt

    # fill constraint matrices
    def fill_constraints(mapping, idx_map, off_row1, off_row2, off_col):
        # root constraints
        root_idx = idx_map[EMPTY]

        M[off_row1][off_col + root_idx] = Fr(-1)  # -E, -F
        M[off_row2][off_col + root_idx] = Fr(1)   # E, F
        M[off_col + root_idx][off_row1] = Fr(1)   # Et, Ft
        M[off_col + root_idx][off_row2] = Fr(-1)  # -Et, -Ft

        q[off_row1] = Fr(1)
        q[off_row2] = Fr(-1)

        # for every infoset: P(parent_sequence) = sum of P(child_sequences)
        # each infoset represents a row in E, F
        for i, (h, parent_seq) in enumerate(mapping.items()):
            row = i + 1
            p_idx = idx_map[parent_seq]

            # parent sequence (-1 entry in E, F)
            M[off_row1 + row][off_col + p_idx] = Fr(1)   # -E, -F
            M[off_row2 + row][off_col + p_idx] = Fr(-1)  # E, F
            M[off_col + p_idx][off_row1 + row] = Fr(-1)  # Et, Ft
            M[off_col + p_idx][off_row2 + row] = Fr(1)   # -Et, -Ft

            # child action (1 entry in E, F)
            for a in h.actions:
                child_idx = idx_map[parent_seq + ((h, a),)]
                M[off_row1 + row][off_col + child_idx] = Fr(-1)  # -E, -F
                M[off_row2 + row][off_col + child_idx] = Fr(1)   # E, F
                M[off_col + child_idx][off_row1 + row] = Fr(1)   # Et, Ft
                M[off_col + child_idx][off_row2 + row] = Fr(-1)  # -Et, -Ft

            # other entries are 0

    fill_constraints(infoset_to_parent1, idx1, o3, o4, o1)
    fill_constraints(infoset_to_parent2, idx2, o5, o6, o2)

    return M, q, ns1, ns2, infoset_to_parent1, infoset_to_parent2, idx1, idx2


def get_action_probabilities(player, infoset_to_parent, idx, x):
    """Convert a realization plan x to a list of action probabilities."""

    result = []

    for h in player.infosets:
        parent_seq = infoset_to_parent[h]
        parent_val = x[idx[parent_seq]]
        probs = []

        for a in h.actions:
            child_val = x[idx[parent_seq + ((h, a),)]]
            if parent_val == 0:
                # choosing uniform behavior arbitrarily
                probs.append(Fr(1, len(h.actions)))
            else:
                probs.append(child_val / parent_val)

        result.append(probs)

    return result


def solve_via_sequence_form(game):
    """Solves a given extensive-form game via LCP built by sequence form."""

    if not game.is_perfect_recall:
        raise RuntimeError("Game needs to have perfect recall.")

    if len(game.players) != 2:
        raise RuntimeError("Number of players needs to be 2.")

    (
        M,
        q,
        ns1,
        ns2,
        infoset_to_parent1,
        infoset_to_parent2,
        idx1,
        idx2,
    ) = build_sequence_form_lcp(game)

    d = [Fr(1) for _ in range(len(q))]

    lcp_instance = lcp_from_data(M, q, d)
    sol = runlemke(lcp=lcp_instance)

    # realization plans
    x_y = sol[1:(ns1 + ns2 + 1)]
    x = x_y[:ns1]
    y = x_y[ns1:]

    x_probs = get_action_probabilities(game.players[PLAYER_1], infoset_to_parent1, idx1, x)
    y_probs = get_action_probabilities(game.players[PLAYER_2], infoset_to_parent2, idx2, y)

    return x_probs, y_probs
