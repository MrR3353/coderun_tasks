
def solve(data):
    n, m = map(int, data.split(' '))
    field = [[0 for _ in range(m)] for _ in range(n)]
    field[0][0] = 1
    moves = [(2, 1), (1, 2)]
    for i in range(n):
        for j in range(m):
            for move in moves:
                prev_y = i - move[0]
                prev_x = j - move[1]
                if prev_y >= 0 and prev_x >= 0:
                    field[i][j] += field[prev_y][prev_x]
    return field[n-1][m-1]


def main():
    import sys
    result = solve(sys.stdin.read())
    print(result)

# [1, 0, 0, 0, 0, 0, 0]
# [0, 0, 1, 0, 0, 0, 0]
# [0, 1, 0, 0, 1, 0, 0]
# [0, 0, 0, 2, 0, 0, 1]
# [0, 0, 1, 0, 0, 3, 0]
# [0, 0, 0, 0, 3, 0, 0]
# [0, 0, 0, 1, 0, 0, 6]

# https://coderun.yandex.ru/problem/knight-move
if __name__ == '__main__':
    # test()
    main()

