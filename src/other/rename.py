import os


def batch_rename_pdfs(folder_path):
    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            new_name = filename.replace("2024-09-30__", "_2024-09-30_")
            if new_name != filename:  # 仅当文件名有变化时才重命名
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_name)
                os.rename(old_path, new_path)
                print(f"Renamed: {filename} → {new_name}")
# 使用示例

if __name__ == "__main__":
    folder_path = '../../result/report'

    batch_rename_pdfs(folder_path)
    print('批量重命名完成！')