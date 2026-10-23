

def test():
    data = """\
5 5
9 9 9 9 9
3 0 0 0 0
9 9 9 9 9
6 6 6 6 8
9 9 9 9 9
"""
    a, b = solve(data)
    assert a == 74
    assert b == 'D D R R R R D D'

def solve(data):
    lines = iter(data.splitlines())
    n, m = map(int, next(lines).split())
    fields = []
    for line in lines:
        fields.append(list(map(int, line.split())))

    max_sum = 0
    route = [[] for i in range(n)]
    route[0].append(0)
    for i in range(n):
        for j in range(m):
            if i + j == 0:
                continue
            elif i == 0:
                fields[i][j] = fields[i][j] + fields[i][j - 1]
                route[i].append('R')
            elif j == 0:
                fields[i][j] = fields[i][j] + fields[i - 1][j]
                route[i].append('D')
            else:
                if fields[i - 1][j] > fields[i][j - 1]:
                    fields[i][j] = fields[i][j] + fields[i - 1][j]
                    route[i].append('D')
                else:
                    fields[i][j] = fields[i][j] + fields[i][j - 1]
                    route[i].append('R')
    # for i in range(n):
    #     print(fields[i])
    # for i in range(n):
    #     print(route[i])

    max_sum = fields[n - 1][m - 1]

    best_route = []
    i, j = n - 1, m - 1
    while i > 0 or j > 0:
        best_route.append(route[i][j])
        if best_route[-1] == 'D':
            i -= 1
        else:
            j -= 1
    best_route.reverse()
    best_route = ' '.join(best_route)
    return max_sum, best_route



def main():
    import sys
    a, b = solve(sys.stdin.read())
    print(a)
    print(b)


def test2():
    with open('3_in.txt') as f:
        data_in = f.read()
    


# https://coderun.yandex.ru/problem/print-the-route-of-the-maximum-cost
if __name__ == '__main__':
    # test()
    main()

