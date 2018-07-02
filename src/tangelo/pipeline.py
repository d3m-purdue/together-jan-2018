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
import pprint

import core_pb2 as core_pb2
import core_pb2_grpc as core_pb2_grpc

import core_pb2 as cpb
from core_pb2_grpc import CoreStub

import problem_pb2
import value_pb2

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


def metricLookup(metricString, task_type):
  # classification metrics
  if (metricString == 'accuracy'):
    print 'accuracy metric'
    return problem_pb2.ACCURACY
  if (metricString == 'f1'):
    print 'f1 metric'
    return problem_pb2.F1
  if (metricString == 'f1Macro'):
    print 'f1-macro metric'
    return problem_pb2.F1_MACRO
  if (metricString == 'f1Micro'):
    print 'f1-micro metric'
    return problem_pb2.F1_MICRO
  if (metricString == 'ROC_AUC'):
    print 'roc-auc metric'
    return problem_pb2.ROC_AUC
  if (metricString == 'rocAuc'):
    print 'rocAuc metric'
    return problem_pb2.ROC_AUC
  if (metricString == 'rocAucMicro'):
    print 'roc-auc-micro metric'
    return problem_pb2.ROC_AUC_MICRO
  if (metricString == 'rocAucMacro'):
    print 'roc-auc-macro metric'
    return problem_pb2.ROC_AUC_MACRO
  # clustering
  if (metricString == 'normalizedMutualInformation'):
    print 'normalized mutual information metric'
    return problem_pb2.NORMALIZED_MUTUAL_INFORMATION
  if (metricString == 'jaccardSimilarityScore'):
    print 'jaccard similarity metric'
    return problem_pb2.JACCARD_SIMILARITY_SCORE
  # regression
  if (metricString == 'meanSquaredError'):
    print 'MSE metric'
    return problem_pb2.MEAN_SQUARED_ERROR
  if (metricString == 'rootMeanSquaredError'):
    print 'RMSE metric'
    return problem_pb2.ROOT_MEAN_SQUARED_ERROR
  if (metricString == 'rootMeanSquaredErrorAvg'):
    print 'RMSE Average metric'
    return problem_pb2.ROOT_MEAN_SQUARED_ERROR_AVG
  if (metricString == 'rSquared'):
    print 'rSquared metric'
    return problem_pb2.R_SQUARED
  if (metricString == 'meanAbsoluteError'):
    print 'meanAbsoluteError metric'
    return problem_pb2.MEAN_ABSOLUTE_ERROR
  # we don't recognize the metric, assign a value to the unknown metric according to the task type. 
  else:
    print 'undefined metric received, so assigning a metric according to the task type'
    if task_type==problem_pb2.CLASSIFICATION:
      print 'classification: assigning f1Macro'
      return problem_pb2.F1_MACRO
    elif task_type==problem_pb2.CLUSTERING:
      print 'clustering: assigning normalized mutual information'
      return problem_pb2.NORMALIZED_MUTUAL_INFORMATION
    else:
      print 'regression: assigning RMSE'
      return problem_pb2.ROOT_MEAN_SQUARED_ERROR

def make_target(spec):
    return problem_pb2.ProblemTarget(
            target_index = spec['targetIndex'],
            resource_id = spec['resID'],
            column_index = spec['colIndex'],
            column_name = spec['colName'])

def taskTypeLookup(task):
  if (task=='classification'):
    print 'detected classification task'
    return problem_pb2.CLASSIFICATION
  elif (task == 'clustering'):
    print 'detected clustering task'
    return problem_pb2.CLUSTERING
  else:
    print 'assuming regression'
    return problem_pb2.REGRESSION

def subTaskLookup(sub):
  if (sub == 'multiClass'):
    print 'multiClass subtype'
    return problem_pb2.MULTICLASS
  if (sub == 'multivariate'):
    return problem_pb2.MULTIVARIATE
  if (sub == 'univariate'):
    return problem_pb2.UNIVARIATE
  else:
    print 'assuming NONE subtask'
    return problem_pb2.NONE


