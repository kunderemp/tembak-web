# -----------------------------------------------------------
# Running Performance Test for HTTP request
#
# (C) 2020 Narpati Wisjnu Ari Pradana, Jakarta, Indonesia
# -----------------------------------------------------------

#import requests

from datetime import timedelta
from datetime import datetime
from datetime import timezone
import asyncio
import argparse
import commentjson
import h11
import httpcore
import httpx
import io
import json
import jsonpath_ng
import logging
import math
import os
import random
import re
import shutil
import signal
import string
import sys

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.NOTSET)
logging.getLogger("urllib3").setLevel(logging.WARNING)
timeout = httpx.Timeout(60.0, connect=20)

the_requests = []
static_variables = {}
dynamic_variables = []
request_processed = 0
process_id_sequence = 0
max_request_processed = 0
last_milestone_request_processed = 0
result_records = []
jakartatd = timedelta(hours=7)
jakartatz = timezone(jakartatd, name="Asia/Jakarta")
progress_step_size=2
milestone_size=math.ceil(100 / progress_step_size)

temp_total_duration = timedelta(microseconds=0)
temp_min_duration = timedelta.max
temp_max_duration = timedelta.min
temp_per_request = []
temp_per_ok_request = []

start_all_process_timestamp = datetime.now(tz=jakartatz)

def copy_dict(current_dict):
  dict_copy = current_dict.copy()
  for a in dict_copy:
    if dict_copy[a] is not None :

      if isinstance(dict_copy[a], dict):
        dict_copy[a] = copy_dict(dict_copy[a])
      elif isinstance(dict_copy[a], list):
        new_list = []
        old_list = dict_copy[a]
        dict_copy[a] = new_list
        #print("len old list: " + str(len(old_list)))
        for i in range(len(old_list)):
          #print("i: " + str(i))
          if isinstance(old_list[i], dict):
              list_object = old_list[i]
              new_list.append(copy_dict(list_object))
          else:
              new_list.append(old_list[i])



  return dict_copy



class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

class ResultPerRequest:
    def __init__ (self, starttime, endtime, timedelta, request, result):
      self.starttime=starttime
      self.endtime=endtime
      self.duration=timedelta
      self.request=request
      self.result=result

    def __str__(self):
      strdict = {}
      strdict['starttime'] = str(self.starttime)
      strdict['endtime'] = str(self.endtime)
      strdict['duration'] = str(self.duration)

      requestdict = {}
      requestdict['method'] = self.request.method
      if self.request.header is not None:
        requestdict['header'] = self.request.header
      if self.request.data is not None:
        requestdict['data'] = self.request.data
      requestdict['url'] = self.request.url
      strdict['request'] = requestdict

      resultdict = {}
      if self.result is not None:
        resultdict['status_code'] = self.result.status_code
        resultdict['text'] = self.result.text
        resultdict['url'] = self.result.url
        try:
          resultdict['reason'] = self.result.reason
        except AttributeError:
          resultdict['reason'] = ""

      strdict['results'] = resultdict
      #return json.dumps(json.dumps(strdict, indent=2))
      #return json.dumps(strdict)
      return str(strdict)

class ResultData:
    def __init__(self, starttime, endtime, timedelta, results_per_request):
      self.starttime=starttime
      self.endtime=endtime
      self.duration=timedelta
      self.results_per_request=results_per_request

    def __str__(self):
      strseries = []
      strdict = {}
      strdict['starttime'] = str(self.starttime)
      strdict['endtime'] = str(self.endtime)
      strdict['duration'] = str(self.duration)
      strseries.append("------------------------------------------------------------------------------\n")
      strseries.append(str(strdict))
      strseries.append("\n|        detail request                                                        |")

      resultsdict = []
      for result_per_request in self.results_per_request:
        resultsdict.append(str(result_per_request))
        strseries.append("\n")
        strseries.append(str(result_per_request))
      strseries.append("\n------------------------------------------------------------------------------\n")
      #strdict['results-per-request'] = resultsdict;
      #return json.dumps(json.dumps(strdict, indent=2))
      #return str(strdict)
      return "".join(strseries)

class RequestEntry:

    def __init__(self, method,url,header,data,files,expected_response_type=None,extract=None,required=None, is_prerequisite=False):
      self.method=method
      self.url=url
      self.header=header
      self.data=data
      self.files=files
      self.expected_response_type=expected_response_type
      self.extract=extract
      self.required=required
      self.is_prerequisite=is_prerequisite
    def __str__(self):
     if self.data is None:
       return "method:" + self.method + " url:" + self.url + "\nheader:" + str(self.header) + "\nis_prerequisite:" + str(self.is_prerequisite)
     else:
       return "method:" + self.method + " url:" + self.url + "\nheader:" + str(self.header) + "\ndata:" + str(self.data) + "\nis_prerequisite:" + str(self.is_prerequisite)




