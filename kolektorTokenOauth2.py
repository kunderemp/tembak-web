# -----------------------------------------------------------
# Collecting token from Oauth2.0
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

import commentjson
import asyncio
import oauthlib
import math
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient
import filelock 
import os
import signal
import logging


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests_oauthlib.oauth2_session").setLevel(logging.ERROR)
logging.getLogger("filelock").setLevel(logging.ERROR)

filenamesource = "configKornessLengkap.json"
fileoutput = "payloadTokenUsernameTemp.json"
filetemp = "tempPayloadTokenUsername.json"
filetemplock = filetemp + ".lock"
num_of_concurrent_process = 10


client_id="project-api-client"
client_secret="project-secret"



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
    pid = os.fork()
    if pid == 0: #the child
      try:
        logging.debug(user_idx)
        oauth = OAuth2Session(client=LegacyApplicationClient(client_id=client_id))
        #logging.debug("username :" + username)
        #logging.debug("password :" + password)
        #logging.debug("client_id:" + client_id)
        #logging.debug("client_secret:" + client_secret)

        token = oauth.fetch_token(
            token_url='https://project-rahasia.co.id/oauth/token',
            username=username, password=password, client_id=client_id,
            client_secret=client_secret)
        #print(token)
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
      except oauthlib.oauth2.rfc6749.errors.InvalidGrantError:
        logging.error("invalid")
      exit()
    else:
      os.waitpid(pid,0)
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

asyncio.run(iterate_user(parsed_json["users"]))


# yang di-komentar ini hanya untuk keperluan developing
# menggunakan user palsu berulang-ulang bukan membaca dari konfigurasi
#users = []
#
#for i in range(0,100):
#  a = {}
#  a["username"] = "85778762542@dbone"
#  a["password"] = "password"
#  users.append(a)
#asyncio.run(iterate_user(users))
#iterate_user(users)



complete()


