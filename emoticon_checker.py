"""이모티콘 검수 윈도우 애플리케이션 — 진입점.

GUI (기본):
    python emoticon_checker.py
CLI (자동화/테스트용):
    python emoticon_checker.py --check "C:\\작업\\[MOBILE] happy" [--csv output\\결과.csv]

exe 빌드:  build.bat  →  dist\\emoticon_checker.exe
검수 기준: PRD.md / 규격 수치는 src/spec.py 에서만 관리.
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
from pathlib import Path

from src.rules import (FAIL, PASS, WARN, Finding, _content_margins,
                       check_device_folder, find_device_folders,
                       find_junk_files, find_space_named, parse_device_folder,
                       rename_spaces_to_underscore, summarize, total_size_kb)
from src.report import default_report_path, write_report
from src import spec

# 윈도우 콘솔(cp949)에서 한글/특수문자(— 등) 출력 시 UnicodeEncodeError 방지.
# 창 모드 exe 에서는 stdout 이 None 일 수 있어 예외를 무시한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

APP_TITLE = "이모티콘 검수 도구"
APP_VERSION = "0.3.0"  # v01~v03 요구사항 반영 (요구사항_v01/v02/v03.md 참고)

LEVEL_COLORS = {FAIL: "#c62828", WARN: "#b26a00", PASS: "#2e7d32"}
LEVEL_LABELS = {FAIL: "불합격", WARN: "확인 필요", PASS: "통과"}


# ---------------------------------------------------------------- CLI 모드 --

def run_cli(target: str, csv_path: str | None) -> int:
    root = Path(target)
    if not root.is_dir():
        print(f"폴더가 없습니다: {root}", file=sys.stderr)
        return 2
    folders = find_device_folders(root)
    if not folders:
        print("검수 대상([MOBILE]/[DESKTOP] 폴더)을 찾지 못했습니다.", file=sys.stderr)
        return 2

    print(f"전체 용량(합계): {total_size_kb(folders):,.1f}KB")

    results = {}
    total_fail = 0
    for d in folders:
        findings = check_device_folder(d)
        results[d.name] = findings
        p, w, f = summarize(findings)
        total_fail += f
        print(f"\n=== {d.name} — PASS {p} / WARN {w} / FAIL {f} ===")
        for fd in findings:
            if fd.level != PASS:
                print(f"  [{fd.level}] {fd.category} | {fd.target} | {fd.message}")

    if csv_path:
        print(f"\n리포트 저장: {write_report(results, csv_path)}")
    return 1 if total_fail else 0


# ---------------------------------------------------------------- GUI 모드 --

def run_gui(initial_folder: str | None = None) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from PIL import Image, ImageTk

    root = tk.Tk()
    root.title(f"{APP_TITLE} v{APP_VERSION}")
    root.geometry("1300x820")
    root.minsize(1040, 640)

    state = {
        "folders": [],          # 검수한 디바이스 폴더 Path 목록
        "results": {},          # {폴더명: [Finding]}
        "paths": {},            # {폴더명: Path}
        "running": False,
        "photo": None,          # 미리보기 이미지 참조 유지
    }
    msg_q: "queue.Queue[tuple]" = queue.Queue()

    # ============================== 상단: 폴더 선택 / 정보 입력 ==============================
    top = ttk.Frame(root, padding=(12, 10, 12, 4))
    top.pack(fill="x")
    top.columnconfigure(1, weight=1)

    folder_var = tk.StringVar()
    ttk.Label(top, text="검수 폴더:").grid(row=0, column=0, sticky="w")
    ttk.Entry(top, textvariable=folder_var).grid(row=0, column=1, sticky="we", padx=6)

    def pick_folder():
        path = filedialog.askdirectory(title="[MOBILE]/[DESKTOP] 폴더 또는 상위 폴더 선택")
        if path:
            folder_var.set(path)

    ttk.Button(top, text="찾아보기…", command=pick_folder).grid(row=0, column=2)
    ttk.Label(top, foreground="#666",
              text="※ '[MOBILE] 영문명' 폴더를 직접 선택하거나, 그런 폴더들이 들어있는 상위 폴더를 선택"
              ).grid(row=1, column=1, sticky="w", padx=6)

    info_frame = ttk.LabelFrame(root, text="이모티콘 정보 (선택 입력 — 글자수 검사)", padding=(12, 6))
    info_frame.pack(fill="x", padx=12, pady=(6, 0))
    name_ko = tk.StringVar(); name_en = tk.StringVar()
    desc_ko = tk.StringVar(); desc_en = tk.StringVar()
    for i, (label, var, width) in enumerate((
            ("국문명(≤20자)", name_ko, 26),
            ("영문명·표시명(≤20자)", name_en, 26),
            ("국문 설명(≤120자)", desc_ko, 44),
            ("영문 설명(≤120자)", desc_en, 44))):
        r, c = divmod(i, 2)
        ttk.Label(info_frame, text=label).grid(row=r, column=c * 2, sticky="w",
                                               padx=(0 if c == 0 else 14, 4), pady=2)
        ttk.Entry(info_frame, textvariable=var, width=width).grid(row=r, column=c * 2 + 1,
                                                                  sticky="w", pady=2)

    # ============================== 버튼 줄 + 진행 표시 ==============================
    btns = ttk.Frame(root, padding=(12, 8))
    btns.pack(fill="x")

    run_btn = ttk.Button(btns, text="검수 실행")
    run_btn.pack(side="left")
    csv_btn = ttk.Button(btns, text="CSV 리포트 저장")
    csv_btn.pack(side="left", padx=6)
    junk_btn = ttk.Button(btns, text="불필요 파일 삭제")
    junk_btn.pack(side="left")
    space_btn = ttk.Button(btns, text="파일명 공백 수정")
    space_btn.pack(side="left", padx=6)
    show_pass_var = tk.BooleanVar(value=False)
    show_pass_chk = ttk.Checkbutton(btns, text="통과 항목도 표시", variable=show_pass_var)
    show_pass_chk.pack(side="left", padx=12)

    progress = ttk.Progressbar(btns, mode="determinate", length=180)
    progress.pack(side="left", padx=(12, 6))
    status_var = tk.StringVar(value="폴더를 선택하고 [검수 실행]을 누르세요.")
    ttk.Label(btns, textvariable=status_var, font=("Malgun Gothic", 10, "bold")).pack(side="left", padx=4)

    # ============================== 본문: 결과 트리(좌) + 미리보기(우) ==============================
    paned = ttk.PanedWindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    tree_frame = ttk.Frame(paned)
    paned.add(tree_frame, weight=3)

    cols = ("level", "category", "target", "message")
    tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings")
    tree.heading("level", text="결과"); tree.column("level", width=64, anchor="center", stretch=False)
    tree.heading("category", text="항목"); tree.column("category", width=86, anchor="center", stretch=False)
    tree.heading("target", text="대상"); tree.column("target", width=250, anchor="w")
    tree.heading("message", text="내용"); tree.column("message", width=360, anchor="w")
    tree.column("#0", width=28, stretch=False)
    ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=ysb.set)
    tree.pack(side="left", fill="both", expand=True)
    ysb.pack(side="right", fill="y")
    for level, color in LEVEL_COLORS.items():
        tree.tag_configure(level, foreground=color)

    # --- 결과 텍스트 복사 (Ctrl+C / 우클릭 메뉴) ---
    def _rows_to_text(rows):
        lines = []
        for r in rows:
            vals = tree.item(r, "values")
            lines.append("\t".join(str(v) for v in vals))
        return "\n".join(lines)

    def copy_rows(event=None):
        rows = tree.selection()
        if not rows:
            return "break"
        root.clipboard_clear()
        root.clipboard_append(_rows_to_text(rows))
        status_var.set(f"{len(rows)}개 행 복사됨 (붙여넣기 가능)")
        return "break"

    def copy_all(event=None):
        rows = []
        for parent in tree.get_children(""):
            rows.append(parent)
            rows.extend(tree.get_children(parent))
        if not rows:
            return
        root.clipboard_clear()
        root.clipboard_append(_rows_to_text(rows))
        status_var.set("전체 결과 복사됨 (붙여넣기 가능)")

    tree.bind("<Control-c>", copy_rows)
    tree.bind("<Control-C>", copy_rows)
    tree_menu = tk.Menu(tree, tearoff=0)
    tree_menu.add_command(label="선택 행 복사  (Ctrl+C)", command=copy_rows)
    tree_menu.add_command(label="전체 결과 복사", command=copy_all)

    def _popup_menu(event):
        row = tree.identify_row(event.y)
        if row and row not in tree.selection():
            tree.selection_set(row)
        tree_menu.tk_popup(event.x_root, event.y_root)
    tree.bind("<Button-3>", _popup_menu)

    # --- 미리보기 패널 ---
    preview = ttk.LabelFrame(paned, text="이미지 미리보기 — 결과 행을 클릭하세요", padding=8)
    paned.add(preview, weight=2)

    CANVAS_W, CANVAS_H = 460, 460
    canvas = tk.Canvas(preview, width=CANVAS_W, height=CANVAS_H,
                       highlightthickness=0, bg="#f0f0f0")
    canvas.pack(anchor="w")

    verdict_var = tk.StringVar()
    verdict_lbl = tk.Label(preview, textvariable=verdict_var, justify="left",
                           font=("Malgun Gothic", 12, "bold"))
    verdict_lbl.pack(anchor="w", fill="x", pady=(8, 0))
    reason_var = tk.StringVar()
    reason_lbl = tk.Label(preview, textvariable=reason_var, wraplength=CANVAS_W,
                          justify="left", font=("Malgun Gothic", 10))
    reason_lbl.pack(anchor="w", fill="x")
    path_var = tk.StringVar()
    path_lbl = tk.Label(preview, textvariable=path_var, wraplength=CANVAS_W,
                        justify="left", foreground="#666", font=("Malgun Gothic", 9))
    path_lbl.pack(anchor="w", fill="x", pady=(4, 0))

    def _sync_wrap(event):
        # 미리보기 패널 폭에 맞춰 라벨 줄바꿈 폭을 갱신 (긴 경로/사유 텍스트 잘림 방지)
        w = max(160, event.width - 24)
        for lbl in (verdict_lbl, reason_lbl, path_lbl):
            lbl.configure(wraplength=w)
    preview.bind("<Configure>", _sync_wrap)

    open_btn = ttk.Button(preview, text="탐색기에서 열기")
    open_btn.pack(anchor="w", pady=(8, 0))
    state["preview_file"] = None

    def draw_checkerboard():
        cell = 16
        for y in range(0, CANVAS_H, cell):
            for x in range(0, CANVAS_W, cell):
                color = "#ffffff" if (x // cell + y // cell) % 2 == 0 else "#dcdcdc"
                canvas.create_rectangle(x, y, x + cell, y + cell, fill=color, outline="")

    def clear_preview(text=""):
        canvas.delete("all")
        draw_checkerboard()
        state["photo"] = None
        state["preview_file"] = None
        verdict_var.set(text)
        reason_var.set("")
        path_var.set("")

    def _margin_spec_for(folder_base, file_path: Path):
        """이 파일에 여백 규정이 있으면 규정 px 반환 (없으면 None)."""
        if folder_base is None:
            return None
        parsed = parse_device_folder(folder_base)
        if not parsed:
            return None
        device, _ = parsed
        name = file_path.name.lower()
        for suffix, req in spec.MARGIN_SPECS.get(device, {}).items():
            if name.endswith(suffix):
                return req
        return None

    def show_preview(finding: Finding, file_path: Path, folder_base=None):
        canvas.delete("all")
        draw_checkerboard()
        # 상단 판정 배너와 하단 범례가 이미지를 가리지 않도록 그 사이 영역에만 배치
        required = _margin_spec_for(folder_base, file_path)
        TOP_BAND = 26
        BOT_BAND = 46 if required is not None else 10
        try:
            with Image.open(file_path) as im:
                im = im.convert("RGBA")
                w, h = im.size
                # 실제 크기 확인이 중요하므로 규격보다 크게 확대하지 않는 선에서 맞춤
                avail_w = CANVAS_W - 40
                avail_h = CANVAS_H - TOP_BAND - BOT_BAND - 12
                scale = min(avail_w / w, avail_h / h, 4.0)
                disp = im.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                 Image.NEAREST if scale >= 2 else Image.LANCZOS)
                photo = ImageTk.PhotoImage(disp)
        except Exception as e:
            clear_preview("이미지를 열 수 없음")
            reason_var.set(str(e))
            path_var.set(str(file_path))
            return

        state["photo"] = photo  # GC 방지
        state["preview_file"] = file_path
        cx = CANVAS_W // 2
        cy = TOP_BAND + (CANVAS_H - TOP_BAND - BOT_BAND) // 2
        canvas.create_image(cx, cy, image=photo)
        # 판정 색 테두리 + 실측 크기 라벨을 이미지 위에 표시
        color = LEVEL_COLORS[finding.level]
        bw, bh = photo.width(), photo.height()
        canvas.create_rectangle(cx - bw // 2 - 3, cy - bh // 2 - 3,
                                cx + bw // 2 + 3, cy + bh // 2 + 3,
                                outline=color, width=3)

        # 여백 규정이 있는 파일이면 기준선/콘텐츠 경계를 겹쳐 그린다 (원본 미변경, 화면 표시만)
        if required is not None:
            sc = bw / w   # 표시 배율
            x0, y0 = cx - bw // 2, cy - bh // 2
            # 빨간 점선 = 여백 기준선 (이 선 밖으로 콘텐츠가 나가면 여백 부족)
            m = required * sc
            canvas.create_rectangle(x0 + m, y0 + m, x0 + bw - m, y0 + bh - m,
                                    outline="#e53935", width=2, dash=(5, 3))
            # 파란 실선 = 실제 콘텐츠 경계
            margins = _content_margins(file_path)
            if margins:
                ml, mt, mr, mb = margins
                canvas.create_rectangle(x0 + ml * sc, y0 + mt * sc,
                                        x0 + bw - mr * sc, y0 + bh - mb * sc,
                                        outline="#1e88e5", width=2)
            # 범례 (하단 2줄 바 — 가로 잘림 방지)
            leg_h = 42
            canvas.create_rectangle(0, CANVAS_H - leg_h, CANVAS_W, CANVAS_H,
                                    fill="#ffffff", outline="")
            canvas.create_line(8, CANVAS_H - leg_h + 13, 26, CANVAS_H - leg_h + 13,
                               fill="#e53935", width=2, dash=(5, 3))
            canvas.create_text(30, CANVAS_H - leg_h + 13, anchor="w",
                               font=("Malgun Gothic", 9),
                               text=f"여백 기준선 {required}px")
            canvas.create_line(8, CANVAS_H - 13, 26, CANVAS_H - 13,
                               fill="#1e88e5", width=2)
            canvas.create_text(30, CANVAS_H - 13, anchor="w",
                               font=("Malgun Gothic", 9),
                               text="콘텐츠 경계 (기준선 밖 = 여백 부족)")
        canvas.create_rectangle(0, 0, CANVAS_W, 24, fill=color, outline="")
        canvas.create_text(6, 12, anchor="w", fill="white",
                           font=("Malgun Gothic", 10, "bold"),
                           text=f"[{LEVEL_LABELS[finding.level]}] {finding.category} — 실제 {w}×{h}px")

        verdict_lbl.configure(foreground=color)
        verdict_var.set(f"{LEVEL_LABELS[finding.level]} — {finding.category}")
        reason_var.set(finding.message)
        path_var.set(str(file_path))

    def on_select(_event=None):
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        parent = tree.parent(item)
        if not parent:  # 폴더 요약 행
            clear_preview("폴더 요약 — 아래 상세 행을 클릭하세요")
            return
        folder_name = tree.item(parent, "values")[2]
        level, category, target, message = tree.item(item, "values")
        finding = Finding(level, category, target, message)
        base = state["paths"].get(folder_name)
        file_path = (base / target) if base else None
        if file_path and file_path.is_file():
            show_preview(finding, file_path, base)
        else:
            clear_preview("(이미지 파일이 아닌 항목)")
            verdict_lbl.configure(foreground=LEVEL_COLORS[level])
            verdict_var.set(f"{LEVEL_LABELS[level]} — {category} | {target}")
            reason_var.set(message)

    tree.bind("<<TreeviewSelect>>", on_select)

    def open_in_explorer():
        f = state.get("preview_file")
        if not f:
            return
        try:
            import os
            import subprocess
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", str(f)])
            else:
                os.startfile(str(f))  # type: ignore[attr-defined]
        except Exception:
            pass

    open_btn.configure(command=open_in_explorer)

    # ============================== 검수 실행 (백그라운드 + 실시간 표시) ==============================
    folder_nodes = {}

    def worker(folders, info):
        try:
            for d in folders:
                msg_q.put(("folder_start", d.name))
                findings = check_device_folder(
                    d, info, on_finding=lambda fd, name=d.name: msg_q.put(("finding", name, fd)))
                msg_q.put(("folder_done", d.name, findings))
            msg_q.put(("done",))
        except Exception as e:  # 예기치 못한 오류도 화면에 표시
            msg_q.put(("error", str(e)))

    def poll_queue():
        try:
            while True:
                msg = msg_q.get_nowait()
                kind = msg[0]
                if kind == "folder_start":
                    name = msg[1]
                    node = tree.insert("", "end", text="", open=True,
                                       values=("…", "", name, "검수 중…"))
                    folder_nodes[name] = node
                    status_var.set(f"검수 중: {name}")
                elif kind == "finding":
                    _, name, fd = msg
                    progress.step(1)
                    if show_pass_var.get() or fd.level != PASS:
                        tree.insert(folder_nodes[name], "end", text="",
                                    values=(fd.level, fd.category, fd.target, fd.message),
                                    tags=(fd.level,))
                        tree.see(tree.get_children(folder_nodes[name])[-1])
                elif kind == "folder_done":
                    _, name, findings = msg
                    state["results"][name] = findings
                    p, w, f = summarize(findings)
                    lvl = FAIL if f else (WARN if w else PASS)
                    tree.item(folder_nodes[name],
                              values=(lvl, "", name, f"PASS {p} / WARN {w} / FAIL {f}"),
                              tags=(lvl,))
                elif kind == "done":
                    state["running"] = False
                    run_btn.configure(state="normal")
                    progress.configure(value=progress["maximum"])
                    totals = [summarize(v) for v in state["results"].values()]
                    tp = sum(t[0] for t in totals); tw = sum(t[1] for t in totals)
                    tf = sum(t[2] for t in totals)
                    verdict = ("❌ 불합격 항목 있음" if tf
                               else ("⚠️ 확인 필요 항목 있음" if tw else "✅ 전체 통과"))
                    status_var.set(f"{verdict} — PASS {tp} / WARN {tw} / FAIL {tf}")
                    # 첫 문제 항목을 자동 선택해 미리보기를 바로 보여준다
                    for top_node in tree.get_children(""):
                        picked = False
                        for child in tree.get_children(top_node):
                            if tree.item(child, "values")[0] in (FAIL, WARN):
                                tree.selection_set(child)
                                tree.see(child)
                                picked = True
                                break
                        if picked:
                            break
                    return
                elif kind == "error":
                    state["running"] = False
                    run_btn.configure(state="normal")
                    status_var.set(f"오류: {msg[1]}")
                    return
        except queue.Empty:
            pass
        if state["running"]:
            root.after(50, poll_queue)

    def run_check():
        if state["running"]:
            return
        target = folder_var.get().strip()
        if not target:
            messagebox.showwarning(APP_TITLE, "검수할 폴더를 선택하세요.")
            return
        rootdir = Path(target)
        if not rootdir.is_dir():
            messagebox.showerror(APP_TITLE, f"폴더가 없습니다:\n{rootdir}")
            return
        folders = find_device_folders(rootdir)
        if not folders:
            messagebox.showerror(APP_TITLE,
                                 "검수 대상을 찾지 못했습니다.\n"
                                 "'[MOBILE] 영문명' / '[DESKTOP] 영문명' 폴더를 선택했는지 확인하세요.")
            return

        info = {"name_ko": name_ko.get().strip(),
                "name_en": name_en.get().strip(),
                "desc_ko": desc_ko.get().strip(),
                "desc_en": desc_en.get().strip()}
        state["folders"] = folders
        state["paths"] = {d.name: d for d in folders}
        state["results"] = {}
        folder_nodes.clear()
        tree.delete(*tree.get_children())
        clear_preview()

        # 맨 처음에 전체 용량(KB) 요약 — 선택한 상위 폴더(MOBILE+DESKTOP) 합산, 판정 없는 정보성 행
        total_kb = total_size_kb(folders)
        tree.insert("", "end", text="",
                    values=("정보", "용량", "전체(합계)", f"{total_kb:,.1f}KB"))

        # 진행바 최대치: 대략 파일 수 + 고정 검사 수 (정확할 필요는 없음)
        approx = sum(1 for d in folders for f in d.rglob("*") if f.is_file()) + len(folders) * 10
        progress.configure(maximum=max(approx, 1), value=0)

        state["running"] = True
        run_btn.configure(state="disabled")
        status_var.set("검수 시작…")
        threading.Thread(target=worker, args=(folders, info), daemon=True).start()
        root.after(50, poll_queue)

    def save_csv():
        if not state["results"]:
            messagebox.showwarning(APP_TITLE, "먼저 검수를 실행하세요.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            initialfile=Path(default_report_path()).name,
                                            filetypes=[("CSV", "*.csv")])
        if path:
            write_report(state["results"], path)
            messagebox.showinfo(APP_TITLE, f"리포트 저장 완료:\n{path}")

    def delete_junk():
        if not state["folders"]:
            messagebox.showwarning(APP_TITLE, "먼저 검수를 실행하세요.")
            return
        junk = [j for d in state["folders"] for j in find_junk_files(d)]
        if not junk:
            messagebox.showinfo(APP_TITLE, "삭제할 불필요 파일이 없습니다.")
            return
        names = "\n".join(f" - {j}" for j in junk[:15]) + ("\n …" if len(junk) > 15 else "")
        if not messagebox.askyesno(APP_TITLE, f"불필요 파일 {len(junk)}건을 삭제할까요?\n\n{names}"):
            return
        import shutil
        for j in junk:
            try:
                shutil.rmtree(j) if j.is_dir() else j.unlink()
            except OSError:
                pass
        messagebox.showinfo(APP_TITLE, "삭제 완료. 다시 검수를 실행해 확인하세요.")

    def fix_spaces():
        if not state["folders"]:
            messagebox.showwarning(APP_TITLE, "먼저 검수를 실행하세요.")
            return
        targets = [s for d in state["folders"] for s in find_space_named(d)]
        if not targets:
            messagebox.showinfo(APP_TITLE, "이름에 공백이 있는 파일·폴더가 없습니다.")
            return
        names = "\n".join(f" - {t.name}" for t in targets[:15]) + ("\n …" if len(targets) > 15 else "")
        if not messagebox.askyesno(APP_TITLE,
                                   f"이름에 공백이 있는 파일·폴더 {len(targets)}건을 "
                                   f"언더바(_)로 바꿀까요?\n\n{names}"):
            return
        total_renamed = sum(len(rename_spaces_to_underscore(d)) for d in state["folders"])
        messagebox.showinfo(APP_TITLE, f"{total_renamed}건 변경 완료. 다시 검수를 실행해 확인하세요.")

    run_btn.configure(command=run_check)
    csv_btn.configure(command=save_csv)
    junk_btn.configure(command=delete_junk)
    space_btn.configure(command=fix_spaces)

    clear_preview()
    if initial_folder:  # 실행 인자로 폴더가 오면 자동 검수 시작
        folder_var.set(initial_folder)
        root.after(400, run_check)
    root.mainloop()


# ------------------------------------------------------------------- main --

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_TITLE} — PRD.md 기준 자동 검수")
    parser.add_argument("folder", nargs="?",
                        help="(선택) GUI 를 이 폴더로 열고 자동으로 검수 시작")
    parser.add_argument("--check", metavar="폴더", help="GUI 없이 폴더를 검수하고 결과를 출력")
    parser.add_argument("--csv", metavar="경로", help="--check 결과를 CSV 로 저장")
    args = parser.parse_args(argv)

    if args.check:
        return run_cli(args.check, args.csv)
    run_gui(args.folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
