import pathlib
from shutil import copytree

from api import config
from . import NestedPathMixin, IOPathMixin


def fix_output_dir(src_dir) -> str:
    """
    Since pipeline_jobs automatically creates a folder for next input/output,
    there is a mismatch when copying the final jobs output to runs output
    To fix this issue, the path is deconstructed and the id is decremented once
    """

    src_dir = str(src_dir)
    src_prefix = src_dir[:len(config.PIPELINE_OUTPUT_PRE_DIR)]
    src_suffix = src_dir[-len(config.PIPELINE_OUTPUT_SUF_DIR):]
    src_id = src_dir[:-len(config.PIPELINE_OUTPUT_SUF_DIR)
                     ][len(config.PIPELINE_OUTPUT_PRE_DIR):]
    src_id = int(src_id) - 1
    src_dir = src_prefix + str(src_id) + src_suffix

    return src_dir


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

    if final_node:
        # TODO: Write a test case to verify correctness
        src_dir = fix_output_dir(src_dir)

    print(f"COPYING {src_dir} to {dst_dir}")
    copytree(src_dir, dst_dir, dirs_exist_ok=True)


def strip_prefix(str_: str, prefix: str):
    if str_.startswith(prefix):
        str_ = str_[len(prefix):]

    return str_
