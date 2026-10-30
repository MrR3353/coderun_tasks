
def main():
    n = int(input())
    seq1 = list(map(int, input().split()))
    m = int(input())
    seq2 = list(map(int, input().split()))



    max_idx = []
    for left_idx in range(n):
        idx = []
        for i in range(left_idx, n):
            last_idx = idx[-1] + 1 if idx else 0
            for j in range(last_idx, m):
                if seq1[i] == seq2[j]:
                    idx.append(j)
                    if len(idx) > len(max_idx):
                        max_idx = idx
                    break

    print(' '.join(map(str, map(seq2.__getitem__, max_idx))))

# https://coderun.yandex.ru/problem/nop-with-response-recovery
if __name__ == '__main__':
    main()