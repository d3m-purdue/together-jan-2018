from google.protobuf.json_format import MessageToJson
from google.protobuf.json_format import Parse
import grpc
import json
import re
import tangelo
import time
import os
import d3mds
import csv
import shutil

import core_pb2 as core_pb2
import core_pb2_grpc as core_pb2_grpc

import core_pb2 as cpb
from core_pb2_grpc import CoreStub


@tangelo.restful
def post(op='', **kwargs):
    if op == '':
        return createPipeline(**kwargs)
    elif op == 'execute':
        return executePipeline(**kwargs)
    elif op == 'export':
        return exportPipeline(**kwargs)
    else:
        tangelo.http_status(404)


def toConstCase(s):
    def corner_cases(tag):
        if tag == 'MULTI_CLASS':
            return 'MULTICLASS'
        else:
            return tag

    return corner_cases('_'.join(map(lambda x: x.upper(), re.findall('[a-zA-Z][^A-Z]*', s))))


def get_stub():
  server_channel_address = os.environ.get('TA2_SERVER_CONN')
  # complain in the return if we didn't get an address to connect to
  if server_channel_address is None:
    tangelo.http_status(500)
    return {'error': 'TA2_SERVER_CONN environment variable is not set!'}
  channel = grpc.insecure_channel(server_channel_address)
  stub = core_pb2_grpc.CoreStub(channel)
  return stub



def createPipeline(context=None, data_uri=None, task_type=None, task_subtype=None, target_features=None, predict_features=[],metrics=None,max_pipelines=10):

  stub = get_stub()
  
  problem_schema_path = os.environ.get('PROBLEM_ROOT')
  problem_supply = d3mds.D3MProblem(problem_schema_path)

  # get the target features into the record format expected by the API
  targets =  problem_supply.get_targets()
  features = []
  for entry in targets:
    tf = core_pb2.Feature(resource_id=entry['resID'],feature_name=entry['colName'])
    features.append(tf)

  # we are having trouble parsing the problem specs into valid API specs, so just hardcode
  # to this problem type for now.  We could fix this with a lookup table to return valid API codes
  task = core_pb2.REGRESSION
  tasksubtype = core_pb2.UNIVARIATE

  # the metrics in the files are imprecise text versions of the enumerations, so just standardize.  A lookup table
  # would help here, too
  metrics=[core_pb2.ROC_AUC]

  context_in = cpb.SessionContext(session_id=context)

  request_in =  cpb.PipelineCreateRequest(context=context_in,
                                                          dataset_uri=data_uri,
                                                          task=task,
                                                          task_subtype=tasksubtype,
                                                          metrics=metrics,
                                                          task_description='Modsquad pipeline create request',
                                                          target_features=features,                                                       
                                                          predict_features=[],
                                                          max_pipelines=10)
  resp = stub.CreatePipelines(request_in)

  return map(lambda x: json.loads(MessageToJson(x)), resp)




def pipelineCreateResults(context=None, pipeline=None, data_uri=None):
    stub = get_stub()

    # add file descriptor if it is missing. some systems might be inconsistent, but file:// is the standard
    if data_uri[0:4] != 'file':
      data_uri = 'file://%s' % (data_uri)

    context_in = cpb.SessionContext(session_id=context)

    request_in = cpb.PipelineCreateResultsRequest(context=context_in,                      
                                                  pipeline_id=pipeline)
    resp = stub.GetCreatePipelineResults(request_in)
    return map(lambda x: json.loads(MessageToJson(x)), resp)




def executePipeline(context=None, pipeline=None, data_uri=None):
    stub = get_stub()

    # add file descriptor if it is missing. some systems might be inconsistent, but file:// is the standard
    if data_uri[0:4] != 'file':
      data_uri = 'file://%s' % (data_uri)

    context_in = cpb.SessionContext(session_id=context)

    request_in = cpb.PipelineExecuteRequest(context=context_in,                      
                                            pipeline_id=pipeline,
                                            dataset_uri=data_uri)
    resp = stub.ExecutePipeline(request_in)

    executedPipes =  map(lambda x: json.loads(MessageToJson(x)), resp)
    print executedPipes
    # now loop through the returned pipelines and copy their data
    map(lambda x: copyToWebRoot(x), executedPipes)
    return executedPipes


# read the CSV written out as the predicted result of a pipeline and return it as 
# a list of json dictionaries
def copyToWebRoot(returnRec=None):
    
    resultURI = returnRec['resultUri']
    print 'copying pipelineURI:',resultURI
    if resultURI is None:
        tangelo.http_status(500)
        return {'error': 'no resultURI for executed pipeline'}
    if resultURI[0:7] == 'file://':
        resultURI = resultURI[7:]
    
    # copy the results file under the webroot so it can be read by
    # javascript without having cross origin problems
    shutil.copy(resultURI,'pipelines')
    print 'copy completed'

    return resultURI



def exportPipeline(context=None, pipeline=None):
    stub = get_stub()
    context_in = cpb.SessionContext(session_id=context)

    # be sure to make a URI that matches where the TA2 will be able to write out during execution
    executables_root = os.environ.get('EXECUTABLES_ROOT')
    exec_name = '%s/modsquad-%s-%s-%f.executable' % (executables_root, context, pipeline, time.time())
    exec_uri = 'file://%s' % (exec_name)

    resp = stub.ExportPipeline(cpb.PipelineExportRequest(context=context_in,
                                                         pipeline_id=pipeline,
                                                         pipeline_exec_uri=exec_uri))

    return json.loads(MessageToJson(resp))
