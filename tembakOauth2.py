# -----------------------------------------------------------
# Tembak Oauth2.0
# 
# usage: 
# define the variable of filenamesource, fileoutput, filetemp,
# and num_of_concurrent_process
# Filename source is a file containing json which contain list of
#   username and password
#
#   for example:
#   { "users" = [{"username":"User Oneng", "password":"p4ssw0rd"},
#                {"username":"User Twong", "password":"P566w0rd"}
#               ]
#   }
#
# (C) 2020 Narpati Wisjnu Ari Pradana, Jakarta, Indonesia
# -----------------------------------------------------------

#import requests
import httpx
import httpcore
#import re
from datetime import timedelta
from datetime import datetime
from datetime import timezone
import asyncio
import argparse
import sys
import json
import commentjson
import math
#import jsonpath_ng
import logging
import random
import signal
import filelock 
import os
import base64

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)
filenamesource = "configLengkap.json"
fileoutput = "payloadTokenUsername.json"
filetemp = "tempPayloadTokenUsername.json"
filetemplock = filetemp + ".lock"
num_of_concurrent_process = 100
timeout = httpx.Timeout(60.0, connect_timeout=30)


client_id="project-api-client"
client_secret="project-secret"

oauth_url = "https//domain.project.to/oauth/token"


def complete():
  token_and_usernames = []
  try:
    with writelock.acquire(timeout=10):
      w_file = open(filetemp,"r")
      temp = w_file.read().rstrip(",")
      current_string = []
      in_data = False
      for the_char in temp:
        if not in_data and the_char == '[':
          in_data = True
          current_string = ["["]
        elif in_data and the_char == ']':
          current_string.append("]")
          #logging.error("current string: ".join(current_string))
          token_and_usernames.append( commentjson.loads("".join(current_string)) )
          current_string = []
          in_data = False
        elif in_data:
          current_string.append(the_char)
      
      #for line in temp.split(','):
      #  logging.error(line)
      #  token_and_usernames.append(commentjson.loads(line))
      #token_and_usernames = commentjson.loads(temp)
      w_file.close()
  except filelock.Timeout:
    logging.error("Timeout when re-read temp file")

  result = {}
  result["version"] = 1
  result["variables"] = []
  variable = {}
  result["variables"].append(variable)
  variable["names"] = ["token","username"]
  variable["values"] = token_and_usernames

  w_file = open(fileoutput,"w")
  w_file.write( str( result ).replace("'","\"") )
  w_file.close()

  logging.info("Finished writing token for " + str(len(token_and_usernames)) + " users.")


def sigint_handler(signum, frame):
  logging.info("Program interrupted... ")
  if os.path.exists(filetemp):
    logging.info("Temp file has been created. Creating result.... ")
    complete()
  else:
    logging.info("No result yet.")
  os.sys.exit(1)

