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
import copy

import core_pb2 as core_pb2
import core_pb2_grpc as core_pb2_grpc

import core_pb2 as cpb
from core_pb2_grpc import CoreStub

import problem_pb2
import value_pb2

@tangelo.restful
def get(op='',**kwargs):
  if op == 'results':
    return serveDataFromLocation(**kwargs)
  else:
     tangelo.http_status(404)


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
  elif (task == 'objectDetection'):
    print 'detected object detection task'
    return problem_pb2.OBJECT_DETECTION
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


# process the spec file and generate a new one with any inactive variables not included
def generate_modified_database_spec(original,modified,inactive):
  # read the schema in dsHome
  _dsDoc = os.path.join(original, 'datasetDoc.json')
  assert os.path.exists(_dsDoc)
  with open(_dsDoc, 'r') as f:
    dsDoc = json.load(f)
    outDoc = {}
    outDoc['about'] = dsDoc['about']
    # loop through the resources and add them to the output spec if the feature is not inactive
    outDoc['dataResources'] = []
    for resource in dsDoc['dataResources']:
      # We moved only the dataset spec, update the paths to have an absolute path to the
      # original content
      resource['resPath'] = os.path.join(original, resource['resPath'])
      # pass things besides tables through automatically. tables have a list of features
      if resource['resType'] != 'table':
        outDoc['dataResources'].append(resource)
      else:
        # if it is a table, copy the header information, but clear out the column names and only
        # add columns that are not listed in the inactive list.  Inactive entries won't be added. 
        resourceOut = copy.deepcopy(resource)
        resourceOut['columns'] = []
        for column in resource['columns']:
          if column['colName'] not in inactive:
            # pass this feature record to the output columns 
            resourceOut['columns'].append(column)
        outDoc['dataResources'].append(resourceOut)
    # now the updated dataset spec will be written out to the write-enabled new location
    outFileName = os.path.join(modified, 'datasetDoc.json')
    assert os.path.exists(_dsDoc)
    with open(outFileName,'w') as outfile:
      json.dump(outDoc, outfile)


