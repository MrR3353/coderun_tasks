
def solve(data):
    n, m = map(int, data.split(' '))
    field = [[0 for _ in range(m)] for _ in range(n)]
    field[0][0] = 1
    moves = [(2, 1), (1, 2)]
    move(field, (0, 0), moves[0], n, m, moves)
    move(field, (0, 0), moves[1], n, m, moves)
    return field[n - 1][m - 1]

def move(field: list[list[int]], position: tuple[int, int], step: tuple[int, int], n: int, m: int, moves: list[tuple[int, int]]) -> None:
    y, x = position
    step_y, step_x = step
    new_y, new_x = y + step_y, x + step_x
    if new_y < n and new_x < m:
        field[new_y][new_x] = field[new_y][new_x] + 1
        move(field, (new_y, new_x), moves[0], n, m, moves)
        move(field, (new_y, new_x), moves[1], n, m, moves)


def main():
    import sys
    result = solve(sys.stdin.read())
    print(result)

# * * * *
# * * 1 *
# * 1 * *
# * * * 2

# https://coderun.yandex.ru/problem/knight-move
if __name__ == '__main__':
    # test()
    main()

