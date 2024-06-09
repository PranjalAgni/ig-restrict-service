import json
import os
from dotenv import load_dotenv
from instagram_private_api import Client
from instagram_private_api.compat import compat_pickle

# Load environment variables from .env file
load_dotenv()

api = None

def file_get_contents(path, flags, is_json=False):
  if os.path.exists(path):
      f = open(path, flags)
      output = f.read()
      f.close()
      if is_json:
          return json.loads(output)
      return compat_pickle.loads(output)
  return None

def file_put_contents(path, flags, content, is_json=False):
  f = open(path, flags)
  if is_json:
      f.write(json.dumps(content, indent=4))
  else:
      f.write(compat_pickle.dumps(content))
  f.close()

def blocked_users():
  global api
  blocked_list = []
  results = api.blocked_user_list()
  for u in results.get("blocked_list", []):
    blocked_list.append(u.get("user_id"))

  return blocked_list

def blocked_from_users():
  global api
  always_hide_from = []
  results = api.blocked_reels()

  for u in results.get("users", []):
    always_hide_from.append(u.get("pk"))

  return always_hide_from

def followers():
  global api
  followers_list = []
  rank_token = api.generate_uuid()
  results = api.user_followers(api.authenticated_user_id, rank_token)

  times = 1
  followers_list.extend(results.get('users', []))
  next_max_id = results.get('next_max_id')
  while next_max_id and len(followers_list) <= 600:
    results = api.user_followers(api.authenticated_user_id, rank_token, max_id=next_max_id)
    followers_list.extend(results.get('users', []))
    next_max_id = results.get('next_max_id')
    times += 1

  print("times api called = ", times)
  print("Total followers =", len(followers_list))
  print("Everyone: ", followers_list)
  for i in range(len(followers_list)):
     followers_list[i] = followers_list[i].get("pk")
  
  return followers_list

def fetcher():
  followers_list = followers()
  always_hide_from = blocked_from_users()
  blocked_list = blocked_users()

  return followers_list, always_hide_from, blocked_list

def hide_all(to_hide_ids):
  global api
  api.set_reel_block_status(to_hide_ids, 'block')
  print("All your followers can not see your stories anymore.")

def unhide_all(to_unhide_ids, always_hide_from):
  global api
  unhide_ids = [id for id in to_unhide_ids if id not in always_hide_from]
  api.set_reel_block_status(unhide_ids, 'unblock')
  print("All your followers can see your stories now.")

def main(username, password):
  global api
  auth_filename = "{}-auth.bin".format(username)
  meta_filename = "{}-meta.json".format(username)
  try:
    api = Client(None, None, settings=file_get_contents(auth_filename, "rb"))
    print("Using persisted session ✅")
  except:
    if os.path.exists(auth_filename):
      os.remove(auth_filename)

    api = Client(username, password)

  # save the session
  if os.path.exists(auth_filename) == False:
    file_put_contents(auth_filename, "wb", api.settings)

  # fetch and store the metadata about followers
  # this is the fetcher only call it if you are running it for the first time or want to refresh the data, as too many api calls can block your account
  if os.path.exists(meta_filename) == False:
    followers_list, always_hide_from, blocked_list = fetcher()
    # store it to meta.json
    file_put_contents(meta_filename,"w", {
      "followers": followers_list,
      "always_hide_from": always_hide_from,
      "blocked_users": blocked_list
    }, True)
  else:
    print("Reusing persisted metadata")

  metadata = file_get_contents(meta_filename, 'r', True)
  for key in metadata.keys():
    print("Count {} = {}".format(key, len(metadata.get(key, []))))
  
  # hide_all(to_hide_ids=metadata.get("followers", []))
  # unhide_all(to_unhide_ids=metadata.get("followers", []), always_hide_from=metadata.get("always_hide_from", []))

user_name = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")

main(username=user_name, password=password)