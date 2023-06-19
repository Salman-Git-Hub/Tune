import os
import shutil


def remove_pycache(path):
    count = 0
    for file in os.listdir(path):
        t_path = os.path.join(path, file)
        if os.path.isdir(t_path):
            if file == "__pycache__":
                count += 1
                shutil.rmtree(t_path, ignore_errors=True)
                return count
            count += remove_pycache(t_path)
            continue
    return count


def clear_cache():
    return remove_pycache(os.getcwd())