def initiateRequests(request_json):
  data = None
  files = None
  expected_response_type = None
  extract = None
  required = None
  is_prerequisite = False
  if 'data' in request_json:
    data = request_json['data']
  if 'files' in request_json:
    #files = []
    #for curr_file in request_json['files']:
    #  temp_file_value = (curr_file['field-name'],(curr_file['file-name'],open(curr_file['file-name'],'rb'),curr_file['content-type']))
    #  files.append(temp_file_value)
    files = request_json['files']
    logging.debug("selesai file")
    logging.debug(files)
  if 'expected_response_type' in request_json:
    expected_response_type = request_json['expected_response_type']
  if 'extract' in request_json:
    extract = request_json['extract']
  if 'required' in request_json:
    required = request_json['required']
  if 'is_prerequisite' in request_json:
    is_prerequisite = request_json['is_prerequisite']
  theRequest = RequestEntry(request_json['method'], request_json['url'], request_json['header'], data,files, 
      expected_response_type, extract, required, is_prerequisite)
  return theRequest

def initiateStaticVariable(static_variable_json):
  for key in static_variable_json:
    value = static_variable_json[key]
    static_variables[key] = value

def initiateDynamicVariable(dynamic_variable_json):
  labels = []
  if 'names' in dynamic_variable_json and isinstance(dynamic_variable_json['names'], list):
    for name in dynamic_variable_json['names']:
      labels.append(name)
  if 'values' in dynamic_variable_json and isinstance(dynamic_variable_json['values'], list):
    dynamic_variable = {}
    dynamic_variable["labels"] = labels
    variable_list = []
    for valuerow in dynamic_variable_json['values']:
      if isinstance(valuerow, list) and len(valuerow) == len(labels):
        variable_rows= {}
        for index in range(len(valuerow)):
          label = labels[index]
          value = valuerow[index]
          variable_rows[label] = value
        variable_list.append(variable_rows)
          
      elif isinstance(valuerow, list):
        logging.info('labels: '+ str(labels) + ' current row number of values: ' + str(len(valuerow)))
        logging.error('the number of values in current row is not equal to the number of len.')
        #print('the number of values in current row is not equal to the number of len.') 
        #print('labels:')
        #print(labels)
        #print('current row number of values: ')
        #print(len(valuerow))
        sys.exit(1)
      else:
        logging.error('expect values in dynamic variables as a list. valuerow: ' + str(valuerow))
        sys.exit(1)
    dynamic_variable["variables"] = variable_list
    dynamic_variables.append(dynamic_variable)

def parseJson(json_string):
  parsed_json = (commentjson.loads(json_string))
  
  if 'requests' in parsed_json and isinstance(parsed_json["requests"], list):
    requests_json = parsed_json['requests']
    for request_json in requests_json:
      parsed_request = initiateRequests(request_json)
      the_requests.append(parsed_request)
  if 'static-variable' in parsed_json:
    initiateStaticVariable(parsed_json['static-variable'])
  if 'variables' in parsed_json and isinstance(parsed_json["variables"], list):
    for variable_json in parsed_json["variables"]:
      initiateDynamicVariable(variable_json)

def readFile(filename):
  f = open(filename,"r")
  parseJson(f.read())

def replace_data_with_past_variable(data,required,past_variable):
  if isinstance(data, bool) or isinstance(data, int) or isinstance(data, float):
    return data
  if isinstance(data, str):
    return data.replace("{{"+required+"}}",str(past_variable[required]))  
  if isinstance(data, list):
    for data_index in range(len( data )):
      datum = data[data_index]
      data[data_index] = replace_data_with_past_variable(datum,required,past_variable)
    return data
  for datakey in data: 
    if data[datakey] is not None:
      if isinstance(data[datakey], dict):
        data[datakey] = replace_data_with_past_variable(data[datakey],required,past_variable)
      elif isinstance(data[datakey], list):
        for data_index in range(len( data[datakey] )):
          datum = data[datakey][data_index]
          data[datakey][data_index] = replace_data_with_past_variable(datum,required,past_variable)
      elif isinstance(data[datakey], str): 
        data[datakey] = data[datakey].replace("{{"+required+"}}",str(past_variable[required]))  
  return data
    


