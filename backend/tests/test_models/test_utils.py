import pathlib

from api import config

from api.models._utils import fix_output_dir


def test_fix_output_dir():
    output_path_one = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(2) + config.PIPELINE_OUTPUT_SUF_DIR
    output_path_two = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(78) + config.PIPELINE_OUTPUT_SUF_DIR
    output_path_n = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(20187) + config.PIPELINE_OUTPUT_SUF_DIR

    result_path_one = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(1) + config.PIPELINE_OUTPUT_SUF_DIR
    result_path_two = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(77) + config.PIPELINE_OUTPUT_SUF_DIR
    result_path_n = config.PIPELINE_OUTPUT_PRE_DIR + \
        str(20186) + config.PIPELINE_OUTPUT_SUF_DIR

    output_list = [output_path_one, output_path_two, output_path_n]
    result_list = [result_path_one, result_path_two, result_path_n]

    for output, result in zip(output_list, result_list):
        src_dir = pathlib.Path(output).resolve()
        converted_path = fix_output_dir(src_dir)
        assert converted_path == result