def createPipeline(data_uri=None):
  stub = get_stub()

  problem_schema_path = os.environ.get('PROBLEM_ROOT')
  problem_supply = d3mds.D3MProblem(problem_schema_path)

  dataset_schema_path = os.environ.get('TRAINING_DATA_ROOT')
  dataset_supply = d3mds.D3MDataset(dataset_schema_path)

  # get the target features into the record format expected by the API
  targets =  problem_supply.get_targets()
  # features = []
  # for entry in targets:
    # tf = core_pb2.Feature(resource_id=entry['resID'],feature_name=entry['colName'])
    # features.append(tf)

  # we are having trouble parsing the problem specs into valid API specs, so just hardcode
  # to certain problem types for now.  We could fix this with a more general lookup table to return valid API codes
  # task = taskTypeLookup(task_type)
  # tasksubtype = subTaskLookup(task_subtype)

  # the metrics in the files are imprecise text versions of the enumerations, so just standardize.  A lookup table
  # would help here, too
  # metrics=[core_pb2.F1_MICRO, core_pb2.ROC_AUC, core_pb2.ROOT_MEAN_SQUARED_ERROR, core_pb2.F1, core_pb2.R_SQUARED]

  # context_in = cpb.SessionContext(session_id=context)

  # problem_pb = Parse(json.dumps(problem_supply.prDoc), problem_pb2.ProblemDescription(), ignore_unknown_fields=True)
  problem = problem_pb2.Problem(
    id = problem_supply.get_problemID(),
    version = problem_supply.get_problemSchemaVersion(),
    name = 'modsquad_problem',
    description = 'amaaaazing problem',
    task_type = taskTypeLookup(problem_supply.get_taskType()),
    task_subtype = subTaskLookup(problem_supply.get_taskSubType()),
    performance_metrics = map(lambda x: problem_pb2.ProblemPerformanceMetric(metric=metricLookup(x['metric'], problem_supply.get_taskType())), problem_supply.get_performance_metrics()))

  value = value_pb2.Value(dataset_uri=data_uri)
  req = core_pb2.SearchSolutionsRequest(
          user_agent='modsquad',
          version="2018.6.2",
          time_bound=1,
          problem=problem_pb2.ProblemDescription(
              problem=problem,
              inputs=[problem_pb2.ProblemInput(
                  dataset_id=dataset_supply.get_datasetID(),
                  targets=map(make_target, problem_supply.get_targets()))]),
          inputs=[value])
  resp = stub.SearchSolutions(req)

  # return map(lambda x: json.loads(MessageToJson(x)), resp)
  search_id = json.loads(MessageToJson(resp))['searchId']

  # Get actual pipelines.
  req = core_pb2.GetSearchSolutionsResultsRequest(search_id=search_id)
  results = stub.GetSearchSolutionsResults(req)
  results = map(lambda x: json.loads(MessageToJson(x)), results)

  stub.StopSearchSolutions(core_pb2.StopSearchSolutionsRequest(search_id=search_id))

  return results

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

    # context_in = cpb.SessionContext(session_id=context)

    input = value_pb2.Value(dataset_uri=data_uri)
    request_in = cpb.FitSolutionRequest(solution_id=pipeline,
                                        inputs=[input])
    resp = stub.FitSolution(request_in)

    resp = json.loads(MessageToJson(resp))
    pprint.pprint(resp)

    fittedPipes = stub.GetFitSolutionResults(core_pb2.GetFitSolutionResultsRequest(request_id=resp['requestId']))
    # print list(fittedPipes)
    # fittedPipes = map(lambda x: MessageToJson(x), fittedPipes)
    # for f in fittedPipes:
        # f['fittedSolutionId'] = json.loads(f['fittedSolutionId'])

    fittedPipes = list(fittedPipes)
    # map(pprint.pprint, fittedPipes)
    # map(lambda x: pprint.pprint(MessageToJson(x)), fittedPipes)

    pipes = []
    for f in fittedPipes:
        # f = json.loads(MessageToJson(f))
        pprint.pprint(f)

        pipes.append(json.loads(MessageToJson(f)))

    executedPipes = map(lambda x: stub.ProduceSolution(core_pb2.ProduceSolutionRequest(
        fitted_solution_id=x['fittedSolutionId'],
        inputs=[input])), filter(lambda x: x['progress']['state'] == 'COMPLETED', pipes))

    # executedPipes = map(lambda x: json.loads(MessageToJson(x)), executedPipes)

    pprint.pprint(executedPipes)

    results = map(lambda x: stub.GetProduceSolutionResults(core_pb2.GetProduceSolutionResultsRequest(request_id=x.request_id)), executedPipes)

    pprint.pprint(results)
    exposed = []
    for r in results:
        for rr in r:
            #pprint.pprint(rr)
            #pprint.pprint(MessageToJson(rr))

            exposed.append(json.loads(MessageToJson(rr)))

    exposed = filter(lambda x: x['progress']['state'] == 'COMPLETED', exposed)
    pprint.pprint(exposed)

    # now loop through the returned pipelines and copy their data
    map(lambda x: copyToWebRoot(x), exposed)
    return exposed


# read the CSV written out as the predicted result of a pipeline and return it as 
# a list of json dictionaries
def copyToWebRoot(returnRec=None):
    
    resultURI = returnRec['exposedOutputs']['outputs.0']['csvUri']
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
