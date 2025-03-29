import re
import os
import customtkinter as ctk
from tkinter import filedialog, END


# SRT解析関数: ブロックごとに番号、タイムスタンプ、テキストを抽出
def parse_srt(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.splitlines()
        if len(lines) >= 3:
            block_id = lines[0]
            timestamp = lines[1]
            text = "\n".join(lines[2:])
            blocks.append({"id": block_id, "timestamp": timestamp, "text": text})
    return blocks


# SRT再構築関数
def reassemble_srt(blocks):
    output = []
    for block in blocks:
        output.append(block["id"])
        output.append(block["timestamp"])
        output.append(block["text"])
        output.append("")  # ブロック間の改行
    return "\n".join(output)


# 各テキスト内に対して正規表現置換を1件ずつ実行
def process_text(text, pattern, replacement):
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex '{pattern}': {e}")
    index = 0
    while True:
        m = regex.search(text, index)
        if not m:
            break
        start, end = m.start(), m.end()
        # 置換：置換は対象部分の1件のみ
        text = text[:start] + replacement + text[end:]
        index = start + len(replacement)
    return text


# SRT全体の変換処理：各ブロックのテキストに対し、辞書順に置換を実施
def convert_srt(filepath, regex_pairs):
    blocks = parse_srt(filepath)
    for block in blocks:
        original_text = block["text"]
        modified_text = original_text
        for pattern, replacement in regex_pairs:
            modified_text = process_text(modified_text, pattern, replacement)
        block["text"] = modified_text
    return blocks


# GUIアプリケーション
class SRTConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SRT Term Converter")
        self.geometry("700x500")

        # SRTファイル入力
        self.srt_path_entry = ctk.CTkEntry(self, placeholder_text="SRTファイルパス")
        self.srt_path_entry.grid(row=0, column=0, padx=10, pady=10, sticky="we")
        self.srt_browse_btn = ctk.CTkButton(self, text="参照", command=self.browse_srt)
        self.srt_browse_btn.grid(row=0, column=1, padx=10, pady=10)

        # 出力フォルダ選択
        self.output_path_entry = ctk.CTkEntry(self, placeholder_text="出力フォルダパス")
        self.output_path_entry.grid(row=1, column=0, padx=10, pady=10, sticky="we")
        self.folder_browse_btn = ctk.CTkButton(
            self, text="参照", command=self.browse_folder
        )
        self.folder_browse_btn.grid(row=1, column=1, padx=10, pady=10)

        # 辞書エディタ（1行につき「pattern => replacement」）
        ctk.CTkLabel(self, text="正規表現 辞書 (1行: pattern => replacement)").grid(
            row=2, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.dict_textbox = ctk.CTkTextbox(self, width=400, height=150)
        self.dict_textbox.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
        # 初期例を設定
        self.dict_textbox.insert(END, r"\bteh\b => the\n")  # 例: teh -> the

        # 変換実行ボタン
        self.execute_btn = ctk.CTkButton(
            self, text="変換実行", command=self.execute_conversion
        )
        self.execute_btn.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # エラー表示エリア
        ctk.CTkLabel(self, text="エラー/メッセージ").grid(
            row=5, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.error_textbox = ctk.CTkTextbox(self, width=400, height=100)
        self.error_textbox.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        self.grid_columnconfigure(0, weight=1)

    def browse_srt(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("SRT files", "*.srt"), ("All Files", "*.*")]
        )
        if file_path:
            self.srt_path_entry.delete(0, END)
            self.srt_path_entry.insert(0, file_path)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path_entry.delete(0, END)
            self.output_path_entry.insert(0, folder)

    def log_message(self, message):
        self.error_textbox.insert(END, message + "\n")
        self.error_textbox.see(END)

    def execute_conversion(self):
        self.error_textbox.delete("1.0", END)
        srt_filepath = self.srt_path_entry.get().strip()
        output_folder = self.output_path_entry.get().strip()
        if not srt_filepath or not os.path.isfile(srt_filepath):
            self.log_message("有効なSRTファイルを指定してください。")
            return
        if not output_folder or not os.path.isdir(output_folder):
            self.log_message("有効な出力フォルダを指定してください。")
            return

        # 辞書エディタの内容をパース: 各行が "pattern => replacement" 形式とする
        regex_pairs = []
        lines = self.dict_textbox.get("1.0", END).strip().splitlines()
        for idx, line in enumerate(lines, start=1):
            if "=>" not in line:
                self.log_message(f"行 {idx}: '=>' 区切りが見つかりません。")
                return
            parts = line.split("=>", 1)
            pattern = parts[0].strip()
            replacement = parts[1].strip()
            if not pattern:
                self.log_message(f"行 {idx}: パターンが空です。")
                return
            regex_pairs.append((pattern, replacement))

        try:
            blocks = convert_srt(srt_filepath, regex_pairs)
            converted_text = reassemble_srt(blocks)
            # 出力ファイルパスの決定
            base = os.path.splitext(os.path.basename(srt_filepath))[0]
            output_file = os.path.join(output_folder, base + "_converted.srt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(converted_text)
            self.log_message("変換が完了しました。出力ファイル: " + output_file)
        except Exception as e:
            self.log_message("エラーが発生しました: " + str(e))


if __name__ == "__main__":
    app = SRTConverterApp()
    app.mainloop()
