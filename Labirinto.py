import tkinter as tk
from tkinter import ttk, messagebox
from search_algorithms import bidirectional_bfs
from config import COLS, ROWS, CELL_SIZE, PAD, COLORS

class MazeEditorGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Solucionador de Labirintos - Editor + BFS")
        # Modelo e view do labirinto
        self.labirinto = [[' ' for _ in range(COLS)] for _ in range(ROWS)]
        self.grid_cells = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.inicio_pos = None  # (r, c)
        self.fim_pos = None     # (r, c)

        # Estado de UI
        self.tool_var = tk.StringVar(value='wall')
        self.tool_rbs = []
        self.running = False  # se a simulação está em execução

        # Animação
        self.visited_seq = []
        self.final_path = []
        self._anim_index = 0
        self._path_idx = 0
        self._batch_size = 150
        self._anim_delay = 25     # Milisegundos entre frames
        self.job_after = None

        self._build_ui()
        self._draw_grid_initial()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=8, pady=8)

        # Canvas
        canvas_width = COLS * CELL_SIZE + 2 * PAD
        canvas_height = ROWS * CELL_SIZE + 2 * PAD
        self.canvas = tk.Canvas(main_frame, width=canvas_width, height=canvas_height, bg='gray90')
        self.canvas.grid(row=0, column=0, rowspan=6, sticky='nsew', padx=(0,10))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

        # Ferramentas (Radiobuttons)
        tools_frame = ttk.LabelFrame(main_frame, text="Modo Edição - Ferramenta")
        tools_frame.grid(row=0, column=1, sticky='nw', padx=4, pady=4)
        for text, val in (("Parede (#)", 'wall'), ("Caminho ( )", 'path'),
                          ("Início (S)", 'start'), ("Fim (E)", 'end')):
            rb = ttk.Radiobutton(tools_frame, text=text, variable=self.tool_var, value=val)
            rb.pack(anchor='w', padx=6, pady=2)
            self.tool_rbs.append(rb)

        # Controles de simulação
        sim_frame = ttk.LabelFrame(main_frame, text="Simulação (BFS)")
        sim_frame.grid(row=1, column=1, sticky='nw', padx=4, pady=6)
        self.start_btn = ttk.Button(sim_frame, text="Iniciar Busca (BFS)", command=self.iniciar_busca)
        self.start_btn.pack(fill='x', padx=6, pady=4)
        self.reset_search_btn = ttk.Button(sim_frame, text="Resetar Busca", command=self.resetar_busca)
        self.reset_search_btn.pack(fill='x', padx=6, pady=4)
        self.clear_btn = ttk.Button(sim_frame, text="Limpar Labirinto", command=self.limpar_labirinto)
        self.clear_btn.pack(fill='x', padx=6, pady=4)

        # Legenda simples
        legend_frame = ttk.LabelFrame(main_frame, text="Legenda")
        legend_frame.grid(row=2, column=1, sticky='nw', padx=4, pady=6)
        self._make_legend(legend_frame)

        # Expansão do grid do main_frame
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _make_legend(self, parent):
        items = [
            ('Parede (#)', COLORS['wall']),
            ('Caminho ( )', COLORS['path']),
            ('Início (S)', COLORS['start']),
            ('Fim (E)', COLORS['end']),
            ('Fronteira', COLORS['frontier']),
            ('Visitado', COLORS['visited']),
            ('Caminho Final', COLORS['final_path'])
        ]
        for label, color in items:
            frame = ttk.Frame(parent)
            frame.pack(fill='x', padx=6, pady=2)
            sw = tk.Canvas(frame, width=18, height=14)
            sw.create_rectangle(0,0,18,14, fill=color, outline='black')
            sw.pack(side='left')
            ttk.Label(frame, text=label).pack(side='left', padx=6)

    def _draw_grid_initial(self):
        # Desenha a grade e armazena os ids
        for r in range(ROWS):
            for c in range(COLS):
                x1 = PAD + c * CELL_SIZE
                y1 = PAD + r * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                rect = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                    fill=COLORS['path'],
                                                    outline="#cccccc")
                self.grid_cells[r][c] = rect

    def _coords_to_cell(self, x, y):
        # Converte coordenadas do canvas para índices da célula
        cx = x - PAD
        cy = y - PAD
        if cx < 0 or cy < 0:
            return None
        c = int(cx / CELL_SIZE)
        r = int(cy / CELL_SIZE)
        if 0 <= r < ROWS and 0 <= c < COLS:
            return (r, c)
        return None

    def on_canvas_click(self, event):
        cell = self._coords_to_cell(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if cell:
            self.editar_celula(cell[0], cell[1], self.tool_var.get())

    def on_canvas_drag(self, event):
        cell = self._coords_to_cell(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if cell:
            self.editar_celula(cell[0], cell[1], self.tool_var.get())

    def editar_celula(self, r, c, tool):
        if self.running: return
        current = self.labirinto[r][c]

        if tool == 'start':
            if self.inicio_pos and self.inicio_pos != (r,c):
                ir, ic = self.inicio_pos
                self.labirinto[ir][ic] = ' '
                self._color_cell(ir, ic, 'path')
            self.inicio_pos = (r,c)
            self.labirinto[r][c] = 'S'
            self._color_cell(r, c, 'start')

            if self.fim_pos == (r,c):
                self.fim_pos = None

        elif tool == 'end':
            if self.fim_pos and self.fim_pos != (r,c):
                er, ec = self.fim_pos
                self.labirinto[er][ec] = ' '
                self._color_cell(er, ec, 'path')
            self.fim_pos = (r,c)
            self.labirinto[r][c] = 'E'
            self._color_cell(r, c, 'end')
            if self.inicio_pos == (r,c): self.inicio_pos = None

        elif tool == 'wall':
            self.labirinto[r][c] = '#'
            self._color_cell(r, c, 'wall')
            if self.inicio_pos == (r,c): self.inicio_pos = None
            if self.fim_pos == (r,c): self.fim_pos = None

        elif tool == 'path':
            self.labirinto[r][c] = ' '
            self._color_cell(r, c, 'path')
            if self.inicio_pos == (r,c): self.inicio_pos = None
            if self.fim_pos == (r,c): self.fim_pos = None

    def _color_cell(self, r, c, kind):
        col = COLORS.get(kind, COLORS['path'])
        rect_id = self.grid_cells[r][c]
        self.canvas.itemconfigure(rect_id, fill=col)

    def iniciar_busca(self):
        if self.running: return

        # Garante posições de início/fim
        if not self.inicio_pos or not self.fim_pos:
            for r in range(ROWS):
                for c in range(COLS):
                    if self.labirinto[r][c] == 'S':
                        self.inicio_pos = (r, c)
                    elif self.labirinto[r][c] == 'E':
                        self.fim_pos = (r, c)
        if not self.inicio_pos or not self.fim_pos:
            messagebox.showwarning("Aviso","Defina um ponto de início (S) e um ponto de fim (E) antes de iniciar a busca.")
            return

        self._set_controls_state('disabled')
        self.running = True

        # Inicializar estruturas BFS bidirecionado
        start, end = self.inicio_pos, self.fim_pos
        visited_seq, path = bidirectional_bfs(self.labirinto, start, end)

        # Armazenar resultados para animação
        self.visited_seq = visited_seq or []
        self.final_path = path or []
        self._anim_index = 0
        self._path_idx = 0

        self.job_after = self.root.after(self._anim_delay, self._animate_search)

    def _animate_search(self):
        total = len(self.visited_seq)
        if self._anim_index >= total:
            if self.final_path:
                self.job_after = self.root.after(150, self._animate_path_indexed)
            else:
                self.running = False
                self._set_controls_state('normal')
                messagebox.showinfo("Resultado", "Busca finalizada — Caminho não encontrado.")
                self.job_after = None
            return

        end = min(self._anim_index + self._batch_size, total)
        for i in range(self._anim_index, end):
            r, c = self.visited_seq[i]
            if self.labirinto[r][c] not in ('#', 'S', 'E'):
                self._color_cell(r, c, 'visited') # pintar como visitado
        self._anim_index = end

        if self.running:
            self.job_after = self.root.after(self._anim_delay, self._animate_search)
        else:
            self.job_after = None

    def _animate_path_indexed(self):
        self._path_idx = getattr(self, '_path_idx', 0)
        if self._path_idx >= len(self.final_path):
            self._path_idx = 0
            self.running = False
            self._set_controls_state('normal')
            messagebox.showinfo("Resultado", "Busca finalizada — Caminho encontrado!")
            self.job_after = None
            return

        r, c = self.final_path[self._path_idx]
        if (r, c) != self.inicio_pos and (r, c) != self.fim_pos and self.labirinto[r][c] != '#':
            self._color_cell(r, c, 'final_path')
        self._path_idx += 1
        self.job_after = self.root.after(60, self._animate_path_indexed)

    def processar_passo_bfs(self):
        # Se fila vazia -> não encontrou
        if not self.fila:
            self.running = False
            self._set_controls_state('normal')
            messagebox.showinfo("Resultado", "Busca finalizada — Caminho não encontrado.")
            self.job_after = None
            return

        r, c = self.fila.popleft()

        # Se é o fim, reconstruir
        if (r, c) == self.fim_pos:
            self.running = False
            self._reconstruir_caminho((r,c))
            self._set_controls_state('normal')
            self.job_after = None
            return

        # Marcar atual como visitado (não colorir o start)
        if (r, c) != self.inicio_pos:
            # Só pinta visitado se não for parede/Start/End
            if self.labirinto[r][c] not in ('#', 'S', 'E'):
                self._color_cell(r, c, 'visited')

        # Vizinhos 4-direções
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if (nr, nc) not in self.visitados:
                    cell_val = self.labirinto[nr][nc]
                    # Podemos atravessar apenas caminhos e E (não paredes)
                    if cell_val != '#':
                        self.visitados.add((nr, nc))
                        self.predecessores[(nr, nc)] = (r, c)
                        # Se é fim, vamos setar e quebrar no próximo ciclo
                        if (nr, nc) == self.fim_pos:
                            self.fila.appendleft((nr, nc))  # priorizar checagem imediata
                        else:
                            # pintar como fronteira (fila) se não for start/end
                            if self.labirinto[nr][nc] not in ('S', 'E'):
                                self._color_cell(nr, nc, 'frontier')
                            self.fila.append((nr, nc))

        # Agendar próximo passo se ainda rodando
        if self.running:
            self.job_after = self.root.after(80, self.processar_passo_bfs)
        else:
            self.job_after = None

    def _reconstruir_caminho(self, end_pos):
        # Usa self.predecessores para voltar até S
        path = []
        cur = end_pos
        while cur != self.inicio_pos:
            path.append(cur)
            cur = self.predecessores.get(cur)
            if cur is None:
                # algo deu errado — aborta
                break
        # pintar caminho (excluindo S e E? normalmente pintamos até S inc.)
        for (r, c) in path:
            if (r, c) != self.fim_pos and (r,c) != self.inicio_pos:
                self._color_cell(r, c, 'final_path')

        messagebox.showinfo("Resultado", "Busca finalizada — Caminho encontrado!")

    def resetar_busca(self):
        if self.job_after:
            try:
                self.root.after_cancel(self.job_after)
            except Exception:
                pass
            self.job_after = None

        self.running = False
        self.visited_seq = []
        self.final_path = []
        self._anim_index = 0
        self._path_idx = 0

        self._set_controls_state('normal')

        for r in range(ROWS):
            for c in range(COLS):
                val = self.labirinto[r][c]
                if val == '#':
                    self._color_cell(r, c, 'wall')
                elif val == 'S':
                    self._color_cell(r, c, 'start')
                elif val == 'E':
                    self._color_cell(r, c, 'end')
                else:
                    self._color_cell(r, c, 'path')

    def limpar_labirinto(self):
        if self.running:
            messagebox.showwarning("Aviso", "Não é possível limpar o labirinto enquanto a simulação está rodando. Pressione 'Resetar Busca' primeiro.")
            return
        self.inicio_pos = None
        self.fim_pos = None
        for r in range(ROWS):
            for c in range(COLS):
                self.labirinto[r][c] = ' '
                self._color_cell(r, c, 'path')

    def _set_controls_state(self, state):
        btn_state = 'disabled' if state == 'disabled' else 'normal'
        self.start_btn.config(state=btn_state)
        self.reset_search_btn.config(state=btn_state)
        self.clear_btn.config(state=btn_state)

        # Radiobuttons de ferramenta
        for rb in getattr(self, 'tool_rbs', ()):
            try:
                rb.config(state=btn_state)
            except Exception:
                pass

        # Edição no canvas
        if state == 'disabled':
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
        else:
            self.canvas.bind("<Button-1>", self.on_canvas_click)
            self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    def on_close(self):
        # Garantece que a simulação é parada antes de fechar
        if getattr(self, 'job_after', None):
            try:
                self.root.after_cancel(self.job_after)
            except Exception:
                pass
            self.job_after = None
        try:
            self.root.destroy()
        except Exception:
            pass

def main():
    root = tk.Tk()
    app = MazeEditorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == '__main__':
    main()