async def process_request(thread_id, idlock, finishlock, requests_list):
  process_id = 0
  global process_id_sequence, result_records
  global request_processed, max_request_processed, last_milestone_request_processed
  global temp_total_duration, temp_min_duration, temp_max_duration, temp_per_request, temp_per_ok_request

  # await asyncio.sleep(random.randint(4,14))
  async with idlock:
    process_id = process_id_sequence
    process_id_sequence += 1

  if process_id >= max_request_processed:
    return
  the_request_row = requests_list[process_id]
  results_per_request = []
  results = []
  async with httpx.AsyncClient() as session_requests:
  #with requests.session() as session_requests:
    request_index = 0;
    starttime = datetime.now(tz=jakartatz)
    originalstarttime = starttime
    past_variable = {}

    #logging.debug("original start time: " + str( originalstarttime ))
    for the_request in the_request_row:
      #print("current request_index: " + str(request_index))

      if request_index > 0:
        past_request = the_request_row[request_index - 1]
        if past_request.is_prerequisite:
          starttime = datetime.now(tz=jakartatz) #don't add the duration of previous request into final calculation

        if the_request.required is not None:
          #logging.debug("Request.required is not none. " + str(the_request.required))
          #logging.debug("past_variable: " + str(past_variable))
          logging.debug("the request.required")
          logging.debug(the_request.required)
          if len( the_request.required ) > len( past_variable ):
            logging.debug("past variables: " + str(past_variable))
            logging.debug("required : " + str(the_request.required))
            logging.error("lenn required: " + str( len(the_request.required) ) + " > len past_variable: "+ str(len(past_variable)) )
            break
          
          for required in the_request.required:
            if required in past_variable:
              if the_request.header is not None:
                for headerkey in the_request.header:
                  the_request.header[headerkey] = the_request.header[headerkey].replace("{{"+required+"}}",str(past_variable[required]))
              if the_request.url is not None:
                the_request.url = the_request.url.replace("{{"+required+"}}",str(past_variable[required]))
              if the_request.data is not None:
                the_request.data = replace_data_with_past_variable(the_request.data, required,past_variable)


    
      method=the_request.method
      url=the_request.url
      header=the_request.header
      data=the_request.data
      files=the_request.files
          
      startrequesttime = datetime.now(tz=jakartatz)

      if method == "POST":
        result = None
        try:
          binary_files = None
          if files is not None:
            binary_files = []
            for curr_file in files:
              temp_file_value = (curr_file['field-name'],(curr_file['file-name'],open(curr_file['file-name'],'rb'),curr_file['content-type']))
              binary_files.append(temp_file_value)
          if data is None and binary_files is None:
            result = await session_requests.post(
                url,
                headers = header,
                timeout = timeout
                )
          elif data is None:
            result = await session_requests.post(
              url,
              headers = header,
              files = binary_files,
              timeout = timeout
              )
          elif binary_files is None:
            result = await session_requests.post(
              url,
              json = data,
              headers = header,
              timeout = timeout
              )
          else:
            result = await session_requests.post(
              url,
              json = data,
              files = binary_files,
              headers = header,
              timeout = timeout
              )
            #print(result.text)
          if binary_files is not None:
            for individual_file_info in binary_files:
              if individual_file_info is not None:
                for file_info in individual_file_info:
                  if isinstance(file_info, tuple):
                    for file_data in file_info:
                      if(isinstance(file_data,io.BufferedReader)):
                        file_data.close()
        except httpcore._exceptions.ReadTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectError:
          result = httpx._models.Response(status_code = 900, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ProtocolError as e: 
          logging.error("Protocol Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.WriteError as e: 
          logging.error("Write Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 409, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ReadError as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Read Error. Set response code to 452. url = " + url )
          result = httpx._models.Response(status_code = 452, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpx._exceptions.ConnectTimeout as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Connection Time Out Error.  Set response code to 453 : url = " + url)
          result = httpx._models.Response(status_code = 453, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except h11._util.LocalProtocolError as e:
          logging.error("Local Protocol Error. ", exc_info=True)
          logging.info("LocalProtocolError.  Set response code to 454 : url = " + url)
          try:
            if e.message is not None:
              logging.info("error message: " + e.message)
          except:
            logging.info("Failed get info from LocalProtocolError.")
          try:
            if result is not None:
              logging.debug("Result: ")
              logging.debug(result)
            else:
              logging.debug("Result is None when LocalProtocolError")
          except:
            logging.info("Failed when get Result information when handling LocalProtocolError")
          result = httpx._models.Response(status_code = 454, request = httpx._models.Request(method=method, url=url) )
          result.close()
      elif method == "OAUTH2_LOGIN":
          try:
            result = await session_requests.post(
              url,
              files={"grant_type":(None,"password")},
              data = data,
              headers = header,
              timeout = timeout
              )
          except httpcore._exceptions.ReadTimeout:
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpcore._exceptions.ConnectTimeout:
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpcore._exceptions.ConnectError:
            result = httpx._models.Response(status_code = 900, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpcore._exceptions.ProtocolError as e: 
            logging.error("Protocol Error. ", exc_info=True)
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpcore._exceptions.WriteError as e: 
            logging.error("Write Error. ", exc_info=True)
            result = httpx._models.Response(status_code = 409, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpcore._exceptions.ReadError as e: 
            logging.error("Read Error. ", exc_info=True)
            logging.info("Read Error. Set response code to 452. url = " + url )
            result = httpx._models.Response(status_code = 452, request = httpx._models.Request(method=method, url=url) )
            result.close()
          except httpx._exceptions.ConnectTimeout as e: 
            logging.error("Read Error. ", exc_info=True)
            logging.info("Connection Time Out Error.  Set response code to 453 : url = " + url)
            result = httpx._models.Response(status_code = 453, request = httpx._models.Request(method=method, url=url) )
            result.close()
      elif method == "PUT":
        try:
          if data is None:
            result = await session_requests.put(
                url,
                headers = header,
                timeout = timeout
                )
          else:
            result = await session_requests.put(
              url,
              json = data,
              headers = header,
              timeout = timeout
              )
        except httpcore._exceptions.ReadTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectError:
          result = httpx._models.Response(status_code = 900, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ProtocolError as e: 
          logging.error("Protocol Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.WriteError as e: 
          logging.error("Write Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 409, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ReadError as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Read Error. Set response code to 452. url = " + url )
          result = httpx._models.Response(status_code = 452, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpx._exceptions.ConnectTimeout as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Connection Time Out Error.  Set response code to 453 : url = " + url)
          result = httpx._models.Response(status_code = 453, request = httpx._models.Request(method=method, url=url) )
          result.close()
      elif method == "GET":
        try:
          if data is None:
            result = await session_requests.get(
              url,
              headers = header,
              timeout = timeout
              )
          else:
            result = await session_requests.get(
              url,
              data = data,
              headers = header,
              timeout = timeout
              )
        except httpcore._exceptions.ReadTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectTimeout:
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ConnectError:
          result = httpx._models.Response(status_code = 900, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ProtocolError as e: 
          logging.error("Protocol Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.WriteError as e: 
          logging.error("Write Error. ", exc_info=True)
          result = httpx._models.Response(status_code = 409, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpcore._exceptions.ReadError as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Read Error. Set response code to 452. url = " + url )
          result = httpx._models.Response(status_code = 452, request = httpx._models.Request(method=method, url=url) )
          result.close()
        except httpx._exceptions.ConnectTimeout as e: 
          logging.error("Read Error. ", exc_info=True)
          logging.info("Connection Time Out Error.  Set response code to 453 : url = " + url)
          result = httpx._models.Response(status_code = 453, request = httpx._models.Request(method=method, url=url) )
          result.close()
      else:
        logging.error("Bukan Post ataupun Get. Apa ini?" + method)
        logging.info("Bukan Post ataupun Get. Apa ini ?" + method)
        result = httpx._models.Response(status_code = 405, request = httpx._models.Request(method=method, url=url) )
        result.close()
      endrequesttime = datetime.now(tz=jakartatz)
      durationrequest = endrequesttime - startrequesttime

      result_per_request = ResultPerRequest(startrequesttime, endrequesttime, durationrequest, the_request, result)
      results_per_request.append(result_per_request)

      if the_request.extract is not None: 
        for curr_extract in the_request.extract:
          expected_response_type = the_request.expected_response_type 
          if result.status_code != 200:
            logging.debug("cannot extract from status code: " + str(result.status_code))
            break
          if expected_response_type is not None and expected_response_type == "json":
            #logging.debug("extracting")
            #logging.debug("past_result_per_request: " + str(past_result_per_request))
            if result_per_request.result.text is None or result_per_request.result.text == "":
              logging.error("No variable could be extracted")
              break
            datapath_expr =  jsonpath_ng.parse(curr_extract["datapath"])
            #logging.debug("parsing datapath: " + curr_extract["datapath"])
            #logging.debug(datapath_expr)
            parsed_result_json = None
            try:
              parsed_result_json = json.loads(result_per_request.result.text)
            except RecursionError as re: 
              logging.info("last result text befor parsed error:" + str(result_per_request.result.text))
              logging.error("Error when parsed result_per_request.result.text",exc_info=True)
              break
            #logging.debug(parsed_result_json)
            for match in datapath_expr.find(parsed_result_json):
              past_variable[ curr_extract["mapped-variable"] ] = match.value
              #logging.debug("extract to past_variable[" + curr_extract["mapped-variable"] + "]")
          if expected_response_type is not None and expected_response_type == "int":              
            try:
              past_variable[ curr_extract["mapped-variable"] ] = str( int(result_per_request.result.text) )
            except:
              past_variable[ curr_extract["mapped-variable"] ] = "-9999999"


      async with finishlock:
        if len(temp_per_request) == request_index:
          curr_temp_per_request = {}
          curr_temp_per_request["total_duration"] = timedelta(microseconds=0)
          curr_temp_per_request["min_duration"] = timedelta.max
          curr_temp_per_request["max_duration"] = timedelta.min
          curr_temp_per_request["num_of_request"] = 0
          temp_per_request.append(curr_temp_per_request)

        if len(temp_per_ok_request) == request_index:
          curr_temp_per_ok_request = {}
          curr_temp_per_ok_request["total_duration"] = timedelta(microseconds=0)
          curr_temp_per_ok_request["min_duration"] = timedelta.max
          curr_temp_per_ok_request["max_duration"] = timedelta.min
          curr_temp_per_ok_request["num_of_request"] = 0
          temp_per_ok_request.append(curr_temp_per_ok_request)


        curr_temp_per_request = temp_per_request[request_index]
        curr_temp_per_request["total_duration"] += durationrequest
        if curr_temp_per_request["min_duration"] >  durationrequest:
          curr_temp_per_request["min_duration"] = durationrequest
        if curr_temp_per_request["max_duration"] < durationrequest:
          curr_temp_per_request["max_duration"] = durationrequest
        curr_temp_per_request["num_of_request"] += 1

        curr_temp_per_ok_request = temp_per_ok_request[request_index]
        if result is not None and result.status_code == 200:
          curr_temp_per_ok_request["total_duration"] += durationrequest
          if curr_temp_per_ok_request["min_duration"] >  durationrequest:
            curr_temp_per_ok_request["min_duration"] = durationrequest
          if curr_temp_per_ok_request["max_duration"] < durationrequest:
            curr_temp_per_ok_request["max_duration"] = durationrequest
          curr_temp_per_ok_request["num_of_request"] += 1

        temp_total_duration += durationrequest
        if temp_min_duration > durationrequest:
          temp_min_duration = durationrequest
        if temp_max_duration < durationrequest:
          temp_max_duration = durationrequest
        temp_avg = temp_total_duration / (request_processed if request_processed > 0 else 1 )

        task_info_arr = [
            "task-",
            str(thread_id),
            " --- ",
            str(request_processed),
            " processed .. current duration: ",
            str(durationrequest),
            " timelapsed: ",
            str((datetime.now(tz=jakartatz) - start_all_process_timestamp).total_seconds()),
            " timestamp: ",
            str(datetime.now(tz=jakartatz))
          ]

        logging.debug("".join(task_info_arr))
        temp_duration_arr = [
          "ALL REQUEST total duration[",str( temp_total_duration.total_seconds()),
          "] min duration [",str(temp_min_duration.total_seconds()),
          "] max duration [",str(temp_max_duration.total_seconds()),
          "] avg duration [",str(temp_avg.total_seconds()),"]",
          " timestamp [",str(datetime.now(tz=jakartatz)),"]"
          ]

        logging.debug("".join(temp_duration_arr))
        temp_duration_per_request_arr = [
          "CURRENT REQUEST ",url,
          " num of request[",str(curr_temp_per_request["num_of_request"]), 
          "] total duration[",str(curr_temp_per_request["total_duration"].total_seconds()), 
          "] min duration [",str(curr_temp_per_request["min_duration"].total_seconds()),
          "] max duration [",str(curr_temp_per_request["max_duration"].total_seconds()), 
          "] avg duration [",str((curr_temp_per_request["total_duration"] / (curr_temp_per_request["num_of_request"] if curr_temp_per_request["num_of_request"] > 0 else 1) ).total_seconds()),"]",
          " timestamp [",str(datetime.now(tz=jakartatz)),"]"
          ]

        logging.debug("".join(temp_duration_per_request_arr))

        temp_duration_per_ok_request_arr = [
          "CURRENT OK ONLY REQUEST ",url,
          " num of ok request[",str(curr_temp_per_ok_request["num_of_request"]), 
          "] total duration[",str(curr_temp_per_ok_request["total_duration"].total_seconds()), 
          "] min duration [",str(curr_temp_per_ok_request["min_duration"].total_seconds()),
          "] max duration [",str(curr_temp_per_ok_request["max_duration"].total_seconds()), 
          "] avg duration [",str((curr_temp_per_ok_request["total_duration"] / (curr_temp_per_ok_request["num_of_request"] if curr_temp_per_ok_request["num_of_request"] > 0 else 1) ).total_seconds()),"]"
          ]
        logging.debug("".join(temp_duration_per_ok_request_arr) )


      request_index += 1

  endtime = datetime.now(tz=jakartatz)
  duration = endtime - starttime


  async with finishlock:
    request_processed += 1
    result_record = ResultData(starttime, endtime, duration, results_per_request)
    result_records.append(result_record)
    milestone = max_request_processed / milestone_size
    if request_processed - last_milestone_request_processed >= milestone:
      last_milestone_request_processed = request_processed
      logging.info("Progress: " + str(math.ceil(request_processed * 100 / max_request_processed)) + '%')



def replace_variable(the_string, index):
  global the_requests, static_variables, dynamic_variables
  to_replaced = []
  temp_word = []
  opened_1 = False
  opened_2 = False
  closed_1 = False
  
  for the_char in the_string:
    if the_char == '{':
      if not opened_1:
        opened_1 = True
      elif not opened_2:
        opened_2 = True
    elif the_char == '}':
      if opened_2 and not closed_1:
        closed_1 = True
      elif opened_2 and closed_1:
        opened_1 = False
        opened_2 = False
        closed_1 = False
        to_replaced.append(''.join(temp_word))
        temp_word = []
    else:
      if opened_2:
        temp_word.append(the_char)

  for to_replaced_elem in to_replaced:
    replacement = None
    # search in static

    if to_replaced_elem in static_variables:
      the_string = the_string.replace("{{"+to_replaced_elem+"}}",static_variables[to_replaced_elem])
    elif len(dynamic_variables) > 0:
      for potential_dynamic_variable in dynamic_variables:
        if len(potential_dynamic_variable["variables"]) > 0:
          index_dynamic = index % len(potential_dynamic_variable["variables"])
          dynamic_variable = potential_dynamic_variable["variables"][index_dynamic]
          #print("current dynamic variable")
          #print(dynamic_variables)
          if to_replaced_elem in dynamic_variable:
            the_string = the_string.replace("{{"+to_replaced_elem+"}}",dynamic_variable[to_replaced_elem])

  return the_string

def preparing_request():
  requests = []
  global max_request_processed
  last_progress_percentage = 0
  for i in range(max_request_processed):
    request_row=[]
    for the_request in the_requests:
      url=the_request.url
      need_replace_url = re.match(r'(.*){{(.*)}}(.*)', url, re.M)
      if(need_replace_url):
        url = replace_variable(url,i)
      method=the_request.method
      header= copy_dict(the_request.header) #.copy()
      data = None
      files = the_request.files
      expected_response_type=the_request.expected_response_type
      extract=the_request.extract
      required=the_request.required
      is_prerequisite=the_request.is_prerequisite

      if the_request.data is not None:
        data = copy_dict(the_request.data) # .copy()

      # check if header is need to replace
      for headerkey in header:
        need_replace = re.match(r'(.*){{(.*)}}(.*)', header[headerkey], re.M)
        if(need_replace):
          header[headerkey] = replace_variable(header[headerkey], i)

      
      if data is not None:
        for datakey in data:
          if data[datakey] is not None and isinstance(data[datakey], str):
            need_replace = re.match(r'(.*){{(.*)}}(.*)', data[datakey], re.M)
            if(need_replace):
              data[datakey] = replace_variable(data[datakey], i)

      
      currentRequest = RequestEntry(method, url,header, data, files, expected_response_type, extract, required, is_prerequisite)
      request_row.append(currentRequest)

    requests.append(request_row)
    progress = math.ceil(i * 100 / max_request_processed)
    if 10 <= progress - last_progress_percentage:
      logging.info("preparing progress: " + str(progress) + '%')
      last_progress_percentage = progress

  return requests
    

def print_result_records():
  logging.debug("calculate average, success, etc")
  end_all_process_timestamp = datetime.now(tz=jakartatz)
  total_duration = timedelta(microseconds=0)
  min_duration = timedelta.max
  max_duration = timedelta.min
  num_of_ok_response = 0
  num_of_error_response = 0
  status_dict = {}
  status_per_request_dict = {}
  durations_per_request = []
  durations_per_ok_request = []

  number_of_expected_complete_request = len(the_requests)
  number_of_expected_test_request = 0
  for row_request in the_requests:
    if row_request.is_prerequisite == False:
      number_of_expected_test_request += 1
  number_of_test = len(result_records)
  number_of_incomplete_test = 0
  number_of_expected_request = 0
  number_of_error_request = 0
  
  for result_record in result_records:
    print(result_record)
    total_duration = total_duration + result_record.duration
    if result_record.duration < min_duration:
      min_duration = result_record.duration
    if result_record.duration > max_duration:
      max_duration = result_record.duration
    num_of_complete_request = len(result_record.results_per_request)
    if num_of_complete_request < number_of_expected_complete_request:
      number_of_incomplete_test += 1
    num_of_ok_request_in_test = 0
    for result_per_request_idx in range(num_of_complete_request):
      result_per_request = result_record.results_per_request[result_per_request_idx]
      if result_per_request_idx == len(durations_per_request):
        curr_durations_per_request = {}
        curr_durations_per_request["total_duration"] = timedelta(microseconds=0)
        curr_durations_per_request["min_duration"] = timedelta.max
        curr_durations_per_request["max_duration"] = timedelta.min
        curr_durations_per_request["num_request"] = 0
        durations_per_request.append( curr_durations_per_request )
        curr_durations_per_ok_request = {}
        curr_durations_per_ok_request["total_duration"] = timedelta(microseconds=0)
        curr_durations_per_ok_request["min_duration"] = timedelta.max
        curr_durations_per_ok_request["max_duration"] = timedelta.min
        curr_durations_per_ok_request["num_request"] = 0
        durations_per_ok_request.append(curr_durations_per_ok_request)



      duration_per_request = durations_per_request[result_per_request_idx]
      duration_per_request["total_duration"] = duration_per_request["total_duration"] + result_per_request.duration
      if result_per_request.duration < duration_per_request["min_duration"]:
        duration_per_request["min_duration"] = result_per_request.duration
      if result_per_request.duration > duration_per_request["max_duration"]:
        duration_per_request["max_duration"] = result_per_request.duration
      duration_per_request["num_request"] += 1



      if result_per_request.result is not None:
        result = result_per_request.result
        if result.status_code == 200:
          num_of_ok_response += 1
        else:
          num_of_error_response += 1
        current_status_code = '' + str(result.status_code)
        if current_status_code  in status_dict:
          status_dict[current_status_code] += 1
        else:
          status_dict[current_status_code] = 1
        
        current_status_code_per_request = str(result.status_code) + " of request[" + str(result_per_request_idx) + "] "
        if current_status_code_per_request  in status_per_request_dict:
          status_per_request_dict[current_status_code_per_request] += 1
        else:
          status_per_request_dict[current_status_code_per_request] = 1

        if result.status_code == 200 :
          #num_of_ok_request_in_test += 1
          if result_per_request.request.is_prerequisite == False:
            num_of_ok_request_in_test += 1
          curr_durations_per_ok_request = durations_per_ok_request[result_per_request_idx]
          curr_durations_per_ok_request["total_duration"] += result_per_request.duration
          if result_per_request.duration < curr_durations_per_ok_request["min_duration"]:
            curr_durations_per_ok_request["min_duration"] = result_per_request.duration
          if result_per_request.duration > curr_durations_per_ok_request["max_duration"]:
            curr_durations_per_ok_request["max_duration"] = result_per_request.duration
          curr_durations_per_ok_request["num_request"] += 1

    num_of_error_request = number_of_expected_test_request - num_of_ok_request_in_test
    number_of_error_request += num_of_error_request
    number_of_expected_request += number_of_expected_test_request #number_of_expected_complete_request
    

  avg_duration = total_duration / len(result_records)


  logging.info("Finished/interrupted after " + str((end_all_process_timestamp - start_all_process_timestamp).total_seconds()) )
  logging.info("Start at " + str(start_all_process_timestamp))
  logging.info("End at " + str(end_all_process_timestamp))
  logging.info("Number of Request    : " + str(static_variables['num-of-request']))
  logging.info("Number of concurrent at a time: " + str(static_variables['num-of-concurrent-request']))

  logging.info("total duration (in s): " + str(total_duration.total_seconds()))
  logging.info("min duration   (in s): " + str(min_duration.total_seconds()))
  logging.info("max duration   (in s): " + str(max_duration.total_seconds()))
  logging.info("avg duration   (in s): " + str(avg_duration.total_seconds()))
  logging.info("num_of_ok_response    : " + str(num_of_ok_response))
  logging.info("num_of_error_response : " + str(num_of_error_response))
  logging.info("".join(["num_of_incomplete_test: ",str(number_of_incomplete_test)," ( ",str(( (number_of_incomplete_test * 100) / number_of_test ))," % )"]) )
  logging.info("".join(["num_of_error          : ",str(number_of_error_request)," ( ",str(( (number_of_error_request * 100) / number_of_expected_request ))," % )"]) )
  for curr_status_dict in status_dict:
    logging.info("num of status " + curr_status_dict + " : " + str(status_dict[curr_status_dict]))
  logging.info(" ----- statistic per request --------- ")
  for duration_idx in range(len(durations_per_request)):
    logging.info(" ----- statistic of request ["+ str(duration_idx) +"]--------- ")
    logging.info("url                  : " + str(the_requests[duration_idx].url))
    logging.info("is_prerequisite      : " + str(the_requests[duration_idx].is_prerequisite))
    request_duration = durations_per_request[duration_idx]
    request_avg_duration = request_duration["total_duration"] / request_duration["num_request"]
    logging.info("total duration (in s): " + str(request_duration["total_duration"].total_seconds()))
    logging.info("min duration   (in s): " + str(request_duration["min_duration"].total_seconds()))
    logging.info("max duration   (in s): " + str(request_duration["max_duration"].total_seconds()))
    logging.info("avg duration   (in s): " + str(request_avg_duration.total_seconds()))
    ok_request_duration = durations_per_ok_request[duration_idx]
    ok_request_avg_duration = timedelta.min
    if ok_request_duration["num_request"] != 0 :
      ok_request_avg_duration = ok_request_duration["total_duration"] / ok_request_duration["num_request"]
    logging.info("total duration of ok request (in s): " + str(ok_request_duration["total_duration"].total_seconds()))
    logging.info("min duration   of ok request (in s): " + str(ok_request_duration["min_duration"].total_seconds()))
    logging.info("max duration   of ok request (in s): " + str(ok_request_duration["max_duration"].total_seconds()))
    logging.info("avg duration   of ok request (in s): " + str(ok_request_avg_duration.total_seconds()))
  
  for curr_status_dict in sorted(status_per_request_dict.keys()):
    logging.info("".join(["num of status ",curr_status_dict," : ",str(status_per_request_dict[curr_status_dict])," ( ",str(( (status_per_request_dict[curr_status_dict] * 100) / number_of_test ))," % )"]))


async def async_request(num_of_loop, num_of_concurrent):
  logging.debug("async request with num of loop: " + str(num_of_loop) + " num of concurrent: " + str(num_of_concurrent))
  global max_request_processed, request_processed,result_records, start_all_process_timestamp
  requests = preparing_request()
  idlock = asyncio.Lock()
  finishlock = asyncio.Lock()

  start_all_process_timestamp = datetime.now(tz=jakartatz)
  for i in range(num_of_loop):
    asyncloop = [asyncio.create_task(process_request(i, idlock, finishlock, requests)) for i in range(num_of_concurrent)]
    await asyncio.gather(*asyncloop)

  print_result_records()



def start_process():
  logging.info("process_request")
  global max_request_processed
  if 'num-of-request' in static_variables:
    max_request_processed = static_variables['num-of-request']
  if 'num-of-concurrent-request' in static_variables:
    num_of_loop = max_request_processed / static_variables['num-of-concurrent-request']
    asyncio.run(async_request(math.ceil(num_of_loop),static_variables['num-of-concurrent-request']))
  else:
    asyncio.run(async_request(max_request_processed,1))

  

def process(config):
  for configFile in config:
    try:
      readFile(configFile)
    except FileNotFoundError:
      logging.info("Cannot find file " + configFile)
      sys.exit(1)
  start_process()
  #logging.debug("dynamic variables size: " + str( len(dynamic_variables) ) )
  #if len(dynamic_variables)  > 0:
  #  for variable_row in dynamic_variables:
  #    logging.debug("{")
  #    for label in variable_row :
  #      keypair = [label, ":", str( variable_row[label] )]
  #      logging.debug("".join(keypair))
  #    logging.debug("}")
  

def sigint_handler(signum, frame):
  logging.info("Program interrupted... ")
  if len(result_records) > 1 :
    logging.info("There has been a few result.")
    print_result_records()
  else:
    logging.info("No result yet.")
  sys.exit(1)

def main():
  parser = MyParser(description='Performance Test of Web Request.')
  #parser = argparse.ArgumentParser(description='Performance Test of Web Request.')
  parser.add_argument("-c","--config",action='append', help="file configuration in JSON format")
  args = parser.parse_args()
  if args.config is None:
    parser.print_help(sys.stderr)
    sys.exit(1)
  logging.info(args)
  logging.info(len(args.config))
  process(args.config)

signal.signal(signal.SIGINT, sigint_handler)
main()