# called to start a search for solutions to this problem.  The URI is passed so it can 
# be sent to the TA2 (changed first, if necessary)
def createPipeline(data_uri=None,inactive=None,time_limit=1):
  stub = get_stub()

  problem_schema_path = os.environ.get('PROBLEM_ROOT')
  problem_supply = d3mds.D3MProblem(problem_schema_path)

  # get a pointer to the original dataset description doc
  dataset_schema_path = os.environ.get('TRAINING_DATA_ROOT')

  # if the user has elected to ignore some variables, then generate a modified spec
  # and load from the modified spec

  if inactive != None:
    print 'detected inactive variables:', inactive
    modified_dataset_schema_path = '/output/supporting_files'
    generate_modified_database_spec(dataset_schema_path,modified_dataset_schema_path, inactive)
    dataset_supply = d3mds.D3MDataset(modified_dataset_schema_path)
  else:
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

  # currently HTTP timeout occurs after 2 minutes (probably from , so clamp this value to 2 minutes temporarily)
  #print 'clamping search time to 2 minutes to avoid timeouts'
  #time_limit = min(2,int(time_limit))
  

  problem = problem_pb2.Problem(
    id = problem_supply.get_problemID(),
    version = problem_supply.get_problemSchemaVersion(),
    name = 'modsquad_problem',
    description = 'modsquad problem',
    task_type = taskTypeLookup(problem_supply.get_taskType()),
    task_subtype = subTaskLookup(problem_supply.get_taskSubType()),
    performance_metrics = map(lambda x: problem_pb2.ProblemPerformanceMetric(metric=metricLookup(x['metric'], problem_supply.get_taskType())), problem_supply.get_performance_metrics()))

  value = value_pb2.Value(dataset_uri=data_uri)
  req = core_pb2.SearchSolutionsRequest(
          user_agent='modsquad',
          #version=core_pb2.protcol_version,
          version="2018.7.7",
          time_bound=int(time_limit),
          problem=problem_pb2.ProblemDescription(
              problem=problem,
              inputs=[problem_pb2.ProblemInput(
                  dataset_id=dataset_supply.get_datasetID(),
                  targets=map(make_target, problem_supply.get_targets()))]),
          inputs=[value])
  resp = stub.SearchSolutions(req)
  print 'set time bound to be: ',time_limit,' minutes'
  print 'using hard-coded version 2018.7.7 of the API. Should pull from the proto files instead'

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
    print 'fitted pipes:'
    map(lambda x: pprint.pprint(MessageToJson(x)), fittedPipes)

    pipes = []
    for f in fittedPipes:
        # f = json.loads(MessageToJson(f))
        #pprint.pprint(f)
        pipes.append(json.loads(MessageToJson(f)))

    fitted_solution_id = map(lambda x: x['fittedSolutionId'],filter(lambda x: x['progress']['state'] == 'COMPLETED', pipes))
    print 'fitted_solution_id', fitted_solution_id

    executedPipes = map(lambda x: stub.ProduceSolution(core_pb2.ProduceSolutionRequest(
        fitted_solution_id=x['fittedSolutionId'],
        inputs=[input])), filter(lambda x: x['progress']['state'] == 'COMPLETED', pipes))

    # executedPipes = map(lambda x: json.loads(MessageToJson(x)), executedPipes)
    #print 'executed pipes:'
    #pprint.pprint(executedPipes)

    results = map(lambda x: stub.GetProduceSolutionResults(core_pb2.GetProduceSolutionResultsRequest(request_id=x.request_id)), executedPipes)

    #print 'results is:'
    #pprint.pprint(results)
    exposed = []
    for r in results:
        for rr in r:
            #pprint.pprint(rr)
            #pprint.pprint(MessageToJson(rr))

            exposed.append(json.loads(MessageToJson(rr)))

    exposed = filter(lambda x: x['progress']['state'] == 'COMPLETED', exposed)
    #pprint.pprint(exposed)

    # the loop through the returned pipelines to copy their data
    # is not used anymore. Tngelo
    #map(lambda x: copyToWebRoot(x), exposed)
    return {'exposed': exposed, 'fitted_solution_id':fitted_solution_id}
    # magic saved here: return [{exposed: v[0], fitted_id: v[1]} for v in zip(exposed, fitted_solution_id)]


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


# read the CSV written out as the predicted result of a pipeline and return it as
# a list of json dictionaries
def serveDataFromLocation(resultURI=None):

    print 'copying pipelineURI:',resultURI
    if resultURI is None:
        tangelo.http_status(500)
        return {'error': 'no resultURI for executed pipeline'}
    if resultURI[0:7] == 'file://':
        resultURI = resultURI[7:]

    # copy the results file under the webroot so it can be read by
    # javascript without having cross origin problems
    with open(resultURI,'r') as f:
      content = f.read()
      f.close()
      return content

# this is a global variable used by the method below.  It represents the
# "ranking" value of solutions selected by the user.  rank=1 is the highest, with
# successive rankings (2,3,etc.) corresponding to lower quality model fits
globalNextRankToUse = 1


# send a message to the modeling engine that the user has chosen to output
# a solution.  The fiddedID is passed as the pipeline argument in the call. The
# caller can optionally overload
def exportPipeline(context=None, pipeline=None, rankInput=None):
    global globalNextRankToUse
    stub = get_stub()

    # if there was a rank input to this call, use that rank, otherwise
    # increment a global ranked value each time this method is called.
    # This way, successfive exports will have increasing rank numbers (1,2,3,etc.)
    if rankInput:
      rankToOutput = int(rankInput)
      globalNextRankToUse = rankInput + 1
    else:
      rankToOutput = int(globalNextRankToUse)
      # increment the global counter so the next use will have a higher rank
      globalNextRankToUse += 1

    request_in = cpb.SolutionExportRequest(fitted_solution_id=pipeline,
                                        rank=int(rankToOutput))

    print 'requesting solution export:', request_in
    resp = stub.SolutionExport(request_in)

    return json.loads(MessageToJson(resp))
