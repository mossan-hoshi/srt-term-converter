import re
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, END


# 新規追加: タイムスタンプを秒に変換する関数
def parse_timestamp(ts_str):
    # ts_str例: "00:01:05,000"
    h, m, s_ms = ts_str.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


# 新規追加: 秒からタイムスタンプ文字列に変換する関数
def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# SRT解析関数: ブロックごとに番号、タイムスタンプ、テキストを抽出
def parse_srt(filepath):
    with Path(filepath).open("r", encoding="utf-8") as f:
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


# 各テキスト内に対して正規表現置換を1件ずつ実行（※1文字単位で処理）
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
        text = text[:start] + replacement + text[end:]
        index = start + len(replacement)
    return text


# SRT全体の変換処理：各ブロックのテキストを1文字ずつに分解し、正規表現置換を実施
# 変更: 1ブロック内の列数・行数指定に従ってブロックをグループ化するためのパラメータを追加
def convert_srt(filepath, regex_pairs, block_cols, block_rows):
    # 元のSRTブロックから文字単位のデータを作成
    original_blocks = parse_srt(filepath)
    char_data = []
    for block in original_blocks:
        ts_parts = block["timestamp"].split(" --> ")
        start_time = parse_timestamp(ts_parts[0])
        end_time = parse_timestamp(ts_parts[1])
        text = block["text"].replace("\n", "")
        if not text:
            continue
        duration = end_time - start_time
        char_duration = duration / len(text)
        for i, ch in enumerate(text):
            token_time = start_time + i * char_duration
            char_data.append({"timestamp": token_time, "text": ch})
    all_text = "".join(token["text"] for token in char_data)

    # 各パターンに対してall_text上で検索・置換を実施し、タイムスタンプを再計算
    for pattern, replacement in regex_pairs:
        new_all_text = ""
        new_char_data = []
        regex = re.compile(pattern)
        index = 0
        while index < len(all_text):
            m = regex.search(all_text, index)
            if not m:
                # 置換なし部分のコピー
                for token in char_data[index:]:
                    new_all_text += token["text"]
                    new_char_data.append(token)
                break
            # 置換対象外の部分をコピー
            for token in char_data[index : m.start()]:
                new_all_text += token["text"]
                new_char_data.append(token)
            # マッチ箇所の開始・終了タイミングを取得
            seg_start_time = char_data[m.start()]["timestamp"]
            seg_end_time = char_data[m.end() - 1]["timestamp"]
            rep_text = replacement
            rep_len = len(rep_text)
            if rep_len > 0:
                delta = (seg_end_time - seg_start_time) / rep_len
            else:
                delta = 0
            # 置換後の文字列に対してタイムスタンプを均等に割り当て
            for i, ch in enumerate(rep_text):
                new_token_time = seg_start_time + i * delta
                new_char_data.append({"timestamp": new_token_time, "text": ch})
                new_all_text += ch
            index = m.end()
        all_text = new_all_text
        char_data = new_char_data

    def is_ascii_letter(ch):
        return ch.isalpha() and ch.isascii()

    rows = []
    i = 0
    n = len(char_data)
    while i < n:
        end_idx = min(i + block_cols, n)
        # 延ばして、行末と次行の先頭がASCII文字なら単語を分割しない
        while (
            end_idx < n
            and is_ascii_letter(char_data[end_idx - 1]["text"])
            and is_ascii_letter(char_data[end_idx]["text"])
        ):
            end_idx += 1
        rows.append(char_data[i:end_idx])
        i = end_idx

    row_texts = ["".join(token["text"] for token in row) for row in rows]
    # 各行の開始・終了タイムスタンプ（行が空でない前提）
    row_timestamps = [
        (row[0]["timestamp"], row[-1]["timestamp"]) for row in rows if row
    ]
    # block_rows 行ごとにグループ化してブロック作成
    new_blocks = []
    new_id = 1
    for i in range(0, len(row_texts), block_rows):
        block_lines = row_texts[i : i + block_rows]
        # グループ内の最初の行と最後の行のタイムスタンプを使用
        start_t = row_timestamps[i][0]
        end_t = row_timestamps[min(i + block_rows, len(row_timestamps)) - 1][1]
        text_block = "\n".join(block_lines)
        timestamp_str = f"{format_timestamp(start_t)} --> {format_timestamp(end_t)}"
        new_blocks.append(
            {"id": str(new_id), "timestamp": timestamp_str, "text": text_block}
        )
        new_id += 1
    return new_blocks


