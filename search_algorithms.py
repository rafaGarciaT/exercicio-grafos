from collections import deque
from heapq import heappush, heappop

def _in_bounds(r, c, R, C):
    return 0 <= r < R and 0 <= c < C

def bidirectional_bfs(grid, start, end):
    """
    grid: list[list[str]] where '#' is wall, others traversable
    start, end: (r, c)
    Returns: (visited_sequence, path_list)
      visited_sequence: list of (r,c) in discovery order (merge of both fronts)
      path_list: list from start..end (empty if not found)
    """
    if start == end:
        return [start], [start]

    R = len(grid)
    C = len(grid[0])

    # visited flags as per-row bytearrays (fast)
    vf = [bytearray(C) for _ in range(R)]
    vb = [bytearray(C) for _ in range(R)]

    qf = deque([start])
    qb = deque([end])
    vf[start[0]][start[1]] = 1
    vb[end[0]][end[1]] = 1

    pred_f = {start: None}
    pred_b = {end: None}

    visited_seq = [start, end]  # merged order (front then back)
    # expand smaller frontier each iteration
    while qf and qb:
        # choose frontier
        if len(qf) <= len(qb):
            q = qf
            visited = vf
            pred = pred_f
            other_visited = vb
            other_pred = pred_b
            expanding_from_front = True
        else:
            q = qb
            visited = vb
            pred = pred_b
            other_visited = vf
            other_pred = pred_f
            expanding_from_front = False

        for _ in range(len(q)):
            r, c = q.popleft()
            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                nr, nc = r+dr, c+dc
                if not _in_bounds(nr, nc, R, C):
                    continue
                if grid[nr][nc] == '#':
                    continue
                if visited[nr][nc]:
                    continue
                visited[nr][nc] = 1
                pred[(nr, nc)] = (r, c)
                q.append((nr, nc))
                visited_seq.append((nr, nc))
                # If the other side has seen this node -> meet
                if other_visited[nr][nc]:
                    # reconstruct path
                    meet = (nr, nc)
                    # build path from start to meet
                    path_f = []
                    cur = meet
                    # ensure pred_f points toward start
                    if expanding_from_front:
                        # we expanded front, so meet node is in front side and other_pred is back
                        p = pred_f
                        qother = pred_b
                    else:
                        p = pred_f
                        qother = pred_b
                    # walk from meet back to start using pred_f (if present), else via pred (current)
                    # Build left part
                    cur2 = meet
                    left = []
                    while cur2 is not None:
                        left.append(cur2)
                        cur2 = pred_f.get(cur2)
                    left = left[::-1]  # start..meet
                    # Build right part from meet to end using pred_b
                    right = []
                    cur3 = pred_b.get(meet)
                    while cur3 is not None:
                        right.append(cur3)
                        cur3 = pred_b.get(cur3)
                    # final path = left + right
                    path = left + right
                    return visited_seq, path
        # continue loop - next side will expand
    return visited_seq, []