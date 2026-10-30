import sys


def solve(data):
    lines = iter(data.splitlines())
    n, m = map(int, next(lines).split())
    field = []
    for line in lines:
        field.append(list(map(int, line.split())))

    for i in range(n):
        for j in range(m):
            if i > 0 and j > 0:
                field[i][j] += min(field[i - 1][j], field[i][j - 1])
            elif i > 0:
                field[i][j] += field[i - 1][j]
            elif j > 0:
                field[i][j] += field[i][j - 1]
    print(field[n - 1][m - 1])

def main():
    data = sys.stdin.read()
    solve(data)

# https://coderun.yandex.ru/problem/cheapest-way
if __name__ == '__main__':
    main()