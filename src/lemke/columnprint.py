"""Automatic pretty printing in columns."""


class ColumnPrint:
    """Buffer that collects strings and prints them aligned in columns.

    Parameters
    ----------
    num_cols : int
        Number of columns, at least 1.

    Raises
    ------
    ValueError
        If `num_cols` is less than 1.
    """

    def __init__(self, num_cols: int) -> None:  # void colset(int c);
        if num_cols < 1:
            raise ValueError(f"Need positive number of columns, got {num_cols}")
        self.buf: list[list[str]] = []
        self.num_cols = num_cols
        self.col_width: list[int] = [0] * num_cols
        self.width_sign: list[int] = [1] * num_cols
        self.curr_lines = 0
        self.curr_col = 0
        self.line: list[str] = []

    def __str__(self):  # colout(void)
        """Create string, intermittent lines (not last line) separated by \n."""
        out = ""
        for line in self.buf:
            out += self._format_line(line) + "\n"
        if not self.line:
            out = out[:-1]
        else:
            out += self._format_line(self.line)
        return out

    def _format_line(self, line: list[str]) -> str:  # prline(char *s)
        """(Private) string from line, which is a list of strings."""
        out = ""
        for i, word in enumerate(line):
            if self.width_sign[i] == 1:
                word = word.rjust(self.col_width[i])
            else:
                word = word.ljust(self.col_width[i])
            out += word
            if i < self.num_cols - 1:
                out += " "  # single spacing here
        return out.rstrip()

    def iprint(self, i: int) -> None:  # colipr(i)
        """Print integer i into the current column."""
        self.sprint(str(i))

    def make_left(self, c: int) -> None:  # colleft(int c)
        """Make column c in  0..ncols-1  left-adjusted."""
        self.width_sign[c] = -1

    def newline(self) -> None:  # colnl(void);
        """Terminate current line early. Blank line if in column 0."""
        for _ in range(self.num_cols - self.curr_col):
            self.sprint("")

    def sprint(self, s: str) -> None:  # colpr(const char *s)
        """Store string  s  into the current column, updating column width."""
        w = len(s)
        if self.col_width[self.curr_col] < w:
            self.col_width[self.curr_col] = w
        self.line.append(s)
        self.curr_col += 1
        if self.curr_col == self.num_cols:
            self.buf.append(self.line)
            self.line = []
            self.curr_col = 0


if __name__ == "__main__":
    print("example with 3 columns, first left-justified")
    print("============================================")
    M = ColumnPrint(3)
    M.make_left(0)
    M.sprint("z0")
    M.sprint("z1")
    M.sprint("z2")
    for i in [1, 200, 3, 20000, 0, -1, 88, 9]:
        M.iprint(i)
    print(M)
    print("example with 2 columns")
    print("======================")
    M = ColumnPrint(2)
    M.sprint("z0")
    M.sprint("z1")
    for i in [1, 200, 3, 20000, 0, -1, 88, 9]:
        M.iprint(i)
    print(M)
