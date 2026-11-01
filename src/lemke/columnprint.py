"""Automatic pretty printing in columns."""


class columnprint:
    """Buffer that collects strings and prints them aligned in columns.

    Parameters
    ----------
    c : int
        Number of columns, at least 1.

    Raises
    ------
    ValueError
        If `c` is less than 1.
    """

    def __init__(self, c):  # void colset(int c);
        if c < 1:
            raise ValueError(f"Need positive number of columns, got {c}")
        self.buf = []
        self.ncols = c
        self.colwidth = [0] * c
        self.widthsign = [1] * c
        self.currlines = 0
        self.currcol = 0
        self.line = []

    def __str__(self):  # colout(void)
        """Create string, intermittent lines (not last line) separated by \n."""
        out = ""
        for ell in self.buf:
            out += self.prline(ell) + "\n"
        if not self.line:
            out = out[:-1]
        else:
            out += self.prline(self.line)
        return out

    def prline(self, line):  # prline(char *s)
        """(Private) string from line, which is a list of strings."""
        out = ""
        for i, word in enumerate(line):
            if self.widthsign[i] == 1:
                word = word.rjust(self.colwidth[i])
            else:
                word = word.ljust(self.colwidth[i])
            out += word
            if i < self.ncols - 1:
                out += " "  # single spacing here
        return out.rstrip()

    def iprint(self, i):  # colipr(i)
        """Print integer i into the current column."""
        self.sprint(str(i))

    def makeLeft(self, c):  # colleft(int c)
        """Make column c in  0..ncols-1  left-adjusted."""
        self.widthsign[c] = -1

    def newline(self):  # colnl(void);
        """Terminate current line early. Blank line if in column 0."""
        for _ in range(self.ncols - self.currcol):
            self.sprint("")

    def sprint(self, s):  # colpr(const char *s)
        """Store string  s  into the current column, updating column width."""
        w = len(s)
        if self.colwidth[self.currcol] < w:
            self.colwidth[self.currcol] = w
        self.line.append(s)
        self.currcol += 1
        if self.currcol == self.ncols:
            self.buf.append(self.line)
            self.line = []
            self.currcol = 0


if __name__ == "__main__":
    print("example with 3 columns, first left-justified")
    print("============================================")
    M = columnprint(3)
    M.makeLeft(0)
    M.sprint("z0")
    M.sprint("z1")
    M.sprint("z2")
    for i in [1, 200, 3, 20000, 0, -1, 88, 9]:
        M.iprint(i)
    print(M)
    print("example with 2 columns")
    print("======================")
    M = columnprint(2)
    M.sprint("z0")
    M.sprint("z1")
    for i in [1, 200, 3, 20000, 0, -1, 88, 9]:
        M.iprint(i)
    print(M)
