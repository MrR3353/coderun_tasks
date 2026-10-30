
def main():
    n = int(input())
    seq1 = list(map(int, input().split()))
    m = int(input())
    seq2 = list(map(int, input().split()))

    seq_start_idx = 0
    seq_end_idx = 0
    for i in range(n):
        curr_len = 0
        for j in range(m):
            if i + curr_len == n:
                break
            if seq1[i + curr_len] != seq2[j]:
                curr_len = 0
                continue
            curr_len += 1
            if curr_len > seq_end_idx - seq_start_idx:
                seq_start_idx = i
                seq_end_idx = i + curr_len

    print(*seq1[seq_start_idx: seq_end_idx])


if __name__ == '__main__':
    main()