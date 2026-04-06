import os
import zipfile

def zip_dir(dir_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dir_path)
                try:
                    # Fix pre-1980 timestamps for Docker sandbox files
                    zinfo = zipfile.ZipInfo(arcname)
                    zinfo.date_time = (2026, 4, 4, 0, 0, 0)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    with open(file_path, "rb") as f:
                        zipf.writestr(zinfo, f.read())
                except Exception as e:
                    print(f"Error zipping {file_path}: {e}")

zip_dir(r"D:\Cosmo\backend\workspace", r"D:\Cosmo\workspace_benchmark_results.zip")
print("Zipped successfully!")
