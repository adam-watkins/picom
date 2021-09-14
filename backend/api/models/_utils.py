import pathlib
from shutil import copytree

from . import NestedPathMixin, IOPathMixin


def fix_output_dir(src_dir) -> str:
    """
    Since pipeline_jobs automatically creates a folder for next input/output,
    there is a mismatch when copying the final jobs output to runs output
    To fix this issue, the path is deconstructed and the id is decremented once
    """
    src_dir = str(src_dir)
    id_pos = 0
    dir_split = src_dir.split('/')
    for idx, word in enumerate(dir_split):
        if word.isdigit():
            id_pos = idx
    dir_split[id_pos] = str(int(dir_split[id_pos]) - 1)
    new_dir = '/'.join(dir_split)

    return new_dir


def copy_model_fs(src: NestedPathMixin, dst: IOPathMixin, dst_subdir='input', src_subdir='output', final_node=False):
    """
    This function can be used to copy a model underlying folder (eg: a input or output folder) to the underlying folder
    of another model
    """
    if src_subdir not in ['input', 'output']:
        ValueError('src_subdir kwarg can only be "input" or "output"')
    if dst_subdir not in ['input', 'output']:
        ValueError('dst_subdir kwarg can only be "input" or "output"')
    src_dir = pathlib.Path(src.get_abs_path(subdir=src_subdir)).resolve()
    dst_dir = pathlib.Path(dst.get_abs_path(subdir=dst_subdir)).resolve()

    # Test fails due to pathing issues, commented until solution is found
    # if final_node:
    #     src_dir = fix_output_dir(src_dir)

    print(f"COPYING {src_dir} to {dst_dir}")
    copytree(src_dir, dst_dir, dirs_exist_ok=True)


def strip_prefix(str_: str, prefix: str):
    if str_.startswith(prefix):
        str_ = str_[len(prefix):]

    return str_