async def get_token_oauth2_session(username, password, user_idx):
  
  try:
    #pid = os.fork()
    #if pid == 0: #the child
    #  try:
        async with httpx.AsyncClient() as session_requests:
          try:
            
            #data = {"username":username,"password":password,"grant_type":"password"}
            #data = [("username",username),("password",password),("grant_type","password")]
            #data = []
            #data = "".join([
            #  "username=",username,"&",
            #  "password=",password,"&",
            #  "grant_type=password"#,"&",
            #  #"scope=read+write"
            #  ])
            client_str = "".join([client_id,":",client_secret])
            client_str_encoded = client_str.encode("ascii")
            encoded_client_secret = base64.b64encode(client_str_encoded)
            #logging.debug("encoded_client_secret: " + encoded_client_secret.decode("ascii"))
            basic_authorization = "Basic "+ encoded_client_secret.decode("ascii")
            header={"Authorization":basic_authorization, 
              #"Content-Type": "multipart/form-data"
              #"Content-type": "application/x-www-form-urlencoded"
              #"Content-type": "multipart/form-data"
              #"Content-type": "multipart/form-data; boundary=------------------------097633407ba4be92"
              }
            result = await session_requests.post(
                #"http://localhost:8765",
                oauth_url,
                #files={"dummy":(None, 'content')},
                files={
                  "grant_type":(None,"password")
                },
                data = { 
                  "username": username,
                 "password": password
                },
                #data=data,
                headers = header,
                timeout = timeout
                )
            #logging.debug("get result.")
            #for res_attr, res_value in result.__dict__.items():
            #  logging.debug(res_attr + " : " +  str(res_value))
            #logging.debug("request")
            #for req_attr, req_value in result.request.__dict__.items():
            #  logging.debug(req_attr + " : " + str(req_value))
            if result.status_code == 200:
              json_text = result.text
              #logging.debug(result.text)
              token = commentjson.loads(json_text)
              result.close()
            else:
              logging.error("Error obtaining token for username: " + username)
              #logging.error("data which are error: " + str(data))
              logging.error("header: " + str(header))
              result.close()
              return
          except httpcore._exceptions.ReadTimeout:
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method="POST", url=oauth_url) )
            result.close()
            return
          except httpcore._exceptions.ConnectTimeout:
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method="POST", url=oauth_url) )
            result.close()
            return
          except httpcore._exceptions.ConnectError:
            result = httpx._models.Response(status_code = 900, request = httpx._models.Request(method="POST", url=oauth_url) )
            result.close()
            return
          except httpcore._exceptions.ProtocolError as e: 
            logging.error("Protocol Error. ", exc_info=True)
            result = httpx._models.Response(status_code = 408, request = httpx._models.Request(method="POST", url=oauth_url) )
            result.close()
            return
          except httpcore._exceptions.WriteError as e: 
            logging.error("Write Error. ", exc_info=True)
            result = httpx._models.Response(status_code = 409, request = httpx._models.Request(method="POST", url=oauth_url) )
            result.close()
            return

        

        pair = []
        pair.append(token["access_token"])
        pair.append(username)
        writelock = filelock.FileLock(filetemplock)
        try:
          with writelock.acquire(timeout=10):
            w_file = open(filetemp,"a")
            single_quote_pair = str(pair)
          
            w_file.write(single_quote_pair.replace("'","\"") + ",")
            w_file.close()
        except filelock.Timeout:
          logging.error("Timeout when writing temp file")
      #except oauthlib.oauth2.rfc6749.errors.InvalidGrantError:
      #  logging.error("invalid")
    #  except ValueError: 
    #    logging.error("ValueError whatever")
    #  exit()
    #else:
    #  os.waitpid(pid,0)
  except OSError:
    logging.error("OS Error when forking")



async def iterate_user(users):
  logging.info("iterate_users")
  #idlock = asyncio.Lock()
  finishlock = asyncio.Lock()

  num_of_users = len(users)
  num_of_loop = math.ceil(num_of_users / num_of_concurrent_process)
  for i in range(0, num_of_loop):
    start_index = i * num_of_concurrent_process
    end_index = ((i + 1) * num_of_concurrent_process)
    logging.debug("start: " + str(start_index) + "  --- end: " + str(end_index) )
    asyncloop = []
    for user_idx in range(start_index, end_index):
      if user_idx < num_of_users:
        userdata = users[user_idx]
        asyncloop.append(asyncio.create_task(get_token_oauth2_session(userdata["username"],userdata["password"], user_idx)))
    await asyncio.gather(*asyncloop)


writelock = filelock.FileLock(filetemplock)
try:
  with writelock.acquire(timeout=10):
    if os.path.exists(filetemp):
      os.remove(filetemp)
except filelock.Timeout:
  logging.error("Timeout when delete temp file")

signal.signal(signal.SIGINT, sigint_handler)
f = open(filenamesource,"r")
parsed_json = (commentjson.loads(f.read()))
f.close()
#users = []

#for i in range(0,100):
#  a = {}
#  a["username"] = "85778762542@dbone"
#  a["password"] = "password"
#  users.append(a)
#asyncio.run(iterate_user(users))
#iterate_user(users)
asyncio.run(iterate_user(parsed_json["users"]))



complete()