# GUIアプリケーション
class SRTConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SRT Term Converter")
        self.geometry("700x600")
        self.csv_path = Path("./replace_terms.csv")  # CSVファイルパス

        # SRTファイル入力
        self.srt_path_entry = ctk.CTkEntry(self, placeholder_text="SRTファイルパス")
        self.srt_path_entry.grid(row=0, column=0, padx=10, pady=10, sticky="we")
        self.srt_browse_btn = ctk.CTkButton(self, text="参照", command=self.browse_srt)
        self.srt_browse_btn.grid(row=0, column=1, padx=10, pady=10)

        # 出力フォルダ選択
        self.output_path_entry = ctk.CTkEntry(self, placeholder_text="出力フォルダパス")
        self.output_path_entry.grid(row=1, column=0, padx=10, pady=10, sticky="we")
        self.output_path_entry.insert(0, "./outputs/")
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
        # CSVから辞書内容を読み込み
        self.load_dictionary()

        # 辞書保存ボタン（任意保存用）
        self.save_dict_btn = ctk.CTkButton(
            self, text="辞書保存", command=self.save_dictionary
        )
        self.save_dict_btn.grid(row=3, column=2, padx=10, pady=10)

        # 新規追加: 出力ブロックサイズの指定（列数・行数）
        ctk.CTkLabel(self, text="ブロックの列数 (1行あたりの最大文字数)").grid(
            row=4, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.block_cols_entry = ctk.CTkEntry(self)
        self.block_cols_entry.grid(row=4, column=1, padx=10, pady=(10, 0))
        self.block_cols_entry.insert(0, "35")
        ctk.CTkLabel(self, text="ブロックの行数 (1ブロックあたりの最大行数)").grid(
            row=5, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.block_rows_entry = ctk.CTkEntry(self)
        self.block_rows_entry.grid(row=5, column=1, padx=10, pady=(10, 0))
        self.block_rows_entry.insert(0, "2")

        # 変換実行ボタン
        self.execute_btn = ctk.CTkButton(
            self, text="変換実行", command=self.execute_conversion
        )
        self.execute_btn.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        # エラー表示エリア
        ctk.CTkLabel(self, text="エラー/メッセージ").grid(
            row=7, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.error_textbox = ctk.CTkTextbox(self, width=400, height=100)
        self.error_textbox.grid(row=8, column=0, columnspan=2, padx=10, pady=10)

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

    def load_dictionary(self):
        # CSVファイルから読み込み、テキストボックスに「pattern => replacement」形式で表示
        if self.csv_path.is_file():
            with self.csv_path.open("r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            self.dict_textbox.delete("1.0", END)
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split(",", 1)
                pattern = parts[0].strip()
                replacement = parts[1].strip() if len(parts) > 1 else ""
                self.dict_textbox.insert(END, f"{pattern} => {replacement}\n")
        else:
            self.dict_textbox.insert(END, r"\bteh\b => the\n")

    def save_dictionary(self):
        # テキストボックスの内容をCSV形式（「pattern,replacement」）に変換して保存
        content = self.dict_textbox.get("1.0", END).strip().splitlines()
        csv_lines = []
        for idx, line in enumerate(content, start=1):
            if "=>" not in line:
                continue  # 不正な行は無視
            parts = line.split("=>", 1)
            pattern = parts[0].strip()
            replacement = parts[1].strip()
            csv_lines.append(f"{pattern},{replacement}")
        self.csv_path.write_text("\n".join(csv_lines), encoding="utf-8")

    def execute_conversion(self):
        self.error_textbox.delete("1.0", END)
        srt_filepath = self.srt_path_entry.get().strip()
        output_folder = self.output_path_entry.get().strip()
        srt_path = Path(srt_filepath)
        output_folder_path = Path(output_folder)
        if not srt_path.is_file():
            self.log_message("有効なSRTファイルを指定してください。")
            return
        if not output_folder_path.is_dir():
            self.log_message("有効な出力フォルダを指定してください。")
            return

        # 辞書保存：テキストボックスの内容をCSVファイルへ自動保存
        self.save_dictionary()

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
            block_cols = int(self.block_cols_entry.get().strip())
            block_rows = int(self.block_rows_entry.get().strip())
        except ValueError:
            self.log_message("ブロックの列数と行数は整数で指定してください。")
            return

        try:
            blocks = convert_srt(srt_filepath, regex_pairs, block_cols, block_rows)
            converted_text = reassemble_srt(blocks)
            base = srt_path.stem
            output_file = output_folder_path / (base + "_converted.srt")
            output_file.write_text(converted_text, encoding="utf-8")
            self.log_message("変換が完了しました。出力ファイル: " + str(output_file))
        except Exception as e:
            self.log_message("エラーが発生しました: " + str(e))


if __name__ == "__main__":
    app = SRTConverterApp()
    app.mainloop()
