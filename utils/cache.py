import os
import shutil

count = 0


def remove_pycache(path):
    global count
    for file in os.listdir(path):
        t_path = os.path.join(path, file)
        if os.path.isdir(t_path):
            if file == "__pycache__":
                count += 1
                shutil.rmtree(t_path, ignore_errors=True)
                return count
            count += remove_pycache(t_path)
            continue
    return 0


def clear_cache():
    remove_pycache(os.getcwd())
    return count
