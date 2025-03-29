import os
import re
import sys


def remove_spaces_from_text_lines(input_file, output_dir_path):
    # Ensure the output directory exists.
    os.makedirs(output_dir_path, exist_ok=True)
    # Use the same base filename for the output file.
    output_file = os.path.join(output_dir_path, os.path.basename(input_file))

    with open(input_file, encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            # タイムコード行（先頭が2桁＋コロン）ならそのまま出力
            if re.match(r"^\d\d:", line):
                f.write(line)
            else:
                # 空白（ホワイトスペース）の削除
                # 改行は残るように、一度rstrip()で改行を取り、処理後に改行を追加
                stripped = line.rstrip("\n")
                new_line = re.sub(r"\s+", "", stripped)
                f.write(new_line + "\n")


if __name__ == "__main__":
    # Usage: python elevenlabs.py <input_file> [<output_dir_path>]
    if not (2 <= len(sys.argv) <= 3):
        print("Usage: python elevenlabs.py <input_file> [<output_dir_path>]")
        sys.exit(1)

    input_path = sys.argv[1]
    # Default output directory is ./outputs/elevenlabs/ if not provided.
    output_dir_path = sys.argv[2] if len(sys.argv) == 3 else "./outputs/elevenlabs/"
    remove_spaces_from_text_lines(input_path, output_dir_path)
