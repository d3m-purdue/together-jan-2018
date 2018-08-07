import json
import os
import tangelo


def run():
    config_file = os.environ.get('JSON_CONFIG_PATH')
    print 'environment variable said:',config_file
    #config_file = "/Users/clisle/proj/D3M/code/eval/config.json"
    print 'config service: looking for config file..',config_file
    if config_file is None:
        tangelo.http_status(500)
        return {'error': 'JSON_CONFIG_PATH is not set!'}

    try:
        with open(config_file) as f:
            text = f.read()
    except IOError as e:
        tangelo.http_status(500)
        return {'error': str(e)}

    try:
        config = json.loads(text)
    except ValueError as e:
        tangelo.http_status(500)
        return {'error': 'Could not parse JSON - %s' % (str(e))}

    # clean up the output filesystem to remove any files from old runs
    try:
        os.system('rm -rf /output/*')
        os.mkdir('/output/pipelines')
        os.mkdir('/output/executables')
        os.mkdir('/output/supporting_files')
        os.mkdir('/output/predictions')
    except:
        pass

    print 'received json configuration:',config

    os.environ['PROBLEM_SCHEMA_PATH'] = config['problem_schema']
    os.environ['DATASET_SCHEMA_PATH'] = config['dataset_schema']
    os.environ['TRAINING_DATA_ROOT'] = config['training_data_root']
    os.environ['PROBLEM_ROOT'] = config['problem_root']
    os.environ['EXECUTABLES_ROOT'] = config['executables_root']
    # used by the ta2read service
    os.environ['TEMP_STORAGE_ROOT'] = config['temp_storage_root']
    return config
